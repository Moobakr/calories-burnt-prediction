param([string]$Python = "python")
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $ProjectRoot
try {
    & $Python -c "import sys; assert sys.version_info[:2] == (3, 12), 'Use Python 3.12'"
    if ($LASTEXITCODE -ne 0) { throw "Python 3.12 is required" }
    & $Python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw "Virtual environment creation failed" }
    & .\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
    if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed" }
    & .\.venv\Scripts\python.exe -m pip install --no-build-isolation --no-deps -e .
    if ($LASTEXITCODE -ne 0) { throw "Project installation failed" }
    & .\.venv\Scripts\python.exe -m pip check
    if ($LASTEXITCODE -ne 0) { throw "Dependency consistency check failed" }
    & .\.venv\Scripts\python.exe -m calorie_estimation doctor --require-ml --output runs/environment.json
    if ($LASTEXITCODE -ne 0) { throw "Environment verification failed" }
} finally { Pop-Location }
