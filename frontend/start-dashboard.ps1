# Portable Node — no system install required
$nodeDir = Join-Path $PSScriptRoot ".tools\node-v22.17.0-win-x64"
$env:PATH = "$nodeDir;$env:PATH"
Set-Location $PSScriptRoot
Write-Host "Using portable Node from $nodeDir"
node -v
npm -v
npm install
# Call vite directly with equals-form flags (PowerShell strips bare --host/--port)
npx --yes vite --host=127.0.0.1 --port=5173
