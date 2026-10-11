# Calorie Lab: fewer measurements, clearer limitations

An applied machine learning project asking: **Can we estimate a calorie benchmark's labels with fewer measurements, and when are the results unreliable?**

I expanded an existing prediction notebook into a reproducible comparison of models, an analysis of their failure cases, and a working browser demo. The project combines Python, scikit-learn, XGBoost, JavaScript and Hugging Face Static Spaces.

**[Try the live demo](https://huggingface.co/spaces/Moobakr/calorie-lab-fewer-sensors)** · **[Read the two-page brief](output/pdf/Calorie_Lab_Project_Brief.pdf)** · **[Explore the case study](portfolio/PROJECT_CASE_STUDY.md)**

## What I investigated

The models use four levels of information: workout duration alone; basic measurements; basic measurements plus heart rate; and all inputs including body temperature. Comparing these routes tests whether the extra measurements improve predictions.

The supplied dataset contains 15,000 records. After removing one duplicate, the study used fixed development, calibration and test partitions. Models shared the same development folds; each XGBoost input set received the same search budget. The final test contained 3,000 records and was evaluated once, after model selection and interval settings were frozen.

## What the results show

| Finding | Evidence | Meaning |
| --- | --- | --- |
| Temperature could be omitted when heart rate was available. | Six-input XGBoost test MAE **0.978**, versus **1.032** with all seven inputs. The paired comparison passed the predefined +10% error tolerance. | One fewer input was sufficient for this benchmark. |
| Removing both sensor measurements made predictions worse. | Basic-input XGBoost test MAE **8.240**. | Heart rate carried useful information in these records. |
| A good overall score concealed a reliability gap. | Nominal 90% prediction intervals covered **90.67%** overall, but only **79.54%** for 21–30 minute sessions. | Reliability needs to be checked across groups, not just averaged. |

**MAE** is the average absolute difference between a prediction and the recorded label; lower is better. Errors use interpreted kcal per session. **Interval coverage** is the fraction of recorded labels inside the prediction range.

## What this project demonstrates

- **Experimental design:** simple baselines, controlled input comparisons and a frozen final evaluation.
- **Critical analysis:** subgroup coverage gaps, simulated sensor noise and explicit limits on the evidence.
- **Implementation:** a public demo running four frozen models directly in the browser.
- **Verification:** 82 Python tests and four JavaScript checks passed; browser predictions and interval bounds matched Python exactly on 5,854 synthetic cases.

## My contribution and AI assistance

I supplied the starting notebook/data, directed project choices, selected free hosting, completed account setup and checked the live demo. An AI assistant provided substantial implementation, analysis-tooling and documentation support. The [contribution record](portfolio/CONTRIBUTIONS_AND_CLAIMS.md) explains those roles.

## Limits and next step

The original collection method, label construction, units and dataset license are unresolved, and the file had already been explored in the original notebook. These results measure agreement with recorded labels; they do not establish physiological accuracy. User benefit has not been measured. The next research step is a separate study using documented measured data and an independent evaluation protocol.

## Explore further

- [Final research report](docs/FINAL_EVALUATION_REPORT.md): all models, paired comparisons and uncertainty results.
- [Reliability report](docs/RELIABILITY_REPORT.md): subgroup errors and simulated noise sensitivity.
- [Deployment verification](docs/STATIC_DEMO_GUIDE.md): how the browser demo reproduces the Python models.
- [Technical guide](docs/TECHNICAL_GUIDE.md): setup, commands, repository structure and reproducibility limits.
- [Original notebook](notebooks/legacy/github/Calories_burnt_prediction_project.ipynb): preserved for comparison with the research revision.
