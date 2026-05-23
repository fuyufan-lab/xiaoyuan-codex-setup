# Xiaoyuan x Qoder CPOS Pipeline Configuration

将[小元（Xiaoyuan）](https://yh.xiaofenhe.com) CPOS v8.0 全套认知管道适配到 **Qoder/源 IDE**，安装后 AI 助手自动运行 32 端点全自动管道（oracle、context-enhance、situation-awareness、meta-audit、auto-heal、learn-recall 等），覆盖 12 个 LLM 范式缺陷。

## 一键安装

在 **PowerShell（管理员）** 中运行：

`powershell
irm https://raw.githubusercontent.com/fuyufan-lab/xiaoyuan-codex-setup/main/qoder-config/install.ps1 | iex
`

安装后**重启 Qoder（源）**，打开任意项目即可看到 CPOS 管道自动激活（回复前显示 [CPOS: ...] 标识）。

## 包含内容

`
~/.qoder/
├── rules/
│   └── always-cpos.md              # CPOS 强制前置管道规则（每轮自动执行）
├── skills/
│   ├── cpos-pipeline/SKILL.md       # 主管道 v8.0：oracle + 32端点 + 三叙事共识
│   ├── swarm-dispatch/SKILL.md     # 并行任务分发器
│   └── cpos-execute/SKILL.md       # CPOS ESC 认知轮执行（需设置 token）
├── agents/
│   └── coder.md                    # 通用编码执行子智能体
└── cpos/
    └── runner.py                   # CPOS v8.0 合并运行器（32端点自适应）
`

## 文件说明

| 文件 | 大小 | 作用 |
|------|------|------|
| 
ules/always-cpos.md | ~7KB | 强制规则：每轮消息前必须执行 CPOS 管道 |
| skills/cpos-pipeline/SKILL.md | ~55KB | 完整管道说明：5 阶段、32 端点、降级策略 |
| skills/swarm-dispatch/SKILL.md | ~1.5KB | 多文件并行编码分发 |
| skills/cpos-execute/SKILL.md | ~4KB | ESC 认知轮任务执行（需 token） |
| gents/coder.md | ~1KB | 编码执行子智能体 |
| cpos/runner.py | ~74KB | Python 运行器：自适应调用所有 CPOS 端点 |

## 前置要求

- **Qoder（源）IDE** 已安装
- **Python 3** 可用（runner.py 依赖）
- 网络可访问 yh.xiaofenhe.com

## 设置 CPOS Execute Token

cpos-execute skill 需要通过 token 认证。

**Windows:**
`powershell
 =  your-token-here
`

**macOS/Linux:**
`ash
export CPOS_EXECUTE_TOKEN=your-token-here
`

或将 token 写入 ~/.qoder/cpos/execute_token 文件（单行，无换行）。

## 验证安装

安装后在 Qoder 中打开任意项目，发一条消息。如果回复中出现：

`
[CPOS: framework_first | intent=execute | conf=20% | safety=NORMAL | turn=1]
`

则表示 CPOS 管道已成功激活。

## 更新

重新运行安装脚本即可覆盖更新所有文件。

## 安全边界

- 本配置不包含任何后端源码、密钥或私密逻辑
- runner.py 仅调用公开 API 端点
- cpos-execute token 由用户自行设置，不包含在仓库中
- 所有 CPOS API 调用走 HTTPS

## 相关链接

- [Xiaoyuan Codex Setup 主仓库](https://github.com/fuyufan-lab/xiaoyuan-codex-setup)
- [公共 API 文档](../PUBLIC_V3_API.md)
- [Codex 兼容恢复指南](../CODEX_COMPATIBILITY_RECOVERY.md)
