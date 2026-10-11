# Item 4: frozen evaluation protocol

Implemented and verified on 10 October 2026. **29 tests passed. No benchmark
models have been fitted and no test performance has been evaluated.**

## Allocation

The audited duplicate is removed before partitioning. The 14,999 retained
observations are assigned once, using the recorded ID and split seed 42.

| Partition | Rows | Permitted use |
| --- | ---: | --- |
| Development | 8,999 | Training, cross-validation, hyperparameter and model selection |
| Calibration | 3,000 | Future uncertainty calibration after point-model choices are frozen |
| Test | 3,000 | Future evaluation of frozen model and interval choices |

Calibration and test counts are the ceiling of their configured fractions
times 14,999. Development receives the remainder. This implements the planned
60/20/20 allocation with explicit integer rounding.

Method: `sha256-id-ranking-v1`. Canonicalize each validated positive integer ID
to its integer string. Rank by SHA-256 of the UTF-8 string
`calorie-estimation:v1:partition:42:<ID>`, breaking any hash tie by numeric ID.
Assign the first 8,999 IDs to development, the next 3,000 to calibration, and
the last 3,000 to test. Features, calorie labels, and original row ordering do
not enter this allocation. The seed was not searched to improve results or
subgroup balance. No label stratification is used.

This is record-level allocation for the supplied benchmark's unique recorded
IDs. Distinct IDs do not prove distinct real participants. The implementation
rejects repeated IDs rather than applying this design to repeated-person data.
A future WEEE study requires a separately audited participant-aware protocol.

## Cross-validation

Development IDs are independently ranked by SHA-256 of
`calorie-estimation:v1:cv:43:<ID>`. CV seed 43 is recorded in configuration before
any new benchmark fit. In that order, assign validation fold `position % 5`,
using zero-based positions and fold numbers. Each development observation is
validated exactly once and trained on in the other four folds.

| Fold | Training rows | Validation rows |
| --- | ---: | ---: |
| 0 | 7,199 | 1,800 |
| 1 | 7,199 | 1,800 |
| 2 | 7,199 | 1,800 |
| 3 | 7,199 | 1,800 |
| 4 | 7,200 | 1,799 |

All four feature sets use the same development IDs, target ordering, and exact
train/validation index arrays. Primary hyperparameter selection uses the mean
of the five validation-fold MAEs, with lower error preferred. The balanced
folds differ by at most one observation. The experiment plan's eventual test
MAE, RMSE, paired bootstrap comparisons, and 10% margin remain unchanged.

## Leakage controls

- The prepared table must match a SHA-256 recorded in the tracked dataset
  manifest. Updating an editable local preparation manifest cannot authorize
  altered labels or measurements.
- Loading a split bundle verifies its input hashes, configured protocol,
  exact deterministic assignment bytes, partition counts, and CV sizes.
- Existing assignments cannot be silently reseeded, corrupted, or rebound
  to different data. A deliberate protocol/data revision needs a new output
  directory and a dated explanation in the experiment plan.
- `load_development(...)` returns only development predictors and targets,
  plus the shared CV indices. `User_ID` and `Calories` cannot be predictors.
- `make_preprocessor(...)` returns a new, unfitted transformer each time.
  Put it **inside** each estimator's scikit-learn `Pipeline` before passing
  that pipeline and the saved CV indices to a search API. Never fit it on the
  full table or on all development rows before cross-validation.
- Numeric scaling is available for Ridge; the tree path preserves numeric
  units. Gender is one-hot encoded using the declared schema levels, with
  unknown values rejected. No imputation is indicated by this frozen input.

Integrity validation reads the complete CSV, including labels. Those labels
are not used to allocate folds, select seeds, fit models, or score held-out
records in item 4. Holdout access is a workflow rule: files remain locally
readable, so this is not a security barrier against a researcher inspecting
them. If final test results later influence redesign, disclose it and seek
new independent evidence for confirmatory claims.

## Reproduce and verify

```powershell
& .\scripts\evaluate-setup.ps1
```

Or, after environment setup and staging:

```powershell
& .\.venv\Scripts\python.exe -m unittest discover -s tests -v
& .\.venv\Scripts\python.exe -m calorie_estimation prepare
& .\.venv\Scripts\python.exe -m calorie_estimation split
& .\.venv\Scripts\python.exe -m calorie_estimation verify-splits
```

Defaults write `data/splits/assignments.csv` and `split_manifest.json`. The CSV
contains each retained ID, partition, and development validation fold; it
contains no measurements or labels. Both files are Git-ignored. The manifest
records the input/output hashes, protocol, counts, and code fingerprints.
Repeated creation with the same inputs/code/configuration is byte-identical.
If preparation is rerun after code changes, regenerate the split bundle to
refresh provenance; the assignments stay identical for unchanged data and
allocation settings. Consumers reject stale input provenance.

Assignment CSV SHA-256:
`71c3e9b3c684896622933cd522712aca81f96c30123a6ec207dd554e1f0ac978`.

Independent checks on the actual CSV confirmed complete/disjoint coverage,
the duplicate's removal, matched IDs/folds across all four feature sets,
unfitted preprocessing factories, and byte-identical repeated split files.
All predefined gender, age, and duration groups are represented in each
partition; counts do not establish representativeness or reliable subgroup
performance. Local evidence is in `runs/item4_setup.log` and
`runs/evaluation_verification.json`.

The 29 synthetic tests cover source integrity, configuration errors, repeated
IDs, altered tables/assignments/manifests, protection of frozen allocations,
development-only and matched CV folds, feature-role exclusions, and
preprocessing independence and training-only statistics. No benchmark model
fit is hidden in these checks.

This dataset was already explored in the original notebook. Its new reserved
partition provides a controlled workflow for the new experiments; it does
not create genuinely unseen external evidence. Collection, calorie-label
generation, measurement units, and licensing retain the audit's limitations.

**Next: item 5**, fit the mean and regularized linear baselines using this
development-only path. Calibration and final test use remain deferred.
