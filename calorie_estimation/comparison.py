"""Matched development-only XGBoost search and input-requirement comparisons."""

import csv
from datetime import datetime, timezone
import json
import math
from pathlib import Path
from time import perf_counter

import numpy as np
from sklearn.model_selection import ParameterSampler
from sklearn.pipeline import Pipeline
from threadpoolctl import threadpool_info, threadpool_limits
from xgboost import XGBRegressor

from .baselines import cross_validate_candidate, errors
from .config import ROOT, file_hash, fingerprints
from .data import atomic_write, csv_bytes, write_json
from .evaluation import load_development, verify_splits
from .preprocessing import make_preprocessor


def settings(config):
    value = config["comparison"]
    if set(config["feature_sets"]) != {"duration", "basic", "heart_rate", "full"}:
        raise ValueError("Comparison requires the four planned input sets")
    for key in ("search_seed", "model_seed"):
        if type(value[key]) is not int or value[key] < 0:
            raise ValueError("Search/model seeds must be nonnegative integers")
    if (type(value["n_candidates"]) is not int or value["n_candidates"] != 30
            or type(value["threads"]) is not int or value["threads"] != 1
            or value["tree_method"] != "hist"):
        raise ValueError("Comparison requires 30 configurations, one thread and histogram trees")
    if (type(value["latency_warmups"]) is not int or value["latency_warmups"] < 1
            or type(value["latency_repeats"]) is not int or value["latency_repeats"] < 2
            or value["latency_batch_sizes"] != [1, 100]
            or any(type(size) is not int for size in value["latency_batch_sizes"])):
        raise ValueError("Invalid latency protocol")
    space = value["search_space"]
    expected = {"n_estimators", "max_depth", "learning_rate", "min_child_weight", "subsample",
                "colsample_bytree", "reg_lambda", "reg_alpha"}
    if set(space) != expected:
        raise ValueError("Search space must contain the eight documented XGBoost parameters")
    for name, values in space.items():
        if (not isinstance(values, list) or not values
                or any(isinstance(v, bool) or not isinstance(v, (int, float))
                       or not math.isfinite(v) for v in values) or len(set(values)) != len(values)):
            raise ValueError("Search values must be distinct finite numbers")
        if name in ("n_estimators", "max_depth"):
            valid = all(type(v) is int and v > 0 for v in values)
        elif name in ("reg_alpha", "reg_lambda", "min_child_weight"):
            valid = all(v >= 0 for v in values)
        else:
            valid = all(0 < v <= 1 for v in values)
        if not valid:
            raise ValueError(f"Invalid values for {name}")
    if math.prod(len(values) for values in space.values()) < value["n_candidates"]:
        raise ValueError("Search space is smaller than the 30-configuration budget")
    return {key: value[key] for key in ("search_seed", "model_seed", "n_candidates", "threads", "tree_method",
                                      "latency_warmups", "latency_repeats", "latency_batch_sizes", "search_space")}


def sample_candidates(protocol):
    return list(ParameterSampler(protocol["search_space"], n_iter=protocol["n_candidates"],
                                 random_state=protocol["search_seed"]))


def xgb_pipeline(features, manifest, parameters, model_seed):
    return Pipeline([("preprocess", make_preprocessor(features, manifest, scale_numeric=False)),
                     ("model", XGBRegressor(**parameters, objective="reg:squarederror", eval_metric="mae",
                                            tree_method="hist", n_jobs=1, random_state=model_seed))])


def select_candidate(candidates):
    return min(candidates, key=lambda candidate: (candidate["mean_fold_mae"], candidate["candidate_index"]))


def evaluate_search(data, features, manifest, candidates, model_seed, progress=None):
    results, predictions = [], {}
    for index, parameters in enumerate(candidates):
        metrics, oof = cross_validate_candidate(xgb_pipeline(features, manifest, parameters, model_seed), data)
        results.append({"candidate_index": index, "parameters": parameters, **metrics})
        predictions[index] = oof
        if progress:
            progress(f"candidate {index + 1}/{len(candidates)}: mean-fold MAE {metrics['mean_fold_mae']:.6f}")
    selected = select_candidate(results)
    return results, selected, predictions[selected["candidate_index"]]


