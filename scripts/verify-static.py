"""Verify browser exports on synthetic inputs, never on the reserved test set."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from calorie_estimation.demo_app import Demo


def verify(folder):
    meta = json.loads((folder / "metadata.json").read_bytes())
    original = Demo(ROOT / "runs/demo-space-v1/bundle", ROOT / "demo")
    rng = np.random.default_rng(20261011)
    payloads, expected, counts = [], [], {}
    for mode, system in meta["systems"].items():
        forest = json.loads((folder / system["browser_artifact"]).read_bytes())
        assert hashlib.sha256((folder / system["browser_artifact"]).read_bytes()).hexdigest() == system["browser_sha256"]
        source = ROOT / "runs/input-comparison-v1" / original.manifest["systems"][mode]["artifact"]
        assert hashlib.sha256(source.read_bytes()).hexdigest() == system["model_sha256"]
        model = joblib.load(source)
        rows = [{name: example["values"][name] for name in system["input_columns"]} for example in meta["examples"]]
        for _ in range(1000):
            row = {}
            for name in system["input_columns"]:
                field = meta["fields"][name]
                if "categories" in field:
                    row[name] = str(rng.choice(field["categories"]))
                elif field["integer"]:
                    row[name] = int(rng.integers(field["min"], field["max"] + 1))
                else:
                    row[name] = float(rng.uniform(field["min"], field["max"]))
            rows.append(row)
        # Exact split equality plus both neighbouring float32 values; numeric
        # whole-number fields instead use the nearest valid integers on each side.
        thresholds = set()
        for tree in forest["trees"]:
            for index, left in enumerate(tree["left"]):
                if left != -1:
                    thresholds.add((tree["feature"][index], tree["value"][index]))
        baseline = rows[0]
        for index, threshold in sorted(thresholds):
            feature = forest["features"][index]
            name, field = feature["name"], meta["fields"][feature["name"]]
            if "category" in feature:
                candidates = field["categories"]
            elif field["integer"]:
                candidates = [int(np.ceil(threshold)) - 1, int(np.ceil(threshold))]
            else:
                point = np.float32(threshold)
                candidates = [float(np.nextafter(point, np.float32(-np.inf))), float(point),
                              float(np.nextafter(point, np.float32(np.inf)))]
            for value in candidates:
                if "categories" not in field and not field["min"] <= value <= field["max"]:
                    continue
                rows.append({**baseline, name: value})
        for name in system["input_columns"]:
            field = meta["fields"][name]
            for value in field.get("categories", [field.get("min"), field.get("max")]):
                rows.append({**baseline, name: value})
        predictions = model.predict(pd.DataFrame(rows, columns=system["input_columns"]))
        q = system["threshold"]
        for row, prediction in zip(rows, predictions, strict=True):
            payloads.append({"mode": mode, "inputs": row})
            expected.append((float(prediction), float(prediction)-q, float(prediction)+q))
        counts[mode] = len(rows)
    harness = """
const fs=require('node:fs');
const engine=require(process.argv[1]+'/engine.js');
const meta=JSON.parse(fs.readFileSync(process.argv[1]+'/metadata.json','utf8'));
const forests=Object.fromEntries(Object.entries(meta.systems).map(([mode,s])=>[mode,JSON.parse(fs.readFileSync(process.argv[1]+'/'+s.browser_artifact,'utf8'))]));
const inputs=JSON.parse(fs.readFileSync(0,'utf8'));
process.stdout.write(JSON.stringify(inputs.map(x=>engine.predict(meta,forests,x))));
"""
    completed = subprocess.run(["node", "-e", harness, str(folder.resolve())], input=json.dumps(payloads),
                               capture_output=True, text=True, check=True)
    actual = json.loads(completed.stdout)
    for payload, result, reference in zip(payloads, actual, expected, strict=True):
        assert (result["prediction"], result["lower"], result["upper"]) == reference, (payload, result, reference)
        mode = payload["mode"]
        assert result["test_mae"] == original.manifest["systems"][mode]["test_mae"]
        assert result["test_coverage"] == original.manifest["systems"][mode]["test_coverage"]
        group = next(row for row in original.manifest["systems"][mode]["duration_groups"]
                     if int(row["group"].split("-")[0]) <= payload["inputs"]["Duration"] <= int(row["group"].split("-")[1]))
        assert result["duration_group"] == group
    for mode, system in meta["systems"].items():
        for example in meta["examples"]:
            payload = {"mode":mode, "inputs":{key:example["values"][key] for key in system["input_columns"]}}
            index = payloads.index(payload)
            assert actual[index] == original.predict(payload)
    package = json.loads((folder / "PACKAGE_MANIFEST.json").read_bytes())
    assert package["hosting_sdk"] == "static"
    allowed = set(package["files_sha256"]) | {"PACKAGE_MANIFEST.json"}
    assert allowed == {path.relative_to(folder).as_posix() for path in folder.rglob("*") if path.is_file()}
    for name, digest in package["files_sha256"].items():
        assert hashlib.sha256((folder / name).read_bytes()).hexdigest() == digest
    report = {"status":"passed", "node_version":subprocess.check_output(["node", "--version"], text=True).strip(),
              "synthetic_sessions_verified":len(payloads), "sessions_by_mode":counts,
              "random_seed":20261011, "random_sessions_per_mode":1000,
              "cases":"fictional examples, uniform synthetic sessions, valid range endpoints, category levels and valid neighbours of every unique split",
              "exact_float32_prediction_and_unclipped_interval_parity":True,
              "all_duration_groups_and_benchmark_metadata_match":True,
              "package_sha256":hashlib.sha256((folder / "PACKAGE_MANIFEST.json").read_bytes()).hexdigest(),
              "files_verified":len(allowed), "training_fits":0, "new_test_scoring_runs":0,
              "browser_visual_check":"pending", "hosted_deployment":"pending"}
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--folder", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    report = verify(args.folder)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
