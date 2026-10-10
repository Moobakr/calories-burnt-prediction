# Calorie estimation project checklist

Updated: 10 October 2026

- [x] Review the existing notebook.
- [x] 1. Audit the dataset. See DATA_AUDIT.md. Collection provenance, calorie-label generation, and dataset licensing remain unresolved.
- [x] 2. Finalize the research question and data strategy. See PROJECT_BRIEF.md and EXPERIMENT_PLAN.md. First milestone uses the existing CSV as an exploratory benchmark; WEEE is a proposed separate extension pending a readiness check.
- [x] 3. Make the project reproducible. See calorie-estimation/README.md and calorie-estimation/docs/REPRODUCIBILITY_REPORT.md. Isolated Python environment, pinned dependencies, frozen data manifest, deterministic preparation and 11 integrity tests verified. Published on research/reproducibility in the existing repository; [PR #1](https://github.com/Moobakr/calories-burnt-prediction/pull/1) is attached to this chat. The publishing script recorded commit 6abc516. Original files preserved; no models trained.
- [x] 4. Establish trustworthy evaluation. See calorie-estimation/docs/EVALUATION_PROTOCOL.md. Frozen 8,999 / 3,000 / 3,000 development/calibration/test allocation, five shared development-only CV folds, verified input hashes and unfitted preprocessing implemented on local branch research/evaluation. All 29 tests passed; no benchmark models fitted or test results evaluated.
- [x] 5. Build baseline models. See BASELINE_RESULTS.md and BASELINE_METRICS.json. Mean and Ridge fitted on development only with the shared five folds; six alphas per Ridge input set, 125 CV fits and five development refits. All 36 tests passed. Pipelines reload identically, and independent output checks passed. Full-input Ridge development CV MAE 8.303 versus mean baseline 52.833; these are tuning estimates. Local branch research/baselines; calibration/test evaluation deferred.
- [x] 6. Compare accuracy against input requirements. See INPUT_COMPARISON.md and INPUT_COMPARISON_METRICS.json. Identical 30-configuration XGBoost search across four input sets: 600 shared-fold CV fits and four development refits. All 42 tests and independent output checks passed. XGBoost development MAE: duration 11.313, basic 8.242, heart-rate 1.080, full 1.117. Added input tradeoffs, tail-error diagnostics, prediction timings and comparison figures. Saved on local research/input-comparison; no calibration/test fitting or scoring.
- [ ] 7. Investigate reliability, subgroup errors, noisy inputs, and uncertainty.
- [ ] 8. Finalize model selection and evaluate frozen systems. The planned XGBoost search budget was completed in item 6; do not silently start a second search or use reserved test results to redesign models.
- [ ] 9. Build the demo.
- [ ] 10. Gather evidence of usefulness through a usability study.
- [ ] 11. Package the report, repository, demo, and measured contributions for applications.

Direction: calorie estimation with fewer measurements. The first milestone studies input requirements, error, and reliability on recorded benchmark labels. A proposed WEEE extension would investigate a documented energy-expenditure reference in a separate study. Mean/Ridge baselines and the nonlinear input comparison are complete on development data; reliability, final evaluation and impact evidence remain future work.
