# Explaining the project

Use this as a preparation checklist. Work through the code and reproduce small fictional examples before presenting a skill as independently mastered. The answers below describe the project evidence, not a record of knowledge you have already demonstrated.

| Question | A defensible answer and evidence to inspect |
| --- | --- |
| What question did you investigate? | Incremental value of heart rate/temperature for recorded-label prediction and whether reliability differs across groups. PROJECT_BRIEF.md and the final report. |
| Why include simple baselines? | The mean and Ridge quantify the value of session inputs and nonlinearity; XGBoost beating them alone does not answer which sensors are needed. Compare mean MAE 54.236, full Ridge 8.613 and four XGBoost routes. |
| How did you prevent leakage? | Exclude ID, remove the exact duplicate, fit preprocessing within each fold, tune on development only, separate interval fit/audit, freeze model/threshold bindings before test. Original prior exploration and unknown dependence still limit external validity. |
| Why choose the heart-rate model? | It had lowest recorded development mean-fold MAE under the fixed selection rule. Final test results were not used to select it. Inspect FINAL_SELECTION.json and the pre-test commit. |
| What does MAE 0.978 mean? | Mean absolute disagreement with recorded labels, in interpreted kcal/session. It is not an accuracy percentage or evidence of calorimetry validity. |
| What does the paired interval compare? | Relative difference (reduced MAE - full MAE) / full MAE, using identical sampled rows for both systems, 2,000 percentile draws. It describes row-sampling variation conditional on frozen models; dependence/training uncertainty remain limitations. |
| What is the +10% rule? | A project-defined benchmark tolerance fixed before final evaluation. Competitive only if the interval upper bound is at most +10%; no clinical noninferiority claim. |
| Why isn't 90.67% coverage sufficient? | It averages over groups. Long-session coverage is 79.54% and short-session coverage 99.38%; nominal coverage is not an individual guarantee. |
| How were intervals calibrated? | Fixed absolute-residual quantile from 1,500 interval-fit records, rank ceil((n+1)*0.9); separate audit and test records never refit it. Primary half-width 2.228363. |
| What did the sensor-noise study establish? | Sensitivity under a chosen simulated Gaussian HR-noise scenario, not a measured sensor specification. SD 5 bpm raised development MAE from 1.080 to 7.777. |
| How can browser predictions match Python? | Export numeric passthrough/one-hot ordering and scalar trees, compare float32 inputs/thresholds, sum float32 leaf values in order. Check hashes and test split neighbours; 5,854 synthetic cases match exactly. |
| What cloud skills are demonstrated? | Authenticated publishing, static model delivery, manifest/hash checks and deployed-asset verification. A Docker template exists, but no Linux container execution, backend deployment or production operations is verified. |
| How did you measure impact? | No user-impact study was conducted; participant collection was explicitly skipped. State benchmark findings and deployment outputs, not health/adoption/cost claims. |
| What did you personally do, and how was AI used? | Use CONTRIBUTIONS_AND_CLAIMS.md and your actual subsequent work. State substantial assistant implementation support; do not imply independent authorship of every component. |
| What would strengthen the research next? | A separately audited dataset with documented measured targets/participant IDs and an independent protocol. Address coverage/noise failures in a new study rather than retuning on the released test. |

Practical exercises: trace one fictional request from validation to feature encoding to tree output; calculate a tiny paired-MAE example by hand; compute a small residual quantile with the fixed rank rule; explain why missing sensors route to a separately trained model rather than zero filling. These are preparation exercises, not completed achievements or additional benchmark evaluations.
