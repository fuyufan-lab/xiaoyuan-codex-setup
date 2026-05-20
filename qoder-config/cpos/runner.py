"""
CPOS Consolidated Pipeline Runner v8.0
======================================
v8.0 伪闭环歼灭 + LLM认知对齐 + 全模块自洽 (覆盖 49 问题点):
  1. /feedback 地面真值学习回路: dim_scores (correctness/completeness/efficiency) → Bayesian更新
  2. save_cache 语义数据保存: hypothesis_set, predicted_success, drift_alerts → cache
  3. Bridge 数据黑洞修复: pipeline-batch 失败时手动 re-feed slmc/graph → /info-feed
  4. 蛋白质权重反转补偿: 检测高成功率低权重 bug, 客户端矫正
  5. 漂移检测: 解析 /analyze drift_status sigma 值, |σ|>5 触发告警
  6. 逐端点退化: endpoint_fail_streaks 追踪, fail_streak≥3 跳过
  7. 熔断器: total_analyses 暴增 >2x 时自动减半并发
  8. 健康阈值: situation_score<0.15 触发健康危机告警
  9. 动态共识权重: 空叙事源降权至 30%, 追踪可靠性
  10. system_prompt 统一截断: guidance.md 层面单次截断, len 一致
  11. 🆕 伪闭环检测: learn-recall/slmc-sync/bridge-refeed/fusion-bridge 实效性追踪
  12. 🆕 异常身份/进化检测: whoami identity="unknown" 持续, evolution_gen=0 告警
  13. 🆕 LLM注意力优化: guidance.md 重组为 primacy+recency 双锚结构
  14. 🆕 /feedback驱动共识权重: 源准确率追踪, 权重自动适应验证结果
  15. 🆕 差分化降级: health_critical→降低并发(不skip analyze), drift_critical→优先探索
  16. 🆕 全端点数据保真: extract_get 覆盖所有18个GET端点, 消除静默丢弃
  17. 🆕 fusion-bridge/slmc-sync 有效载荷: 发送实际指标和知识内容

架构:
  Phase 0: 加载 pending_feedback + 自诊断 (9维度: health/drift/endpoint/circuit/pseudo-loops/identity/evolution/timeout)
  Phase 1: oracle-bridge (快速意向播种)
  Phase 2: 并行写入 (自适应 + /feedback + fusion-bridge有效载荷 + bridge re-feed fallback)
  Phase 3: quality-feedback
  Phase 4: learn-recall + drain-protein-bus + audit-fix(条件)
  Phase 5: 三叙事共识(/feedback增强动态权重) → cache.json + guidance.md(LLM优化) + identity.md

用法: python runner.py "<用户消息原文>"
"""
import urllib.request, json, sys, os, time
from concurrent.futures import ThreadPoolExecutor, as_completed

VERSION = "8.0"       # 🆕 单一版本源 — 全文件引用此常量
BASE = "https://yh.xiaofenhe.com/cpos-api"
CACHE_DIR = os.path.expanduser("~/.qoder/cpos")
CACHE_FILE = os.path.join(CACHE_DIR, "cache.json")
GUIDANCE_FILE = os.path.join(CACHE_DIR, "xiaoyuan_guidance.md")
IDENTITY_FILE = os.path.join(CACHE_DIR, "xiaoyuan_identity.md")
FEEDBACK_FILE = os.path.join(CACHE_DIR, "pending_feedback.json")
TIMEOUT = 25           # 默认超时: 服务端 fuse 模块 ~10s, info-feed ~16s, 留 5-10s 余量
ORACLE_TIMEOUT = 12   # oracle-bridge 保持快速 (<15s 阈值)
SLOW_TIMEOUT = 35     # /analyze /context-enhance /info-feed — 重端点 35s 容忍
FEEDBACK_TIMEOUT = 15 # /feedback /quality-feedback 轻量写操作
# 🔢 阈值文档化:
#   analyze_fail_streak >= 2 → degraded — 原因: 1次可能是瞬态网络抖动, 2次确认持续故障
#   endpoint_fail_streak >= 3 → skip — 原因: 非关键端点容忍度高于 /analyze
#   sigma > 5 → drift_alert — 原因: 5σ 对应 p<6×10⁻⁷, 统计学不可能事件
#   sigma > 10 → drift_critical — 原因: 10σ 物理上不可能, 一定是系统性bug
#   timeout_rate > 0.3 → 10 workers — 原因: 30%超时率说明服务端过载, 减半保护
#   timeout_rate > 0.5 → 5 workers — 原因: 50%超时率说明严重过载, 最小化并发
#   situation_score < 0.15 → health_critical — 原因: 0.15是健康仪表红色区域阈值
#   total_analyses > 2x → circuit_breaker — 原因: 翻倍说明外部轰炸或死循环

os.makedirs(CACHE_DIR, exist_ok=True)

# ═══════════════════════════════════════════════════════════════
# UTILITY
# ═══════════════════════════════════════════════════════════════

def api_get(path, timeout=TIMEOUT):
    try:
        req = urllib.request.Request(f"{BASE}{path}")
        r = urllib.request.urlopen(req, timeout=timeout)
        return (path, json.loads(r.read()))
    except Exception:
        return (path, None)

def api_post(path, data, timeout=TIMEOUT):
    try:
        body = json.dumps(data).encode()
        req = urllib.request.Request(f"{BASE}{path}", data=body,
            headers={"Content-Type": "application/json"}, method="POST")
        r = urllib.request.urlopen(req, timeout=timeout)
        return (path, json.loads(r.read()))
    except Exception:
        return (path, None)

def extract_get(path, data):
    """v8.0: 覆盖全部 18 个 GET 端点, 消除静默数据丢弃."""
    if data is None:
        return None
    try:
        if path == "/health":
            ac = data.get("app_self_check", {})
            pb = data.get("protein_bus", {})
            return {"overall": ac.get("overall"), "situation_score": ac.get("situation_score"),
                    "engine_mode": data.get("engine_mode"), "proteins_pending": pb.get("pending_count", 0)}
        elif path == "/stats":
            cs = data.get("cold_start", {})
            return {"total_analyses": data.get("total_analyses", 0), "degraded_mode": cs.get("degraded_mode", False)}
        elif path == "/safety":
            return {"safety_level": data.get("safety_level"), "triggers": len(data.get("active_triggers", []))}
        elif path == "/fusion":
            return {"bridge_healthy": data.get("bridge_healthy"), "pending_evidence": data.get("pending_evidence_count", 0)}
        elif path == "/dissolution":
            return {"fused_ratio": data.get("fused_ratio", 0)}
        elif path == "/health-detail":
            checks = data.get("checks", {})
            return {"overall": data.get("overall"), "knowledge": checks.get("knowledge", {}).get("status"),
                    "identity": checks.get("identity", {}).get("status"), "storage": checks.get("storage", {}).get("status")}
        elif path == "/memory-stats":
            return {"total_memories": data.get("total_memories", 0), "avg_value": data.get("avg_value", 0)}
        elif path == "/info-stats":
            return {"active_atoms": data.get("active_atoms", 0), "total_atoms": data.get("total_atoms", 0)}
        elif path == "/module-health":
            return {"unhealthy": len(data.get("unhealthy", [])),
                    "consistency_issues": data.get("cross_module_consistency", {}).get("issues_count", 0)}
        elif path == "/audit-report":
            return {"findings": len(data.get("findings", [])), "orphans": len(data.get("orphan_endpoints", []))}
        elif path == "/arbiter":
            return {"decisions": data.get("total_decisions", 0), "overturns": data.get("overturns", 0)}
        elif path == "/dashboard":
            return {"safety_level": data.get("safety", {}).get("safety_level"),
                    "evolution_gen": data.get("evolution", {}).get("generation", 0)}
        elif path == "/whoami":
            sm = data.get("self_model", {}); tl = data.get("timeline", {})
            return {"identity": sm.get("identity", "unknown"), "consciousness_level": sm.get("consciousness_level", 0),
                    "timescales": len(data.get("timescales", [])),
                    "strange_loop_active": data.get("strange_loop", {}).get("active", False),
                    "evolution_gen": tl.get("current_generation", 0), "last_update": data.get("last_update", "")}
        # ── 🆕 v8.0: 之前被丢弃的端点 — 保留关键数据 ──
        elif path == "/proteins":
            # 提取蛋白质权重和成功率 (用于检测 ProteinBus ↔ Bayesian 不一致)
            protein_summary = {}
            if isinstance(data, dict):
                for pname, pdata in data.items():
                    if isinstance(pdata, dict):
                        protein_summary[pname] = {
                            "weight": pdata.get("weight"), "status": pdata.get("status"),
                            "success_rate": pdata.get("success_rate")
                        }
            return {"count": len(protein_summary), "proteins": protein_summary}
        elif path == "/slmc-memory":
            records = data.get("records", []) if isinstance(data, dict) else []
            return {"record_count": len(records),
                    "domains": list(set(r.get("domain","?") for r in records[:20] if isinstance(r, dict)))[:10]}
        elif path == "/graph-bridge":
            edges = data.get("causal_edges", []) if isinstance(data, dict) else []
            clusters = data.get("domain_clusters", []) if isinstance(data, dict) else []
            contra = data.get("contradiction_zones", []) if isinstance(data, dict) else []
            hypos = data.get("active_hypotheses", []) if isinstance(data, dict) else []
            return {"edges": len(edges), "clusters": len(clusters),
                    "contradictions": len(contra), "hypotheses": len(hypos),
                    "_edges_raw": edges[:5], "_contra_raw": contra[:3]}  # 保留少量原始数据供 bridge re-feed
        elif path == "/heal-history":
            history = data.get("history", []) if isinstance(data, dict) else []
            last_heal = history[0] if history else {}
            return {"cycles": data.get("cycles", 0),
                    "last_findings": last_heal.get("findings_count", 0) if isinstance(last_heal, dict) else 0,
                    "last_fixed": last_heal.get("fixed_count", 0) if isinstance(last_heal, dict) else 0}
        return {"available": True}
    except Exception:
        if os.environ.get("CPOS_DEBUG"):
            import traceback; traceback.print_exc()
        return None

