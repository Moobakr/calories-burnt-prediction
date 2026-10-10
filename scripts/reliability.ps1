param([string]$BaselineRunDirectory = "runs/baselines-v1", [string]$ComparisonRunDirectory = "runs/input-comparison-v1", [string]$RunDirectory = "runs/reliability-v1")
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $ProjectRoot
try {
    if (-not (Test-Path -LiteralPath (Join-Path $ComparisonRunDirectory "metrics.json") -PathType Leaf)) {
        throw "Run compare-inputs.ps1 first; reliability reuses its frozen models."
    }
    & (Join-Path $PSScriptRoot "evaluate-setup.ps1")
    & .\.venv\Scripts\python.exe -m calorie_estimation reliability --baseline-run-dir $BaselineRunDirectory --comparison-run-dir $ComparisonRunDirectory --run-dir $RunDirectory
    if ($LASTEXITCODE -ne 0) { throw "Reliability audit failed" }
} finally { Pop-Location }
