# Calorie Lab: sensor requirements and reliability

**Moobakr | AI-assisted applied machine learning project | 11 October 2026**

[Live demo](https://huggingface.co/spaces/Moobakr/calorie-lab-fewer-sensors) · [Existing repository](https://github.com/Moobakr/calories-burnt-prediction). The updated research source is packaged locally; GitHub publication remains pending. No usability study was conducted.

## Question and contribution

How does prediction error change when heart rate or body temperature is unavailable, and what does an overall error score conceal about reliability? This project turns an existing calorie-prediction notebook into a documented comparison of input requirements, calibrated intervals, subgroup behavior and a deployed browser implementation. The contribution is the experimental workflow and transparent evidence, rather than a new estimator.

## Data and experimental controls

The supplied CSV contains 15,000 records. Removing one exact duplicate excluding its identifier leaves 14,999. Identifiers are excluded from inputs. A fixed allocation assigns 8,999 development, 3,000 calibration and 3,000 test observations; five development folds are shared across comparisons. The dataset had already been explored in the original notebook, so the reserved partition does not establish untouched external validity.

The study compares a mean baseline, four Ridge pipelines and four XGBoost pipelines. Each XGBoost input set receives the same 30-configuration, five-fold development search. Preprocessing stays inside fitted pipelines. Calibration is separated into 1,500 interval-fit and 1,500 interval-audit observations. Model/threshold hashes bind saved artifacts to their reports. A committed protocol and a selection manifest written before scoring precede the one-time final test release; test scores do not retune or reselect the primary system.

The primary system, basic measurements plus heart rate, was selected by development mean-fold MAE. Four planned within-family reduced/full comparisons use 2,000 paired row bootstrap resamples. The project-defined acceptance rule allows at most a +10% relative-MAE increase, assessed by the interval upper bound; it is not a clinical standard.

## Frozen results

| XGBoost input set | Fields | Test MAE | Test RMSE |
| --- | ---: | ---: | ---: |
| Duration only | 1 | 11.508 | 16.953 |
| Basic measurements | 5 | 8.240 | 11.723 |
| Basic + heart rate (primary) | 6 | 0.978 | 1.576 |
| Full, including temperature | 7 | 1.032 | 1.645 |

All models use the same 3,000 test records. Errors are in interpreted kcal/session against recorded benchmark labels; original units and label construction remain unverified. The mean baseline has test MAE 54.236 and full Ridge 8.613. Different tuning budgets limit cross-family interpretation.

Heart-rate XGBoost has a relative MAE change of **-5.22%**, with approximate paired 95% percentile interval **[-6.52%, -3.82%]**, versus full inputs. It passes the predefined +10% rule, supporting omission of temperature for this benchmark. Removing both sensors fails: basic XGBoost test MAE is 8.240. A reduction from seven to six fields is an input-count result, not measured device-cost or time savings.

## Reliability finding

The primary fixed 90%-nominal interval covers **90.67%** of all test labels, but only **79.54%** of 21-30 minute sessions (997 records). Coverage is 99.38% for 1-10 minutes and 93.22% for 11-20 minutes. Overall coverage therefore conceals a meaningful group failure. The earlier development stress test raised heart-rate-model MAE from 1.080 to 7.777 under simulated Gaussian heart-rate noise with SD 5 bpm; that scenario is not a measured device error distribution.

Bounds remain unclipped, including negative lower bounds, and no subgroup recalibration was introduced after the test. The app communicates the duration-group gap and the difference between benchmark agreement and a verified measurement.

## Implementation and verification

Python pipelines, pinned research dependencies, deterministic assignments and aggregate reports preserve the experiment. The free Hugging Face Static Space evaluates four exported frozen forests in the browser. Feature order, one-hot encoding and float32 arithmetic are preserved. Prediction inputs are not sent to a prediction API or saved by the app; the host may retain ordinary asset-request logs.

Served assets and repository file hashes were checked against the reviewed package. Downloaded JavaScript and forests match the original Python predictions and unclipped bounds exactly on **5,854 synthetic sessions**, including split boundaries. **82 Python tests and four JavaScript checks** pass in the current source revision. The author confirmed basic page display and estimate updates. Automated browser/mobile/accessibility verification was unavailable. A separate Python/Waitress Docker implementation is retained locally; Linux container execution and hosted Docker deployment were not verified.

## Scope, authorship and next research step

The author supplied the existing notebook/data, directed the portfolio project, selected the free hosting route, completed account authentication and confirmed basic demo interaction. The research revision, code, analyses and documentation were produced with substantial AI-assistant implementation and tooling support. The evidence supports project outcomes; it does not establish independent mastery of every implementation detail.

Original collection, target construction, interpreted units, licensing and possible participant dependence are unresolved. Bootstrap interpretation depends on exchangeability and does not include training uncertainty. The skipped usability study provides **no participant or user-benefit evidence**. The demo is an implementation artifact, not proof of adoption, physiological accuracy, cost savings or health impact. A future extension would require independently documented measured data and its own study, rather than tuning this benchmark against the released test.

Evidence: [final report](../docs/FINAL_EVALUATION_REPORT.md), [aggregate final metrics](../docs/FINAL_EVALUATION_METRICS.json), [reliability report](../docs/RELIABILITY_REPORT.md), [hosted verification](../docs/STATIC_DEMO_VERIFICATION.json), [contribution/claim record](CONTRIBUTIONS_AND_CLAIMS.md).
