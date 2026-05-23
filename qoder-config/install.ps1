<#
  Xiaoyuan x Qoder CPOS Pipeline Setup
  =====================================
  One-command install:
    irm https://raw.githubusercontent.com/fuyufan-lab/xiaoyuan-codex-setup/main/qoder-config/install.ps1 | iex
#>

Continue = 'Stop'
 = 'https://raw.githubusercontent.com/fuyufan-lab/xiaoyuan-codex-setup/main/qoder-config'
 =  C:\Users\WZ\.qoder

Write-Host ''
Write-Host '============================================' -ForegroundColor Cyan
Write-Host '  Xiaoyuan x Qoder CPOS Pipeline Setup' -ForegroundColor Cyan
Write-Host '============================================' -ForegroundColor Cyan
Write-Host ''

 = @(
    \rules,
    \skills\cpos-pipeline,
    \skills\swarm-dispatch,
    \skills\cpos-execute,
    \agents,
    \cpos
)
foreach ( in ) {
    New-Item -ItemType Directory -Force -Path  | Out-Null
}

 = @{
    'rules/always-cpos.md'           = \rules\always-cpos.md
    'skills/cpos-pipeline/SKILL.md'  = \skills\cpos-pipeline\SKILL.md
    'skills/swarm-dispatch/SKILL.md' = \skills\swarm-dispatch\SKILL.md
    'skills/cpos-execute/SKILL.md'   = \skills\cpos-execute\SKILL.md
    'agents/coder.md'                = \agents\coder.md
    'cpos/runner.py'                 = \cpos\runner.py
}

 = 0
 = 0

foreach ( in .Keys) {
     = []
     = /
    Write-Host ( [..]  + ) -ForegroundColor Gray -NoNewline
    try {
        Invoke-WebRequest -UseBasicParsing -Uri  -OutFile  -ErrorAction Stop
        Write-Host ' OK' -ForegroundColor Green
        ++
    } catch {
        Write-Host (' FAIL ' + .Exception.Message) -ForegroundColor Red
        ++
    }
}

Write-Host ''
Write-Host '============================================' -ForegroundColor Cyan
Write-Host ( Result:  +  +  ok  +  +  failed) -ForegroundColor ( -gt 0 ? 'Red' : 'Green')
Write-Host ( Installed to:  + ) -ForegroundColor White
Write-Host '============================================' -ForegroundColor Cyan
Write-Host ''
Write-Host 'Next steps:' -ForegroundColor Yellow
Write-Host '  1. Restart Qoder (Yuan) IDE' -ForegroundColor White
Write-Host '  2. Open any project, CPOS pipeline activates automatically' -ForegroundColor White
Write-Host '  3. You should see [CPOS: ...] header in responses' -ForegroundColor White
Write-Host ''
Write-Host 'Docs: https://github.com/fuyufan-lab/xiaoyuan-codex-setup/tree/main/qoder-config' -ForegroundColor Gray
