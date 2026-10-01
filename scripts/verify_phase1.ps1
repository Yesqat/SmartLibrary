param([switch]$E2E)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$projectPython = Join-Path $projectRoot 'backend/.venv/Scripts/python.exe'
$env:npm_config_cache = Join-Path $projectRoot 'work/npm-cache'
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path $projectRoot 'work/playwright'
$env:NEXT_TELEMETRY_DISABLED = '1'

function Invoke-Checked([scriptblock]$Command) {
    & $Command
    if ($LASTEXITCODE -ne 0) { throw "Verification failed with exit code $LASTEXITCODE" }
}

Push-Location $projectRoot
try {
    Invoke-Checked { & $projectPython scripts/export_openapi.py --check }
    Invoke-Checked { & backend/.venv/Scripts/ruff.exe check --config backend/pyproject.toml scripts }
    Invoke-Checked { & backend/.venv/Scripts/ruff.exe format --check --config backend/pyproject.toml scripts }
    Push-Location backend
    try {
        Invoke-Checked { & .venv/Scripts/ruff.exe check . }
        Invoke-Checked { & .venv/Scripts/ruff.exe format --check . }
        Invoke-Checked { & .venv/Scripts/mypy.exe app }
        Invoke-Checked { & .venv/Scripts/pytest.exe -q }
    } finally { Pop-Location }
    Push-Location frontend
    try {
        $beforeTypes = (Get-FileHash types/api.generated.ts -Algorithm SHA256).Hash
        Invoke-Checked { npm run api:generate }
        if ((Get-FileHash types/api.generated.ts -Algorithm SHA256).Hash -ne $beforeTypes) {
            throw 'API types were out of date; review the regenerated file and rerun checks.'
        }
        Invoke-Checked { npm run lint }
        Invoke-Checked { npm run typecheck }
        Invoke-Checked { npm test }
        Invoke-Checked { npm run format:check }
        Invoke-Checked { npm run build }
        if ($E2E) { Invoke-Checked { npm run test:e2e } }
    } finally { Pop-Location }
} finally { Pop-Location }
Write-Output 'PHASE 1 local verification passed'
