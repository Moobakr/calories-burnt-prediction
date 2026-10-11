---
title: Calorie Lab — Fewer Sensors
emoji: 🧪
colorFrom: green
colorTo: gray
sdk: static
app_file: index.html
pinned: false
---

# Calorie Lab

A research implementation by [Moobakr](https://huggingface.co/Moobakr) exploring sensor requirements, prediction error and uncertainty on recorded calorie labels.

This free Static Space runs predictions entirely in your browser. It downloads four exported, frozen XGBoost forests and aggregate metadata; session inputs are not sent to a prediction API, stored by the app or used for training. Hosting infrastructure may retain ordinary asset-request logs. No external JavaScript dependencies or analytics are included.

The primary heart-rate model has frozen test MAE 0.978 versus 1.032 for full inputs. Omitting temperature passed a predefined +10% relative-MAE rule; omitting both sensors failed. Nominal 90% interval coverage was 90.67% overall but 79.54% for 21–30 minute sessions. These describe benchmark labels, not verified physiological accuracy or health advice. Collection, label construction, units and dataset licensing remain unresolved.

The models are exported from the original hash-verified Python pipelines, without fitting or test-set rescoring. Explicit feature ordering, one-hot encoding and float32 tree traversal reproduce the frozen predictors. Two fictional scenarios support exploration. Bounds use the original fixed calibration thresholds and are not clipped. Input ranges come from development observations only and do not establish real-world validity.

`metadata.json` binds exported forests to original model hashes and final research snapshots. `PACKAGE_MANIFEST.json` lists every deployment file's SHA-256. The package excludes dataset observations, per-record predictions, notebooks, Python pickle files and credentials. No software or dataset license is inferred on the author's behalf.

Research source: [calories-burnt-prediction](https://github.com/Moobakr/calories-burnt-prediction). The demo branch may be ahead of the published default branch. The repository also retains a Python/Waitress Docker implementation; this Static Space does not run that server and is not evidence of a deployed container.

For local preview, serve this folder over HTTP (for example, `python -m http.server 7860 --bind 127.0.0.1`) and open `http://127.0.0.1:7860`. Opening the HTML directly from disk does not support the asset integrity checks.
