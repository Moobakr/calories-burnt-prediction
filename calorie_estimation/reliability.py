"""Frozen-model diagnostics, paired sensor stress tests and split-conformal audits."""

from datetime import datetime, timezone
from decimal import Decimal, ROUND_CEILING
import hashlib
import io
import json
from pathlib import Path

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_info, threadpool_limits

from .baselines import errors, ridge_pipeline
from .comparison import load_baseline_run, xgb_pipeline
from .config import ROOT, file_hash, fingerprints
from .data import atomic_write, csv_bytes, write_json
from .evaluation import canonical_id, load_development, verify_splits

REFERENCE = "https://arxiv.org/abs/2107.07511"


def settings(config):
    value = config["reliability"]
    if (type(value["nominal_coverage"]) not in (float, int) or value["nominal_coverage"] != .9
            or type(value["threads"]) is not int or value["threads"] != 1
            or type(value["noise_draws"]) is not int or value["noise_draws"] != 20):
        raise ValueError("Reliability requires 90% nominal coverage, 20 noise draws and one thread")
    for key in ("calibration_role_seed", "noise_seed"):
        if type(value[key]) is not int or value[key] < 0:
            raise ValueError("Reliability seeds must be nonnegative integers")
    if value["heart_rate_noise_sd"] != [2., 5.] or value["temperature_noise_sd"] != [.1, .3]:
        raise ValueError("Use the predefined sensor stress-test magnitudes")
    return dict(value)


def calibration_roles(membership, seed):
    ids = [canonical_id(identity) for identity, (partition, _) in membership.items() if partition == "calibration"]
    if len(ids) < 2 or len(ids) != len(set(ids)):
        raise ValueError("Calibration needs at least two unique records")
    ranked = sorted(ids, key=lambda identity: (hashlib.sha256(
        f"calorie-estimation:v1:calibration-role:{seed}:{identity}".encode()).digest(), int(identity)))
    midpoint = len(ranked) // 2
    return {identity: "interval_fit" if index < midpoint else "interval_audit" for index, identity in enumerate(ranked)}


def conformal_threshold(y, predicted, nominal=.9):
    y, predicted = np.asarray(y, dtype=float), np.asarray(predicted, dtype=float)
    if (y.ndim != 1 or y.shape != predicted.shape or not len(y)
            or not np.isfinite(y).all() or not np.isfinite(predicted).all()
            or isinstance(nominal, bool) or not 0 < nominal < 1):
        raise ValueError("Invalid calibration residuals or nominal coverage")
    rank = int((Decimal(len(y) + 1) * Decimal(str(nominal))).to_integral_value(rounding=ROUND_CEILING))
    residuals = np.abs(y - predicted)
    threshold = float(np.sort(residuals)[rank - 1]) if rank <= len(y) else float("inf")
    return {"fit_rows": len(y), "rank_one_based": rank, "threshold": threshold}


def subset_frame(records, ids, membership, allowed_partition):
    if allowed_partition not in ("development", "calibration"):
        raise ValueError("Reliability cannot load test observations for analysis")
    if len(ids) != len(set(ids)) or any(membership[identity][0] != allowed_partition for identity in ids):
        raise ValueError("Requested IDs differ from the permitted partition")
    by_id = {canonical_id(row["User_ID"]): row for row in records}
    frame = pd.DataFrame([by_id[identity] for identity in ids], index=list(ids))
    for name in frame.columns:
        if name not in ("User_ID", "Gender"):
            frame[name] = pd.to_numeric(frame[name], errors="raise")
    return frame


def group_masks(frame):
    groups = [("gender", label, frame.Gender.to_numpy() == label) for label in ("female", "male")]
    for axis, column, bands in (("age", "Age", ((20,39), (40,59), (60,79))),
                                ("duration", "Duration", ((1,10), (11,20), (21,30)))):
        values = frame[column].to_numpy()
        covered = np.zeros(len(frame), dtype=bool)
        for low, high in bands:
            mask = (values >= low) & (values <= high)
            covered |= mask
            groups.append((axis, f"{low}-{high}", mask))
        if not np.all(covered):
            groups.append((axis, "outside_predefined_bands", ~covered))
    return groups


