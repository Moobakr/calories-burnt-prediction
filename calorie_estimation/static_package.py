"""Export the verified frozen demo models for browser-only inference; never fit."""

import argparse
import json
from pathlib import Path
import shutil
import zipfile

import joblib
import numpy as np

from .config import ROOT, file_hash
from .data import write_json


def export_pipeline(pipeline):
    """Support only the exact numeric/one-hot, scalar gbtree regression format."""
    if list(pipeline.named_steps) != ["preprocess", "model"]:
        raise ValueError("Unsupported pipeline steps")
    prep = pipeline.named_steps["preprocess"]
    declared = {name: transform for name, transform, _ in prep.transformers}
    features = []
    for name, transform, columns in prep.transformers_:
        if name == "numeric" and declared[name] == "passthrough":
            features.extend({"name": column} for column in columns)
        elif name == "categorical":
            from sklearn.preprocessing import OneHotEncoder
            if not isinstance(transform, OneHotEncoder) or transform.handle_unknown != "error":
                raise ValueError("Unsupported category transformer")
            for index, (column, categories) in enumerate(zip(columns, transform.categories_, strict=True)):
                dropped = None if transform.drop_idx_ is None else transform.drop_idx_[index]
                features.extend({"name": column, "category": str(category)}
                                for level, category in enumerate(categories) if level != dropped)
        else:
            raise ValueError("Unsupported preprocessing; browser export must be reviewed")
    booster = pipeline.named_steps["model"].get_booster()
    raw = json.loads(booster.save_raw(raw_format="json"))
    learner = raw["learner"]
    params = learner["learner_model_param"]
    if (learner["objective"]["name"] != "reg:squarederror"
            or learner["gradient_booster"]["name"] != "gbtree"
            or int(params["num_target"]) != 1 or int(params["num_class"]) != 0
            or int(params["num_feature"]) != len(features)):
        raise ValueError("Unsupported booster/objective/shape")
    forest = learner["gradient_booster"]["model"]
    if any(forest["tree_info"]):
        raise ValueError("Only scalar regression trees are supported")
    trees = []
    for tree in forest["trees"]:
        if any(tree["split_type"]) or tree["categories"]:
            raise ValueError("Native categorical splits are unsupported")
        trees.append({"left": tree["left_children"], "right": tree["right_children"],
                      "feature": tree["split_indices"],
                      "value": np.asarray(tree["split_conditions"], dtype=np.float32).astype(float).tolist()})
    return {"format": "calorie-lab-scalar-gbtree-v1", "xgboost_version": raw["version"],
            "features": features, "base_score": float(np.float32(params["base_score"])), "trees": trees}


def package_static(source, destination):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if (not destination.is_relative_to((ROOT / "runs").resolve())
            or destination == (ROOT / "runs").resolve() or destination.exists()):
        raise ValueError("Choose a new package directory under ignored runs/")
    package = json.loads((source / "PACKAGE_MANIFEST.json").read_bytes())
    for name, digest in package["files_sha256"].items():
        path = (source / name).resolve()
        if not path.is_relative_to(source) or file_hash(path) != digest:
            raise ValueError("Source demo package changed")
    metadata = json.loads((source / "bundle/manifest.json").read_bytes())
    selected = json.loads((ROOT / "docs/FINAL_SELECTION.json").read_bytes())
    if (metadata["final_selection_sha256"] != file_hash(ROOT / "docs/FINAL_SELECTION.json")
            or metadata["final_evaluation_sha256"] != file_hash(ROOT / "docs/FINAL_EVALUATION_METRICS.json")):
        raise ValueError("Frozen evaluation binding changed")
    converted = {}
    for mode, system in metadata["systems"].items():
        frozen = next(row for row in selected["systems"] if row["name"] == system["name"])
        if (system["model_sha256"] != frozen["threshold"]["model_sha256"]
                or system["threshold"] != frozen["threshold"]["threshold"]
                or system["input_columns"] != frozen["input_columns"]):
            raise ValueError("Predictor does not match frozen selection")
        artifact = source / "bundle" / system["artifact"]
        if artifact.parent != source / "bundle" or file_hash(artifact) != system["model_sha256"]:
            raise ValueError("Frozen model changed")
        converted[mode] = export_pipeline(joblib.load(artifact))
    destination.mkdir(parents=True)
    (destination / "models").mkdir()
    for mode, forest in converted.items():
        name = f"models/{mode}.json"
        path = destination / name
        path.write_text(json.dumps(forest, separators=(",", ":"), allow_nan=False) + "\n", encoding="utf-8")
        system = metadata["systems"][mode]
        system.pop("artifact")
        system.update(browser_artifact=name, browser_sha256=file_hash(path))
    metadata["runtime"] = "browser-only; no prediction API or Python server"
    write_json(destination / "metadata.json", metadata)
    for name in ("engine.js", "app.js"):
        shutil.copyfile(ROOT / "demo/static" / name, destination / name)
    shutil.copyfile(ROOT / "demo/style.css", destination / "style.css")
    html = (ROOT / "demo/index.html").read_text(encoding="utf-8")
    html = html.replace('href="/style.css"', 'href="./style.css"').replace('src="/app.js"', 'src="./app.js"')
    html = html.replace('<script src="./app.js" defer></script>', '<script src="./engine.js" defer></script><script src="./app.js" defer></script>')
    html = html.replace("Processed in memory. This app does not save your inputs.",
                        "Predictions run in your browser. Inputs are not sent to a prediction server or saved by this app.")
    html = html.replace("no submission storage", "browser inference · no submission storage")
    (destination / "index.html").write_text(html, encoding="utf-8")
    shutil.copyfile(ROOT / "demo/static/SPACE_README.md", destination / "README.md")
    write_json(destination / "PACKAGE_MANIFEST.json", {
        "status": "prepared", "hosting_sdk": "static", "format_version": 1,
        "source_docker_package_sha256": file_hash(source / "PACKAGE_MANIFEST.json"),
        "training_fits": 0, "test_scoring_runs": 0,
        "files_sha256": {path.relative_to(destination).as_posix(): file_hash(path)
                         for path in sorted(destination.rglob("*")) if path.is_file()}})
    with zipfile.ZipFile(destination.with_suffix(".zip"), "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(destination.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(destination).as_posix())
    return {"directory": str(destination), "manifest_sha256": file_hash(destination / "PACKAGE_MANIFEST.json"),
            "training_fits": 0, "test_scoring_runs": 0}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "runs/demo-space-v1")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(package_static(args.source, args.output), indent=2))
