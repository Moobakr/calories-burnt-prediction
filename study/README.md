# Item 10: usability and understanding

**Status: prepared, not conducted. No participant results or measured impact exist yet.** English protocol v1.0, 11 October 2026. This is a small formative study of the demo, not validation of calorie expenditure or a representative survey.

The study asks whether first-time visitors can choose an appropriate input route, obtain an estimate without inventing sensor readings, and explain the benchmark and interval limitations. Plan one excluded pilot and **six retained main participants**. Invite adults who can read English and have not used or helped develop this demo. Seek varied ML familiarity and, where feasible, at least two phone users; disclose actual recruitment/device mix rather than inventing quotas. Convenience recruitment and an author-moderator limit generalization. Do not exclude failures or slow users to improve results.

The small moderated round and think-aloud approach follow [GOV.UK planning guidance](https://www.gov.uk/service-manual/user-research/plan-user-research-for-your-service) and [moderated usability guidance](https://www.gov.uk/service-manual/user-research/using-moderated-usability-testing). Six is a practical project choice within that guidance, not statistical power for population claims. Our tasks, rubric, questionnaire and iteration criteria are custom, not a validated usability scale.

## Run the study

1. Read [MODERATOR_GUIDE.md](MODERATOR_GUIDE.md). Send only [PARTICIPANT_GUIDE.md](PARTICIPANT_GUIDE.md) to volunteers. The invitation text below is ready to copy; no invitations have been sent by the assistant.
2. From the project directory, initialize the ignored local response folder. **The prepared research checkout already has blank `study/private/round-1/` sheets; skip initialization there. In a fresh or standalone copy, run the command below.** It refuses to replace existing records:

   ```powershell
   & .\.venv\Scripts\python.exe -m calorie_estimation.usability init --directory study/private/round-1
   ```

3. Run one pilot as `PILOT01`. Check wording, task limits, browser access and the recording sheet. Pilot answers are excluded from all main outcomes. If anything changes, edit the protocol/guides, increment the version and commit before main data collection; record why in the report. This is not an external preregistration.
4. Check the demo revision, then freeze the local protocol before entering any main participant rows:

   ```powershell
   & .\.venv\Scripts\python.exe -m calorie_estimation.usability check-demo
   & .\.venv\Scripts\python.exe -m calorie_estimation.usability freeze --directory study/private/round-1
   ```

5. Run six individual sessions, about 15–20 minutes each. Use `P01` onward; alternate the first two tasks by odd/even ID. Use fictional values only. Check the demo revision before each session. Record first answers before explaining the caveats. Follow the scoring and stopping rules; include unsuccessful/partial sessions. Stop at six retained main sessions regardless of outcomes. Replace only a genuine consent withdrawal, using a new ID and reporting the withdrawal count.
6. Summarize once six retained sessions are available (an interim summary is explicitly marked incomplete):

   ```powershell
   & .\.venv\Scripts\python.exe -m calorie_estimation.usability summarize --directory study/private/round-1 --output runs/usability-round-1
   ```

7. Complete [RESULTS_TEMPLATE.md](RESULTS_TEMPLATE.md) using the generated counts, anonymized observations and actual limitations. Review everything before copying aggregate findings into `docs/`. Keep real response files, session notes and participant codes private. Item 10 stays open until genuine sessions are collected and analyzed.

The CLI uses the Python standard library only. It never imports models, reads the calorie dataset or changes the app. `init`/`freeze`/`summarize` preserve existing destinations. Freeze hashes the protocol, both guides, header templates and analysis code. A later change causes analysis to refuse the old freeze; disclose a new study version/round instead of overwriting the record. The freeze record contains a local timestamp and hashes, not independently verified registration. `check-demo` is a public read-only network check.

## Data and interpretation

`sessions.csv` has one row per consenting person, no names/contact details or health information. `issues.csv` stores moderator paraphrases, not recordings or identifying quotes. The [moderator guide](MODERATOR_GUIDE.md) is the data dictionary. Both blank templates are safe to publish; completed copies belong only in ignored `study/private/`. Do not upload them to GitHub/Hugging Face. A `.gitignore` rule is a convenience, not access control; avoid shared storage and force-adding records.

Participation and all ratings are voluntary. No audio/video recording or telemetry is needed. A withdrawing participant's measurements and notes must be removed; retain only a row marking their code/cohort and `withdrawn`, with every other cell blank. Keep any scheduling contact outside the research folder. Tell participants that only anonymized aggregate findings and paraphrased issues may appear in the portfolio. Delete private study responses/notes within 30 days after the aggregate report is finalized; do not promise deletion of already published aggregate facts. This is a project handling plan, not a claim of formal ethics approval.

Primary outputs are unassisted completion counts for T1/T2 and correct-before-help counts for four comprehension items, always showing denominators and missingness. Every retained main session stays in the denominator, including partial sessions and technical failures. Times describe observed task performance while thinking aloud; report medians only among unassisted successes, with their count. Custom ratings use medians/ranges and response counts. Report pilot and withdrawal counts separately. Do not pool pilot outcomes, invent missing answers, perform significance tests, label custom ratings SUS, or compare before/after without a separate fixed design.

The predeclared iteration rule reviews an item if fewer than five of six retained participants complete it unassisted/answer correctly. Report actual counts even if thresholds are missed. Meeting these thresholds does not demonstrate general usability, accessibility, real-world accuracy, causal benefit, time saved or scholarship impact. If you revise the app after observing failures, preserve this round and study the new revision separately.

## Invitation to copy

> I'm testing the clarity of a small AI research demo for my portfolio. Would you volunteer for a 15–20 minute session? You'll use fictional workout examples, try a few tasks and explain what the results mean. I'm testing the interface, not your ability; no AI experience is required. Please participate only if you are 18 or older, comfortable reading English and have not used this demo before. Participation is optional, you can skip questions or stop, and I won't record audio/video or ask for health details. I may publish anonymized aggregate findings and paraphrased usability issues. Please don't explore the demo before the session. Let me know if you're interested and whether you'd prefer a phone or computer.

Send this yourself to suitable volunteers; schedule each individually. Do not send the moderator answers or coach participants toward the benchmark finding.
