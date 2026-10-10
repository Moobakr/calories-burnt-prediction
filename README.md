# Calorie estimation with fewer measurements

This is the research revision of
[Moobakr/calories-burnt-prediction](https://github.com/Moobakr/calories-burnt-prediction).
The original GitHub notebook is preserved in
[`notebooks/legacy/github/`](notebooks/legacy/github/Calories_burnt_prediction_project.ipynb)
as a historical reference. The commands below replace its execution workflow.

Research question: how much does prediction error change when heart rate and
body temperature are removed, and how does that change vary across represented
groups and workout durations?

**Status:** items 3–7 provide reproducible preparation, frozen partitions,
shared development CV folds, mean/Ridge baselines and a matched XGBoost input
comparison, plus subgroup, sensor-noise and prediction-interval audits.
**52 tests pass.** See [the reliability report](docs/RELIABILITY_REPORT.md)
for observed coverage gaps and noise sensitivity, [the input comparison](docs/INPUT_COMPARISON.md)
for error versus input requirements, prediction timings and limitations, or
[baseline results](docs/BASELINE_RESULTS.md) for the earlier linear milestone.
Development scores are tuning estimates. Calibration uses separate 1,500-row
interval-fit and interval-audit subsets; final test evaluation remains deferred.
The final system and real-world usefulness are not established.
The target is the supplied benchmark's recorded calorie label. Collection
methods, label generation, and dataset licensing remain unresolved.

## Quick start (Windows PowerShell)

Install Python **3.12** (64-bit), then open PowerShell in this project folder.
Package installation needs internet access. Activation is unnecessary: the
commands explicitly use the isolated environment.

```powershell
& .\scripts\setup.ps1 -Python python
& .\.venv\Scripts\python.exe -m calorie_estimation stage --source "B:\calories\exercise.csv" --notebook "B:\calories\Calories_burnt_prediction_project.ipynb"
& .\scripts\compare-inputs.ps1
& .\scripts\reliability.ps1
```

Substitute your own CSV path. `--notebook` is optional. If PowerShell blocks
scripts, run the equivalent commands listed below; changing a machine-wide
execution policy is unnecessary. The CSV must match the audited SHA-256. If it
does not, review the input and explicitly update the audit before adopting it.
There is no automatic download because the original source and license are
unresolved. Raw and derived observations stay local and are ignored by Git.

## What runs

`setup.ps1` creates `.venv` without system packages, installs the exact versions
in `requirements.lock.txt`, installs this project in editable mode, runs
`pip check`, and checks every pinned version plus imports of the ML libraries.
Python 3.12 is required; the verified patch version is recorded in the report.
The lock records versions, not wheel hashes. Other platforms are unverified;
ML fits may differ across hardware or library builds.

`prepare.ps1` validates the data, runs synthetic integrity tests, and writes:

- `data/processed/modeling_table.csv`: 14,999 rows, keeping source column order,
  units, category strings, and identifiers for traceability.
- `data/processed/deduplication_log.csv`: removed and retained source IDs and
  CSV row numbers (one-based, including the header).
- `data/processed/preparation_manifest.json`: input/output hashes, exact duplicate
  policy, code/configuration fingerprints, and row counts.
- `runs/environment.json` and `runs/validation.json`: local verification records.

The duplicate key includes all columns except `User_ID`, including the target.
It keeps the first occurrence in source order; numeric equality recognizes
equivalent spellings such as `39.5` and `39.50`. Only duplicate observations are
removed. Preparation does not encode categories, scale, impute, split data, or
fit a model. Learned preprocessing must be fitted within each training fold
when model fitting begins.
The preparation manifest is written last; later consumers must verify its
output hashes before use. Repeating preparation on the same input and code
produces identical table, log, and manifest bytes.

## Individual commands

```powershell
python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
& .\.venv\Scripts\python.exe -m pip install --no-build-isolation --no-deps -e .
& .\.venv\Scripts\python.exe -m pip check
& .\.venv\Scripts\python.exe -m calorie_estimation doctor --require-ml --output runs/environment.json
& .\.venv\Scripts\python.exe -m calorie_estimation validate --output runs/validation.json
& .\.venv\Scripts\python.exe -m unittest discover -s tests -v
& .\.venv\Scripts\python.exe -m calorie_estimation prepare
& .\.venv\Scripts\python.exe -m calorie_estimation split
& .\.venv\Scripts\python.exe -m calorie_estimation verify-splits
& .\.venv\Scripts\python.exe -m calorie_estimation baselines --run-dir runs/baselines-v1
& .\.venv\Scripts\python.exe -m calorie_estimation compare-inputs --baseline-run-dir runs/baselines-v1 --run-dir runs/input-comparison-v1
& .\.venv\Scripts\python.exe -m calorie_estimation reliability --baseline-run-dir runs/baselines-v1 --comparison-run-dir runs/input-comparison-v1 --run-dir runs/reliability-v1
```

`validate --data PATH` and `prepare --data PATH --output-dir PATH` support
explicit alternative locations. Defaults resolve relative to this checkout,
regardless of the calling directory after editable installation. The installed
console command `calorie-estimation` provides the same CLI.

`evaluate-setup.ps1` runs preparation and the test suite, then creates and
verifies frozen partitions: **8,999 development / 3,000 calibration / 3,000
test**, with five development-only CV folds shared across all four feature
sets. `split` and `verify-splits` accept `--prepared-dir` and `--split-dir`.
Existing allocations are protected against silent changes. See the
[evaluation protocol](docs/EVALUATION_PROTOCOL.md) for the exact algorithm,
allowed use of each partition, and preprocessing requirements.

`baselines.ps1` runs that setup workflow, then evaluates the training-target
mean and six Ridge alpha settings for each input set, using development rows
only. It selects Ridge alpha by mean-fold MAE and saves five development-fitted
pipelines with provenance and selected OOF predictions inside `runs/`.
Each run directory must be new; repeat with `-RunDirectory runs/baselines-repeat-1`.
Artifacts remain local and Git-ignored. The tracked
[aggregate metrics](docs/BASELINE_METRICS.json) contain candidate/fold scores,
versions, fit times, and source fingerprints, without per-record observations.

`compare-inputs.ps1` runs the same preparation checks, creates the baseline run
if missing, then searches 30 identical XGBoost configurations per input set on
the saved development folds. It verifies historical baseline hashes, IDs,
targets, folds and scores before comparison. It records 600 CV fits, four
development refits, input requirements and prediction timings; numeric tree
inputs retain their original units. Repeat with a new `-RunDirectory`.
The [aggregate comparison metrics](docs/INPUT_COMPARISON_METRICS.json) and
[PNG chart](docs/input_comparison.png) contain no new per-record observations.
Fitted pipelines and selected OOF records remain local under `runs/`.

`reliability.ps1` requires those completed baseline/comparison runs. It replays
the eight selected systems on the original folds (40 fits, no new search),
checks subgroup errors and paired simulated sensor noise, and fits fixed
90%-nominal split-conformal intervals using half the calibration partition.
The other half provides a disjoint interval audit. The
[aggregate reliability metrics](docs/RELIABILITY_METRICS.json) and
[figure](docs/reliability.png) document the results; local thresholds are bound
to exact saved model hashes and frozen for final testing. Audit results do not
change model selection or interval settings. Repeat with a new `-RunDirectory`;
the script preserves existing runs and never repeats the input search.

## Project map

| Location | Purpose |
| --- | --- |
| `calorie_estimation/` | Preparation, frozen evaluation, pipelines, baseline/XGBoost fitting, input comparisons, reliability audits and environment checks |
| `configs/project.toml` | Four input sets, evaluation settings, Ridge grid, fixed XGBoost search, timing and reliability protocols |
| `data/dataset_manifest.json` | Frozen input fingerprint, schema, units and provenance limitations |
| `tests/` | Synthetic fixtures for failure modes and repeatability |
| `docs/` | Audit, research brief, experiment plan and implementation verification |
| `notebooks/legacy/` | Archived GitHub notebook and optional ignored local reference; never executed by these commands |

The four input sets are duration only; basic demographic measurements plus
duration; basic plus heart rate; and full inputs including body temperature.
Configuration loading rejects identifiers and targets as predictor columns.
Frozen assignment files are local and Git-ignored, alongside raw and derived
observations. The development loader excludes calibration and test rows.

Read [the brief](docs/PROJECT_BRIEF.md), [experiment plan](docs/EXPERIMENT_PLAN.md),
and [audit](docs/DATA_AUDIT.md) for study scope and limitations. The previous
notebook has already examined this dataset, so a new split cannot establish
previously unseen external validity. Raw data exclusion is an intentional
publication boundary, not a resolved license. No software license is selected
on the author's behalf yet.
