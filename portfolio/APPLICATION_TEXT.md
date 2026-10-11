# Application text drafts

These drafts describe the AI-assisted project and its verified outputs. Review wording against your own understanding and the chosen application's instructions. They do not claim independent hand coding, user research, clinical validity or measured social impact. Publish the research revision before representing the existing GitHub default branch as the finished project.

## CV entry

**Calorie Lab - Sensor Requirements and Reliability** | AI-assisted applied ML project | 2026  
Python, scikit-learn, XGBoost, JavaScript, Hugging Face Static Spaces  
[Demo](https://huggingface.co/spaces/Moobakr/calorie-lab-fewer-sensors) · [Existing repository; research revision publication pending](https://github.com/Moobakr/calories-burnt-prediction)

- Developed an AI-assisted benchmark study comparing four input sets with shared development folds, matched XGBoost search budgets and frozen final evaluation; the six-field heart-rate model achieved test MAE 0.978 versus 1.032 for seven full inputs across 3,000 records.
- Documented a reliability gap: nominal 90% intervals covered 90.67% overall but 79.54% for long sessions; deployed browser inference on Hugging Face and verified exact Python parity on 5,854 synthetic cases.

For a strict space limit, use the second bullet plus a project title and link. Include “recorded calorie labels; source/units unverified” in the linked case study. Keep the AI-assisted qualifier when describing implementation. Do not write “99% accurate”, “clinically validated”, “reduced costs”, “helped users” or “deployed Docker to the cloud”.

## Short project description

Calorie Lab is my AI-assisted study of which measurements are needed to predict a supplied calorie benchmark's recorded labels. It compares input sets under a controlled evaluation workflow and communicates uncertainty through a public browser demo. Omitting temperature while retaining heart rate passed a predefined error rule, but overall interval coverage concealed a long-session gap. The project includes reproducible source, aggregate evidence and verified model export; source collection and real-world validity remain unresolved.

## Motivation-letter paragraph

My AI-assisted Calorie Lab project examines input requirements and reliability rather than reporting a prediction score alone. Using shared development folds and a frozen evaluation protocol, the project compared reduced-input models and found that temperature could be omitted under a predefined benchmark rule when heart rate was available. A separate interval analysis showed why the result needs qualification: coverage was 90.67% overall but only 79.54% for longer sessions. The public browser demo communicates these limitations and reproduces the frozen Python predictors. This is the kind of applied AI work I want to develop further: explicit questions, reproducible evidence, implementation checks and careful limits on what the results establish.

The final sentence is a suggested motivation, not a fact about your personal history. Keep it only if it reflects your actual aims; add a specific program connection after checking that program's curriculum and prompt. No program fit, admission likelihood, eligibility or scholarship criterion is asserted here.

## Thirty-second introduction

“My project asks whether all seven measurements in a calorie benchmark are necessary. The AI-assisted workflow found that six inputs including heart rate passed our error rule, while removing both sensors did not. The more instructive finding was reliability: a nominal 90% interval covered only about 79.5% of longer sessions. I deployed a browser demo that shows those limits and verified its predictions against Python. The labels are not independently validated physiological measurements, and I have not measured user benefit.”

Be ready to explain the workflow and acknowledge the assistant's role. Do not memorize this in place of understanding the saved models, evaluation design and failure cases.