def score_predictions(y, predicted, frame, threshold=None):
    y, predicted = np.asarray(y, dtype=float), np.asarray(predicted, dtype=float)
    if threshold is not None and (isinstance(threshold, bool) or np.isnan(threshold) or threshold < 0):
        raise ValueError("Interval threshold must be nonnegative")
    metrics = {**errors(y, predicted), "n": len(y),
               "p95_absolute_error": float(np.percentile(np.abs(predicted - y), 95)),
               "negative_predictions": int(np.sum(predicted < 0))}
    if threshold is not None:
        metrics.update(coverage=float(np.mean(np.abs(predicted - y) <= threshold)),
                       covered=int(np.sum(np.abs(predicted - y) <= threshold)),
                       mean_width=2 * threshold, negative_lower_bounds=int(np.sum(predicted - threshold < 0)))
    groups = []
    for axis, label, mask in group_masks(frame):
        if not np.any(mask):
            groups.append({"axis": axis, "group": label, "n": 0, "mae": None, "rmse": None,
                           **({"coverage": None, "mean_width": None} if threshold is not None else {})})
            continue
        row = {"axis": axis, "group": label, "n": int(mask.sum()), **errors(y[mask], predicted[mask]),
               "p95_absolute_error": float(np.percentile(np.abs(predicted[mask] - y[mask]), 95))}
        if threshold is not None:
            row.update(coverage=float(np.mean(np.abs(predicted[mask] - y[mask]) <= threshold)),
                       covered=int(np.sum(np.abs(predicted[mask] - y[mask]) <= threshold)), mean_width=2 * threshold)
        groups.append(row)
    return {"overall": metrics, "groups": groups}


def noise_conditions(protocol):
    return [{"name": f"heart_rate_sd_{sd:g}", "column": "Heart_Rate", "sd": sd}
            for sd in protocol["heart_rate_noise_sd"]] + [
                {"name": f"temperature_sd_{sd:g}", "column": "Body_Temp", "sd": sd}
                for sd in protocol["temperature_noise_sd"]]


def noise_matrix(seed, partition, column, draws, n):
    encoded = f"calorie-estimation:v1:noise:{seed}:{partition}:{column}".encode()
    stream_seed = int.from_bytes(hashlib.sha256(encoded).digest()[:8], "big")
    return np.random.default_rng(stream_seed).standard_normal((draws, n))


def noisy_prediction(model, X, condition, z):
    if condition["column"] not in X:
        return model.predict(X)
    perturbed = X.copy()
    perturbed[condition["column"]] = X[condition["column"]].to_numpy() + condition["sd"] * z
    return model.predict(perturbed)


def noise_summary(y, predictions, frame, clean_predictions, threshold=None):
    y, predictions = np.asarray(y, dtype=float), np.asarray(predictions, dtype=float)
    if (predictions.ndim != 2 or predictions.shape[1] != len(y) or len(predictions) < 2
            or not np.isfinite(predictions).all()):
        raise ValueError("Noise predictions must contain at least two finite matched draws")
    residuals = predictions - y[None, :]
    absolute = np.abs(residuals)
    maes, rmses = absolute.mean(axis=1), np.sqrt((residuals ** 2).mean(axis=1))
    result = {"n": len(y), "draws": len(predictions), "mean_mae": float(maes.mean()),
              "sd_mae_across_draws": float(maes.std(ddof=1)), "mean_rmse": float(rmses.mean()),
              "sd_rmse_across_draws": float(rmses.std(ddof=1)),
              "mae_change_from_clean": float(maes.mean() - errors(y, clean_predictions)["mae"])}
    if threshold is not None:
        coverage = (absolute <= threshold).mean(axis=1)
        result.update(mean_coverage=float(coverage.mean()), sd_coverage_across_draws=float(coverage.std(ddof=1)),
                      mean_width=2 * threshold, groups=[])
        for axis, label, mask in group_masks(frame):
            result["groups"].append({"axis": axis, "group": label, "n": int(mask.sum()),
                                      "mean_coverage": float((absolute[:, mask] <= threshold).mean()) if mask.any() else None})
    return result


