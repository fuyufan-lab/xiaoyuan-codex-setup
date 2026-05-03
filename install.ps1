param(
  [string]$InstallDir = "$env:USERPROFILE\.xiaoyuan-codex-setup",
  [string]$Branch = "main"
)

$ErrorActionPreference = "Stop"
$repo = "https://raw.githubusercontent.com/fuyufan-lab/xiaoyuan-codex-setup/$Branch"
$clientDir = Join-Path $InstallDir "client"
New-Item -ItemType Directory -Force -Path $clientDir | Out-Null

$manifestUrl = "$repo/releases/xiaoyuan/windows/latest.json"
$manifestPath = Join-Path $InstallDir "latest.json"
Invoke-WebRequest -UseBasicParsing -Uri $manifestUrl -OutFile $manifestPath
$manifest = Get-Content -Raw -Path $manifestPath | ConvertFrom-Json

$clientUrl = "$repo/client/xiaoyuan_client.py"
$clientPath = Join-Path $clientDir "xiaoyuan_client.py"
Invoke-WebRequest -UseBasicParsing -Uri $clientUrl -OutFile $clientPath

$expectedClientSha256 = $manifest.installable_payload.client_python_sha256
if (-not $expectedClientSha256) {
  throw "Manifest did not include client_python_sha256. Refusing to install."
}
$actualClientSha256 = (Get-FileHash -Algorithm SHA256 -Path $clientPath).Hash.ToLowerInvariant()
if ($actualClientSha256 -ne $expectedClientSha256.ToLowerInvariant()) {
  throw "Downloaded Xiaoyuan client hash mismatch. Expected $expectedClientSha256 but got $actualClientSha256."
}

$python = Get-Command py -ErrorAction SilentlyContinue
if ($python) {
  $pythonCmd = "py -3"
} else {
  $python = Get-Command python -ErrorAction SilentlyContinue
  if (-not $python) {
    throw "Python 3 is required. Install Python or ask Codex to follow CODEX_COMPATIBILITY_RECOVERY.md."
  }
  $pythonCmd = "python"
}

$cmdPath = Join-Path $InstallDir "xiaoyuan.cmd"
@"
@echo off
$pythonCmd "$clientPath" %*
"@ | Set-Content -Encoding ASCII -Path $cmdPath

$psPath = Join-Path $InstallDir "xiaoyuan.ps1"
@"
`$clientPath = "$clientPath"
if (Get-Command py -ErrorAction SilentlyContinue) {
  & py -3 `$clientPath @args
} else {
  & python `$clientPath @args
}
"@ | Set-Content -Encoding ASCII -Path $psPath

Write-Host "Xiaoyuan public client installed: $InstallDir"
Write-Host "Add this directory to PATH if needed: $InstallDir"
Write-Host "Next:"
Write-Host "  & '$psPath' install"
Write-Host "  & '$psPath' login"
Write-Host "  & '$psPath' doctor --strict"
Write-Host "  & '$psPath' start"
