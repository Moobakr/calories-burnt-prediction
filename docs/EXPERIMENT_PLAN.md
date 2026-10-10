# Experiment plan

Version 1.4 — 11 October 2026. Item 7 fixes the reliability and uncertainty protocol below before reading calibration labels for analysis. Earlier results are in BASELINE_RESULTS.md and INPUT_COMPARISON.md; item 7 results are in RELIABILITY_REPORT.md.

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

Items 3 and 4 implement this preparation in a derived table; the original source files remain unchanged.

## 3. Partitioning and model selection

Implemented proportions after duplicate handling: 60% development, 20% calibration, and 20% reserved test, using seed 42. Ceiling the calibration and test counts and assigning the remainder to development yields 8,999 / 3,000 / 3,000 rows. Item 4 ranks SHA-256 hashes of canonical ID, purpose, and seed; allocation is independent of source row order and calorie labels. No label stratification or seed search is used. Exact construction and verification are documented in [EVALUATION_PROTOCOL.md](EVALUATION_PROTOCOL.md). No repeated recorded IDs remain in the current file. Repeated participants in any later dataset must stay together across partitions.

Use five-fold cross-validation within development, selecting hyperparameters by mean validation-fold MAE. The fixed folds use separately ranked IDs with CV seed 43, recorded before new benchmark fitting; validation sizes are 1,800 / 1,800 / 1,800 / 1,800 / 1,799. Fit preprocessing on each fold's training subset inside its estimator pipeline. Use the same saved folds across feature sets and algorithms. Do not use calibration or test labels to select features, algorithms, transformations, or search settings. Deliberate data/protocol revisions require a new split output directory and a dated explanation.

The calibration partition is reserved for item 7's uncertainty method. The test partition evaluates frozen model and interval choices. Avoid repeated test-driven redesign. Any deliberate return to development after seeing final results must be disclosed and would require new independent evidence for confirmatory claims.

## 4. Models and compute budget

| Model | Purpose | Planned selection |
| --- | --- | --- |
| Training-target mean | Sanity baseline | No tuning |
| Ridge regression | Simple regularized linear baseline | Tune regularization on development folds |
| XGBoost regression | Nonlinear comparison | Budget of 30 randomized configurations per input set |

Use the same algorithm-specific budget for each input set. Record model versions, random seeds, CPU/thread settings, fit time, and fitted parameters. Use scaling for Ridge inside its pipeline. Avoid redundant external scaling. Any early stopping must use development data only.

Item 5 baseline protocol, fixed before benchmark fitting: Ridge alpha grid `[0.01, 0.1, 1, 10, 100, 1000]`, SVD solver, fitted intercept, and one CPU thread. Select the lowest unweighted mean of the five validation-fold MAEs; exact ties choose the smaller alpha. Standardize numeric inputs within each training fold and use the schema-defined gender encoding. The mean baseline uses each fold's training-target mean and has no input requirement. It is evaluated once because its predictions are identical across input sets. There is no stochastic estimator seed for either baseline.

Record all candidate/fold scores and fit times. Retain development out-of-fold predictions for the selected settings locally; report both mean-fold scores and pooled out-of-fold scores with distinct names. The selected Ridge CV scores reuse the alpha-selection folds and may be optimistic after tuning; they are development estimates, not an independent generalization estimate. Refit each selected pipeline on all 8,999 development rows, save it locally with provenance, and verify save/load prediction parity. Neither calibration nor test data enter fitting or scoring. Final evaluation remains deferred until model choices are frozen.

Item 6 settings, fixed before nonlinear benchmark fitting: sample 30 distinct configurations without replacement using scikit-learn ParameterSampler and search seed 44. Use the same ordered sample for every input set, XGBoost model seed 45, squared-error objective, histogram trees and one CPU thread. The finite search space is `n_estimators=[200,400,600]`, `max_depth=[2,3,4,6]`, `learning_rate=[0.03,0.05,0.1]`, `min_child_weight=[1,5,10]`, `subsample=[0.8,1]`, `colsample_bytree=[0.8,1]`, `reg_lambda=[1,5,10]`, `reg_alpha=[0,0.1,1]`. No early stopping or evaluation set is used. Numeric inputs retain their units; gender uses the same schema encoding inside each fold's pipeline. Select by mean-fold MAE, breaking exact ties by the lower sampled candidate index. Refit each selected pipeline on development only and verify persistence.

This is 600 XGBoost CV fits plus four development refits. Candidate/fold scores, parameters and OOF predictions are recorded. Input comparisons report mean-fold MAE differences and relative changes against full inputs within each algorithm, plus pooled OOF errors as separately labeled diagnostics. No bootstrap competitiveness decision is made from these tuning estimates; the predefined paired test bootstrap remains deferred. The Ridge and XGBoost tuning budgets differ, so the cross-algorithm comparison is descriptive. Item 8 will freeze the final systems and selection decisions; item 6 does not open a second XGBoost search budget.

