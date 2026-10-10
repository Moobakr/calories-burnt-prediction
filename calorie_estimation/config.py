"""Portable project configuration and input-role checks."""

import hashlib
import json
from pathlib import Path
import tomllib

ROOT = Path(__file__).resolve().parent.parent


def load_project():
    with (ROOT / "configs/project.toml").open("rb") as stream:
        config = tomllib.load(stream)
    manifest = json.loads((ROOT / config["data_manifest"]).read_text(encoding="utf-8"))
    allowed = {c["name"] for c in manifest["columns"] if c["role"] == "input"}
    for name, features in config["feature_sets"].items():
        if not features or len(features) != len(set(features)) or not set(features) <= allowed:
            raise ValueError(f"Invalid predictor columns in feature set {name!r}")
    return config, manifest


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fingerprints():
    paths = [*sorted((ROOT / "calorie_estimation").glob("*.py")),
             *sorted((ROOT / "tests").glob("*.py")),
             *sorted((ROOT / "scripts").glob("*.ps1")),
             ROOT / "configs/project.toml", ROOT / "data/dataset_manifest.json",
             ROOT / "requirements.lock.txt", ROOT / "pyproject.toml"]
    return {p.relative_to(ROOT).as_posix(): file_hash(p) for p in paths}
