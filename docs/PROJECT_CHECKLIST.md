# Calorie estimation project checklist

Updated: 10 October 2026

- [x] Review the existing notebook.
- [x] 1. Audit the dataset. See DATA_AUDIT.md. Collection provenance, calorie-label generation, and dataset licensing remain unresolved.
- [x] 2. Finalize the research question and data strategy. See PROJECT_BRIEF.md and EXPERIMENT_PLAN.md. First milestone uses the existing CSV as an exploratory benchmark; WEEE is a proposed separate extension pending a readiness check.
- [x] 3. Make the project reproducible. See calorie-estimation/README.md and calorie-estimation/docs/REPRODUCIBILITY_REPORT.md. Isolated Python environment, pinned dependencies, frozen data manifest, deterministic preparation and 11 integrity tests verified. Integrated into the existing GitHub repository's history on local branch research/reproducibility; remote publication awaits authentication. Original files preserved; no models trained.
- [ ] 4. Establish trustworthy evaluation.
- [ ] 5. Build baseline models.
- [ ] 6. Compare accuracy against input requirements.
- [ ] 7. Investigate reliability, subgroup errors, noisy inputs, and uncertainty.
- [ ] 8. Tune and select the final model.
- [ ] 9. Build the demo.
- [ ] 10. Gather evidence of usefulness through a usability study.
- [ ] 11. Package the report, repository, demo, and measured contributions for applications.

Direction: calorie estimation with fewer measurements. The first milestone studies input requirements, error, and reliability on recorded benchmark labels. A proposed WEEE extension would investigate a documented energy-expenditure reference in a separate study. No new models have been trained under this plan.
