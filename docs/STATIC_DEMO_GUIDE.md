# Free Hugging Face Static Space

Calorie Lab is published at **https://huggingface.co/spaces/Moobakr/calorie-lab-fewer-sensors**. It runs inference in the visitor's browser; there is no prediction API, Python server, GPU, subscription or training step in this deployment. The exact deployed revision and completed checks are recorded in [STATIC_DEMO_VERIFICATION.json](STATIC_DEMO_VERIFICATION.json). The author confirmed that the page displays and estimates update with the fictional examples and measurement dropdown. Automated browser and mobile checks were unavailable; this is a user-reported manual confirmation.

The previous Docker creation attempt failed with HTTP 402 after successful authentication. Hugging Face's current [Space management documentation](https://huggingface.co/docs/huggingface_hub/main/guides/manage-spaces) says Static Spaces are free for everyone, while Docker/Gradio on CPU Basic require a subscription. The user selected the free Static route. The Python/Waitress implementation and original Docker package remain available for local use; they are not deployed containers.

## What changed

The four existing XGBoost pipelines were exported to a small, explicitly versioned JSON forest format. No model was fitted, recalibrated, reselected or scored against the reserved test again. Export checks the original artifact SHA-256, exact feature list and interval threshold against the frozen selection manifest, as well as the original demo package's file digests and final research snapshot bindings.

The exporter accepts only the saved pipeline's numeric passthrough, fixed one-hot encoder, scalar `gbtree` and squared-error objective. It rejects other preprocessing, native categorical splits, objectives and output shapes. The evaluator keeps numeric feature order, dropped binary category encoding, float32 split comparisons, float32 leaf values and float32 accumulation after each tree. Calibration bounds remain double precision additions/subtractions around that point estimate, with the exact original thresholds and no clipping. XGBoost's [model IO documentation](https://xgboost.readthedocs.io/en/stable/tutorials/saving_model.html) describes its official JSON model representation; the browser export is our narrower derived inference format, not a replacement XGBoost model file.

The interface keeps all four input modes, development range validation, fictional examples, fixed reference intervals, benchmark error comparisons and duration-group coverage. The browser downloads and verifies each forest's SHA-256 before prediction. It makes no prediction request or submission-storage call, and uses no third-party JavaScript libraries, analytics, cookies or local storage. Hugging Face serves the files and may log asset requests; it also inserts a creator-ID configuration script into the served HTML. Model hashes detect damaged/mismatched assets; they do not establish independent trust against a compromised hosting origin.

## Verification

- The existing 71 Python tests pass; four JavaScript tests cover invalid inputs, exact split ties, one-hot ordering, float32 summation and corrupt asset rejection.
- JavaScript predictions and unclipped bounds match the original Python pipelines exactly for **5,854 synthetic sessions** across four routes: two fictional examples, 1,000 seeded random sessions per route, valid range endpoints, categories and neighbouring valid values around every unique tree split.
- Duration-group coverage and benchmark metadata match the frozen Python demo. These are conversion checks on synthetic inputs, not a new accuracy evaluation or test-set release.
- Public Space status, pinned repository file hashes and file allowlist, served inference-asset hashes, and the hosted HTML after its verified provider bootstrap are checked separately. The verification script executes downloaded JavaScript/models in Node; it does not claim a rendered-browser check.

Unresolved collection, label construction, units, licensing, dependence and real-world validity remain visible. The original long-session coverage gap and simulated sensor-noise sensitivity are preserved. Neither deployment nor these parity tests establish measured user impact. Item 10 remains a separate usability study.

## Reproduce from the existing frozen artifacts

Run from the research checkout. Choose a new output directory; the exporter refuses to replace an existing package.

```powershell
& .\.venv\Scripts\python.exe -m calorie_estimation.static_package --source runs/demo-space-v1 --output runs/demo-static-v2
node --test tests/static_engine.test.cjs
& .\.venv\Scripts\python.exe scripts/verify-static.py --folder runs/demo-static-v2 --report runs/static-parity-v2.json
& .\.venv\Scripts\python.exe -m http.server 7860 --bind 127.0.0.1 --directory runs/demo-static-v2
```

Open `http://127.0.0.1:7860`, then stop the preview with Ctrl+C. The source archive does not include model weights: export requires the original local frozen artifacts and metadata. The supplied deployment ZIP includes the exported forests and can be previewed directly after extraction, without loading Python model libraries. Serve over HTTP; opening HTML as a local file does not support asset fetching/integrity checks.

## Publish and verify

The deliverables include `huggingface-calorie-lab-static/`, `calorie-lab-static-huggingface.zip` and `PUBLISH_HUGGINGFACE_STATIC_SPACE.ps1`. The familiar `PUBLISH_HUGGINGFACE_SPACE.ps1` now selects this Static package too. The original uploader is retained as `PUBLISH_HUGGINGFACE_DOCKER_SPACE.ps1`, which requires an eligible paid account. The publisher environment remains separate from the research environment.

```powershell
& .\PUBLISH_HUGGINGFACE_STATIC_SPACE.ps1 -CheckOnly
& .\PUBLISH_HUGGINGFACE_STATIC_SPACE.ps1
```

The scripts verify the reviewed manifest and exact 11-file allowlist, require the authenticated account `Moobakr`, and request SDK `static` without compute hardware or billing changes. They preserve a receipt and refuse to overwrite an unrelated existing Space. A matching receipt permits resume of the same package only; a changed package requires a deliberately reviewed update. A fresh machine needs normal CLI login (`-Login`); credentials never belong in chat or the package.

From the project directory, repeat the read-only hosted verification without changing the tracked report:

```powershell
& .\.venv\Scripts\python.exe scripts/verify-static-hosted.py --folder ..\huggingface-calorie-lab-static --report runs/static-hosted-check.json
```

`PUBLISHED_HUGGINGFACE_STATIC_SPACE.json` records the upload; the research verification report records the independent checks. The author confirmed basic rendering and estimate updates, completing item 9 for the selected Static route. A full keyboard/mobile accessibility audit was not performed. This deployment demonstrates exported-model delivery, static hosting, artifact integrity and client-side inference. A deployed Python API/container or production monitoring would need separate evidence.