def load_comparison_run(directory, baseline_directory, dev, config, manifest, split):
    import csv
    baseline, baseline_rows = load_baseline_run(baseline_directory, dev, config, manifest, split)
    directory = Path(directory)
    report = json.loads((directory / "metrics.json").read_bytes())
    for key in ("source_sha256", "modeling_table_sha256", "assignments_sha256"):
        if report[key] != baseline[key]:
            raise ValueError("Comparison data identity differs from the baseline")
    if (report["status"] != "passed" or report["development_rows"] != len(dev.ids)
            or report["calibration_used_for_fitting_or_scoring"] or report["test_used_for_fitting_or_scoring"]
            or report["baseline_metrics_sha256"] != file_hash(Path(baseline_directory) / "metrics.json")):
        raise ValueError("Comparison run must be the frozen development-only experiment")
    for name, expected in report["artifacts_sha256"].items():
        if Path(name).name != name or file_hash(directory / name) != expected:
            raise ValueError("Comparison artifact hash mismatch")
    with (directory / "development_oof.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if tuple(row["User_ID"] for row in rows) != dev.ids or not np.array_equal([float(row["Calories"]) for row in rows], dev.y):
        raise ValueError("Comparison predictions differ from development IDs/labels")
    if ({r["name"] for r in report["results"]} != {f"xgboost_{name}" for name in config["feature_sets"]}
            or len(report["results"]) != len(config["feature_sets"])):
        raise ValueError("Comparison must contain all planned input sets")
    for result in report["results"]:
        prediction = np.array([float(row[result["name"]]) for row in rows])
        mae = float(np.mean([errors(dev.y[valid], prediction[valid])["mae"] for _, valid in dev.cv]))
        if (result["input_columns"] != config["feature_sets"][result["feature_set"]]
                or not np.isclose(mae, result["mean_fold_mae"], rtol=0, atol=1e-10)):
            raise ValueError("Comparison inputs or scores differ from frozen OOF records")
    return baseline, baseline_rows, report, rows


def write_plot(results, directory):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.6), layout="constrained")
    for name, label, color in (("xgboost_heart_rate", "XGBoost: heart rate", "#059669"),
                               ("xgboost_full", "XGBoost: full", "#6366f1")):
        result = next(result for result in results if result["name"] == name)
        dev = [row for row in result["development_oof"]["groups"] if row["axis"] == "duration"]
        audit = [row for row in result["interval_audit"]["groups"] if row["axis"] == "duration"]
        axes[0].plot([row["group"] for row in dev], [row["mae"] for row in dev], "o-", color=color, label=label)
        axes[1].plot([row["group"] for row in audit], [100 * row["coverage"] for row in audit], "o-", color=color)
        coverage = [100 * result["interval_audit"]["overall"]["coverage"]] + [100 * row["interval_audit"]["mean_coverage"] for row in result["noise"]]
        axes[2].plot(range(5), coverage, "o-", color=color)
    axes[0].set(title="Development OOF error", ylabel="MAE (interpreted kcal/session)", xlabel="Duration (minutes)")
    axes[0].set_ylim(bottom=0)
    axes[0].legend(fontsize=8)
    axes[1].set(title="Clean interval-audit coverage", ylabel="Coverage (%)", xlabel="Duration (minutes)", ylim=(0,100))
    axes[2].set(title="Interval audit under simulated noise", ylabel="Mean coverage across 20 draws (%)", ylim=(0,100))
    axes[2].set_xticks(range(5), ["Clean", "HR\nSD 2", "HR\nSD 5", "Temp\nSD .1", "Temp\nSD .3"])
    for axis in axes:
        axis.grid(axis="y", alpha=.2)
    for axis in axes[1:]:
        axis.axhline(90, linestyle="--", color="#444444", linewidth=1)
    fig.suptitle("Reliability diagnostics: fixed models and 90% nominal intervals\nDisjoint interval audit; final test evaluation deferred", fontsize=12)
    fig.savefig(Path(directory) / "reliability.png", dpi=180)
    plt.close(fig)


