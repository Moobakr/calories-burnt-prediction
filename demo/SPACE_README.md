---
title: Calorie Lab — Fewer Sensors
emoji: 🧪
colorFrom: green
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
---

# Calorie Lab

A research implementation by [Moobakr](https://huggingface.co/Moobakr), studying the tradeoff between sensor requirements and prediction error on a supplied calorie-label benchmark.

The frozen heart-rate XGBoost model has test MAE 0.978 versus 1.032 for full inputs. Removing temperature passed a predefined +10% relative-MAE rule; removing both sensors failed it. Nominal 90% interval coverage is 90.67% overall but 79.54% for 21–30 minute sessions. These are benchmark results, not verified calorie measurements or health advice. Original collection, target construction and units remain unverified; dataset licensing is unresolved.

The app loads four previously evaluated XGBoost pipelines and their fixed interval thresholds. It does not train, recalibrate or read the dataset. The two example scenarios are fictional. Submitted inputs are processed in memory; this app does not save submissions or use analytics. Hosting infrastructure may maintain ordinary request logs.

Source and research history: [calories-burnt-prediction](https://github.com/Moobakr/calories-burnt-prediction). The demo branch may be ahead of the published default branch. `bundle/manifest.json` binds the exact model hashes to the frozen selection and evaluation snapshots. The package excludes all raw/derived observations, test predictions, bootstrap draws and credentials. No dataset or software license is inferred on the author's behalf.

## Run the packaged app

```bash
docker build -t calorie-lab .
docker run --rm -p 7860:7860 calorie-lab
```

Open `http://localhost:7860`. Hugging Face builds this Dockerfile and exposes port 7860. This is a small CPU demo with no durable storage or user accounts. Free Spaces can sleep when idle; availability and hosting limits depend on Hugging Face.