At first, compare the input sets within each algorithm so input effects are not confused with changes of model family. A final best system may also be selected using development scores, with the selection rule documented before test evaluation.

Latency will be measured on the same machine with a defined batch size, repeated measurements, and warmed-up prediction calls. Report the environment. Do not equate fewer model fits with a measured energy or carbon saving.

For item 6, measure saved development-fitted Ridge and XGBoost pipelines on the first 1 and first 100 development records in canonical ID order, using 10 warm-up calls and 100 timed calls per batch, one CPU thread and a monotonic high-resolution timer. Report median and 95th-percentile milliseconds per batch, excluding model loading and input parsing. Timing order is Ridge then XGBoost, each in configured input-set order; results are machine-specific diagnostics, not service latency guarantees. Input-field counts and heart-rate/temperature requirements describe available columns, not measured monetary cost or usability burden.

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

Item 7 uses symmetric, constant-width split-conformal intervals at nominal 90% coverage for all eight selected Ridge/XGBoost pipelines. No new hyperparameter search or model-family selection is performed. Each saved model remains fitted on the 8,999 development observations. Within the existing 3,000-row calibration partition, rank canonical IDs by SHA-256 of `calorie-estimation:v1:calibration-role:46:<ID>`; assign the first floor(n/2) to interval fitting and the rest to interval auditing. This gives 1,500 / 1,500 records, with unchanged global partitions. Save roles before loading their labels for interval analysis. Neither calibration subset trains a point predictor or chooses a model, feature set, nominal level, or interval method.

For each frozen predictor, use absolute residuals on interval-fit records. With n residuals, let k = ceil((n+1)*0.90) and take the kth sorted residual, without interpolation (k=1,351 for n=1,500). The interval is prediction plus/minus this residual threshold. If k exceeds n, the threshold is infinite rather than silently capped. Do not clip point predictions or interval bounds. Persist the threshold bound to the exact saved pipeline hash. Audit clean coverage, mean width and subgroup coverage on the disjoint interval-audit records, with sample counts. Do not describe coverage on the quantile-fitting subset as independent validation. Freeze these thresholds for final testing; do not incorporate audit labels afterward or redesign the method from audit results. Final selection in item 8 must use the recorded development criterion, not interval-audit scores.

Before inspecting calibration results, fix the item 8 primary-model selection rule to the lowest recorded mean-fold development MAE across the eight selected systems, breaking exact ties by fewer input fields then model name. The item 6 scores currently favor XGBoost with heart rate and without temperature. Reliability audits cannot change that selection rule; a failure is reported as a limitation rather than used to choose a winner from calibration results. All planned within-algorithm input comparisons remain available for the final test.

Development error/subgroup tables use the previously selected out-of-fold predictions, never predictions from an all-development refit on its own training rows. Selection reused these folds, so the diagnostics remain exploratory tuning analyses. Report MAE, RMSE and 95th-percentile absolute error by recorded gender and the predefined age/duration bands. No intersectional fairness or causal claims are planned.

Noise stress tests use 20 Gaussian draws per observation with seed 47. Perturb one sensor at a time at the predefined standard deviations, without rounding or clipping; labels remain unchanged. For each partition/column, initialize a NumPy generator from the first eight big-endian bytes of SHA-256 of `calorie-estimation:v1:noise:47:<partition>:<column>`, and draw a (20, n) standard-normal matrix in canonical ID order. Reuse that matrix across algorithms/input sets and across the two magnitudes for that sensor. Partitions use separate streams. Refit only the eight already-selected settings on the five saved development folds (40 fits), check clean OOF predictions against the saved records, and score noisy fold-held-out predictions. Reuse saved development-fitted models for interval-audit noise checks; thresholds remain fixed. Report mean MAE/RMSE and coverage across draws, draw standard deviations (not confidence intervals), changes from clean errors, and rates outside development feature ranges. Models without the perturbed sensor must remain unaffected. Calibrated intervals have no promised coverage under these artificial shifts.

Split-conformal marginal coverage requires exchangeability between calibration and future observations conditional on a predictor fitted independently of calibration; it does not guarantee per-group or per-person coverage. This benchmark does not establish those assumptions in real deployment. See [Angelopoulos and Bates, A Gentle Introduction to Conformal Prediction](https://arxiv.org/abs/2107.07511). The disjoint audit is a diagnostic, with finite-sample variation, not final-test evidence. Prediction intervals and bootstrap intervals on MAE changes serve different purposes. The reserved 3,000-row test set remains unused in item 7.

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
