#Requires -Version 5.1
<#
.SYNOPSIS
  Fast v2 training on the CSVs you already have (no overnight run).

  - Uses backend/data/historical/*_hourly.csv (full history in those files)
  - 1-hour horizon only (skips 4h)
  - GradientBoosting + ExtraTrees only (lighter trees)
  - Does NOT overwrite production models in backend/models/saved/
  - Writes to backend/models/saved_v2/

  Typical wall time: ~30–90 minutes for all three assets (machine-dependent).

.EXAMPLE
  .\scripts\train_final_v2_quick.ps1
  .\scripts\train_final_v2_quick.ps1 -Asset BTCUSDT
  .\scripts\train_final_v2_quick.ps1 -Resume
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

$argsList = @("-m", "experiments.train_final_v2", "--quick")
if ($Asset) {
  $argsList += @("--asset", $Asset)
} else {
  $argsList += "--all"
}
if ($Resume) {
  $argsList += "--resume"
}

Write-Host "QUICK train: existing hourly CSVs, 1h horizon, GB+ExtraTrees"
Write-Host "Running: python $($argsList -join ' ')"
Write-Host "Log: experiments\logs\train_final_v2.log"
Write-Host "Models out: backend\models\saved_v2\ (production saved\ untouched)"
Write-Host "When done, compare metrics then: .\scripts\finalize_after_training.ps1 -EnableV2"

python @argsList
exit $LASTEXITCODE