def load_baseline_run(run_dir, data, config, manifest, split_report):
    """Bind historical baseline outputs to the same labels, IDs and saved CV protocol."""
    run_dir = Path(run_dir)
    report = json.loads((run_dir / "metrics.json").read_bytes())
    if (report["status"] != "passed" or report["source_sha256"] != manifest["sha256"]
            or report["modeling_table_sha256"] != split_report["modeling_table_sha256"]
            or report["assignments_sha256"] != split_report["assignments_sha256"]
            or report["split_verification"]["protocol"] != split_report["protocol"]
            or report["development_rows"] != len(data.ids)
            or report["calibration_used_for_fitting_or_scoring"] or report["test_used_for_fitting_or_scoring"]):
        raise ValueError("Baseline run does not match this development dataset/protocol")
    for name, expected in report["artifacts_sha256"].items():
        if Path(name).name != name or file_hash(run_dir / name) != expected:
            raise ValueError("Baseline artifact hash mismatch or invalid filename")
    with (run_dir / "development_oof.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if tuple(row["User_ID"] for row in rows) != data.ids:
        raise ValueError("Baseline predictions do not cover the same development IDs in order")
    if not np.array_equal([float(row["Calories"]) for row in rows], data.y):
        raise ValueError("Baseline targets differ from development labels")
    expected_names = {"mean", *(f"ridge_{name}" for name in config["feature_sets"])}
    if {row["name"] for row in report["results"]} != expected_names or len(report["results"]) != len(expected_names):
        raise ValueError("Baseline results must include mean and all configured Ridge input sets")
    for result in report["results"]:
        expected_features = [] if result["name"] == "mean" else config["feature_sets"][result["feature_set"]]
        if result["input_columns"] != expected_features:
            raise ValueError("Baseline feature sets differ from comparison configuration")
        prediction = np.array([float(row[result["name"]]) for row in rows])
        pooled = errors(data.y, prediction)
        fold_mae = np.mean([errors(data.y[valid], prediction[valid])["mae"] for _, valid in data.cv])
        fold_rmse = np.mean([errors(data.y[valid], prediction[valid])["rmse"] for _, valid in data.cv])
        if (not np.allclose([pooled["mae"], pooled["rmse"], fold_mae, fold_rmse],
                            [result["pooled_oof"]["mae"], result["pooled_oof"]["rmse"],
                             result["mean_fold_mae"], result["mean_fold_rmse"]], rtol=0, atol=1e-10)):
            raise ValueError("Baseline scores do not match saved out-of-fold predictions")
    return report, rows


def input_tradeoffs(results):
    output = []
    for algorithm in ("ridge", "xgboost"):
        group = [result for result in results if result["algorithm"] == algorithm]
        full_mae = next(result["mean_fold_mae"] for result in group if result["feature_set"] == "full")
        for result in group:
            features = result["input_columns"]
            difference = result["mean_fold_mae"] - full_mae
            output.append({"algorithm": algorithm, "feature_set": result["feature_set"],
                           "input_columns": features, "input_field_count": len(features),
                           "requires_heart_rate": "Heart_Rate" in features,
                           "requires_temperature": "Body_Temp" in features,
                           "mean_fold_mae": result["mean_fold_mae"], "mean_fold_rmse": result["mean_fold_rmse"],
                           "absolute_mae_change_vs_full": difference,
                           "relative_mae_change_vs_full": None if full_mae == 0 else difference / full_mae,
                           "competitiveness_decision": "deferred_until_reserved_test"})
    return output


def measure_latency(model, X, protocol):
    measurements = []
    for count in protocol["latency_batch_sizes"]:
        sample = X.iloc[:min(count, len(X))]
        if len(sample) != count:
            continue
        for _ in range(protocol["latency_warmups"]):
            model.predict(sample)
        elapsed = []
        for _ in range(protocol["latency_repeats"]):
            started = perf_counter()
            model.predict(sample)
            elapsed.append((perf_counter() - started) * 1000)
        measurements.append({"batch_rows": count, "warmups": protocol["latency_warmups"],
                             "repeats": len(elapsed), "median_ms_per_batch": float(np.median(elapsed)),
                             "p95_ms_per_batch": float(np.percentile(elapsed, 95))})
    return measurements


def write_plot(rows, run_dir):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5), layout="constrained")
    for algorithm, label, color in (("ridge", "Ridge", "#6366f1"), ("xgboost", "XGBoost", "#059669")):
        group = [row for row in rows if row["algorithm"] == algorithm]
        positions = np.arange(len(group))
        for axis, metric in zip(axes, ("mean_fold_mae", "mean_fold_rmse")):
            axis.plot(positions, [row[metric] for row in group], marker="o", label=label, color=color)
            axis.set_xticks(positions, [f"{row['feature_set']}\n({row['input_field_count']} fields)" for row in group])
            axis.grid(axis="y", alpha=.2)
            axis.set_ylabel(f"{'MAE' if metric.endswith('mae') else 'RMSE'} (interpreted kcal/session)")
            axis.set_ylim(bottom=0)
    axes[0].legend()
    fig.suptitle("Prediction error versus input requirements\nDevelopment tuning CV; final test evaluation deferred", fontsize=12)
    fig.savefig(Path(run_dir) / "input_comparison.png", dpi=180)
    fig.savefig(Path(run_dir) / "input_comparison.svg")
    plt.close(fig)