def run_reliability(prepared_dir, split_dir, baseline_dir, comparison_dir, run_dir, config, manifest, environment, progress=None):
    import joblib
    protocol = settings(config)
    if environment.get("status") != "passed" or not environment.get("isolated_from_system_site_packages"):
        raise ValueError("An isolated environment matching the pinned ML versions is required")
    run_dir, baseline_dir, comparison_dir = map(lambda path: Path(path).resolve(), (run_dir, baseline_dir, comparison_dir))
    local = (ROOT / "runs").resolve()
    if any(not path.is_relative_to(local) or path == local for path in (run_dir, baseline_dir, comparison_dir)):
        raise ValueError("Reliability and source runs must be inside the ignored runs directory")
    if run_dir.exists():
        raise ValueError("Run directory already exists; choose a new name to preserve previous results")
    records, membership, split = verify_splits(prepared_dir, split_dir, config, manifest)
    development = {name: load_development(prepared_dir, split_dir, config, manifest, name) for name in config["feature_sets"]}
    reference = next(iter(development.values()))
    baseline, old_rows, comparison, new_rows = load_comparison_run(comparison_dir, baseline_dir, reference, config, manifest, split)
    roles = calibration_roles(membership, protocol["calibration_role_seed"])
    run_dir.mkdir(parents=True, exist_ok=False)
    atomic_write(run_dir / "calibration_roles.csv", csv_bytes(["User_ID", "role"],
                 [(identity, roles[identity]) for identity in sorted(roles, key=int)]))
    write_json(run_dir / "analysis_manifest.json", {"snapshot_stage": "before_calibration_label_analysis",
               "protocol": protocol, "calibration_roles_sha256": file_hash(run_dir / "calibration_roles.csv"),
               "source_runs": {"baseline": file_hash(baseline_dir / "metrics.json"), "comparison": file_hash(comparison_dir / "metrics.json")},
               "assignments_sha256": split["assignments_sha256"], "project_fingerprints": fingerprints(),
               "experiment_plan_sha256": file_hash(ROOT / "docs/EXPERIMENT_PLAN.md")})
    dev_frame = subset_frame(records, reference.ids, membership, "development")
    fit_ids = tuple(sorted((identity for identity, role in roles.items() if role == "interval_fit"), key=int))
    audit_ids = tuple(sorted((identity for identity, role in roles.items() if role == "interval_audit"), key=int))
    fit = subset_frame(records, fit_ids, membership, "calibration")
    audit = subset_frame(records, audit_ids, membership, "calibration")
    fit_y, audit_y = fit.Calories.to_numpy(dtype=float), audit.Calories.to_numpy(dtype=float)
    conditions = noise_conditions(protocol)
    z = {partition: {column: noise_matrix(protocol["noise_seed"], partition, column, protocol["noise_draws"], n)
                      for column in ("Heart_Rate", "Body_Temp")}
         for partition, n in (("development", len(reference.ids)), ("interval_audit", len(audit_ids)))}
    results, artifacts, thresholds = [], {}, {}
    jobs = [(result, baseline_dir, old_rows) for result in baseline["results"] if result["algorithm"] == "ridge"] + [
             (result, comparison_dir, new_rows) for result in comparison["results"]]
    with threadpool_limits(limits=1):
        effective_threads = threadpool_info()
        for result, directory, rows in jobs:
            name, features = result["name"], result["input_columns"]
            data = development[result["feature_set"]]
            model = joblib.load(directory / result["artifact"])
            clean_oof = np.array([float(row[name]) for row in rows])
            noisy_oof = np.empty((len(conditions), protocol["noise_draws"], len(data.ids)))
            replayed_oof = np.full(len(data.ids), np.nan)
            for fold_index, (train, valid) in enumerate(data.cv):
                estimator = (ridge_pipeline(features, manifest, result["selected_alpha"]) if result["algorithm"] == "ridge"
                             else xgb_pipeline(features, manifest, result["selected_parameters"], comparison["protocol"]["model_seed"]))
                estimator.fit(data.X.iloc[train], data.y[train])
                replayed_oof[valid] = estimator.predict(data.X.iloc[valid])
                for ci, condition in enumerate(conditions):
                    for draw in range(protocol["noise_draws"]):
                        noisy_oof[ci, draw, valid] = (replayed_oof[valid] if condition["column"] not in features else
                            noisy_prediction(estimator, data.X.iloc[valid], condition, z["development"][condition["column"]][draw, valid]))
                if progress:
                    progress(f"{name}: replayed/stressed development fold {fold_index + 1}/{len(data.cv)}")
            if not np.allclose(replayed_oof, clean_oof, rtol=0, atol=1e-10):
                raise ValueError(f"{name}: replayed clean OOF predictions differ from the frozen run")
            fit_prediction = np.asarray(model.predict(fit[features]), dtype=float)
            quantile = conformal_threshold(fit_y, fit_prediction, protocol["nominal_coverage"])
            threshold = quantile["threshold"]
            audit_prediction = np.asarray(model.predict(audit[features]), dtype=float)
            noisy_audit = np.empty((len(conditions), protocol["noise_draws"], len(audit)))
            noise_reports = []
            for ci, condition in enumerate(conditions):
                for draw in range(protocol["noise_draws"]):
                    noisy_audit[ci, draw] = (audit_prediction if condition["column"] not in features else
                        noisy_prediction(model, audit[features], condition, z["interval_audit"][condition["column"]][draw]))
                column = condition["column"]
                low, high = dev_frame[column].min(), dev_frame[column].max()
                perturbed_dev = dev_frame[column].to_numpy()[None, :] + condition["sd"] * z["development"][column]
                perturbed_audit = audit[column].to_numpy()[None, :] + condition["sd"] * z["interval_audit"][column]
                noise_reports.append({**condition, "sensor_used": column in features,
                    "development": {**noise_summary(data.y, noisy_oof[ci], dev_frame, clean_oof),
                        "fraction_outside_development_feature_range": float(np.mean((perturbed_dev < low) | (perturbed_dev > high)))},
                    "interval_audit": {**noise_summary(audit_y, noisy_audit[ci], audit, audit_prediction, threshold),
                        "fraction_outside_development_feature_range": float(np.mean((perturbed_audit < low) | (perturbed_audit > high)))}})
            buffer = io.BytesIO()
            np.savez_compressed(buffer, development_ids=np.asarray(data.ids), interval_fit_ids=np.asarray(fit_ids),
                                interval_audit_ids=np.asarray(audit_ids), clean_oof=clean_oof, noisy_oof=noisy_oof,
                                fit_predictions=fit_prediction, audit_predictions=audit_prediction, noisy_audit=noisy_audit)
            artifact = run_dir / f"{name}_diagnostics.npz"
            atomic_write(artifact, buffer.getvalue())
            artifacts[artifact.name] = file_hash(artifact)
            binding = {**quantile, "nominal_coverage": protocol["nominal_coverage"], "method": "absolute-residual-split-conformal-v1",
                       "model_artifact": result["artifact"], "model_sha256": file_hash(directory / result["artifact"]),
                       "calibration_roles_sha256": file_hash(run_dir / "calibration_roles.csv"),
                       "audit_rows": len(audit), "audit_labels_used_for_quantile": False, "refit_using_audit_allowed": False}
            thresholds[name] = binding
            results.append({"name": name, "algorithm": result["algorithm"], "feature_set": result["feature_set"],
                            "input_columns": features, "model_sha256": binding["model_sha256"], "threshold": binding,
                            "development_oof": score_predictions(data.y, clean_oof, dev_frame),
                            "interval_audit": score_predictions(audit_y, audit_prediction, audit, threshold),
                            "noise": noise_reports, "oof_replay_max_absolute_difference": float(np.max(np.abs(replayed_oof - clean_oof))),
                            "replay_fit_count": len(data.cv), "predictions_artifact": artifact.name})
    write_json(run_dir / "intervals.json", {"status": "frozen", "models": thresholds,
               "test_evaluated": False, "nominal_coverage": protocol["nominal_coverage"], "method_reference": REFERENCE})
    write_plot(results, run_dir)
    for name in ("calibration_roles.csv", "analysis_manifest.json", "intervals.json", "reliability.png"):
        artifacts[name] = file_hash(run_dir / name)
    report = {"status": "passed", "schema_version": 1, "created_at_utc": datetime.now(timezone.utc).isoformat(),
              "scope": "Exploratory development OOF diagnostics and disjoint calibration interval audit; no final test evaluation",
              "protocol": protocol, "method_reference": REFERENCE, "development_rows": len(reference.ids),
              "calibration_role_counts": {"interval_fit": len(fit_ids), "interval_audit": len(audit_ids)},
              "calibration_roles_sha256": file_hash(run_dir / "calibration_roles.csv"),
              "source_sha256": manifest["sha256"], "modeling_table_sha256": split["modeling_table_sha256"],
              "assignments_sha256": split["assignments_sha256"], "split_manifest_sha256": file_hash(Path(split_dir) / "split_manifest.json"),
              "source_run_metrics_sha256": {"baseline": file_hash(baseline_dir / "metrics.json"), "comparison": file_hash(comparison_dir / "metrics.json")},
              "project_fingerprints": fingerprints(), "experiment_plan_sha256": file_hash(ROOT / "docs/EXPERIMENT_PLAN.md"),
              "environment": environment, "effective_threadpools_during_fit": effective_threads,
              "replay_cv_fits": sum(result["replay_fit_count"] for result in results), "new_search_fits": 0,
              "point_models_refit_on_calibration": False, "model_selection_using_calibration": False,
              "audit_labels_used_for_quantiles": False, "test_evaluated": False, "artifacts_sha256": artifacts, "results": results}
    write_json(run_dir / "metrics.json", report)
    return {"status": "passed", "run_dir": str(run_dir), "replay_cv_fits": report["replay_cv_fits"],
            "test_evaluated": False, "interval_audit": [{"name": r["name"], **r["interval_audit"]["overall"]} for r in results]}
