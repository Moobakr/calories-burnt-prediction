"""Development-only mean and Ridge baselines on the frozen shared CV folds."""

from datetime import datetime, timezone
import math
from pathlib import Path
from time import perf_counter

import numpy as np
from sklearn.base import clone
from sklearn.dummy import DummyRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from threadpoolctl import threadpool_info, threadpool_limits

from .config import ROOT, file_hash, fingerprints
from .data import atomic_write, csv_bytes, write_json
from .evaluation import load_development, verify_splits
from .preprocessing import make_preprocessor


def settings(config):
    value = config["baselines"]
    alphas = value["ridge_alphas"]
    if (not isinstance(alphas, list) or not alphas
            or any(isinstance(a, bool) or not isinstance(a, (int, float))
                   or not math.isfinite(a) or a <= 0 for a in alphas)
            or len(set(alphas)) != len(alphas)):
        raise ValueError("Ridge alphas must be distinct, positive finite numbers")
    if value["ridge_solver"] != "svd" or type(value["threads"]) is not int or value["threads"] != 1:
        raise ValueError("Baseline protocol requires the SVD solver and one thread")
    return {"ridge_alphas": sorted(float(a) for a in alphas), "ridge_solver": "svd", "threads": 1}


def ridge_pipeline(features, manifest, alpha):
    return Pipeline([("preprocess", make_preprocessor(features, manifest, scale_numeric=True)),
                     ("model", Ridge(alpha=alpha, solver="svd", fit_intercept=True))])


def errors(y, predicted):
    y, predicted = np.asarray(y, dtype=float), np.asarray(predicted, dtype=float)
    if y.ndim != 1 or y.shape != predicted.shape or not len(y):
        raise ValueError("Expected matching nonempty one-dimensional targets and predictions")
    residual = predicted - y
    if not np.isfinite(residual).all():
        raise ValueError("Expected finite one-dimensional predictions and targets")
    return {"mae": float(np.mean(np.abs(residual))),
            "rmse": float(np.sqrt(np.mean(residual ** 2)))}


def cross_validate_candidate(estimator, data):
    """Fit independent pipelines; each row receives exactly one out-of-fold prediction."""
    predicted = np.full(len(data.y), np.nan)
    coverage = np.zeros(len(data.y), dtype=int)
    folds = []
    for index, (train, valid) in enumerate(data.cv):
        if (not len(train) or not len(valid) or len(np.unique(train)) != len(train)
                or len(np.unique(valid)) != len(valid) or np.intersect1d(train, valid).size
                or set(train) | set(valid) != set(range(len(data.y)))):
            raise ValueError("CV fold must partition development into disjoint train/validation rows")
        model = clone(estimator)
        started = perf_counter()
        model.fit(data.X.iloc[train], data.y[train])
        elapsed = perf_counter() - started
        prediction = model.predict(data.X.iloc[valid])
        metrics = errors(data.y[valid], prediction)
        predicted[valid] = prediction
        coverage[valid] += 1
        folds.append({"fold": index, "train_rows": len(train), "validation_rows": len(valid),
                      "fit_seconds": elapsed, **metrics})
    if not np.all(coverage == 1):
        raise ValueError("CV must validate each development row exactly once")
    return {"folds": folds,
            "mean_fold_mae": float(np.mean([fold["mae"] for fold in folds])),
            "mean_fold_rmse": float(np.mean([fold["rmse"] for fold in folds])),
            "pooled_oof": errors(data.y, predicted)}, predicted


def select_candidate(candidates):
    # Alpha is the deterministic tie breaker, independent of grid ordering.
    return min(candidates, key=lambda candidate: (candidate["mean_fold_mae"], candidate["alpha"]))