def run_comparison(prepared_dir, split_dir, baseline_run_dir, run_dir, config, manifest, environment, progress=None):
    import joblib

    protocol = settings(config)
    candidates = sample_candidates(protocol)
    if environment.get("status") != "passed" or not environment.get("isolated_from_system_site_packages"):
        raise ValueError("An isolated environment matching the pinned ML versions is required")
    run_dir, baseline_run_dir = Path(run_dir).resolve(), Path(baseline_run_dir).resolve()
    local = (ROOT / "runs").resolve()
    if any(not path.is_relative_to(local) or path == local for path in (run_dir, baseline_run_dir)):
        raise ValueError("Comparison and baseline run directories must be inside the ignored runs directory")
    if run_dir.exists():
        raise ValueError("Run directory already exists; choose a new name to preserve previous results")
    _, _, split_report = verify_splits(prepared_dir, split_dir, config, manifest)
    development = {name: load_development(prepared_dir, split_dir, config, manifest, name)
                   for name in config["feature_sets"]}
    reference = next(iter(development.values()))
    for data in development.values():
        if data.ids != reference.ids or not np.array_equal(data.y, reference.y) or len(data.cv) != len(reference.cv):
            raise ValueError("Input sets must share development data and CV folds")
        if any(not np.array_equal(a, b) for pair, other in zip(data.cv, reference.cv) for a, b in zip(pair, other)):
            raise ValueError("Input sets must share development CV folds")
    baseline, baseline_rows = load_baseline_run(baseline_run_dir, reference, config, manifest, split_report)
    run_dir.mkdir(parents=True, exist_ok=False)
    write_json(run_dir / "search_manifest.json", {"protocol": protocol, "candidates": candidates,
               "project_fingerprints": fingerprints(), "experiment_plan_sha256": file_hash(ROOT / "docs/EXPERIMENT_PLAN.md"),
               "assignments_sha256": split_report["assignments_sha256"],
               "snapshot_stage": "before_first_xgboost_fit_in_this_run"})
    results, artifacts = [], {}
    predictions = {"User_ID": reference.ids, "Calories": reference.y}
    with threadpool_limits(limits=protocol["threads"]):
        effective_threads = threadpool_info()
        for name, data in development.items():
            callback = None if progress is None else lambda message, name=name: progress(f"{name}: {message}")
            scores, selected, oof = evaluate_search(data, config["feature_sets"][name], manifest,
                                                   candidates, protocol["model_seed"], callback)
            model = xgb_pipeline(config["feature_sets"][name], manifest, selected["parameters"], protocol["model_seed"])
            started = perf_counter()
            model.fit(data.X, data.y)
            fit_seconds = perf_counter() - started
            artifact = run_dir / f"xgboost_{name}.joblib"
            joblib.dump(model, artifact)
            reloaded = joblib.load(artifact)
            np.testing.assert_allclose(reloaded.predict(data.X), model.predict(data.X), rtol=0, atol=0)
            predictions[f"xgboost_{name}"] = oof
            artifacts[artifact.name] = file_hash(artifact)
            results.append({"name": f"xgboost_{name}", "algorithm": "xgboost", "feature_set": name,
                            "input_columns": config["feature_sets"][name],
                            "selected_candidate_index": selected["candidate_index"],
                            "selected_parameters": selected["parameters"], "candidates": scores,
                            "mean_fold_mae": selected["mean_fold_mae"], "mean_fold_rmse": selected["mean_fold_rmse"],
                            "pooled_oof": selected["pooled_oof"], "cv_fit_count": len(candidates) * len(data.cv),
                            "development_refit_rows": len(data.y), "development_refit_seconds": fit_seconds,
                            "fitted_boosting_rounds": model.named_steps["model"].get_booster().num_boosted_rounds(),
                            "artifact": artifact.name, "reload_predictions_identical": True})
        latencies = []
        for result, directory in ([(r, baseline_run_dir) for r in baseline["results"] if r["algorithm"] == "ridge"]
                                   + [(r, run_dir) for r in results]):
            data = development[result["feature_set"]]
            latencies.append({"name": result["name"], "measurements": measure_latency(
                joblib.load(directory / result["artifact"]), data.X, protocol)})
    prediction_path = run_dir / "development_oof.csv"
    atomic_write(prediction_path, csv_bytes(list(predictions), zip(*predictions.values())))
    artifacts[prediction_path.name] = file_hash(prediction_path)
    tradeoffs = input_tradeoffs(baseline["results"] + results)
    diagnostics = []
    for result, rows in [(r, baseline_rows) for r in baseline["results"]] + [(r, None) for r in results]:
        predicted = (np.array([float(row[result["name"]]) for row in rows]) if rows is not None
                     else predictions[result["name"]])
        absolute = np.abs(predicted - reference.y)
        diagnostics.append({"name": result["name"], "negative_oof_predictions": int(np.sum(predicted < 0)),
                            "median_absolute_error": float(np.median(absolute)),
                            "p90_absolute_error": float(np.percentile(absolute, 90)),
                            "p95_absolute_error": float(np.percentile(absolute, 95))})
    write_plot(tradeoffs, run_dir)
    for name in ("search_manifest.json", "input_comparison.png", "input_comparison.svg"):
        artifacts[name] = file_hash(run_dir / name)
    report = {"status": "passed", "schema_version": 1, "created_at_utc": datetime.now(timezone.utc).isoformat(),
              "result_scope": "Development tuning CV; selected scores reuse hyperparameter-selection folds",
              "selection_rule": "lowest unweighted mean-fold MAE; exact ties choose lower candidate index",
              "target_unit": "interpreted kcal/session; unverified label method", "development_rows": len(reference.ids),
              "protocol": protocol, "search_candidates": candidates, "results": results, "input_tradeoffs": tradeoffs,
              "latency": latencies, "oof_diagnostics": diagnostics,
              "baseline_metrics_sha256": file_hash(baseline_run_dir / "metrics.json"),
              "baseline_project_fingerprints": baseline["project_fingerprints"],
              "source_sha256": manifest["sha256"], "modeling_table_sha256": split_report["modeling_table_sha256"],
              "assignments_sha256": split_report["assignments_sha256"],
              "split_manifest_sha256": file_hash(Path(split_dir) / "split_manifest.json"),
              "experiment_plan_sha256": file_hash(ROOT / "docs/EXPERIMENT_PLAN.md"),
              "project_fingerprints": fingerprints(), "environment": environment,
              "effective_threadpools_during_fit": effective_threads, "artifacts_sha256": artifacts,
              "total_cv_fits": sum(r["cv_fit_count"] for r in results), "total_development_refits": len(results),
              "calibration_used_for_fitting_or_scoring": False, "test_used_for_fitting_or_scoring": False}
    write_json(run_dir / "metrics.json", report)
    return {"status": "passed", "run_dir": str(run_dir), "total_cv_fits": report["total_cv_fits"],
            "test_evaluated": False, "input_tradeoffs": tradeoffs}