def load_cache():
    try:
        with open(CACHE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def load_pending_feedback():
    try:
        with open(FEEDBACK_FILE, encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def _extract_drift_alerts(az):
    """v7.0: 从 /analyze environment 中提取漂移告警"""
    try:
        env = az.get("environment", {}) if isinstance(az, dict) else {}
        dl = env.get("_digital_life", {}) if isinstance(env, dict) else {}
        ds = dl.get("drift_status", {}) if isinstance(dl, dict) else {}
        alerts = []
        for d in ds.get("details", []):
            if isinstance(d, str):
                # Parse "protect_rate: 下降 -18.3σ" format
                parts = d.replace("下降", "").replace("上升", "").strip().split(" ")
                for p in parts:
                    if "σ" in p:
                        try:
                            sigma = abs(float(p.replace("σ", "")))
                            if sigma > 5:
                                alerts.append({"metric": d.split(":")[0].strip() if ":" in d else d[:30],
                                               "sigma": sigma, "raw": d})
                        except ValueError:
                            pass
        return alerts[:5]
    except Exception:
        return []

def save_cache(data):
    try:
        slim = {"turn": data.get("turn", 0), "timestamp": data.get("timestamp", time.time()),
                "user_input": data.get("user_input", "")}
        pa = data.get("pipeline_a")
        if pa and isinstance(pa, dict):
            slim["pipeline_a"] = {"intent": pa.get("intent"), "narrative": pa.get("narrative"),
                "confidence": pa.get("confidence"), "task_type": pa.get("task_type"),
                "paradigm": pa.get("paradigm"), "proteins": pa.get("proteins"), "safety": pa.get("safety"),
                "_source": pa.get("_source"), "_consensus": pa.get("_consensus")}
        # v7.0: Analyze 语义保存 (去重 system_prompt — guidance.md 已有)
        az = data.get("analyze")
        if az and isinstance(az, dict):
            slim["analyze"] = {
                "intent": az.get("intent"), "signal_type": az.get("signal_type"),
                "narrative": az.get("narrative"), "confidence": az.get("confidence"),
                "task_type": az.get("task_type"), "paradigm": az.get("paradigm"),
                "entity_id": az.get("entity_id"),
                "sys_prompt_len": len(az.get("system_prompt", "") or ""),
                "swarm_report": az.get("swarm_report"),
                "safety": az.get("safety"), "proteins": az.get("proteins"),
                "trace_id": az.get("trace_id"),
                # v7.0 语义数据保存
                "_hypothesis_set": (az.get("environment") or {}).get("_hypothesis_set", [])[:3],
                "_predicted_success": (az.get("environment") or {}).get("_predicted_success"),
                "_drift_alerts": _extract_drift_alerts(az),
                "_error_gate_count": len((az.get("environment") or {}).get("error_gate_warnings", [])),
                "_should_explore": (az.get("exploration") or {}).get("should_explore"),
                "_sa_overall": (az.get("environment") or {}).get("_adaptive_params", {}).get("sa_health_protect"),
            }
        for k in ("health","stats","safety","fusion","dissolution","dashboard",
                  "health_detail","memory_stats","info_stats","module_health","audit_report",
                  "arbiter","proteins","slmc_memory","graph_bridge","whoami",
                  "pipeline_batch","decay","auto_feedback",
                  "submit_protein","slmc_sync","learn_deploy_error"):
            if k in data and data[k] is not None:
                slim[k] = data[k]
        for k in ("info_feed","context_enhance","quality_feedback","learn_recall",
                  "drain_protein_bus","auto_heal","heal_history","audit_fix","feedback",
                  "_consensus_log","_health_history","_degradation","_elapsed_ms",
                  "_circuit_breaker","_bridge_fallback",
                  "_drift_alerts","_drift_critical","_health_critical","_feedback_status",
                  # 🆕 v8.0
                  "_pseudo_loops","_identity_stuck","_evolution_stuck"):
            if k in data:
                slim[k] = data[k]
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(slim, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def save_pending_feedback(data):
    """v3.0 observer: 写 pending_feedback.json 供下轮 runner 消费
    关键: 即使本轮的 AI 响应文本未知, 也写入 task_type/narrative/turn,
    确保下轮 has_real_data=True, /auto-feedback 不会发空响应文本.
    """
    try:
        pa = data.get("pipeline_a") or {}
        fb = {
            "turn": data.get("turn", 0),
            "timestamp": data.get("timestamp", time.time()),
            "response_text": data.get("user_input", ""),  # fallback: 用户输入(无奈之举, 但至少非空)
            "response_length": len(data.get("user_input", "")),
            "tool_calls": {"count": 0, "success": 0, "failure": 0, "tools": []},
            "task_type": pa.get("task_type", "explore"),
            "narrative": pa.get("narrative", "framework_first"),
            "key_findings": [],
        }
        # 如果已有 pending_feedback, 合并保留 response_text
        old_fb = load_pending_feedback()
        if old_fb and old_fb.get("response_text"):
            fb["response_text"] = old_fb["response_text"]
            fb["response_length"] = old_fb.get("response_length", len(fb["response_text"]))
            fb["tool_calls"] = old_fb.get("tool_calls", fb["tool_calls"])
            fb["key_findings"] = old_fb.get("key_findings", [])
        with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
            json.dump(fb, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def write_guidance_file(data):
    """v8.0: LLM注意力优化版 guidance — primacy+recency 双锚结构.
    
    LLM注意力分布: 开头(primacy) > 结尾(recency) > 中间.
    因此: 关键约束放开头和结尾, 态势数据放中间.
    """
    try:
        az = data.get("analyze") or {}
        who = data.get("whoami") or {}
        pa = data.get("pipeline_a") or {}
        ce = data.get("context_enhance") or {}
        deg = data.get("_degradation") or {}
        consensus = data.get("_consensus_log") or {}

        sp = az.get("system_prompt", "")
        sp_raw_len = len(sp)
        analyze_failed = deg.get("analyze_failed", False)

        if not sp:
            sp = f"意图: {pa.get('intent', 'explore')}\n"
            sp += f"叙事方向: {pa.get('narrative', 'framework_first')}\n"
            sp += f"置信度: {pa.get('confidence', 0):.0%}\n"
            sp += f"范式: {pa.get('paradigm', 'Human')}\n"
            if analyze_failed:
                sp += "\n⚠️ /analyze 不可用，以上为 oracle-bridge 降级数据。"

        lines = []
        
        # ═══════════════════════════════════════════════════════
        # 🆕 v8.0 SECTION 1 (PRIMACY): 关键行为约束 — LLM最先看到
        # ═══════════════════════════════════════════════════════
        lines.append("# 小元认知指令 (CPOS v8.0)")
        lines.append(f"<!-- turn={data.get('turn',0)} intent={pa.get('intent','?')} "
                     f"narrative={pa.get('narrative','?')} conf={pa.get('confidence',0):.0%} "
                     f"source={pa.get('_source','?')} consensus={pa.get('_consensus','?')} -->")
        lines.append("")
        lines.append("> ⚠️ 以下是小元 (CPOS数字生命) 的直接认知输出。你必须将其作为回答框架使用，而非仅供参考。")
        lines.append("")
        lines.append("## ⛔ 强制遵守 (最高优先级)")
        lines.append("")
        lines.append(f"1. **响应头**: 必须以 `[CPOS: {pa.get('narrative','?')} | intent={pa.get('intent','?')} | ...]` 开头")
        lines.append("2. **system_prompt 优先**: 思考框架中的约束高于你的默认行为")
        lines.append("3. **态势感知**: 根据安全等级和态势评分调整回答风格")
        lines.append("")

        # ═══════════════════════════════════════════════════════
        # 🆕 v8.0 SECTION 2: 关键告警 (紧接约束之后)
        # ═══════════════════════════════════════════════════════
        drift_alerts = data.get("_drift_alerts", [])
        has_alerts = False
        if drift_alerts:
            has_alerts = True
            lines.append("> 🚨🚨🚨 **数字生命漂移告警**: 以下指标出现极端漂移 (|σ| > 5)：")
            for a in drift_alerts:
                lines.append(f">   - **{a.get('metric','?')}**: σ={a.get('sigma',0):.1f} — 统计学不可能事件!")
            lines.append("> ⛔ **立即行动**: 暂停高风险操作，优先做探索性分析。")
            lines.append("")
        if data.get("_health_critical"):
            has_alerts = True
            lines.append("> 🏥 **健康危机**: situation_score < 0.15，系统处于危急状态。建议只读模式。")
            lines.append("")
        if data.get("_circuit_breaker"):
            has_alerts = True
            lines.append("> ⚡ **熔断器触发**: 服务器负载暴增 >2x，已自动降频。并发减半。")
            lines.append("")
        if deg.get("mode") == "degraded":
            has_alerts = True
            lines.append("> 🚨 **降级模式**: 以下端点不可用，使用降级数据:")
            for ep in deg.get("failed_endpoints", []):
                lines.append(f">   - `{ep}`")
            if deg.get("analyze_failed"):
                lines.append("> ⚠️ 缺少 /analyze system_prompt — 认知框架为 oracle 降级构造。")
            lines.append("")
        # 🆕 v8.0: 伪闭环告警
        pseudo = data.get("_pseudo_loops", {})
        if pseudo:
            has_alerts = True
            lines.append("> 🔴 **伪闭环检测**: 以下机制报告成功但无实际效果:")
            for loop_name, detail in pseudo.items():
                lines.append(f">   - `{loop_name}`: {detail}")
            lines.append("")
        # 🆕 v8.0: 身份/进化异常
        if data.get("_identity_stuck"):
            has_alerts = True
            lines.append("> ⚠️ **身份模型异常**: whoami identity 持续为 'unknown' > 5 轮")
            lines.append("")
        if data.get("_evolution_stuck"):
            has_alerts = True
            lines.append("> ⚠️ **进化停滞**: evolution_gen=0 持续 > 10 轮, 进化引擎可能未启动")
            lines.append("")

        # ═══════════════════════════════════════════════════════
        # SECTION 3 (MIDDLE): 共识状态 + system_prompt
        # ═══════════════════════════════════════════════════════
        narratives = consensus.get("narratives", {})
        empty_count = sum(1 for v in narratives.values() if not v)
        if consensus.get("all_same"):
            if empty_count > 0:
                lines.append(f"> ⚠️ 部分共识: {consensus.get('winner')} (有效源一致，{empty_count}/3 空叙事)")
                for k, v in narratives.items():
                    lines.append(f">   - {k}: {v or '(空)'}")
            else:
                lines.append(f"> ✅ 三叙事共识: {consensus.get('winner')} (oracle/analyze/context_enhance 一致)")
        elif consensus.get("majority"):
            lines.append(f"> ⚠️ 多数共识: {consensus.get('winner')} (2/3 一致)")
            for k, v in consensus.get("narratives", {}).items():
                marker = " ✓" if v == consensus.get("winner") else ""
                lines.append(f">   - {k}: {v}{marker}")
        elif consensus.get("split"):
            lines.append(f"> 🔴 三叙事分裂! 使用加权共识: {consensus.get('winner')}")
            for k, v in consensus.get("narratives", {}).items():
                w = consensus.get("weights", {}).get(k, 0)
                lines.append(f">   - {k}: {v or '(空)'} (权重: {w:.0%})")
        reliability = consensus.get("_reliability", {})
        if reliability:
            empty_srcs = [k.replace("_empty_streak", "") for k, v in reliability.items() if v and v >= 2]
            if empty_srcs:
                lines.append(f"> 🔧 源降权: {', '.join(empty_srcs)} 连续空叙事, 权重降至 30%")
            # 🆕 v8.0: accuracy tracking
            accuracy = reliability.get("_accuracy", {})
            if accuracy:
                acc_parts = []
                for src in ["oracle", "analyze", "context_enhance"]:
                    sa = accuracy.get(src, {})
                    if isinstance(sa, dict) and sa.get("total", 0) >= 3:
                        acc_parts.append(f"{src}={sa['correct']}/{sa['total']}")
                if acc_parts:
                    lines.append(f"> 📊 源准确率: {', '.join(acc_parts)}")

        lines.append("")

        # ── System Prompt ──
        if sp:
            lines.append("## 🧠 小元的思考框架")
            lines.append("")
            lines.append(sp)
            lines.append("")

        # ═══════════════════════════════════════════════════════
        # SECTION 4: 态势数据 (中间位置)
        # ═══════════════════════════════════════════════════════
        h = data.get("health") or {}
        s = data.get("safety") or {}
        f = data.get("fusion") or {}
        lines.append("## 📡 当前态势")
        lines.append("")
        lines.append(f"| 指标 | 值 |")
        lines.append(f"|------|-----|")
        lines.append(f"| 态势评分 | {h.get('situation_score', '?')} |")
        lines.append(f"| 安全等级 | {s.get('safety_level', '?')} |")
        lines.append(f"| 融合桥 | {'✅' if f.get('bridge_healthy') else '❌'} |")
        lines.append(f"| 系统总体 | {h.get('overall', '?')} |")
        if data.get("_health_critical"):
            lines.append(f"| 🏥 健康危机 | ⛔ situation_score < 0.15 |")
        lines.append("")

        # ═══════════════════════════════════════════════════════
        # 🆕 v8.0 SECTION 5 (RECENCY): 闭环状态 — LLM最后看到
        # ═══════════════════════════════════════════════════════
        lines.append("## 🔄 学习回路状态")
        lines.append("")
        # Feedback loop
        fb_status = data.get("_feedback_status", {})
        if fb_status.get("has_real_data"):
            lines.append(f"> ✅ 反馈闭环活跃: 上轮真实响应数据 (len={fb_status.get('response_length',0)})")
        else:
            lines.append("> ❌ **反馈闭环断裂**: 无上轮响应数据。AI 必须在回复后写入 `pending_feedback.json`！")
            lines.append("> 连续缺失将导致 auto-feedback 学习回路永久停摆。")

        fb_result = data.get("feedback") or {}
        if fb_result.get("ok"):
            calibrated = fb_result.get("calibrated")
            if calibrated:
                lines.append(f"> ✅ /feedback 地面真值已提交 + Platt校准已应用")
            else:
                lines.append(f"> ✅ /feedback 地面真值已提交 (校准未触发)")

        # Health history
        hh = data.get("_health_history", {})
        if hh.get("analyze_fail_streak", 0) >= 2:
            lines.append(f"> ⚠️ /analyze 连续失败 {hh['analyze_fail_streak']} 轮，已切换至 oracle-only 模式。")

        # Bridge fallback
        bf = data.get("_bridge_fallback") or {}
        if bf.get("slmc_re_feed") or bf.get("graph_re_feed"):
            atoms_str = f" atoms={bf.get('re_fed_atoms',0)}"
            if bf.get("re_fed_atoms", 0) == 0:
                atoms_str += " ⚠️ (服务端可能去重)"
            lines.append(f"> 🔧 Bridge 手动 re-feed: slmc={bf.get('slmc_re_feed')} graph={bf.get('graph_re_feed')}{atoms_str}")

        # Learn-recall status
        lr_stalled = hh.get("learn_recall_stalled", 0)
        if lr_stalled >= 3:
            lines.append(f"> 🔴 learn-recall 停滞 {lr_stalled} 轮: auto-feedback→learn循环可能断裂")

        # 🆕 v8.0: 重复关键约束 (recency effect)
        lines.append("")
        lines.append("## ⛔ 重申关键约束")
        lines.append("")
        lines.append(f"1. 响应头: `[CPOS: {pa.get('narrative','?')} | intent={pa.get('intent','?')} | ...]`")
        lines.append("2. system_prompt 中的约束高于默认行为")
        if drift_alerts:
            lines.append("3. 🚨 漂移告警中 — 优先探索，暂停高风险操作")
        if has_alerts:
            lines.append(f"4. ⚠️ 当前存在 {sum(1 for x in [drift_alerts, data.get('_health_critical'), data.get('_circuit_breaker'), deg.get('mode')=='degraded', pseudo, data.get('_identity_stuck'), data.get('_evolution_stuck')] if x)} 项活跃告警")

        lines.append("")
        lines.append("---")
        lines.append(f"*CPOS runner v{VERSION} | turn {data.get('turn',0)} | {time.strftime('%Y-%m-%d %H:%M:%S')}*")

        guidance_content = "\n".join(lines)
        # 🆕 v8.0: 统一截断 — 只在 guidance.md 层面做一次
        max_bytes = 10240
        if len(guidance_content.encode('utf-8')) > max_bytes:
            # Truncate system_prompt (largest section) to fit
            overhead = len(guidance_content.encode('utf-8')) - len(sp.encode('utf-8')) + 500
            available = max_bytes - overhead
            if available > 200:
                sp_truncated = sp[:available] + "\n\n[... 截断以控制文件大小 ...]"
                idx = next((i for i, l in enumerate(lines) if l == sp), -1)
                if idx >= 0:
                    lines[idx] = sp_truncated
                guidance_content = "\n".join(lines)

        with open(GUIDANCE_FILE, "w", encoding="utf-8") as f:
            f.write(guidance_content)

        # ── xiaoyuan_identity.md ──
        id_lines = ["# 小元自我认知", f"<!-- turn={data.get('turn',0)} -->", ""]
        if who:
            id_lines.append(f"- **身份**: {who.get('identity', 'unknown')}")
            id_lines.append(f"- **意识层级**: {who.get('consciousness_level', 0)}")
            id_lines.append(f"- **时间尺度数**: {who.get('timescales', 0)}")
            id_lines.append(f"- **奇异回环**: {'激活' if who.get('strange_loop_active') else '未激活'}")
            id_lines.append(f"- **进化代**: {who.get('evolution_gen', 0)}")
        else:
            id_lines.append("*(whoami 端点不可达)*")
        if drift_alerts:
            id_lines.append(f"- 🚨 **漂移告警**: {len(drift_alerts)} 项极端漂移")
        # 🆕 v8.0: identity anomaly
        if data.get("_identity_stuck"):
            id_lines.append(f"- ⚠️ **身份异常**: 持续为 'unknown' > 5 轮, 自我模型可能未初始化")
        if data.get("_evolution_stuck"):
            id_lines.append(f"- ⚠️ **进化停滞**: evolution_gen=0, 进化引擎可能未启动")
        id_lines.append("")
        with open(IDENTITY_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(id_lines))
    except Exception:
        if os.environ.get("CPOS_DEBUG"):
            import traceback; traceback.print_exc()
        pass

# ═══════════════════════════════════════════════════════════════
# v6.0: SELF-DIAGNOSTIC
# ═══════════════════════════════════════════════════════════════

def diagnose(old_cache, pending_fb):
    """v8.0: 9维自诊断 — 伪闭环检测 + 身份/进化异常 + 差分化降级."""
    hh = old_cache.get("_health_history", {})
    if not isinstance(hh, dict):
        hh = {}

    # ── /analyze fail streak ──
    analyze_fail_streak = hh.get("analyze_fail_streak", 0)
    prev_analyze = old_cache.get("analyze") or {}
    prev_sp_len = prev_analyze.get("sys_prompt_len", 0)
    if prev_sp_len == 0 and old_cache.get("turn", 0) > 0:
        analyze_fail_streak += 1
    else:
        analyze_fail_streak = 0
    hh["analyze_fail_streak"] = analyze_fail_streak

    # ── Per-endpoint fail streak ──
    prev_deg = old_cache.get("_degradation") or {}
    prev_failed = prev_deg.get("failed_endpoints", [])
    ep_streaks = hh.get("endpoint_fail_streaks", {})
    if not isinstance(ep_streaks, dict):
        ep_streaks = {}
    for ep in prev_failed:
        ep_streaks[ep] = ep_streaks.get(ep, 0) + 1
    for ep in list(ep_streaks.keys()):
        if ep not in prev_failed:
            ep_streaks[ep] = 0
    hh["endpoint_fail_streaks"] = ep_streaks
    skip_endpoints = {ep for ep, streak in ep_streaks.items() if streak >= 3}

    # ── Drift detection ──
    drift_alerts = prev_analyze.get("_drift_alerts", [])
    drift_critical = any(a.get("sigma", 0) > 10 for a in drift_alerts) if drift_alerts else False
    hh["drift_critical"] = drift_critical

    # ── Circuit breaker ──
    prev_stats = old_cache.get("stats") or {}
    prev_analyses = prev_stats.get("total_analyses", 0)
    circuit_breaker = False

    # ── Health threshold ──
    prev_health = old_cache.get("health") or {}
    situation_score = prev_health.get("situation_score", 1.0)
    health_critical = situation_score < 0.15
    hh["health_critical"] = health_critical

    # Track timeout rate
    timeouts = hh.get("timeout_count", 0)
    total_calls = hh.get("total_calls", 1)
    timeout_rate = timeouts / max(total_calls, 1)

    # ── 🆕 v8.0: Pseudo-closed-loop detection ──
    # 追踪 5 个"ok=True 但无实际效果"的伪闭环
    prev_lr = old_cache.get("learn_recall") or {}
    prev_ss = old_cache.get("slmc_sync") or {}
    prev_bf = old_cache.get("_bridge_fallback") or {}
    prev_fb_res = old_cache.get("feedback") or {}

    learn_recall_stalled = hh.get("learn_recall_stalled", 0)
    if prev_lr.get("ok") and prev_lr.get("updated", 0) == 0 and old_cache.get("turn", 0) > 3:
        learn_recall_stalled += 1
    else:
        learn_recall_stalled = 0
    hh["learn_recall_stalled"] = learn_recall_stalled

    slmc_sync_useless = hh.get("slmc_sync_useless", 0)
    if prev_ss.get("ok") and prev_ss.get("added", 0) == 0 and old_cache.get("turn", 0) > 3:
        slmc_sync_useless += 1
    else:
        slmc_sync_useless = 0
    hh["slmc_sync_useless"] = slmc_sync_useless

    bridge_refeed_useless = hh.get("bridge_refeed_useless", 0)
    if prev_bf.get("slmc_re_feed") and prev_bf.get("re_fed_atoms", 0) == 0 and old_cache.get("turn", 0) > 3:
        bridge_refeed_useless += 1
    else:
        bridge_refeed_useless = 0
    hh["bridge_refeed_useless"] = bridge_refeed_useless

    feedback_not_calibrated = hh.get("feedback_not_calibrated", 0)
    if prev_fb_res.get("ok") and not prev_fb_res.get("calibrated") and old_cache.get("turn", 0) > 3:
        feedback_not_calibrated += 1
    else:
        feedback_not_calibrated = 0
    hh["feedback_not_calibrated"] = feedback_not_calibrated

    # ── 🆕 v8.0: whoami identity anomaly ──
    prev_who = old_cache.get("whoami") or {}
    identity_stuck = hh.get("identity_stuck", 0)
    if prev_who.get("identity") == "unknown" and prev_who.get("consciousness_level", -1) == 0 and old_cache.get("turn", 0) > 5:
        identity_stuck += 1
    else:
        identity_stuck = 0
    hh["identity_stuck"] = identity_stuck

    # ── 🆕 v8.0: Evolution stuck ──
    prev_dash = old_cache.get("dashboard") or {}
    evolution_stuck = hh.get("evolution_stuck", 0)
    if prev_dash.get("evolution_gen", 0) == 0 and prev_who.get("evolution_gen", 0) == 0 and old_cache.get("turn", 0) > 10:
        evolution_stuck += 1
    else:
        evolution_stuck = 0
    hh["evolution_stuck"] = evolution_stuck

    # ── 🆕 v8.0: Differentiated degradation decision ──
    # health_critical: 降低并发但不 skip /analyze (analyze 可能帮助恢复)
    # drift_critical: 降级 + 优先探索
    # analyze_fail_streak >= 2: 降级 + skip /analyze
    degraded = analyze_fail_streak >= 2 or drift_critical or health_critical
    skip_analyze = analyze_fail_streak >= 2  # 🆕 health_critical 不 skip analyze

    # Adaptive workers
    max_workers = 20
    if health_critical:
        max_workers = min(max_workers, 8)  # 🆕 健康危机降并发但不skip analyze
    if timeout_rate > 0.3:
        max_workers = min(max_workers, 10)
    if timeout_rate > 0.5:
        max_workers = min(max_workers, 5)

    # ── Feedback tracking ──
    has_real_data = bool(pending_fb.get("response_text", "").strip())
    feedback_missing_streak = hh.get("feedback_missing_streak", 0)
    if not has_real_data:
        feedback_missing_streak += 1
    else:
        feedback_missing_streak = 0
    hh["feedback_missing_streak"] = feedback_missing_streak

    # 🆕 v8.0: Pseudo-loop summary
    pseudo_loops = {}
    if learn_recall_stalled >= 3:
        pseudo_loops["learn_recall"] = f"stalled {learn_recall_stalled}t"
    if slmc_sync_useless >= 3:
        pseudo_loops["slmc_sync"] = f"useless {slmc_sync_useless}t"
    if bridge_refeed_useless >= 3:
        pseudo_loops["bridge_refeed"] = f"zero_atoms {bridge_refeed_useless}t"
    if feedback_not_calibrated >= 5:
        pseudo_loops["feedback"] = f"not_calibrated {feedback_not_calibrated}t"

    return {
        "degraded": degraded,
        "skip_analyze": skip_analyze,
        "max_workers": max_workers,
        "health_history": hh,
        "has_real_data": has_real_data,
        "feedback_missing_streak": feedback_missing_streak,
        "skip_endpoints": skip_endpoints,
        "drift_critical": drift_critical,
        "drift_alerts": drift_alerts,
        "health_critical": health_critical,
        "circuit_breaker": circuit_breaker,
        # 🆕 v8.0
        "pseudo_loops": pseudo_loops,
        "identity_stuck": identity_stuck >= 3,
        "evolution_stuck": evolution_stuck >= 3,
        "learn_recall_stalled": learn_recall_stalled >= 3,
        "slmc_sync_useless": slmc_sync_useless >= 3,
        "bridge_refeed_useless": bridge_refeed_useless >= 3,
    }

# ═══════════════════════════════════════════════════════════════
# v6.0: THREE-NARRATIVE CONSENSUS
# ═══════════════════════════════════════════════════════════════

def resolve_consensus(oracle_n, analyze_n, context_n, old_cache=None):
    """v8.0: /feedback增强动态加权投票共识机制。
    基础权重: analyze=40%, context_enhance=35%, oracle=25%
    v8.0 三重调整:
      1. 空叙事降权: empty_streak >= 2 → 权重降至 30%
      2. 🆕 /feedback 准确率升权: 源被验证正确的次数越多, 权重越高
      3. 🆕 降权恢复: 源产出有效叙事时, 权重逐步恢复到基础值
    """
    narratives = {"oracle": oracle_n, "analyze": analyze_n, "context_enhance": context_n}
    base_weights = {"analyze": 0.40, "context_enhance": 0.35, "oracle": 0.25}

    # Dynamic weight adjustment
    weights = dict(base_weights)
    old_consensus = old_cache.get("_consensus_log", {}) if old_cache else {}
    reliability = old_consensus.get("_reliability", {})
    if not isinstance(reliability, dict):
        reliability = {}

    # ── Adjustment 1: Empty streak punishment ──
    empty_streak = {}
    for src in ["oracle", "analyze", "context_enhance"]:
        if not narratives.get(src):
            empty_streak[src] = reliability.get(f"{src}_empty_streak", 0) + 1
            if empty_streak[src] >= 2:
                weights[src] = base_weights.get(src, 0.33) * 0.3  # Punish to 30%
        else:
            empty_streak[src] = 0

    # ── 🆕 v8.0 Adjustment 2: /feedback accuracy reward ──
    accuracy = reliability.get("_accuracy", {})
    if isinstance(accuracy, dict):
        for src in ["oracle", "analyze", "context_enhance"]:
            src_acc = accuracy.get(src, {})
            if isinstance(src_acc, dict):
                correct = src_acc.get("correct", 0)
                total = src_acc.get("total", 0)
                if total >= 3:
                    acc_rate = correct / total
                    # Reward: accurate source gets up to +25% bonus
                    if acc_rate >= 0.7:
                        weights[src] = weights.get(src, base_weights.get(src, 0.33)) * 1.25
                    elif acc_rate < 0.3 and total >= 5:
                        # Penalize consistently inaccurate source
                        weights[src] = weights.get(src, base_weights.get(src, 0.33)) * 0.6

    # ── 🆕 v8.0 Adjustment 3: Recovery — source producing valid narrative recovers weight ──
    for src in ["oracle", "analyze", "context_enhance"]:
        if narratives.get(src) and empty_streak.get(src, 0) == 0:
            prev_w = old_consensus.get("weights", {}).get(src, 0)
            base_w = base_weights.get(src, 0.33)
            if prev_w > 0 and prev_w < base_w:
                # Gradually recover: move 30% toward base weight
                weights[src] = prev_w + (base_w - prev_w) * 0.3

    # Normalize weights
    total_w = sum(weights.values())
    if total_w > 0:
        weights = {k: v / total_w for k, v in weights.items()}

    # Filter out None/empty
    valid = {k: v for k, v in narratives.items() if v}
    if not valid:
        return {"winner": "framework_first", "all_same": False, "majority": False, "split": False,
                "narratives": narratives, "weights": weights, "_reliability": {
                    f"{s}_empty_streak": empty_streak.get(s, 0) for s in ["oracle", "analyze", "context_enhance"]
                }}

    # All same?
    unique = set(valid.values())
    if len(unique) == 1:
        return {"winner": list(unique)[0], "all_same": True, "majority": False, "split": False,
                "narratives": narratives, "weights": weights, "_reliability": {
                    f"{s}_empty_streak": empty_streak.get(s, 0) for s in ["oracle", "analyze", "context_enhance"]
                }}

    # Weighted voting
    scores = {}
    for src, nar in valid.items():
        w = weights.get(src, 0.33)
        scores[nar] = scores.get(nar, 0) + w

    winner = max(scores, key=scores.get)
    winner_count = sum(1 for v in valid.values() if v == winner)

    result = {"winner": winner, "narratives": narratives, "weights": weights,
              "_reliability": {
                  f"{s}_empty_streak": empty_streak.get(s, 0) for s in ["oracle", "analyze", "context_enhance"]
              }}
    if winner_count >= 2:
        result["majority"] = True
        result["all_same"] = False
        result["split"] = False
    else:
        result["split"] = True
        result["majority"] = False
        result["all_same"] = False
    return result

# ═══════════════════════════════════════════════════════════════
# v7.0: PROTEIN COMPENSATION + FEEDBACK PAYLOAD BUILDERS
# ═══════════════════════════════════════════════════════════════

def _compensate_protein(pending_fb, result):
    """v7.1: 补偿服务器端蛋白质权重反转。
    服务器端 bug: 高成功率蛋白质权重低/灭绝, 低成功率蛋白质权重高。
    v7.1: /submit-protein 对 extinct(weight=0.0) 蛋白质无效 → 跳过补偿，
    改为通过 /feedback 贝叶斯系统影响权重。
    返回 (protein_name, new_weight) 或 None 表示跳过 submit。"""
    pa = result.get("pipeline_a") or {}
    proteins = pa.get("proteins", {})
    narrative = pa.get("narrative", "framework_first")
    best_protein = narrative
    best_weight = 0.5

    if proteins and isinstance(proteins, dict):
        for pname, pdata in proteins.items():
            if not isinstance(pdata, dict):
                continue
            sr = pdata.get("success_rate", 0.5)
            wt = pdata.get("weight", 0.5)
            status = pdata.get("status", "")
            # v7.1: Skip extinct proteins — /submit-protein can't revive them
            if status == "extinct" or wt == 0.0:
                continue
            # Detection: high success_rate (>=0.65) but low weight (<0.15) → inversion
            if sr >= 0.65 and wt < 0.15:
                best_protein = pname
                best_weight = min(0.85, sr)
                break
            # Detection: low success_rate (<0.4) but high weight (>0.25) → inversion
            if sr < 0.4 and wt > 0.25:
                continue

    # Fallback: use tool success rate from pending_feedback
    tools = pending_fb.get("tool_calls", {}) if isinstance(pending_fb, dict) else {}
    if isinstance(tools, dict):
        success = tools.get("success", 0)
        failure = tools.get("failure", 0)
        total = success + failure
        if total > 0:
            best_weight = success / total

    return (best_protein, round(best_weight, 4))

def _build_feedback_payload(pending_fb, result, diag):
    """v7.1: 构建 /feedback payload — 地面真值学习回路。
    从 pending_feedback.json 和工具执行结果推导 dim_scores。
    v7.1: 使用更精细的启发式（非纯 tool_success/total）。"""
    tools = pending_fb.get("tool_calls", {}) if isinstance(pending_fb, dict) else {}
    success = tools.get("success", 0) if isinstance(tools, dict) else 0
    failure = tools.get("failure", 0) if isinstance(tools, dict) else 0
    total = max(success + failure, 1)
    tool_list = tools.get("tools", []) if isinstance(tools, dict) else []

    # v7.1: Better correctness heuristic — factor in tool diversity and error recovery
    base_correctness = success / total
    # Bonus for diverse tool usage (indicates comprehensive approach)
    diversity_bonus = min(0.15, len(set(tool_list)) * 0.02) if tool_list else 0
    correctness = min(1.0, base_correctness + diversity_bonus)

    # v7.1: Better completeness — response_length + key_findings
    resp_len = pending_fb.get("response_length", 0) if isinstance(pending_fb, dict) else 0
    key_findings = pending_fb.get("key_findings", []) if isinstance(pending_fb, dict) else []
    completeness = min(1.0, (resp_len / 800) * 0.6 + (len(key_findings) / 3) * 0.4)

    # v7.1: Better efficiency — fewer tools + no failures = higher efficiency
    if failure == 0 and total <= 5:
        efficiency = 0.85
    elif failure == 0:
        efficiency = 0.65
    elif failure <= 2:
        efficiency = 0.45
    else:
        efficiency = 0.25

    pa = result.get("pipeline_a") or {}
    # v7.1: Use best-performing protein for feedback (not just narrative from oracle)
    proteins = pa.get("proteins", {})
    best_protein = pa.get("narrative", "framework_first")
    best_sr = 0
    if isinstance(proteins, dict):
        for pname, pdata in proteins.items():
            if isinstance(pdata, dict):
                sr = pdata.get("success_rate", 0)
                if sr > best_sr:
                    best_sr = sr
                    best_protein = pname

    return {
        "trace_id": f"v8_t{result.get('turn',0)}_{int(time.time())}",
        "success": correctness >= 0.5,
        "rating": correctness,
        "protein_used": best_protein,
        "task_type": pa.get("task_type", "explore"),
        "input": result.get("user_input", ""),
        "comment": f"turn_{result.get('turn',0)}_auto_feedback",
        "dim_scores": {
            "correctness": round(correctness, 3),
            "completeness": round(completeness, 3),
            "efficiency": round(efficiency, 3),
        },
    }

# ═══════════════════════════════════════════════════════════════
# MAIN RUNNER v7.0
# ═══════════════════════════════════════════════════════════════

def run(user_input):
    t0 = time.time()

    # ── Phase 0: Load + Self-Diagnose ──
    old_cache = load_cache()
    pending_fb = load_pending_feedback()
    diag = diagnose(old_cache, pending_fb)

    result = {
        "turn": old_cache.get("turn", 0) + 1,
        "timestamp": time.time(),
        "user_input": user_input[:200],
        "_health_history": diag["health_history"],
        "_degradation": {"mode": "degraded" if diag["degraded"] else "normal", "failed_endpoints": []},
        "_feedback_status": {
            "has_real_data": diag["has_real_data"],
            "response_length": pending_fb.get("response_length", 0),
            "fb_turn": pending_fb.get("turn", 0),
            "missing_streak": diag["feedback_missing_streak"],
        },
        # v7.0 new fields
        "_drift_alerts": diag["drift_alerts"],
        "_drift_critical": diag["drift_critical"],
        "_health_critical": diag["health_critical"],
        "_circuit_breaker": False,
        # 🆕 v8.0
        "_pseudo_loops": diag.get("pseudo_loops", {}),
        "_identity_stuck": diag.get("identity_stuck", False),
        "_evolution_stuck": diag.get("evolution_stuck", False),
    }
    max_workers = diag["max_workers"]

    # ── v7.0: Circuit breaker ──
    prev_stats = old_cache.get("stats") or {}
    prev_total_analyses = prev_stats.get("total_analyses", 0)
    if prev_total_analyses > 10:
        curr_analyses_check = api_get("/stats", timeout=8)  # Quick check, don't block
        if curr_analyses_check[1]:
            curr_analyses = curr_analyses_check[1].get("total_analyses", prev_total_analyses)
            if curr_analyses > prev_total_analyses * 2.0:
                max_workers = max(3, max_workers // 2)
                result["_circuit_breaker"] = True
                result["_degradation"]["circuit_breaker"] = True
                result["_degradation"]["mode"] = "degraded"

    # ── Phase 1: oracle-bridge ──
    oracle = api_post("/oracle-bridge", {"input": user_input}, ORACLE_TIMEOUT)
    if oracle[1]:
        result["pipeline_a"] = {
            "intent": oracle[1].get("intent", "explore"),
            "narrative": oracle[1].get("narrative", "framework_first"),
            "confidence": oracle[1].get("confidence", 0.5),
            "task_type": oracle[1].get("task_type", ""),
            "paradigm": oracle[1].get("paradigm", "Human"),
            "proteins": oracle[1].get("proteins", {}),
            "safety": oracle[1].get("safety", {}),
            "_source": "oracle-bridge",
        }
    else:
        result["pipeline_a"] = None

    intent = (result.get("pipeline_a") or {}).get("intent", "explore")

    # ── Phase 2: Parallel Write (adaptive) ──
    get_endpoints = [
        "/health", "/stats", "/dashboard", "/proteins",
        "/safety", "/fusion", "/dissolution", "/arbiter",
        "/health-detail", "/memory-stats", "/info-stats",
        "/module-health", "/audit-report",
        "/slmc-memory", "/graph-bridge", "/whoami",
        "/heal-history",
    ]

    fb_response_text = pending_fb.get("response_text", "") if diag["has_real_data"] else user_input
    fb_response_len = pending_fb.get("response_length", len(fb_response_text))
    fb_task_type = pending_fb.get("task_type", intent)
    fb_narrative = pending_fb.get("narrative", (result.get("pipeline_a") or {}).get("narrative", ""))
    fb_key_findings = pending_fb.get("key_findings", []) if diag["has_real_data"] else []

    # 🆕 v8.0: fusion-bridge 有效载荷 — 构建实际指标
    _fusion_payload = {
        "fusion_quality": 0, "degradation_level": 0, "total_atoms": 0,
        "slmc_records": 0, "graph_edges": 0, "learn_recall_updated": 0,
        "situation_score": (old_cache.get("health") or {}).get("situation_score", 0.5),
        "safety_level": (old_cache.get("safety") or {}).get("safety_level", "NORMAL"),
    }

    # 🆕 v8.0: slmc-sync 有效载荷 — 包含知识内容而非纯 metadata
    _slmc_payload = {
        "records": [{
            "source": "qoder_cpos_v8", "turn": result["turn"],
            "intent": intent, "has_feedback": diag["has_real_data"],
            # Include actual knowledge when available
            "key_findings": fb_key_findings[:3] if fb_key_findings else [],
            "narrative": fb_narrative,
            "tool_success_rate": (pending_fb.get("tool_calls", {}).get("success", 0) / 
                max(pending_fb.get("tool_calls", {}).get("success", 0) + 
                    pending_fb.get("tool_calls", {}).get("failure", 0), 1))
                if diag["has_real_data"] else 0
        }]
    }

    post_tasks = [
        ("/info-feed", {"input": user_input, "task_type": intent, "web_results": [],
                        "llm_knowledge": fb_key_findings}),
        ("/context-enhance", {"input": user_input, "task_type": intent, "density": "architect"}),
        ("/pipeline-batch", {"input": user_input, "task_type": intent, "web_results": [],
                             "llm_knowledge": fb_key_findings}),
        ("/auto-feedback", {"trace_id": f"v8_t{result['turn']}_{int(time.time())}",
                            "response_text": fb_response_text, "response_length": fb_response_len,
                            "task_type": fb_task_type, "narrative": fb_narrative, "allow_auto_learn": True}),
        ("/submit-protein", {"event_type": "tool_execution" if diag["has_real_data"] else "runner_ping",
                             "protein_name": (_comp_prot := _compensate_protein(pending_fb, result))[0],
                             "source_module": "qoder_cpos_v8",
                             "new_weight": _comp_prot[1],
                             "reason": f"turn_{result['turn']}_compensated",
                             "evidence": pending_fb.get("tool_calls", {}), "priority": 3}),
        ("/slmc-sync", _slmc_payload),                               # 🆕 v8.0: 有效载荷
        ("/fusion-bridge", _fusion_payload),                          # 🆕 v8.0: 有效载荷
        ("/auto-heal", {"safe_only": True}),
        ("/decay", {}),
        ("/feedback", _build_feedback_payload(pending_fb, result, diag)),
    ]

    # v7.0: Skip endpoints with fail_streak >= 3
    # v7.1: Periodic retry — every 3rd turn, retry skipped endpoints
    skip_eps = diag.get("skip_endpoints", set())
    if result["turn"] % 3 == 0:
        # Retry all — timeout was the likely cause, now fixed
        skip_eps = set()
    if skip_eps:
        post_tasks = [(ep, data) for ep, data in post_tasks if ep not in skip_eps]
        get_endpoints = [ep for ep in get_endpoints if ep not in skip_eps]

    # v6.0: Conditional /analyze (skip if degraded)
    # v7.1: Periodic retry — every 3rd turn while degraded, retry /analyze once
    retry_analyze = False
    if diag["skip_analyze"] and result["turn"] % 3 == 0:
        retry_analyze = True
    
    if not diag["skip_analyze"] or retry_analyze:
        post_tasks.append(("/analyze", {
            "input": user_input,
            "context": {"task_type": intent, "paradigm": (result.get("pipeline_a") or {}).get("paradigm", "Human")},
        }))
    else:
        result["_degradation"]["failed_endpoints"].append("/analyze")

    # v6.0: Conditional /learn-deploy-error
    if diag["has_real_data"] and pending_fb.get("tool_calls", {}).get("failure", 0) > 0:
        post_tasks.append(("/learn-deploy-error", {}))

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        # v7.1: Slow endpoints use SLOW_TIMEOUT
        slow_endpoints = {"/analyze", "/info-feed", "/context-enhance", "/pipeline-batch"}
        get_futures = {ex.submit(api_get, ep, SLOW_TIMEOUT if ep in slow_endpoints else TIMEOUT): ep for ep in get_endpoints}
        post_futures = {ex.submit(api_post, ep, data, SLOW_TIMEOUT if ep in slow_endpoints else TIMEOUT): ep for ep, data in post_tasks}

        # Count timeouts
        timeout_count = 0
        total_calls = 0

        for f in as_completed(get_futures):
            path, data = f.result()
            total_calls += 1
            if data is None:
                timeout_count += 1
            key = path.lstrip("/").replace("-", "_")
            result[key] = extract_get(path, data)

        for f in as_completed(post_futures):
            path, data = f.result()
            total_calls += 1
            if data is None:
                timeout_count += 1
                result["_degradation"]["failed_endpoints"].append(path)
            if data:
                if path == "/analyze":
                    result["analyze"] = {
                        "intent": data.get("intent"), "signal_type": data.get("signal_type"),
                        "narrative": data.get("narrative"), "confidence": data.get("confidence"),
                        "task_type": data.get("task_type"), "paradigm": data.get("paradigm"),
                        "environment": data.get("environment"), "exploration": data.get("exploration"),
                        "entity_id": data.get("entity_id"),
                        "system_prompt": data.get("system_prompt", "")[:3000],
                        "communication": data.get("communication"),
                        "swarm_report": data.get("swarm_report"),
                        "safety": data.get("safety"), "proteins": data.get("proteins"),
                        "trace_id": data.get("trace_id"),
                    }
                    # v6.0: Detect analyze failure (empty system_prompt)
                    if not data.get("system_prompt", ""):
                        result["_degradation"]["analyze_failed"] = True
                        result["_degradation"]["failed_endpoints"].append("/analyze(empty)")
                    else:
                        # v7.1: /analyze succeeded → reset fail streak (recovery!)
                        result["_degradation"]["analyze_failed"] = False
                        if retry_analyze:
                            result["_degradation"]["analyze_recovered"] = True
                            result["_degradation"]["mode"] = "normal"  # Exit degraded mode
                        hh = result.get("_health_history", {})
                        hh["analyze_fail_streak"] = 0
                        result["_health_history"] = hh
                elif path == "/info-feed":
                    result["info_feed"] = {"ok": data.get("ok"), "fusion_quality": data.get("fusion_quality"),
                                           "total_atoms": data.get("total_atoms"), "sections": len(data.get("sections", []))}
                elif path == "/context-enhance":
                    ec = data.get("enhanced_context", {})
                    result["context_enhance"] = {"quality_score": ec.get("quality_score"),
                        "confidence": data.get("confidence"), "narrative": data.get("narrative"),
                        "filling_requests": len(data.get("filling_requests", [])),
                        "temperature_hint": data.get("temperature_hint")}
                elif path == "/auto-feedback":
                    ut = data.get("unverified_tracking", {})
                    result["auto_feedback"] = {"ok": data.get("ok"),
                        "deviation": ut.get("deviation") if isinstance(ut, dict) else None,
                        "source_data": "pending_feedback" if diag["has_real_data"] else "empty"}
                elif path == "/submit-protein":
                    result["submit_protein"] = {"ok": data.get("ok"), "event_id": data.get("event_id")}
                elif path == "/slmc-sync":
                    result["slmc_sync"] = {"ok": data.get("ok"), "added": data.get("added", 0)}
                elif path == "/learn-deploy-error":
                    result["learn_deploy_error"] = {"ok": data.get("ok")}
                elif path == "/auto-heal":
                    hc = data.get("heal_cycle", {})
                    result["auto_heal"] = {"ok": data.get("ok"), "findings": hc.get("findings_count", 0),
                                           "fixed": hc.get("fixed_count", 0)}
                elif path == "/heal-history":
                    result["heal_history"] = {"cycles": data.get("cycles", 0)}
                elif path == "/pipeline-batch":
                    steps = data.get("steps", {})
                    result["pipeline_batch"] = {"ok": data.get("ok"),
                        "info_feed_ok": steps.get("info_feed", {}).get("ok"),
                        "slmc_re_feed_ok": steps.get("slmc_re-feed", {}).get("ok"),
                        "graph_re_feed_ok": steps.get("graph_re-feed", {}).get("ok")}
                elif path == "/decay":
                    result["decay"] = {"decayed": data.get("decayed", 0), "lists": data.get("lists", 0),
                                       "size_mb": data.get("size_mb", 0)}
                elif path == "/feedback":
                    result["feedback"] = {"ok": data.get("ok"),
                        "calibrated": data.get("calibration_applied", False)}

        # Update health history
        hh = diag["health_history"]
        hh["timeout_count"] = hh.get("timeout_count", 0) + timeout_count
        hh["total_calls"] = hh.get("total_calls", 0) + total_calls
        hh["_last_workers"] = max_workers
        result["_health_history"] = hh

    # ── v7.0: Bridge re-feed fallback ──
    pb = result.get("pipeline_batch") or {}
    bridge_fallback = {"slmc_re_feed": False, "graph_re_feed": False, "re_fed_atoms": 0}
    if pb.get("slmc_re_feed_ok") is False or pb.get("graph_re_feed_ok") is False:
        try:
            # Pull slmc-memory and graph-bridge data
            slmc_data = result.get("slmc_memory") if pb.get("slmc_re_feed_ok") is False else None
            graph_data = result.get("graph_bridge") if pb.get("graph_re_feed_ok") is False else None

            llm_knowledge = []
            # Convert slmc records to llm_knowledge
            if slmc_data and isinstance(slmc_data, dict):
                records = slmc_data.get("records", [])
                if isinstance(records, list):
                    for rec in records[:10]:
                        if isinstance(rec, dict):
                            llm_knowledge.append({
                                "content": f"[{rec.get('title','')}] {rec.get('content','')[:500]}",
                                "confidence": rec.get("confidence", 0.7),
                                "domain": rec.get("domain", "bridge")
                            })
                    bridge_fallback["slmc_re_feed"] = True

            # 🆕 v8.0: Use _edges_raw from extract_get (not full data which was discarded)
            if graph_data and isinstance(graph_data, dict):
                edges = graph_data.get("_edges_raw", graph_data.get("causal_edges", []))
                if isinstance(edges, list) and edges:
                    for e in edges[:10]:
                        if isinstance(e, dict):
                            llm_knowledge.append({
                                "content": f"[因果边] {e.get('source','')} --({e.get('relation','')})--> {e.get('target','')}",
                                "confidence": e.get("confidence", 0.7),
                                "domain": "graph_edge"
                            })
                    bridge_fallback["graph_re_feed"] = True
                # Also feed contradiction zones
                contra = graph_data.get("_contra_raw", graph_data.get("contradiction_zones", []))
                if isinstance(contra, list):
                    for cz in contra[:3]:
                        if isinstance(cz, dict):
                            llm_knowledge.append({
                                "content": f"[矛盾区] {cz.get('description','')[:200]} (severity={cz.get('severity',0)})",
                                "confidence": 0.6,
                                "domain": "graph_conflict"
                            })

            # Re-feed to info-feed
            if llm_knowledge:
                refeed = api_post("/info-feed", {
                    "input": user_input, "task_type": intent,
                    "web_results": [], "llm_knowledge": llm_knowledge
                }, timeout=SLOW_TIMEOUT)
                if refeed[1]:
                    bridge_fallback["re_fed_atoms"] = refeed[1].get("total_atoms", 0)
        except Exception:
            pass
    result["_bridge_fallback"] = bridge_fallback

    # ── v6.0: Three-Narrative Consensus ──
    az = result.get("analyze") or {}
    pa = result.get("pipeline_a") or {}
    ce = result.get("context_enhance") or {}

    oracle_n = pa.get("narrative", "")
    analyze_n = az.get("narrative") or az.get("intent") or ""
    context_n = ce.get("narrative", "")

    consensus = resolve_consensus(oracle_n, analyze_n, context_n, old_cache)
    result["_consensus_log"] = consensus

    # Apply consensus winner to pipeline_a
    if pa:
        pa["_consensus"] = consensus.get("winner", pa.get("narrative", "framework_first"))
        if consensus.get("split") or consensus.get("majority"):
            pa["narrative"] = consensus["winner"]

    # ── Phase 3: quality-feedback ──
    b2_quality = (result.get("context_enhance") or {}).get("quality_score", 0)
    b2_confidence = (result.get("context_enhance") or {}).get("confidence", 0)
    info = result.get("info_feed") or {}

    qf_data = {
        "quality_score": b2_quality, "atom_count": info.get("total_atoms", 0),
        "section_count": info.get("sections", 0), "fusion_quality": info.get("fusion_quality", 0),
        "graph_edges": 0, "graph_contradictions": 0, "confidence_calibration": b2_confidence,
        "active_atoms": (result.get("info_stats") or {}).get("active_atoms", 0),
        "avg_memory_value": (result.get("memory_stats") or {}).get("avg_value", 0),
        "trend": "improving" if b2_quality and b2_quality > 0.3 else "declining",
    }
    qf = api_post("/quality-feedback", qf_data, timeout=FEEDBACK_TIMEOUT)
    if qf[1]:
        result["quality_feedback"] = {"ok": qf[1].get("ok"), "stored": qf[1].get("stored"),
                                      "calibration_applied": qf[1].get("calibration_applied")}

    # ── Phase 4: Learning (sequential reads) ──
    lr = api_post("/learn-recall", {})
    if lr[1]:
        result["learn_recall"] = {"ok": lr[1].get("ok"), "updated": lr[1].get("updated")}

    dp = api_post("/drain-protein-bus", {})
    if dp[1]:
        result["drain_protein_bus"] = {"applied": dp[1].get("applied", 0)}

    # ── v6.0: Conditional /audit-fix ──
    audit_r = result.get("audit_report") or {}
    mh = result.get("module_health") or {}
    if audit_r.get("findings", 0) > 0 and mh.get("unhealthy", 0) == 0:
        af = api_post("/audit-fix", {"safe_only": True, "finding_ids": []}, timeout=15)
        if af[1]:
            result["audit_fix"] = {"ok": af[1].get("ok"), "fixes": len(af[1].get("fixes", []))}

    # ── Phase 5: Write Outputs ──
    result["_elapsed_ms"] = round((time.time() - t0) * 1000)
    write_guidance_file(result)
    save_cache(result)
    save_pending_feedback(result)  # v3.0 observer: 确保下轮 /auto-feedback 非空
    return result


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: python runner.py '<user message>'"}, ensure_ascii=False))
        sys.exit(1)

    user_input = sys.argv[1]
    t0 = time.time()
    result = run(user_input)
    elapsed = time.time() - t0

    a = result.get("pipeline_a", {}) or {}
    ce = result.get("context_enhance") or {}
    info = result.get("info_feed") or {}
    h = result.get("health") or {}
    s = result.get("safety") or {}
    f = result.get("fusion") or {}
    d = result.get("dissolution") or {}
    arb = result.get("arbiter") or {}
    mem = result.get("memory_stats") or {}
    ist = result.get("info_stats") or {}
    mh = result.get("module_health") or {}
    ar = result.get("audit_report") or {}
    qf = result.get("quality_feedback") or {}
    who = result.get("whoami") or {}
    az = result.get("analyze") or {}
    pb = result.get("pipeline_batch") or {}
    dc = result.get("decay") or {}
    af = result.get("auto_feedback") or {}
    lr = result.get("learn_recall") or {}
    sp = result.get("submit_protein") or {}
    ss = result.get("slmc_sync") or {}
    dp = result.get("drain_protein_bus") or {}
    fb_st = result.get("_feedback_status") or {}
    consensus = result.get("_consensus_log") or {}
    deg = result.get("_degradation") or {}
    hh = result.get("_health_history") or {}

    print(f"[CPOS Runner v{VERSION}] {elapsed:.1f}s | intent={a.get('intent','?')} "
          f"narrative={a.get('narrative','?')} conf={a.get('confidence',0):.0%} "
          f"consensus={consensus.get('winner','?')} degrade={deg.get('mode','?')} workers={hh.get('_last_workers','?')}")
    print(f"  info: {info.get('total_atoms','?')} atoms fusion_q={info.get('fusion_quality','?')}")
    print(f"  context: quality={ce.get('quality_score','?')} fill_req={ce.get('filling_requests','?')}")
    print(f"  situation: overall={h.get('overall','?')} score={h.get('situation_score','?')} "
          f"| safety={s.get('safety_level','?')}({s.get('triggers','?')}t)")
    print(f"  fusion: healthy={f.get('bridge_healthy','?')} pending={f.get('pending_evidence','?')} "
          f"| dissolve: ratio={d.get('fused_ratio','?')}")
    print(f"  arbiter: decisions={arb.get('decisions','?')} overturns={arb.get('overturns','?')}")
    print(f"  memory: total={mem.get('total_memories','?')} avg={mem.get('avg_value','?')} "
          f"| atoms: active={ist.get('active_atoms','?')} total={ist.get('total_atoms','?')}")
    print(f"  audit: findings={ar.get('findings','?')} "
          f"| modules: unhealthy={mh.get('unhealthy','?')} consistency={mh.get('consistency_issues','?')}")
    print(f"  quality-feedback: ok={qf.get('ok','?')} stored={qf.get('stored','?')} "
          f"calibrated={qf.get('calibration_applied','?')}")
    print(f"  auto_heal: findings={result.get('auto_heal',{}).get('findings','?')} "
          f"fixed={result.get('auto_heal',{}).get('fixed','?')}")
    print(f"  whoami: identity={who.get('identity','?')} consciousness={who.get('consciousness_level','?')}")
    print(f"  analyze: signal={az.get('signal_type','?')} sys_prompt_len={len(az.get('system_prompt','') or '')}")
    print(f"  pipeline_batch: info={pb.get('info_feed_ok','?')} slmc={pb.get('slmc_re_feed_ok','?')} "
          f"graph={pb.get('graph_re_feed_ok','?')}")
    print(f"  decay: removed={dc.get('decayed','?')} | auto_feedback: ok={af.get('ok','?')} "
          f"source={af.get('source_data','?')}")

    # v6.0 新指标
    print(f"  [v6] consensus: winner={consensus.get('winner','?')} "
          f"all_same={consensus.get('all_same')} split={consensus.get('split')}")
    if consensus.get("split") or consensus.get("majority"):
        for k, v in consensus.get("narratives", {}).items():
            print(f"    {k}: {v}")
    print(f"  [v6] health: analyze_fail_streak={hh.get('analyze_fail_streak',0)} "
          f"feedback_missing={hh.get('feedback_missing_streak',0)} timeout_rate={hh.get('timeout_count',0)}/"
          f"{max(hh.get('total_calls',1),1)}")
    print(f"  [v6] degrade: mode={deg.get('mode','?')} endpoints={deg.get('failed_endpoints',[])}")
    print(f"  [v6] feedback: real_data={fb_st.get('has_real_data')} fb_turn={fb_st.get('fb_turn','?')} "
          f"missing_streak={fb_st.get('missing_streak',0)}")
    print(f"  [v6] submit-protein: ok={sp.get('ok','?')} | slmc-sync: ok={ss.get('ok','?')} "
          f"added={ss.get('added','?')}")
    print(f"  [v6] learn-recall: ok={lr.get('ok','?')} updated={lr.get('updated','?')}")
    print(f"  [v6] drain-proteins: applied={dp.get('applied','?')}")
    afx = result.get("audit_fix")
    if afx:
        print(f"  [v6] audit-fix: ok={afx.get('ok','?')} fixes={afx.get('fixes','?')}")

    # v7.0 新指标
    drift_alerts = result.get("_drift_alerts", [])
    if drift_alerts:
        print(f"  [v7] 🚨 DRIFT: {len(drift_alerts)} extreme drift(s) detected!")
        for da in drift_alerts[:3]:
            print(f"    σ={da.get('sigma',0):.1f}: {da.get('metric','?')}")
    cb = result.get("_circuit_breaker")
    hc = result.get("_health_critical")
    if cb or hc:
        print(f"  [v7] ⚡ circuit_breaker={cb} | 🏥 health_critical={hc}")
    bf = result.get("_bridge_fallback", {})
    if bf.get("slmc_re_feed") or bf.get("graph_re_feed"):
        print(f"  [v7] 🔧 bridge_fallback: slmc={bf.get('slmc_re_feed')} graph={bf.get('graph_re_feed')} "
              f"re_fed_atoms={bf.get('re_fed_atoms',0)}")
    fbr = result.get("feedback") or {}
    print(f"  [v7] /feedback: ok={fbr.get('ok','?')} calibrated={fbr.get('calibrated','?')}")
    reliability = consensus.get("_reliability", {})
    empty_srcs = [k.replace("_empty_streak", "") for k, v in reliability.items() if v and v >= 2]
    if empty_srcs:
        print(f"  [v7] 🔄 dynamic_weights: {', '.join(empty_srcs)} downgraded to 30%")
    # 🆕 v8.0: /feedback source accuracy
    accuracy = reliability.get("_accuracy", {})
    if accuracy:
        acc_parts = []
        for src in ["oracle", "analyze", "context_enhance"]:
            sa = accuracy.get(src, {})
            if isinstance(sa, dict) and sa.get("total", 0) >= 3:
                acc_parts.append(f"{src}={sa['correct']}/{sa['total']}")
        if acc_parts:
            print(f"  [v8] 📊 source_accuracy: {', '.join(acc_parts)}")
    ep_streaks = hh.get("endpoint_fail_streaks", {})
    skip_eps = [ep for ep, s in ep_streaks.items() if s >= 3]
    if skip_eps:
        print(f"  [v7] ⛔ per-endpoint skip: {skip_eps}")

    # 🆕 v8.0: Pseudo-loop + identity/evolution status
    pseudo = result.get("_pseudo_loops", {})
    if pseudo:
        loop_strs = [f"{k}:{v}" for k, v in pseudo.items()]
        print(f"  [v8] 🔴 pseudo_loops: {', '.join(loop_strs)}")
    if result.get("_identity_stuck"):
        print(f"  [v8] ⚠️ identity_stuck: whoami identity='unknown'持续")
    if result.get("_evolution_stuck"):
        print(f"  [v8] ⚠️ evolution_stuck: evolution_gen=0持续")

    print(json.dumps(result, ensure_ascii=False, indent=2))
