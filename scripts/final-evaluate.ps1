param([string]$BaselineRunDirectory = "runs/baselines-v1", [string]$ComparisonRunDirectory = "runs/input-comparison-v1", [string]$ReliabilityRunDirectory = "runs/reliability-v1", [string]$RunDirectory = "runs/final-evaluation-v1")
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $ProjectRoot
try {
    if (Test-Path -LiteralPath "runs/final-test-access.json") {
        throw "Reserved test already released. Inspect its recorded run; preserve the release record."
    }
    & (Join-Path $PSScriptRoot "evaluate-setup.ps1")
    & .\.venv\Scripts\python.exe -m calorie_estimation final-evaluate --baseline-run-dir $BaselineRunDirectory --comparison-run-dir $ComparisonRunDirectory --reliability-run-dir $ReliabilityRunDirectory --run-dir $RunDirectory
    if ($LASTEXITCODE -ne 0) { throw "Frozen final evaluation failed; preserve any test-release record and inspect the run." }
} finally { Pop-Location }
