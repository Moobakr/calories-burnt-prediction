# Calorie Lab demo and Hugging Face deployment

Item 9 implementation — 11 October 2026. The inference app and a Docker Space package are built. All **71 tests** passed, as did eight HTTP prediction/interval parity checks using two fictional scenarios across all four input routes. **Hosted deployment, Linux container execution and visual browser verification remain pending.** See [DEMO_VERIFICATION.json](DEMO_VERIFICATION.json) for the actual checks and limits.

## Experience

The page lets a visitor select basic + heart rate (the frozen primary system), full inputs, basic without sensors, or duration only. Each route uses its own previously evaluated XGBoost pipeline and fixed interval threshold. Missing readings are never replaced with zero. Input changes clear an old estimate and cancel pending requests so a result cannot silently describe another session. Two clearly labeled fictional examples support exploration without personal data.

The result includes the recorded-label estimate, an unclipped nominal 90% reference interval, test MAE, overall coverage and coverage for the entered duration band. The page also compares all four input requirements against their frozen test errors. It explains the primary long-session coverage gap, simulated heart-rate noise sensitivity, unresolved label construction and interpreted units. No per-person coverage, clinical accuracy, causal explanation or measured user-benefit claim is made.

Only the benchmark's recorded categories are accepted. Numeric fields use their recorded whole-number/continuous schema. Inputs outside development-only feature ranges are rejected; remaining inside those ranges does not establish deployment validity. No input submissions are written to disk and no analytics are installed. A hosting provider may retain ordinary access logs.

## Local run

From the research checkout:

```powershell
& .\scripts\demo.ps1
```

Open `http://127.0.0.1:7860`. The script installs the separate pinned serving dependency if needed, creates the package only if absent and starts Waitress on loopback. Stop with Ctrl+C. The research dependency lock is unchanged. The demo does not run preparation, fit any model or evaluate the test set again.

Direct package creation, preserving existing run directories:

```powershell
& .\.venv\Scripts\python.exe -m calorie_estimation.demo_package --output runs/demo-space-v1
```

Packaging requires the matching frozen comparison run and final selection/results snapshots. It derives range metadata from development only. The runtime app itself never opens dataset files or evaluation assignments.

## Deployable package

The local deliverable `calorie-lab-huggingface.zip` contains a root Dockerfile, Hugging Face Space README, pinned runtime requirements, the three interface assets, the small inference module, four hash-verified model files and aggregate inference metadata. It excludes raw/derived data, notebooks, IDs, test predictions, bootstrap draws, Git history, caches and credentials. `PACKAGE_MANIFEST.json` records each uploaded file's digest. The upload helper verifies both the reviewed manifest digest and the exact file allowlist before sending anything.

The Dockerfile uses Python 3.12.14, installs the pinned research inference libraries plus Waitress 3.0.2, runs as user ID 1000, limits numerical threads, exposes port 7860 and defines a health check. It has no training step, GPU requirement, database or persistent user storage. This targets the default CPU Space; no paid hardware upgrade is requested. The base image patch is pinned but not an immutable image digest, OS packages are not version locked, and container prediction parity remains unverified on this Windows host.

These settings follow [Hugging Face's Docker Spaces documentation](https://huggingface.co/docs/hub/spaces-sdks-docker). The serving implementation uses [Waitress](https://docs.pylonsproject.org/projects/waitress/en/stable/usage.html). SDK publishing uses the official [folder upload](https://huggingface.co/docs/huggingface_hub/guides/upload) and [Space management](https://huggingface.co/docs/huggingface_hub/guides/manage-spaces) APIs.

## Publish under Moobakr

The prepared target is `Moobakr/calorie-lab-fewer-sensors`. A separate publisher environment uses `huggingface_hub==2.2.0`, leaving the research environment unchanged. `PUBLISH_HUGGINGFACE_SPACE.ps1` sits beside the project in the deliverables folder. It can check the package offline, authenticate through Hugging Face's normal CLI, then create the public Docker Space and upload the verified folder. It refuses to overwrite a pre-existing unrelated Space and records the newly created target before upload so a failed upload can resume.

Run in your normal PowerShell session:

```powershell
& .\PUBLISH_HUGGINGFACE_SPACE.ps1 -Login
```

Enter a Hugging Face write token only into the CLI's hidden authentication prompt, never in this chat or a script. The login command may require the account's normal verification steps. The script reads credentials through the official SDK and does not print or package them. The uploader creates a public Space, so its four fitted model files and serving source will be accessible there; dataset observations are excluded and the unresolved provenance/license status stays visible in the Space README.

An upload receipt proves only that files were committed, not that the image built or the app works online. After upload, check the Space build/runtime status, `/api/health`, all four fictional-example routes, invalid inputs, mobile layout and interval messages. Record the hosted revision and results before claiming verified cloud deployment. Free Spaces may sleep while idle; see [Spaces overview](https://huggingface.co/docs/hub/spaces-overview).

## Verification completed and remaining

The suite adds checks for exact required fields, missing/unused sensors, unknown categories, invalid/nonfinite/bool/fractional numbers, range boundaries, cross-origin requests, bounded body sizes, excluded file routes and artifact corruption before deserialization. Actual HTTP checks independently compare every fictional result and bound with the original saved model and threshold. Package file hashes/exclusions, historical research snapshots, the global assignments and final-test release record were verified unchanged. JavaScript syntax checking passed.

Browser automation ended because Computer Use could not verify Chrome's current URL; no visual or interactive browser success is claimed. Docker's daemon was unavailable, so no local container build was run. Hugging Face authentication was not available to this session; no Space has been created or uploaded here. The local implementation is ready for review, and the cloud validation step remains open. A usability study and measured impact still belong to item 10.
