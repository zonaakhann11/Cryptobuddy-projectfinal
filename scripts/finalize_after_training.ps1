#Requires -Version 5.1
<#
.SYNOPSIS
  After overnight training: build comparison tables / manifest.
  Pass -EnableV2 only when you are ready for the dashboard to prefer v2.

.EXAMPLE
  .\scripts\finalize_after_training.ps1
  .\scripts\finalize_after_training.ps1 -EnableV2
#>
param(
  [switch]$EnableV2
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $RepoRoot "backend"
$VenvActivate = Join-Path $Backend "venv\Scripts\Activate.ps1"

Set-Location $RepoRoot
. $VenvActivate
$env:PYTHONPATH = "$Backend;$RepoRoot"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

$argsList = @("-m", "experiments.finalize_after_training")
if ($EnableV2) {
  $argsList += "--enable-v2"
}

Write-Host "Running: python $($argsList -join ' ')"
python @argsList
exit $LASTEXITCODE
