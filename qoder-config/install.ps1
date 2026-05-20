<# 
  小元 x Qoder 配置一键安装脚本
  用法: irm https://raw.githubusercontent.com/fuyufan-lab/xiaoyuan-codex-setup/main/qoder-config/install.ps1 | iex
#>

$ErrorActionPreference = Stop
$repo = https://raw.githubusercontent.com/fuyufan-lab/xiaoyuan-codex-setup/main/qoder-config
$qoderDir = $env:USERPROFILE\.qoder

Write-Host === 小元 x Qoder 配置安装 === -ForegroundColor Cyan

# 1. 创建目录结构
$dirs = @(
    $qoderDir\rules,
    $qoderDir\skills\cpos-pipeline,
    $qoderDir\skills\swarm-dispatch,
    $qoderDir\agents,
    $qoderDir\cpos
)
foreach ($d in $dirs) {
    New-Item -ItemType Directory -Force -Path $d | Out-Null
}

# 2. 下载配置文件
$files = @{
    rules/always-cpos.md                    = $qoderDir\rules\always-cpos.md
    skills/cpos-pipeline/SKILL.md           = $qoderDir\skills\cpos-pipeline\SKILL.md
    skills/swarm-dispatch/SKILL.md          = $qoderDir\skills\swarm-dispatch\SKILL.md
    agents/coder.md                         = $qoderDir\agents\coder.md
    cpos/runner.py                          = $qoderDir\cpos\runner.py
}

foreach ($src in $files.Keys) {
    $dst = $files[$src]
    $url = $repo/$src
    Write-Host  下载: $src -ForegroundColor Gray
    Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $dst
}

Write-Host "
Write-Host 安装完成！ -ForegroundColor Green
Write-Host 文件已写入: $qoderDir -ForegroundColor Green
Write-Host "
Write-Host 接下来重启 Qoder（源）即可生效。 -ForegroundColor Yellow
