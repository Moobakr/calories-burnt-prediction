$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $ProjectRoot
try {
    & (Join-Path $PSScriptRoot "prepare.ps1")
    & .\.venv\Scripts\python.exe -m calorie_estimation split
    if ($LASTEXITCODE -ne 0) { throw "Frozen split creation failed" }
    & .\.venv\Scripts\python.exe -m calorie_estimation verify-splits
    if ($LASTEXITCODE -ne 0) { throw "Frozen split verification failed" }
} finally { Pop-Location }
