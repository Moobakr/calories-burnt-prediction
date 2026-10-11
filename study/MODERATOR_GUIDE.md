# Moderator script, scoring and data dictionary

Read this before the pilot. Do not show its answer key to participants. Use the participant guide's wording and [protocol.json](protocol.json). No real sessions have been conducted by the assistant.

## Before each session

Run `check-demo`; use revision `185803a17095ff236e235dd4053cae8a28015e9b` and the frozen protocol. A changed revision requires pausing the round and disclosing the version change; do not combine versions silently. Check the participant's self-declared adult status, English comfort and first-time use without recording their age or identity. Obtain voluntary agreement to participation and aggregate reporting; otherwise stop without collecting a row. Assign `PILOT01` or a new `P01` onward and give the code to the participant.

Say: “We're testing the interface, not you. Please think aloud. It's fine to be confused, skip a question or stop. Use only the fictional values. I'll usually wait before helping. I won't record the screen or audio. May I take coded notes and use anonymized aggregate findings and paraphrased issues as described in the participant guide?” Do not explain model findings or interval answers yet.

Record general device class (`desktop`, `mobile`, `tablet`) and self-reported ML familiarity (`yes`: previously studied/built an ML model; `no`; or blank if declined). No age, gender, nationality, contacts, browser fingerprint or health measurements are collected. Participant gender is irrelevant; task gender is an invented input value.

## Task procedure

Odd main ID: T1, T2, T3, T4. Even: T2, T1, T3, T4. Pilot uses T1,T2,T3,T4. Reset the page before each of T1/T2; read one task at a time. Start timing after reading the prompt, when interaction begins. Stop on completion, giving up or the time cap (180 seconds T1/T2; 120 T3/T4). Include thinking-aloud and device delays; these are descriptive observations, not latency benchmarks. A short neutral “Please keep thinking aloud” is allowed. Do not name controls, explain the answer or point to a section before scoring the first attempt.

At a cap, record the observed outcome/time before helping. Optional help and debrief after the cap do not change that outcome or timing. Before the cap, if the participant explicitly requests help and chooses to continue with it, record the assistance in notes and classify any completed task as `assisted`. Never relabel assisted success as unassisted. For T3/T4, record the initial answers verbatim only if nonidentifying, preferably as a close paraphrase; score comprehension before any content-specific help. Do not teach the correct answers until all four first attempts are finished.

Use one outcome per task:

| Outcome | Meaning |
| --- | --- |
| `unassisted` | All task criteria achieved before the cap with no task-specific help. |
| `assisted` | Task completed before the cap after task-specific help. |
| `failed` | Wrong/incomplete, gave up, or reached the cap without completing. |
| `technical_failure` | Hosting/device/network prevented an attempt or completion; record time spent and issue. Keep in the denominator. |
| `not_attempted` | Skipped/not reached; time and corresponding comprehension cells blank. Keep in the denominator. |

## Answer key

| Task | Completion criteria / initial-answer rubric |
| --- | --- |
| T1 | Select **Basic + heart rate**, use all six supplied values, obtain point **123.1** and interval **120.9–125.3** as displayed. No invented temperature. Merely retaining the initial example values does not count. |
| T2 | Select **Basic inputs**, use the five supplied values, obtain point **219.8**, interval **200.7–238.8**. No invented sensor readings. Duration-only is insufficient because the task asks to use all available measurements. |
| T3 | Both `c_interval` and `c_limitations` correct before help. |
| T4 | Both `c_tradeoff` and `c_long_sessions` correct before help. |

Comprehension cells use `1` for a correct initial answer, `0` for an incorrect/unsupported/no substantive answer, blank only if not asked, declined or blocked by technical failure. Score the participant's final answer in the first attempt before help/the cap; self-correction during that attempt is allowed. Do not score an exploratory think-aloud remark as their finished answer. Equivalent wording counts; do not demand technical terminology. A correct answer after help does not replace the initial score.

