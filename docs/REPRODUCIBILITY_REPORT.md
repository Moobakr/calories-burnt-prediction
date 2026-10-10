# Item 3 verification

Completed on 10 October 2026. **All checks passed.** No models were trained and
no development/calibration/test partitions were created.

## Verified environment

An isolated Python **3.12.14**, Windows AMD64 environment was created in `.venv`.
`include-system-site-packages = false`; the user site is disabled. All 21 pinned
package versions match `requirements.lock.txt`. Imports of NumPy, pandas,
SciPy, scikit-learn, XGBoost, matplotlib, joblib, and threadpoolctl passed.
`pip check` found no broken requirements. The project was installed in editable
mode. Both PowerShell workflow scripts completed successfully.

## Verified data path

1. Stage local CSV and legacy notebook without executing notebook cells.
2. Verify raw CSV fingerprint, exact header, row count, numeric values,
   category values, unique IDs, and expected duplicate count.
3. Retain the first of the identical observations and write a derived table
   of **14,999 rows**. The log records removed ID `17668038` at CSV row 12854,
   retaining ID `11602373` at CSV row 8268.
4. Repeat preparation and compare complete bytes: table, duplicate log, and
   preparation manifest were identical on both runs.
5. Confirm the staged CSV and notebook remain byte-identical to the supplied
   originals. Source files were not edited.

| Artifact | SHA-256 |
| --- | --- |
| Raw CSV | `411400c2854c99ba508c54d05926d3f826fdb2f7d42dc9d4882b24b2a52d3600` |
| Legacy notebook at staging | `6af4737a6a9ec14648f52de3653ff6bca6e5c69dd6cfadf19aac8d18726fb23a` |
| Archived original GitHub notebook | `94ec50e6c8ba3fb8f6bf91874ad38f7e782733754db4ee7d3812e6de1b2feab6` |
| Modeling table | `ddc094b3afa3776d06e1b12879e5ed044c30966cd69a36e7bc30984b6d0c906b` |
| Duplicate log | `b3d657757caf3ce7340fc090f3785535b216acc9a05a04587309044b15b537e9` |
| Preparation manifest | `9a30f4dcafd1561062aeb15dd6cf78aafbf9abd899991bfc00b5ba0d42b99748` |

Manifest hashes describe this implementation revision. Changing tracked code,
configuration, tests, or scripts changes its recorded project fingerprints.

## Integrity tests

**11 tests passed.** Synthetic fixtures cover changed input bytes, unknown
categories, invalid/nonfinite/nonpositive/fractional numeric values, incorrect
headers and ragged rows, duplicate IDs, incorrect row counts, duplicate
handling that includes the target, deterministic output, protection of the
source file, exclusion of IDs and target from feature sets, and CLI execution
from another directory after installation.

## Repository and evidence

The work is integrated into the existing `Moobakr/calories-burnt-prediction`
history on local branch `research/reproducibility`, based on upstream commit
`20a9802`, preserving all eight upstream commits. The original GitHub notebook is preserved byte for byte under
`notebooks/legacy/github/`. The root README describes the current study rather
than repeating the earlier unverified health-coaching claims. Remote publication
is pending GitHub authentication.

The `.gitattributes` rules keep source text in LF format and disable newline
conversion for notebooks and CSVs. The archived notebook's bytes match the
original Git blob, rather than a Windows checkout with converted line endings.

Git exclusion checks passed for raw and derived observations, the local
provenance registration, the separately supplied local notebook, and the
environment. The source ZIP excludes these local artifacts and Git metadata;
it includes the already tracked historical GitHub notebook.

Detailed local evidence is saved in ignored files under `runs/`:
`setup.log`, `prepare.log`, `verification.log`, `environment.json`,
`validation.json`, and `item3_verification.json`. Re-run the README commands to
regenerate environment and preparation records; the source archive contains
this report, while machine-specific logs remain local.

This verifies the software setup and deterministic data preparation on this
machine. It does not establish real-world label accuracy, resolved dataset
licensing, cross-platform reproducibility, model performance, or user impact.
Those questions retain the boundaries documented in the research brief.

**Next: item 4**, implement the recorded partitioning and validation protocol
before fitting any model.
