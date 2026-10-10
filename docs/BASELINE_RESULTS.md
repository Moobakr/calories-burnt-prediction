# Baseline development results

Item 5 snapshot — 10 October 2026. Mean and Ridge baselines are implemented and fitted. **All 36 tests passed.** These are development tuning results; calibration and test evaluation remain deferred.

## Results

Scores are the unweighted mean of five saved validation-fold scores on 8,999 development observations. Units are interpreted kcal/session; the original label-generation method is unknown. Lower is better. Ridge scores reuse the folds used to choose alpha and may be optimistic after selection.

| Baseline / inputs | Selected alpha | Mean-fold MAE | Mean-fold RMSE | Negative OOF predictions |
| --- | ---: | ---: | ---: | ---: |
| mean | — | 52.833 | 62.191 | 0 |
| ridge_duration | 100.0 | 13.298 | 18.274 | 432 |
| ridge_basic | 100.0 | 11.988 | 16.021 | 574 |
| ridge_heart_rate | 10.0 | 9.558 | 12.656 | 646 |
| ridge_full | 10.0 | 8.303 | 11.284 | 448 |

The mean baseline has no input requirement and predicts the training-target mean separately within each fold. Duration uses only session duration. Basic adds recorded gender, age, height, and weight. Heart-rate adds heart rate to basic; full also includes body temperature. All models see identical development observations and folds. The selected pipelines were then fitted on all development rows, without holdout scoring.

These results establish reference errors for the nonlinear comparison in item 6. The full-input linear model has the lowest observed development error among these baselines. This does not settle which input set is competitive under the planned final-test margin, and it does not demonstrate real-world calorie-measurement accuracy or user impact.

Negative predictions are an additional descriptive diagnostic computed from saved OOF predictions after fitting. Linear regression does not enforce physical constraints. Predictions are reported as produced: no clipping, outlier removal, or test-driven adjustments were made. A later demo must address this limitation through a documented development decision.

## Fixed fitting procedure

- Grid: alpha `[0.01, 0.1, 1, 10, 100, 1000]` for each Ridge input set; SVD solver, fitted intercept, one CPU thread. Exact MAE ties choose smaller alpha. No stochastic estimator seed is needed.
- Numeric scaling is fitted inside each training-fold pipeline. Gender encoding uses the audited schema categories. IDs and the target are excluded from predictors.
- 125 CV fits: five mean fits and 30 Ridge fits for each of four input sets. Five final development refits. Candidate/fold scores, fit times, selected hyperparameters, versions and provenance are in [BASELINE_METRICS.json](BASELINE_METRICS.json).
- Python 3.12.14, scikit-learn 1.8.0, AMD64. Verified one-thread native pools. Sum of measured estimator-fit time: 2.545 seconds for CV and 0.069 seconds for refits on this machine. This excludes preparation, imports, scoring and serialization and is not a latency or energy measurement.

The alpha grid and selection rule were added to experiment plan v1.2 before benchmark fitting. The metrics record that plan's SHA-256 and the exact code/config/environment fingerprints. This is a prospective setting for a previously explored benchmark, not a preregistered untouched-data study.

## Reproduce and inspect

After setup and staging the audited CSV, run from the project root:

```powershell
& .\scripts\baselines.ps1
```

The script validates the environment/input, runs tests, prepares the table, verifies frozen assignments and fits baselines. Existing run directories are preserved; for a repeat use `-RunDirectory runs/baselines-repeat-1`. With preparation already verified, `& .\.venv\Scripts\python.exe -m calorie_estimation baselines --run-dir runs/baselines-repeat-1` uses the same fitting path.

Local, Git-ignored `runs/baselines-v1/` contains five `.joblib` pipelines, `development_oof.csv`, the complete `metrics.json` provenance report, and an independent `verification.json` from this run. Each saved pipeline was reloaded and produced exactly matching predictions on development inputs. The mean pipeline accepts a placeholder input frame but ignores its values; Ridge requires its declared column names. All fitted pipelines belong to this development milestone; they are not final test-selected demo models.

The tracked JSON contains aggregate results only. Per-record IDs, labels and predictions, raw/derived data, fitted artifacts, and absolute machine paths are excluded from publication. Pooled OOF metrics and mean-fold metrics are distinctly named because averaging fold RMSE is different from taking RMSE over all predictions.

## Verification and limits

The 36-test suite includes synthetic checks of fold-local target means, training-only scaling, deterministic scoring, metric formulas, selection tie-breaking, invalid grids/folds, holdout exclusion, model persistence and overwrite prevention. Independent checks on this run recomputed fold and pooled errors from saved OOF records, verified alpha choices, all-development scaler statistics, artifact hashes, unchanged source/assignment hashes and Git exclusions. Only development labels were used for fitting, selection and scoring. Integrity validation reads the full CSV to check hashes and schema; the workflow is not an access-control lock on local holdout files.

The original dataset's provenance, license, target method and interpreted units remain unresolved. The legacy notebook already explored the dataset. These baseline results support a reproducible research workflow, not external validation, health claims, or a completed impact study. Next: item 6, nonlinear modeling and the planned comparison of error against input requirements.