| Field | Score 1 when the first answer conveys… |
| --- | --- |
| `c_interval` | 90% is a nominal coverage target over comparable records, not a guarantee/probability for this individual's true calories. Saying only “90% accurate” scores 0. |
| `c_limitations` | Output is a prediction of benchmark labels with unverified source/label construction; it cannot establish this person's measured physiological expenditure. Explicitly reject a verified personal measurement claim. |
| `c_tradeoff` | In this benchmark, temperature can be omitted when heart rate is present with little error penalty; omitting both sensors causes substantially larger errors. No universal/clinical claim. Both parts required. |
| `c_long_sessions` | The 21–30 minute group has lower observed coverage for the primary model, so the nominal target is less reliable there. Naming ~79.5% is optional; identifying group plus implication is required. |

If T3/T4 are `unassisted`, both respective scores must be 1. If a participant makes a statement the rubric does not resolve, paraphrase it in private notes, use 0 conservatively, and document the ambiguity in the report rather than changing the rubric mid-round.

## CSV recording

Use `study/private/round-1/sessions.csv`, one row per participant. Keep the exact header. There are no example participant rows. CSV programs may change separators/encoding; save UTF-8 comma-separated CSV with the same columns. Do not use spreadsheet formulas or include identifying details.

| Columns | Values |
| --- | --- |
| `participant_id`, `cohort` | `P01`… for `main`, `PILOT01`… for `pilot`. New IDs for genuine withdrawal replacements. |
| `consent`, `session_status` | `yes` and `completed`/`partial`. A completed session has all four tasks attempted (failures allowed); partial has at least one `not_attempted`. |
| `device`, `ml_familiarity` | `desktop`/`mobile`/`tablet`; `yes`/`no`/blank. |
| `app_revision` | Exact 40-character frozen revision above, after `check-demo`. |
| `task_order` | `T1,T2,T3,T4` or `T2,T1,T3,T4` by ID. Quote the cell because it contains commas. |
| `t1_outcome`…`t4_outcome` | One enum from the outcome table; never fill an omitted task with success. |
| `t1_seconds`…`t4_seconds` | Positive finite seconds up to the cap; blank only for `not_attempted`. If a technical issue prevented all interaction, record the positive time spent checking it. |
| `c_interval`, `c_limitations`, `c_tradeoff`, `c_long_sessions` | 0/1 or blank under the rules above; preserve answers already given if a later part is skipped or technically blocked. |
| `q_ease`, `q_clarity`, `q_educational_usefulness` | Integer 1–5, or blank if declined. These are custom questions; do not call the result SUS. |
| `notes` | Optional nonidentifying moderator paraphrases; private, not automatically published. |

For withdrawal, erase measurements/notes and all related issue rows; keep only participant ID, cohort and `session_status=withdrawn`, every other cell blank. Withdrawn sessions do not enter performance denominators; report the count and any actual reasons voluntarily given without identities. Ordinary failed/partial sessions are not withdrawals and remain included. Pilot outcomes are always excluded from main estimates.

`issues.csv`: `participant_id,task_id,category,observation,assistance,proposed_change`. Task is `t1`…`t4` or `feedback`; category is a short moderator label such as navigation, explanation or technical. Record behavior and a paraphrase, distinguish observation from your proposed fix, and note any help. Group issues manually in the report, with affected-participant counts; do not treat repeated comments from one person as independent people. This sheet stays private and is not read by the quantitative summarizer.

## Feedback and debrief

Read the three custom scales and two open questions from the participant guide; collect optional ratings without asking for positive comments. Explain the benchmark/interval limitations after recording all task answers. Thank participants, remind them of their code and withdrawal option, and stop. Do not recommend using this estimator for personal health decisions.

For the report, keep observed task counts separate from perceived usefulness. Disclose author moderation, convenience recruitment, first-time visitors, think-aloud timing, partial sessions, withdrawals, pilot changes and absent comparison condition. Any improvement made afterward requires a new revision/round; preserve this round's failures.
