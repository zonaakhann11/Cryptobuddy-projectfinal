#Requires -Version 5.1
<#
.SYNOPSIS
  Overnight final v2 training (does NOT overwrite v1 models).

.EXAMPLE
  .\scripts\train_final_v2.ps1
  .\scripts\train_final_v2.ps1 -Asset BTCUSDT
  .\scripts\train_final_v2.ps1 -Resume
#>
param(
  [ValidateSet("BTCUSDT", "ETHUSDT", "SOLUSDT", "")]
  [string]$Asset = "",
  [switch]$Resume
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $RepoRoot "backend"
$VenvActivate = Join-Path $Backend "venv\Scripts\Activate.ps1"

if (-not (Test-Path $VenvActivate)) {
  Write-Error "Virtual env not found at $VenvActivate"
}

Set-Location $RepoRoot
. $VenvActivate

$env:PYTHONPATH = "$Backend;$RepoRoot"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

New-Item -ItemType Directory -Force -Path (Join-Path $RepoRoot "experiments\logs") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $RepoRoot "experiments\checkpoints\final_v2") | Out-Null

$argsList = @("-m", "experiments.train_final_v2")
if ($Asset) {
  $argsList += @("--asset", $Asset)
} else {
  $argsList += "--all"
}
if ($Resume) {
  $argsList += "--resume"
}

Write-Host "Running: python $($argsList -join ' ')"
Write-Host "Log: experiments\logs\train_final_v2.log"
Write-Host "Checkpoints: experiments\checkpoints\final_v2\"
Write-Host "v1 models in backend\models\saved\ will NOT be modified."

python @argsList
exit $LASTEXITCODE
