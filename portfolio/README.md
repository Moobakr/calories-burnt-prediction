# Application package

Prepared 11 October 2026. The usability study was skipped at the author's request; no participant sessions, measured user benefit or usability results are claimed. The study materials remain available as an optional future round.

Start with [PROJECT_CASE_STUDY.md](PROJECT_CASE_STUDY.md), then use [APPLICATION_TEXT.md](APPLICATION_TEXT.md) for CV/project-description drafts and [INTERVIEW_GUIDE.md](INTERVIEW_GUIDE.md) to prepare to explain the work. [CONTRIBUTIONS_AND_CLAIMS.md](CONTRIBUTIONS_AND_CLAIMS.md) distinguishes evidence, limitations and AI assistance. A two-page PDF, a current source ZIP and a separate deployment ZIP accompany the deliverables outside this checkout.

The strongest supported contribution is an auditable comparison of input requirements and reliability, followed by verified browser deployment. A low error alone does not establish accurate physical calorie measurement. No novel algorithm, clinical validation, measured cost savings or user-impact study is claimed.

## Public and local artifacts

| Artifact | Current status |
| --- | --- |
| [Live demo](https://huggingface.co/spaces/Moobakr/calorie-lab-fewer-sensors) | Public Static Space; frozen-model parity and served assets verified. Author confirmed basic interaction. |
| [Existing GitHub repository](https://github.com/Moobakr/calories-burnt-prediction) | Existing history preserved. This research/portfolio revision is local; do not assume the default branch contains it. GitHub CLI authentication is unavailable in this session. |
| `calorie-estimation-source.zip` | Current source, aggregate reports, tests and original tracked historical notebook. No raw/derived observations, fitted model weights or private study responses. |
| `calorie-lab-static-huggingface.zip` | Reviewed browser assets, aggregate metadata and exported frozen forests. No observations or credentials. |
| Two-page case-study PDF and editable Markdown | Ready for review; snapshot notes source publication pending and unmeasured impact. |
| Usability study | Skipped, not conducted; prepared kit retained. |

## Finish source publication

`PUBLISH_PORTFOLIO_BRANCH.ps1`, beside the project, verifies the reviewed commit, clean tree, intended repository and private-file exclusions. It can check offline, then push only `research/portfolio` and open/reuse a **draft** PR against `main`. The branch contains the complete research history; pushing it does not require publishing every intermediate branch. Existing PRs and branches are preserved. Nothing merges automatically.

Run from the deliverables folder in the normal PowerShell session where GitHub authentication works:

```powershell
& .\PUBLISH_PORTFOLIO_BRANCH.ps1 -CheckOnly
& .\PUBLISH_PORTFOLIO_BRANCH.ps1
```

After publication, review the draft and confirm the source link resolves to the research revision before using it in an application. The existing reproducibility draft PR is not automatically closed or merged. If upstream main has advanced outside this branch's ancestry, the helper stops rather than forcing changes. Final merging and program-specific submission remain separate actions.

## Using the package

Use one or two project bullets in the CV and link the live demo plus the actual published research revision. Keep detailed metrics in the case study. Do not substitute an accuracy percentage for MAE, call browser hosting a deployed Python container, or describe a study plan as user research that took place. Attribute AI assistance accurately and be ready to explain the design, code and limitations in your own words.

No specific Erasmus Mundus program, eligibility rule, application deadline or required disclosure format has been checked here. Tailor the draft to the chosen program's actual prompt and your real academic history; this package invents neither qualifications nor personal experiences.

## Rebuild the brief

Install `portfolio/requirements-pdf.txt` in a separate document environment, then run `python portfolio/build_brief.py` from the project root. The generator reads aggregate report JSON only; it does not load data/models or repeat evaluation. PDF generation is separate from the pinned ML environment. The delivered two-page PDF was rendered and visually reviewed.