def run_baselines(prepared_dir, split_dir, run_dir, config, manifest, environment):
    import joblib

    protocol = settings(config)
    if environment.get("status") != "passed" or not environment.get("isolated_from_system_site_packages"):
        raise ValueError("An isolated environment matching the pinned ML versions is required")
    run_dir = Path(run_dir).resolve()
    if not run_dir.is_relative_to((ROOT / "runs").resolve()) or run_dir == (ROOT / "runs").resolve():
        raise ValueError("Baseline artifacts must use a new directory inside the ignored runs directory")
    if run_dir.exists():
        raise ValueError("Run directory already exists; choose a new name to preserve previous results")
    _, _, split_report = verify_splits(prepared_dir, split_dir, config, manifest)
    development = {name: load_development(prepared_dir, split_dir, config, manifest, name)
                   for name in config["feature_sets"]}
    reference = next(iter(development.values()))
    for data in development.values():
        if data.ids != reference.ids or not np.array_equal(data.y, reference.y):
            raise ValueError("Feature sets must share development rows and labels")
        if any(not np.array_equal(a, b) for pair, other in zip(data.cv, reference.cv)
               for a, b in zip(pair, other)) or len(data.cv) != len(reference.cv):
            raise ValueError("Feature sets must share development CV folds")

    run_dir.mkdir(parents=True, exist_ok=False)
    results, predictions, artifacts = [], {"User_ID": reference.ids, "Calories": reference.y}, {}
    with threadpool_limits(limits=protocol["threads"]):
        effective_threads = threadpool_info()
        jobs = [("mean", None, reference)] + [("ridge", name, data) for name, data in development.items()]
        for algorithm, feature_set, data in jobs:
            name = "mean" if algorithm == "mean" else f"ridge_{feature_set}"
            features = [] if algorithm == "mean" else config["feature_sets"][feature_set]
            candidates, candidate_predictions = [], {}
            alphas = [None] if algorithm == "mean" else protocol["ridge_alphas"]
            for alpha in alphas:
                estimator = (Pipeline([("model", DummyRegressor(strategy="mean"))]) if alpha is None
                             else ridge_pipeline(features, manifest, alpha))
                metrics, oof = cross_validate_candidate(estimator, data)
                candidates.append({"alpha": alpha, **metrics})
                candidate_predictions[alpha] = oof
            selected = candidates[0] if algorithm == "mean" else select_candidate(candidates)
            estimator = (Pipeline([("model", DummyRegressor(strategy="mean"))]) if algorithm == "mean"
                         else ridge_pipeline(features, manifest, selected["alpha"]))
            started = perf_counter()
            estimator.fit(data.X, data.y)
            fit_seconds = perf_counter() - started
            path = run_dir / f"{name}.joblib"
            joblib.dump(estimator, path)
            reloaded = joblib.load(path)
            # Persistence verification only: no holdout or in-sample performance scoring.
            np.testing.assert_allclose(reloaded.predict(data.X), estimator.predict(data.X), rtol=0, atol=0)
            artifacts[path.name] = file_hash(path)
            predictions[name] = candidate_predictions[selected["alpha"]]
            results.append({"name": name, "algorithm": algorithm, "feature_set": feature_set,
                            "input_columns": features, "selected_alpha": selected["alpha"],
                            "mean_fold_mae": selected["mean_fold_mae"],
                            "mean_fold_rmse": selected["mean_fold_rmse"],
                            "pooled_oof": selected["pooled_oof"], "candidates": candidates,
                            "cv_fit_count": len(alphas) * len(data.cv), "development_refit_rows": len(data.y),
                            "development_refit_seconds": fit_seconds,
                            "model_parameters": estimator.named_steps["model"].get_params(),
                            "artifact": path.name, "reload_predictions_identical": True})

    prediction_path = run_dir / "development_oof.csv"
    atomic_write(prediction_path, csv_bytes(list(predictions), zip(*predictions.values())))
    artifacts[prediction_path.name] = file_hash(prediction_path)
    report = {"status": "passed", "schema_version": 1,
              "created_at_utc": datetime.now(timezone.utc).isoformat(),
              "result_scope": "Development tuning CV; selected Ridge scores reuse alpha-selection folds",
              "selection_rule": "lowest unweighted mean validation-fold MAE; ties choose smaller alpha",
              "target": manifest["target_column"], "target_unit": "interpreted kcal/session; unverified label method",
              "development_rows": len(reference.ids), "calibration_used_for_fitting_or_scoring": False,
              "test_used_for_fitting_or_scoring": False, "protocol": protocol,
              "source_sha256": manifest["sha256"],
              "modeling_table_sha256": file_hash(Path(prepared_dir) / "modeling_table.csv"),
              "assignments_sha256": file_hash(Path(split_dir) / "assignments.csv"),
              "split_manifest_sha256": file_hash(Path(split_dir) / "split_manifest.json"),
              "preparation_manifest_sha256": file_hash(Path(prepared_dir) / "preparation_manifest.json"),
              "experiment_plan_sha256": file_hash(ROOT / "docs/EXPERIMENT_PLAN.md"),
              "split_verification": split_report, "project_fingerprints": fingerprints(),
              "environment": environment, "effective_threadpools_during_fit": effective_threads,
              "total_cv_fits": sum(result["cv_fit_count"] for result in results),
              "total_development_refits": len(results), "artifacts_sha256": artifacts, "results": results}
    # A complete report is written last. Failed/partial runs have no completion report.
    write_json(run_dir / "metrics.json", report)
    return {"status": "passed", "run_dir": str(run_dir), "development_rows": len(reference.ids),
            "total_cv_fits": report["total_cv_fits"], "total_development_refits": len(results),
            "test_evaluated": False, "results": [{key: result[key] for key in
                ("name", "selected_alpha", "mean_fold_mae", "mean_fold_rmse")} for result in results]}
