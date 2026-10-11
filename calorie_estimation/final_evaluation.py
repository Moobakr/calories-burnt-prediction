"""One release of the reserved test for previously fitted, frozen systems."""

from datetime import datetime, timezone
import io
import json
from pathlib import Path

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_info, threadpool_limits

from .config import ROOT, file_hash, fingerprints
from .data import atomic_write, csv_bytes, write_json
from .evaluation import canonical_id, load_development, verify_splits
from .reliability import load_comparison_run, score_predictions


def settings(config):
    value = config["evaluation"]
    if (type(value["bootstrap_seed"]) is not int or value["bootstrap_seed"] != 2026
            or type(value["bootstrap_resamples"]) is not int or value["bootstrap_resamples"] != 2000
            or isinstance(value["competitive_relative_mae_margin"], bool)
            or value["competitive_relative_mae_margin"] != .10):
        raise ValueError("Final evaluation requires the planned 2,000 draws, seed 2026 and 10% margin")
    return {"bootstrap_seed": 2026, "bootstrap_resamples": 2000, "relative_mae_margin": .10,
            "bootstrap_method": "paired-row-percentile", "quantile_method": "linear",
            "confidence_level": .95, "threads": 1,
            "primary_rule": "lowest development mean-fold MAE, then fewer input fields, then model name",
            "planned_pairs": [[f"{family}_{reduced}", f"{family}_full"]
                              for family in ("ridge", "xgboost") for reduced in ("basic", "heart_rate")]}


def select_primary(results):
    candidates = [row for row in results if row["algorithm"] in ("ridge", "xgboost")]
    if not candidates or any(not np.isfinite(row["mean_fold_mae"]) or row["mean_fold_mae"] < 0 for row in candidates):
        raise ValueError("Primary selection requires finite development MAEs")
    return min(candidates, key=lambda row: (row["mean_fold_mae"], len(row["input_columns"]), row["name"]))["name"]


def competitiveness(interval, margin=.10):
    if interval is None:
        return "undefined"
    low, high = interval
    if not np.isfinite(interval).all() or low > high:
        raise ValueError("Invalid relative-change interval")
    return "competitive" if high <= margin else "fails_margin" if low > margin else "inconclusive"


def paired_bootstrap(y, predictions, pairs, seed=2026, draws=2000):
    """Use identical row resamples for both members of every planned pair."""
    y = np.asarray(y, dtype=float)
    if (y.ndim != 1 or not len(y) or not np.isfinite(y).all()
            or type(draws) is not int or draws < 2 or type(seed) is not int or seed < 0):
        raise ValueError("Invalid bootstrap observations or settings")
    errors = {}
    for name, prediction in predictions.items():
        prediction = np.asarray(prediction, dtype=float)
        if prediction.shape != y.shape or not np.isfinite(prediction).all():
            raise ValueError("Bootstrap predictions must be finite and row matched")
        errors[name] = np.abs(y - prediction)
    indices = np.random.default_rng(seed).integers(0, len(y), size=(draws, len(y)), dtype=np.int64)
    output, distributions = [], {}
    for reduced, full in pairs:
        if reduced not in errors or full not in errors or reduced == full:
            raise ValueError("Invalid planned comparison")
        a, b = errors[reduced], errors[full]
        reduced_draws, full_draws = a[indices].mean(axis=1), b[indices].mean(axis=1)
        absolute = reduced_draws - full_draws
        valid = full_draws > 0
        relative = np.full(draws, np.nan)
        relative[valid] = absolute[valid] / full_draws[valid]
        interval = np.quantile(relative, [.025, .975], method="linear").tolist() if valid.all() else None
        point = None if b.mean() == 0 else float((a.mean() - b.mean()) / b.mean())
        name = f"{reduced}_vs_{full}"
        output.append({"name": name, "reduced": reduced, "full": full, "test_rows": len(y),
                       "reduced_mae": float(a.mean()), "full_mae": float(b.mean()),
                       "absolute_mae_change": float(a.mean() - b.mean()), "relative_mae_change": point,
                       "absolute_change_interval_95": np.quantile(absolute, [.025, .975], method="linear").tolist(),
                       "relative_change_interval_95": interval,
                       "undefined_relative_resamples": int((~valid).sum()),
                       "competitiveness_decision": competitiveness(interval), "relative_mae_margin": .10})
        distributions[name + "_absolute"] = absolute
        distributions[name + "_relative"] = relative
    return output, distributions, indices


