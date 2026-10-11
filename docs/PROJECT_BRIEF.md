# Calorie estimation with fewer measurements

Project brief, version 1.1 - 11 October 2026

**Purpose:** investigate the tradeoff between predictive error and measurement requirements, and produce reproducible evidence of when a simpler estimator is sufficient. The project will demonstrate experimental design, software quality, error analysis, and honest interpretation for an applied AI portfolio.

## Research question

> On the supplied calorie benchmark, how much does prediction error change when heart rate and body temperature are removed, and how does that change vary across represented groups and workout durations?

The task is **after-session estimation** of the dataset's recorded calorie label. Heart rate and temperature are treated as session measurements when available; their exact measurement timing remains undocumented. This is not a prediction of calories for a future workout.

The immediate audience is researchers and students evaluating applied regression systems. The deployed Static demo communicates the findings and input tradeoffs. The interface usability study was skipped at the author's request; no participant evidence exists.

## Data decision

**First milestone:** retain the supplied 15,000-record CSV as an exploratory benchmark. Preserve the raw file, exclude `User_ID` from model inputs, account for its duplicate pair before partitioning, and qualify all results as prediction of recorded labels. The dataset's original collection method and license remain unresolved. See [the completed audit](DATA_AUDIT.md).

**Proposed research extension:** investigate WEEE as a separate measured-data study. The [Zenodo record](https://zenodo.org/records/6420886) describes data from 17 participants, an indirect-calorimetry reference, and a 651.6 MB archive; its live repository page lists CC BY 4.0. Its files have not been downloaded or audited. Adoption requires checking usable reference labels, units, timing, participant identifiers, missingness, and compatible sensor channels. This extension is not required to finish the first milestone.

These datasets will not be pooled. WEEE uses different signals and would require its own features and models. Retraining on WEEE would be a separate replication of the research approach, not proof that the original CSV model transfers to real people.

## Planned comparisons

| Input set | Inputs | Question |
| --- | --- | --- |
| Duration baseline | Duration only | How much does workout length explain by itself? |
| Basic | Age, recorded gender, height, weight, duration | What is achievable without sensor measurements? |
| Heart rate | Basic inputs plus heart rate | What incremental value does heart rate provide? |
| Full | All seven original inputs | What incremental value does temperature provide? |

Use a mean predictor as a sanity check. Compare a regularized linear model and XGBoost across the input sets using the same partitions, with matched tuning budgets across input sets within each model family. Tune regularization as well as XGBoost parameters. Deep learning and additional model families are outside the first milestone.

## Evaluation and success criteria

- **Primary outcome:** test mean absolute error (MAE), plus paired differences between reduced and full input sets.
- **Secondary outcomes:** RMSE, error distributions, training time, prediction latency, and number of required session measurements. Measurement count is a burden proxy, not measured financial cost.
- **Decision rule:** a reduced input set is competitive if its relative MAE increase versus the full set is at most 10%. Report a paired 95% bootstrap interval; call the finding inconclusive if that interval crosses the threshold. The 10% margin is a project benchmark choice, not an established health standard.
- **Reliability:** report errors and sample sizes by recorded gender, predefined age bands, and duration bands. Test simulated measurement noise and evaluate prediction intervals separately from point predictions.
- **Integrity:** tune on development data, reserve calibration data for uncertainty estimation, and evaluate frozen choices on a reserved test partition. A new partition of this previously explored file does not create genuinely unseen external evidence.

The project succeeds by producing reproducible, informative results, including a finding that reduced inputs perform worse. Lower error, fewer required measurements, statistical significance, and scholarship selection are not promised outcomes.

## Contribution and deliverables

The intended contribution is a documented study of incremental input value, uncertainty, and failure cases, supported by a consistent prediction pipeline. No new algorithm or priority over existing research is claimed.

Deliver: a reproducible repository, experimental results, a concise research report, a demo using the evaluated pipeline, and an application package describing measured benchmark findings and actual contributions. A usability kit is retained, but collection was skipped.

**Implementation:** items 3?9 are complete: reproducible preparation, frozen evaluation, baselines, input comparison, reliability analysis, one-time final test evaluation and a verified live Static demo. Item 10 is skipped; item 11 materials are prepared on research/portfolio with GitHub source publication pending. See [the checklist](PROJECT_CHECKLIST.md), [final report](FINAL_EVALUATION_REPORT.md) and [portfolio](../portfolio/README.md).
