$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $ProjectRoot
try {
    & .\.venv\Scripts\python.exe -m calorie_estimation doctor --require-ml --output runs/environment.json
    if ($LASTEXITCODE -ne 0) { throw "Environment verification failed" }
    & .\.venv\Scripts\python.exe -m calorie_estimation validate --output runs/validation.json
    if ($LASTEXITCODE -ne 0) { throw "Data validation failed" }
    & .\.venv\Scripts\python.exe -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) { throw "Integrity tests failed" }
    & .\.venv\Scripts\python.exe -m calorie_estimation prepare
    if ($LASTEXITCODE -ne 0) { throw "Data preparation failed" }
} finally { Pop-Location }
