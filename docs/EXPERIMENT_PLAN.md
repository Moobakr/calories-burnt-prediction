# Experiment plan

Version 1.0 — 10 October 2026. No new models have been trained for this plan.

## 1. Scope and hypotheses

The first milestone predicts recorded session calorie labels from the supplied CSV. The main comparison is basic versus full inputs. Heart-rate versus full inputs is the second planned comparison, used to isolate temperature's incremental value. Duration-only prediction is a diagnostic baseline.

Hypotheses to investigate, not conclusions:

1. A reduced input set may retain much of the full set's predictive performance.
2. Average performance may conceal different errors across represented groups and short versus long sessions.
3. Models may respond differently to noisy session measurements.

The file was already explored and a test split was previously evaluated in the original notebook. This plan is a prospective protocol for new experiments on a known benchmark, not a preregistered study on untouched data. Deviations will be dated and explained.

## 2. Data preparation

- Preserve the original CSV and record its SHA-256 in a data manifest.
- Derive a separate modeling table. Remove the later row of the documented identical observation pair, using features plus target and excluding ID to identify equality. Log the removed row and retain its source identity. This yields 14,999 observations if the audited input is unchanged.
- Keep ID for traceability, never as a predictor. Do not drop valid tail observations just because an IQR rule flags them.
- Validate the recorded gender categories and numeric schema. Reject unrecognized categories rather than silently mapping them to an existing category.
- Fit all learned transformations within training folds. Give each estimator its own preprocessing objects so fitting one cannot mutate another's pipeline.

This is a plan; the source files have not been cleaned or edited.

## 3. Partitioning and model selection

Planned proportions after duplicate handling: 60% development, 20% calibration, and 20% reserved test, using a recorded random seed (42). Exact counts and allocation checks belong to item 4. No repeated recorded IDs remain in the current file. Repeated participants in any later dataset must stay together across partitions.

Use five-fold cross-validation within the development partition to select hyperparameters. Fit preprocessing on each fold's training subset. Use matched folds across feature sets and algorithms. Do not use calibration or test labels to select features, algorithms, transformations, or search settings.

The calibration partition is reserved for item 7's uncertainty method. The test partition evaluates frozen model and interval choices. Avoid repeated test-driven redesign. Any deliberate return to development after seeing final results must be disclosed and would require new independent evidence for confirmatory claims.

## 4. Models and compute budget

| Model | Purpose | Planned selection |
| --- | --- | --- |
| Training-target mean | Sanity baseline | No tuning |
| Ridge regression | Simple regularized linear baseline | Tune regularization on development folds |
| XGBoost regression | Nonlinear comparison | Budget of 30 randomized configurations per input set |

Use the same algorithm-specific budget for each input set. Record model versions, random seeds, CPU/thread settings, fit time, and fitted parameters. Use scaling for Ridge inside its pipeline. Avoid redundant external scaling. Any early stopping must use development data only.

At first, compare the input sets within each algorithm so input effects are not confused with changes of model family. A final best system may also be selected using development scores, with the selection rule documented before test evaluation.

Latency will be measured on the same machine with a defined batch size, repeated measurements, and warmed-up prediction calls. Report the environment. Do not equate fewer model fits with a measured energy or carbon saving.

## 5. Outcomes and interpretation

Primary: MAE for each model and input set. Report absolute MAE differences and relative MAE changes against the same algorithm with full inputs. If the full model's MAE is zero, the relative change is undefined and the absolute difference will be reported instead.

Use paired bootstrap resampling of test observations (2,000 resamples, seed 2026) for an approximate 95% interval on each planned relative change. Pairing means comparing predictions on the same resampled records. This interval describes variation in the evaluated observations conditional on the fitted models; it does not include every source of training or measurement uncertainty.

The operational margin is 10% relative MAE degradation:

- Interval entirely at or below 10%: evidence of competitiveness under this benchmark rule.
- Interval entirely above 10%: evidence that the reduced set fails this rule.
- Interval crosses 10%: inconclusive under this rule.

