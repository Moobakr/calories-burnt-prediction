# Dataset audit: calorie expenditure project

Audit date: 10 October 2026

**Decision: retain this file as an exploratory benchmark. Its structural quality is good, but the evidence does not establish the origin or validity of its calorie labels. It cannot currently support a claim of accurate calorie measurement for real people.**

The audit is complete. Questions about collection, label generation, and licensing remain unresolved and are recorded below rather than filled with assumptions.

## 1. Files and scope

The supplied folder contains one notebook and one CSV:

- `B:\calories\Calories_burnt_prediction_project.ipynb`
- `B:\calories\exercise.csv`

Despite its name, the local CSV already includes the `Calories` target alongside the exercise inputs. No additional calories file is required to read this local table. No README, license, data dictionary, collection protocol, or source link accompanies these files. The user does not remember the download source.

The audit parsed every CSV record and inspected the notebook as data. It did not execute notebook cells, train models, clean the source file, or change either supplied file. Checks cover schema, missing values, numeric parsing, finite values, signs, duplicate records, recorded identifiers, ranges, category counts, correlations, and provenance.

## 2. Provenance and license

The likely source is Fernando Fernandez's [fmendes-DAT263x-demos on Kaggle](https://www.kaggle.com/datasets/fmendes/fmendesdat263xdemos). Its live data card lists the license as **Unknown**. Its description, collection methodology, sources, citations, geographic coverage, and temporal coverage are absent. These observations were verified in the browser on the audit date.

The publisher's [Exercise and calories notebook](https://www.kaggle.com/code/fmendes/exercise-and-calories) reads separate exercise and calories files and joins them by `User_ID`. Its displayed first five joined records match the local CSV numerically, and its calorie summary agrees with the local count, mean, standard deviation, quartiles, and range. This is strong evidence of shared lineage, but no full upstream file comparison was performed. Record the source as a **likely match**, not a verified original collection source. That notebook's Apache 2.0 license does not resolve the dataset's unknown license.

### What remains unknown

- Whether the records describe observed people, simulated people, or a mixture.
- Whether calorie labels came from calorimetry, a wearable, an equation, or a simulation.
- The device, protocol, calibration, uncertainty, and measurement timing for heart rate and temperature.
- Whether calories represent active expenditure or total expenditure over the session.
- Sampling location, recruitment, activity types, fitness levels, and inclusion criteria.
- The conditions under which the dataset may be redistributed.

**Neither cleanliness, correlations, nor low prediction error proves that a dataset is synthetic or that its labels are measured. This audit makes neither assertion.** Resolving these questions requires documentation from the creator or a traceable original source. No creator was contacted.

## 3. Structure and integrity

| Check | Result | Implication |
| --- | ---: | --- |
| Records | 15,000 | Sufficient volume for exploratory tabular experiments |
| Columns | 9 | Identifier, seven inputs, one target |
| Blank/missing cells | 0 | No missing-value imputation is indicated by this file |
| Numeric parse failures | 0 | All eight numeric columns parse successfully |
| Nonfinite numeric values | 0 | No NaN or infinity after parsing |
| Nonpositive values in numeric columns | 0 | No zero/negative numeric values to investigate |
| Distinct recorded user IDs | 15,000 | No repeated IDs in this table |
| Duplicate rows including ID | 0 | Every complete row is distinct |
| Duplicate rows excluding ID | 1 extra row in one pair | A duplicate observation exists despite distinct IDs |
| Duplicate seven-input combinations | 1 extra row in one pair | The same pair also has the same target |
| Unexpected gender labels | 0 | Only `male` and `female` are recorded |

Distinct IDs do not independently establish distinct real participants. The identifier should be retained for auditing and excluded from model inputs.

### Duplicate pair

CSV row numbers below are one-based and include the header as row 1.

| CSV row | User_ID | Gender | Age | Height | Weight | Duration | Heart_Rate | Body_Temp | Calories |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 8268 | 11602373 | female | 28 | 164 | 59 | 9 | 90 | 39.5 | 40 |
| 12854 | 17668038 | female | 28 | 164 | 59 | 9 | 90 | 39.5 | 40 |

Before splitting the data, either keep identical observations in the same partition or document removal of one record in a derived dataset. Preserve the raw file. One duplicate pair does not establish the explanation for the notebook's low test error.

## 4. Variables, units, and observed ranges

Units below follow the local notebook's interface and comments. They are working interpretations, not an independently verified measurement protocol.

| Variable | Role | Interpreted unit/type | Minimum | Median | Mean | Maximum |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| User_ID | Identifier | Identifier stored as integer | — | — | — | — |
| Gender | Input | Recorded category | — | — | — | — |
| Age | Input | Years | 20 | 39 | 42.79 | 79 |
| Height | Input | cm | 123 | 175 | 174.47 | 222 |
| Weight | Input | kg | 36 | 74 | 74.97 | 132 |
| Duration | Input | Minutes | 1 | 16 | 15.53 | 30 |
| Heart_Rate | Input | Beats/minute | 67 | 96 | 95.52 | 128 |
| Body_Temp | Input | Degrees Celsius | 37.1 | 40.2 | 40.03 | 41.5 |
| Calories | Target | kcal per session, as interpreted by notebook | 1 | 79 | 89.54 | 314 |

