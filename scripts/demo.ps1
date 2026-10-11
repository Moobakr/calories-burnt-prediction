param([int]$Port = 7860)
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $ProjectRoot
try {
    & .\.venv\Scripts\python.exe -c "import waitress"
    if ($LASTEXITCODE -ne 0) {
        & .\.venv\Scripts\python.exe -m pip install -r demo/requirements-server.txt
        if ($LASTEXITCODE -ne 0) { throw "Demo serving dependency installation failed" }
    }
    if (-not (Test-Path -LiteralPath "runs/demo-space-v1/bundle/manifest.json")) {
        & .\.venv\Scripts\python.exe -m calorie_estimation.demo_package
        if ($LASTEXITCODE -ne 0) { throw "Demo packaging failed" }
    }
    & .\.venv\Scripts\python.exe -m calorie_estimation.demo_app --bundle runs/demo-space-v1/bundle --assets demo --port $Port
    if ($LASTEXITCODE -ne 0) { throw "Demo server failed" }
} finally { Pop-Location }