Report point estimates, intervals, and the full comparison table even when the preferred approach loses. Secondary analyses are exploratory; no multiple-comparison significance claims are planned.

RMSE and error-distribution plots supplement MAE. Use a consistent target unit as interpreted in the audit. Avoid percentage error near the dataset's very small calorie labels. Never convert regression error into a fabricated classification-style accuracy percentage.

## 6. Reliability analyses

Predefine age bands 20–39, 40–59, and 60–79; duration bands 1–10, 11–20, and 21–30 minutes; and the recorded gender categories. Report each group's sample count and MAE. Treat gaps as descriptive error differences rather than proof of discrimination or comprehensive fairness.

Simulated noise experiment: add zero-mean noise to available session measurements, initially heart rate with standard deviations 2 and 5 beats/minute and temperature with standard deviations 0.1 and 0.3 in the recorded units. These are chosen stress-test settings, not validated device error specifications. Use fixed seeds, keep labels unchanged, and report how much the perturbations change error. A noise test is not an external validation study.

For missing sensors, route to the separately trained reduced-input model. Do not silently substitute zero or feed a basic record to a model expecting full inputs.

Item 7 will choose and document an uncertainty method, with a nominal 90% prediction-interval target as the initial setting. Evaluate empirical coverage and interval width overall and by the predefined groups. Calibration assumptions and any failure under shifted inputs must be stated. Prediction intervals and bootstrap intervals on MAE changes serve different purposes.

## 7. WEEE extension: readiness and boundaries

WEEE is the selected candidate for a research extension, not an adopted training dataset. Its documentation lists demographics, heart-rate devices, and other wearable channels. Temperature sources include skin and sensor temperatures, which must not be assumed equivalent to the original CSV's undocumented `Body_Temp`. See the [authors' dataset description](https://wearableenergyexpenditure.github.io/) and [study paper](https://www.nature.com/articles/s41597-022-01643-5).

Before adoption, inspect the archive and protocol to confirm the reference target or a justified derivation, exact units, synchronization, missingness, subject IDs, and candidate sensor availability. Do not use oxygen consumption, device-derived calorie outputs, or other variables used to construct the reference target as predictors in a supposed low-burden model.

If usable, create a separate tabular study based on documented, nonoverlapping time windows, with a precisely specified energy-expenditure target. Match windows across all sensor combinations and avoid future observations in predictors. Splits and any resampling must operate by participant, not randomly by window. Use participant-aware inner validation for tuning, and report participant-level performance so prolific recordings do not dominate.

With the small participant sample, subgroup conclusions will be exploratory. Raw high-frequency samples do not increase the number of independent participants. No deep time-series model is required: begin with transparent aggregated features and the same small set of regression families.

Do not pool WEEE and the supplied CSV, equate their target units without justification, or compare their MAE numbers as if they were the same benchmark. Independently training a WEEE model tests the research approach in another dataset; direct transport of the original fitted model would be a distinct experiment requiring compatible features and labels.

If the readiness check fails, document the reason and complete the first milestone with its limited claims. Selecting another dataset would require an explicit update to this brief before experiments.

## 8. Demonstration and impact evidence

The demo will load the saved evaluated pipeline, validate units and input ranges, support the available input sets, and explain uncertainty. SHAP explanations, if retained, must use the same fitted estimator and transformations as the displayed prediction. Feature contributions will not be labeled causal effects.

Plan a small usability pilot with approximately 5–10 volunteers before a larger study. Collect task completion, time, and comprehension of the estimate and its uncertainty. Use supplied fictional scenarios so personal biometric data is unnecessary. Record consent for participation and retain only the study information needed for analysis. Findings describe usability, not calorie-measurement accuracy or health outcomes.

Portfolio evidence should distinguish planned work from completed work, existing baselines from original contributions, and benchmark performance from measured user benefit. The final report will state limitations and failed experiments alongside successful findings.