All numeric fields except body temperature contain whole numbers. Temperature is recorded in increments of 0.1. The file does not establish the instruments' precision or the target's measurement uncertainty.

Temperature deserves particular clarification: 8,829 records (58.86%) exceed 40 in the recorded units. The file does not specify the measurement site, device, or whether the value is an average, peak, endpoint, or generated quantity. Preserve these values pending documentation; this observation is not a medical interpretation or proof of invalidity.

The descriptive 1.5-IQR rule flags 14 height values, 6 weight values, 1 heart-rate value, 369 temperature values, and 4 calorie values. These flags indicate distribution tails, not confirmed errors, and do not justify automatic deletion. Overlap between flagged records is possible.

## 5. Coverage and representativeness

| Recorded gender | Records | Share |
| --- | ---: | ---: |
| male | 7,447 | 49.65% |
| female | 7,553 | 50.35% |

| Age band | Records |
| --- | ---: |
| 20–29 | 4,387 |
| 30–39 | 3,115 |
| 40–49 | 2,394 |
| 50–59 | 2,011 |
| 60–69 | 1,664 |
| 70–79 | 1,429 |

The nearly even gender counts do not establish fairness or population representativeness. Older age bands have fewer records. The file contains no categories beyond the two recorded labels and does not document what the field measures.

Under the assumed height/weight units, derived BMI ranges from 19.23 to 29.07. This is a descriptive calculation, not a diagnosis. It highlights the limited combinations of height and weight represented in the table.

Evidence from this file is restricted to its observed ranges: ages 20–79 and sessions of 1–30 minutes, for example. There is no empirical support here for extrapolation to children, longer workouts, or substantially different input combinations. Geographic representativeness, activity-specific performance, and temporal generalization cannot be assessed because the relevant fields and documentation are absent.

## 6. Relationships relevant to later experiments

These are Pearson correlations across the complete supplied table. They are descriptive audit findings, not final model-selection results or causal estimates.

| Variables | Correlation |
| --- | ---: |
| Duration / Calories | 0.9554 |
| Heart_Rate / Calories | 0.8979 |
| Body_Temp / Calories | 0.8246 |
| Duration / Body_Temp | 0.9032 |
| Duration / Heart_Rate | 0.8529 |
| Height / Weight | 0.9585 |

Duration, heart rate, and temperature share substantial information in this table. Later experiments should test each input's incremental predictive value rather than interpreting a large correlation or SHAP score as a causal effect. Removing an input may have a different effect in another population or collection setting.

The timing of heart-rate and temperature measurements is unspecified. Before defining the task, decide whether predictions are intended during/after a session or before it begins. A feature unavailable at the intended prediction time should not be treated as an available input.

## 7. Recommendation for this project

Keep this dataset for exploratory model comparisons and an initial study of input requirements. Describe results as prediction of **recorded calorie labels in this dataset** until their origin and validity are established.

For a stronger research contribution, obtain a dataset with a documented collection protocol and reference calorie measurements, or recover that documentation for this one. External validation would then test whether findings transfer beyond this benchmark. A user-interface study can establish usability, but it cannot validate energy-expenditure accuracy.

Before publishing a repository containing raw data, resolve the dataset license. Code and reports can be prepared separately while that question remains open. The original CSV has not been redistributed or changed by this audit.

For item 2, a defensible initial research question is:

> How does removing heart rate and temperature affect prediction of this dataset's recorded calorie labels, and how do errors vary across the represented groups and input ranges?

Any new experiment should acknowledge that this table has already been explored and that a previous test split was evaluated in the notebook. An unseen external dataset would provide stronger validation than another random split of these same records.

## 8. Reproducibility and remaining actions

The companion `dataset_audit_metrics.json` contains exact counts, descriptive statistics, duplicate details, correlations, software versions, and source fingerprints. The audit used Python 3.12.14 and NumPy 1.26.4. Key results were independently checked with pandas.

| File | SHA-256 |
| --- | --- |
| exercise.csv | `411400c2854c99ba508c54d05926d3f826fdb2f7d42dc9d4882b24b2a52d3600` |
| Calories_burnt_prediction_project.ipynb, initial read | `e5c7713d56e835b1c13d69cbb9ba1e4933a2cb46529174f003d52dc1897a1f13` |
| Calories_burnt_prediction_project.ipynb, final verification | `6af4737a6a9ec14648f52de3653ff6bca6e5c69dd6cfadf19aac8d18726fb23a` |

The CSV fingerprint remained unchanged throughout the audit. The notebook was saved during the audit: its CSV-loading cell now points to `B:\calories\exercise.csv`. The audit did not write to the source notebook. Both observed notebook fingerprints are retained to distinguish the versions.

- [x] Locate the supplied files and confirm their structure.
- [x] Check all records for missing values, numeric problems, duplicates, and repeated IDs.
- [x] Document coverage, units as interpreted, and notable relationships.
- [x] Inspect the likely publisher's data card and notebook.
- [ ] Verify the original collection source and calorie-label generation method.
- [ ] Resolve the dataset license before redistributing it.
- [ ] Choose whether this is an exploratory benchmark or part of a study with documented external data.

The unresolved items are findings of the audit. They are not evidence that the dataset is unusable, synthetic, or clinically validated.
