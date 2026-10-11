param([string]$RunDirectory = "runs/baselines-v1")
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $ProjectRoot
try {
    & (Join-Path $PSScriptRoot "evaluate-setup.ps1")
    & .\.venv\Scripts\python.exe -m calorie_estimation baselines --run-dir $RunDirectory
    if ($LASTEXITCODE -ne 0) { throw "Baseline fitting failed" }
} finally { Pop-Location }
