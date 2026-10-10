# Calorie estimation with fewer measurements

This is the research revision of
[Moobakr/calories-burnt-prediction](https://github.com/Moobakr/calories-burnt-prediction).
The original GitHub notebook is preserved in
[`notebooks/legacy/github/`](notebooks/legacy/github/Calories_burnt_prediction_project.ipynb)
as a historical reference. The commands below replace its execution workflow.

Research question: how much does prediction error change when heart rate and
body temperature are removed, and how does that change vary across represented
groups and workout durations?

**Status:** item 3 provides a reproducible environment and data preparation.
Partitioning, model training, and performance results belong to later items.
The target is the supplied benchmark's recorded calorie label. Collection
methods, label generation, and dataset licensing remain unresolved.

## Quick start (Windows PowerShell)

Install Python **3.12** (64-bit), then open PowerShell in this project folder.
Package installation needs internet access. Activation is unnecessary: the
commands explicitly use the isolated environment.

```powershell
& .\scripts\setup.ps1 -Python python
& .\.venv\Scripts\python.exe -m calorie_estimation stage --source "B:\calories\exercise.csv" --notebook "B:\calories\Calories_burnt_prediction_project.ipynb"
& .\scripts\prepare.ps1
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
future ML fits may differ across hardware or library builds.

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
fit a model. Learned preprocessing must be fitted within training folds in item 4.
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
```

`validate --data PATH` and `prepare --data PATH --output-dir PATH` support
explicit alternative locations. Defaults resolve relative to this checkout,
regardless of the calling directory after editable installation. The installed
console command `calorie-estimation` provides the same CLI.

## Project map

| Location | Purpose |
| --- | --- |
| `calorie_estimation/` | Validation, deterministic preparation, environment checks |
| `configs/project.toml` | Four input sets and planned evaluation settings |
| `data/dataset_manifest.json` | Frozen input fingerprint, schema, units and provenance limitations |
| `tests/` | Synthetic fixtures for failure modes and repeatability |
| `docs/` | Audit, research brief, experiment plan and implementation verification |
| `notebooks/legacy/` | Archived GitHub notebook and optional ignored local reference; never executed by these commands |

The four input sets are duration only; basic demographic measurements plus
duration; basic plus heart rate; and full inputs including body temperature.
Configuration loading rejects identifiers and targets as predictor columns.
Evaluation seeds and proportions are recorded now; no partitions exist yet.

Read [the brief](docs/PROJECT_BRIEF.md), [experiment plan](docs/EXPERIMENT_PLAN.md),
and [audit](docs/DATA_AUDIT.md) for study scope and limitations. The previous
notebook has already examined this dataset, so a new split cannot establish
previously unseen external validity. Raw data exclusion is an intentional
publication boundary, not a resolved license. No software license is selected
on the author's behalf yet.
