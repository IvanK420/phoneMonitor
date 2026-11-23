# Lance les deux suites : agent (pytest) et panneau (node --test).
# Usage : .\run-tests.ps1            -> tests rapides
#         .\run-tests.ps1 -System    -> inclut les tests sur les vraies sources
param([switch]$System)

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

$python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) { $python = 'python' }

Write-Host "`n== Agent (pytest) ==" -ForegroundColor Cyan
if ($System) { & $python -m pytest -q -m 'system or not system' } else { & $python -m pytest -q }
$agentCode = $LASTEXITCODE

Write-Host "`n== Panneau (node --test) ==" -ForegroundColor Cyan
node --test "tests/panel/**/*.test.js"
$panelCode = $LASTEXITCODE

if ($agentCode -ne 0 -or $panelCode -ne 0) {
    Write-Host "`nECHEC (agent=$agentCode, panneau=$panelCode)" -ForegroundColor Red
    exit 1
}
Write-Host "`nTout est vert." -ForegroundColor Green