def test_frame(records, membership):
    """An explicit final-test path, separate from development-only loaders."""
    by_id = {canonical_id(row["User_ID"]): row for row in records}
    ids = tuple(sorted((identity for identity, value in membership.items() if value[0] == "test"), key=int))
    if not ids or any(membership[identity][1] is not None for identity in ids):
        raise ValueError("Invalid frozen test allocation")
    frame = pd.DataFrame([by_id[identity] for identity in ids], index=ids)
    for name in frame.columns:
        if name not in ("Gender", "User_ID"):
            frame[name] = pd.to_numeric(frame[name], errors="raise")
    return ids, frame


def claim_release(path, release):
    """Exclusive creation prevents a second run, including concurrent calls."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as stream:
            stream.write((json.dumps(release, indent=2, sort_keys=True) + "\n").encode())
    except FileExistsError as error:
        raise ValueError("Reserved test already released: inspect its recorded run; do not delete the release record") from error


def validate_intervals(report, intervals, jobs):
    if (report["status"] != "passed" or report["test_evaluated"] or intervals["status"] != "frozen"
            or intervals["test_evaluated"] or intervals["nominal_coverage"] != .9
            or report["audit_labels_used_for_quantiles"] or report["model_selection_using_calibration"]):
        raise ValueError("Reliability source must contain frozen, test-independent intervals")
    expected = {row["name"] for row, _ in jobs if row["algorithm"] in ("ridge", "xgboost")}
    if set(intervals["models"]) != expected or {row["name"] for row in report["results"]} != expected:
        raise ValueError("Interval source must match all eight systems")
    diagnostics = {row["name"]: row for row in report["results"]}
    for row, directory in jobs:
        if row["name"] not in expected:
            continue
        binding = intervals["models"][row["name"]]
        if (binding != diagnostics[row["name"]]["threshold"]
                or binding["model_artifact"] != row["artifact"]
                or binding["model_sha256"] != file_hash(directory / row["artifact"])
                or binding["calibration_roles_sha256"] != report["calibration_roles_sha256"]
                or binding["nominal_coverage"] != .9 or binding["fit_rows"] != 1500
                or binding["rank_one_based"] != 1351 or binding["audit_labels_used_for_quantile"]
                or binding["refit_using_audit_allowed"] or not np.isfinite(binding["threshold"])
                or binding["threshold"] < 0):
            raise ValueError("Frozen interval/model binding differs from the verified reliability run")


def write_plot(results, frame, predictions, primary, directory):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.6), layout="constrained")
    x = np.arange(4)
    labels = ("duration", "basic", "heart_rate", "full")
    for offset, family, color in ((-.18, "ridge", "#6366f1"), (.18, "xgboost", "#059669")):
        rows = [next(row for row in results if row["name"] == f"{family}_{label}") for label in labels]
        axes[0].bar(x + offset, [row["test"]["overall"]["mae"] for row in rows], .36, color=color, label=family)
    mean = next(row["test"]["overall"]["mae"] for row in results if row["name"] == "mean")
    axes[0].axhline(mean, color="#444444", linestyle="--", label="Mean baseline")
    axes[0].set_xticks(x, ["Duration", "Basic", "Heart rate", "Full"])
    axes[0].set(title="Frozen-system test errors", ylabel="MAE (interpreted kcal/session)", yscale="log")
    axes[0].legend(fontsize=8)
    for name, color in ((primary, "#059669"), ("xgboost_full", "#6366f1"), ("xgboost_basic", "#ea580c")):
        error = np.sort(np.abs(predictions[name] - frame.Calories.to_numpy()))
        axes[1].plot(error, np.arange(1, len(error)+1)/len(error), color=color, label=name.replace("xgboost_", ""))
    axes[1].set(title="Test absolute-error distribution", xlabel="Absolute error (interpreted kcal/session)", ylabel="Fraction at or below error", xscale="symlog", ylim=(0, 1))
    axes[1].legend(fontsize=8)
    selected = next(row for row in results if row["name"] == primary)
    groups = [row for row in selected["test"]["groups"] if row["axis"] == "duration"]
    axes[2].bar([row["group"] for row in groups], [100*row["coverage"] for row in groups], color="#059669")
    axes[2].axhline(90, color="#444444", linestyle="--")
    axes[2].set(title="Primary model: frozen intervals", xlabel="Duration (minutes)", ylabel="Test coverage (%)", ylim=(0, 100))
    for axis in axes:
        axis.grid(axis="y", alpha=.2)
    fig.suptitle("Reserved test: 3,000 records, models selected on development only\nNo refitting, recalibration or test-driven selection", fontsize=12)
    fig.savefig(Path(directory) / "final_evaluation.png", dpi=180)
    plt.close(fig)


def run_final_evaluation(prepared_dir, split_dir, baseline_dir, comparison_dir, reliability_dir, run_dir, config, manifest, environment):
    import joblib
    protocol = settings(config)
    if environment.get("status") != "passed" or not environment.get("isolated_from_system_site_packages"):
        raise ValueError("Final evaluation requires the verified isolated environment")
    run_dir, baseline_dir, comparison_dir, reliability_dir = map(lambda path: Path(path).resolve(),
        (run_dir, baseline_dir, comparison_dir, reliability_dir))
    local = (ROOT / "runs").resolve()
    if any(not path.is_relative_to(local) or path == local for path in (run_dir, baseline_dir, comparison_dir, reliability_dir)):
        raise ValueError("Final evaluation and its source runs must remain inside ignored runs/")
    release_path = local / "final-test-access.json"
    if release_path.exists():
        raise ValueError("Reserved test already released: inspect runs/final-test-access.json and its recorded run")
    if run_dir.exists():
        raise ValueError("Preserve existing runs: final run directory must be new")
    records, membership, split = verify_splits(prepared_dir, split_dir, config, manifest)
    dev = load_development(prepared_dir, split_dir, config, manifest, "full")
    baseline, _, comparison, _ = load_comparison_run(comparison_dir, baseline_dir, dev, config, manifest, split)
    report = json.loads((reliability_dir / "metrics.json").read_bytes())
    public = json.loads((ROOT / "docs/RELIABILITY_METRICS.json").read_bytes())
    for key in ("results", "protocol", "project_fingerprints", "experiment_plan_sha256", "source_run_metrics_sha256",
                "source_sha256", "modeling_table_sha256", "assignments_sha256", "calibration_roles_sha256"):
        if report[key] != public[key]:
            raise ValueError("Reliability run differs from the published aggregate snapshot")
    if public["verification"]["status"] != "passed":
        raise ValueError("Reliability source has not been independently verified")
    for name, expected in report["artifacts_sha256"].items():
        if Path(name).name != name or file_hash(reliability_dir / name) != expected:
            raise ValueError("Reliability artifact hash mismatch")
    for key, path in (("baseline", baseline_dir), ("comparison", comparison_dir)):
        if file_hash(path / "metrics.json") != report["source_run_metrics_sha256"][key]:
            raise ValueError("Reliability source model run changed")
    for key in ("source_sha256", "modeling_table_sha256", "assignments_sha256"):
        if report[key] != baseline[key]:
            raise ValueError("Reliability data allocation differs from frozen model runs")
    jobs = [(row, baseline_dir) for row in baseline["results"]] + [(row, comparison_dir) for row in comparison["results"]]
    intervals = json.loads((reliability_dir / "intervals.json").read_bytes())
    validate_intervals(report, intervals, jobs)
    primary = select_primary([row for row, _ in jobs])
    models = {row["name"]: joblib.load(directory / row["artifact"]) for row, directory in jobs}
    frozen = {"status": "frozen_before_test_analysis", "created_at_utc": datetime.now(timezone.utc).isoformat(),
              "primary_model": primary, "selection_uses_test_or_calibration": False, "protocol": protocol,
              "project_fingerprints": fingerprints(), "experiment_plan_sha256": file_hash(ROOT / "docs/EXPERIMENT_PLAN.md"),
              "source_sha256": manifest["sha256"], "assignments_sha256": split["assignments_sha256"],
              "source_runs_sha256": {name: file_hash(path / "metrics.json") for name, path in
                  (("baseline", baseline_dir), ("comparison", comparison_dir), ("reliability", reliability_dir))},
              "intervals_sha256": file_hash(reliability_dir / "intervals.json"),
              "systems": [{"name": row["name"], "input_columns": row["input_columns"],
                  "development_mean_fold_mae": row["mean_fold_mae"], "model_sha256": file_hash(directory / row["artifact"]),
                  "threshold": intervals["models"].get(row["name"])} for row, directory in jobs]}
    run_dir.mkdir(parents=True, exist_ok=False)
    write_json(run_dir / "selection_manifest.json", frozen)
    claim_release(release_path, {"status": "released_for_frozen_evaluation", "run_directory": run_dir.relative_to(ROOT).as_posix(),
        "selection_manifest_sha256": file_hash(run_dir / "selection_manifest.json"), "released_at_utc": datetime.now(timezone.utc).isoformat()})
    ids, frame = test_frame(records, membership)
    if len(ids) != split["partition_counts"]["test"]:
        raise ValueError("Final test row count differs from frozen allocation")
    y = frame[manifest["target_column"]].to_numpy(dtype=float)
    results, predictions = [], {}
    with threadpool_limits(limits=1):
        pools = threadpool_info()
        for row, directory in jobs:
            name, features = row["name"], row["input_columns"]
            X = frame[features] if features else np.zeros((len(frame), 1))
            predicted = np.asarray(models[name].predict(X), dtype=float)
            predictions[name] = predicted
            threshold = intervals["models"].get(name)
            results.append({"name": name, "algorithm": row["algorithm"], "feature_set": row["feature_set"],
                "input_columns": features, "development_mean_fold_mae": row["mean_fold_mae"],
                "model_sha256": file_hash(directory / row["artifact"]),
                "interval_threshold": None if threshold is None else threshold["threshold"],
                "test": score_predictions(y, predicted, frame, None if threshold is None else threshold["threshold"])})
    comparisons, distributions, indices = paired_bootstrap(y, predictions, protocol["planned_pairs"],
        protocol["bootstrap_seed"], protocol["bootstrap_resamples"])
    for result in results:
        if result["algorithm"] == "mean":
            continue
        full = next(row for row in results if row["name"] == f"{result['algorithm']}_full")
        a, b = result["test"]["overall"]["mae"], full["test"]["overall"]["mae"]
        result["absolute_mae_change_vs_full"] = a-b
        result["relative_mae_change_vs_full"] = None if b == 0 else (a-b)/b
    atomic_write(run_dir / "test_predictions.csv", csv_bytes(["User_ID", "Calories", *predictions],
        zip(ids, y, *predictions.values())))
    buffer = io.BytesIO()
    np.savez_compressed(buffer, test_ids=np.asarray(ids), indices=indices, **distributions)
    atomic_write(run_dir / "paired_bootstrap.npz", buffer.getvalue())
    write_plot(results, frame, predictions, primary, run_dir)
    artifacts = {name: file_hash(run_dir / name) for name in
        ("selection_manifest.json", "test_predictions.csv", "paired_bootstrap.npz", "final_evaluation.png")}
    result = {"status": "passed", "schema_version": 1, "created_at_utc": datetime.now(timezone.utc).isoformat(),
              "scope": "Frozen-system reserved-test evaluation on a previously explored benchmark; not external validation",
              "test_evaluated": True, "test_rows": len(ids), "primary_model": primary,
              "selection_uses_test_or_calibration": False, "fit_count": 0, "quantile_refit_count": 0,
              "protocol": protocol, "source_sha256": manifest["sha256"],
              "modeling_table_sha256": split["modeling_table_sha256"], "assignments_sha256": split["assignments_sha256"],
              "selection_manifest_sha256": artifacts["selection_manifest.json"], "test_release_sha256": file_hash(release_path),
              "source_runs_sha256": frozen["source_runs_sha256"], "intervals_sha256": frozen["intervals_sha256"],
              "project_fingerprints": fingerprints(), "experiment_plan_sha256": frozen["experiment_plan_sha256"],
              "environment": environment, "effective_threadpools_during_predict": pools,
              "artifacts_sha256": artifacts, "results": results, "planned_comparisons": comparisons}
    write_json(run_dir / "metrics.json", result)
    return {"status": "passed", "primary_model": primary, "test_rows": len(ids), "fit_count": 0,
            "run_directory": run_dir.relative_to(ROOT).as_posix(), "planned_comparisons": comparisons,
            "primary_test": next(row["test"]["overall"] for row in results if row["name"] == primary)}
