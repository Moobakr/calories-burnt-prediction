param([string]$BaselineRunDirectory = "runs/baselines-v1", [string]$RunDirectory = "runs/input-comparison-v1")
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $ProjectRoot
try {
    & (Join-Path $PSScriptRoot "evaluate-setup.ps1")
    if (-not (Test-Path -LiteralPath (Join-Path $BaselineRunDirectory "metrics.json") -PathType Leaf)) {
        & .\.venv\Scripts\python.exe -m calorie_estimation baselines --run-dir $BaselineRunDirectory
        if ($LASTEXITCODE -ne 0) { throw "Baseline fitting failed" }
    }
    & .\.venv\Scripts\python.exe -m calorie_estimation compare-inputs --baseline-run-dir $BaselineRunDirectory --run-dir $RunDirectory
    if ($LASTEXITCODE -ne 0) { throw "Input comparison failed" }
} finally { Pop-Location }
