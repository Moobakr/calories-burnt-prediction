"""Reproducible preparation, frozen evaluation and development baseline commands."""

import argparse
import csv
from importlib import import_module, metadata
import json
from pathlib import Path
import platform
import site
import sys

from .config import ROOT, fingerprints, load_project
from .data import atomic_write, prepare, validate_bytes, validate_file, write_json


def doctor(require_ml=False):
    expected = {}
    for line in (ROOT / "requirements.lock.txt").read_text().splitlines():
        if line.strip() and not line.startswith("#"):
            name, version = line.strip().split("==")
            expected[name] = version
    actual, problems = {}, []
    for name, version in expected.items():
        try:
            actual[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            actual[name] = None
        if actual[name] != version:
            problems.append(f"{name}: expected {version}, found {actual[name]}")
    import_errors = []
    if require_ml:
        for name in ("numpy", "pandas", "scipy", "sklearn", "xgboost", "matplotlib", "joblib", "threadpoolctl"):
            try:
                import_module(name)
            except Exception as error:
                import_errors.append(f"{name}: {type(error).__name__}: {error}")
    python_ok = sys.version_info[:2] == (3, 12)
    passed = python_ok and (not require_ml or (not problems and not import_errors))
    venv_config = Path(sys.prefix) / "pyvenv.cfg"
    isolated = (sys.prefix != sys.base_prefix and not site.ENABLE_USER_SITE
                and venv_config.exists()
                and "include-system-site-packages = false" in venv_config.read_text().lower())
    return {
        "status": "passed" if passed else "failed", "python": platform.python_version(),
        "platform": platform.platform(), "architecture": platform.machine(),
        "executable": sys.executable, "virtual_environment": sys.prefix != sys.base_prefix,
        "isolated_from_system_site_packages": isolated,
        "python_version_matches": python_ok,
        "dependency_versions": actual, "dependency_mismatches": problems,
        "ml_imports_checked": require_ml, "import_errors": import_errors,
        "project_fingerprints": fingerprints(),
    }


def stage(source, notebook, config, manifest):
    source = Path(source).resolve()
    content = source.read_bytes()
    validate_bytes(content, manifest)
    destination = ROOT / config["raw_csv"]
    copies = [(destination, content)]
    registration = {"csv": {"source": str(source), "sha256": manifest["sha256"]}}
    if notebook is not None:
        notebook = Path(notebook).resolve()
        notebook_content = notebook.read_bytes()
        parsed = json.loads(notebook_content)
        if parsed.get("nbformat") != 4 or not isinstance(parsed.get("cells"), list):
            raise ValueError("Legacy reference must be a version 4 notebook")
        import hashlib
        registration["notebook"] = {"source": str(notebook),
                                    "sha256": hashlib.sha256(notebook_content).hexdigest()}
        copies.append((ROOT / "notebooks/legacy/Calories_burnt_prediction_project.ipynb", notebook_content))
    for target, payload in copies:
        if target.exists() and target.read_bytes() != payload:
            raise ValueError(f"Refusing to overwrite a different staged file: {target}")
    for target, payload in copies:
        atomic_write(target, payload)
    write_json(ROOT / "data/local_sources.json", registration)
    return {"status": "passed", "staged_csv": config["raw_csv"],
            "notebook_staged": notebook is not None, "source_sha256": manifest["sha256"]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    env = commands.add_parser("doctor", help="Record Python, pinned versions and source fingerprints")
    env.add_argument("--require-ml", action="store_true", help="Fail on missing/mismatched packages or failed imports")
    env.add_argument("--output", type=Path)
    staging = commands.add_parser("stage", help="Validate and copy local files without executing notebook cells")
    staging.add_argument("--source", required=True, type=Path)
    staging.add_argument("--notebook", type=Path)
    validation = commands.add_parser("validate", help="Verify raw CSV integrity and schema")
    validation.add_argument("--data", type=Path)
    validation.add_argument("--output", type=Path)
    preparation = commands.add_parser("prepare", help="Derive a table with duplicate observations removed")
    preparation.add_argument("--data", type=Path)
    preparation.add_argument("--output-dir", type=Path)
    for name, help_text in (("split", "Create frozen partitions and development CV folds"),
                            ("verify-splits", "Verify frozen partitions against inputs and configuration")):
        splitting = commands.add_parser(name, help=help_text)
        splitting.add_argument("--prepared-dir", type=Path)
        splitting.add_argument("--split-dir", type=Path)
    training = commands.add_parser("baselines", help="Fit mean and Ridge using development folds only")
    training.add_argument("--run-dir", type=Path, default=ROOT / "runs/baselines-v1")
    comparison = commands.add_parser("compare-inputs", help="Run matched development-only XGBoost search and comparisons")
    comparison.add_argument("--baseline-run-dir", type=Path, default=ROOT / "runs/baselines-v1")
    comparison.add_argument("--run-dir", type=Path, default=ROOT / "runs/input-comparison-v1")
    reliability = commands.add_parser("reliability", help="Audit frozen models and calibrate/audit 90% intervals without using test data")
    reliability.add_argument("--baseline-run-dir", type=Path, default=ROOT / "runs/baselines-v1")
    reliability.add_argument("--comparison-run-dir", type=Path, default=ROOT / "runs/input-comparison-v1")
    reliability.add_argument("--run-dir", type=Path, default=ROOT / "runs/reliability-v1")
    final = commands.add_parser("final-evaluate", help="Release reserved test once for the frozen systems; no fitting")
    final.add_argument("--baseline-run-dir", type=Path, default=ROOT / "runs/baselines-v1")
    final.add_argument("--comparison-run-dir", type=Path, default=ROOT / "runs/input-comparison-v1")
    final.add_argument("--reliability-run-dir", type=Path, default=ROOT / "runs/reliability-v1")
    final.add_argument("--run-dir", type=Path, default=ROOT / "runs/final-evaluation-v1")
    args = parser.parse_args(argv)
    try:
        config, manifest = load_project()
        if args.command == "doctor":
            result = doctor(args.require_ml)
        elif args.command == "stage":
            result = stage(args.source, args.notebook, config, manifest)
        elif args.command == "validate":
            source = args.data or ROOT / config["raw_csv"]
            if args.output and args.output.resolve() == source.resolve():
                raise ValueError("Validation report would overwrite the raw input")
            _, _, result = validate_file(source, manifest)
            result["project_fingerprints"] = fingerprints()
        elif args.command == "prepare":
            result = prepare(args.data or ROOT / config["raw_csv"],
                             args.output_dir or ROOT / config["processed_dir"], manifest, fingerprints())
        elif args.command == "baselines":
            from .baselines import run_baselines
            result = run_baselines(ROOT / config["processed_dir"], ROOT / config["split_dir"],
                                   args.run_dir, config, manifest, doctor(require_ml=True))
        elif args.command == "compare-inputs":
            from .comparison import run_comparison
            result = run_comparison(ROOT / config["processed_dir"], ROOT / config["split_dir"],
                                    args.baseline_run_dir, args.run_dir, config, manifest, doctor(require_ml=True),
                                    progress=lambda message: print(message, file=sys.stderr, flush=True))
        elif args.command == "reliability":
            from .reliability import run_reliability
            result = run_reliability(ROOT / config["processed_dir"], ROOT / config["split_dir"],
                                     args.baseline_run_dir, args.comparison_run_dir, args.run_dir,
                                     config, manifest, doctor(require_ml=True),
                                     progress=lambda message: print(message, file=sys.stderr, flush=True))
        elif args.command == "final-evaluate":
            from .final_evaluation import run_final_evaluation
            result = run_final_evaluation(ROOT / config["processed_dir"], ROOT / config["split_dir"],
                args.baseline_run_dir, args.comparison_run_dir, args.reliability_run_dir, args.run_dir,
                config, manifest, doctor(require_ml=True))
        else:
            from .evaluation import create_splits, verify_splits
            prepared_dir = args.prepared_dir or ROOT / config["processed_dir"]
            split_dir = args.split_dir or ROOT / config["split_dir"]
            if args.command == "split":
                result = create_splits(prepared_dir, split_dir, config, manifest, fingerprints())
            else:
                _, _, result = verify_splits(prepared_dir, split_dir, config, manifest)
        if getattr(args, "output", None):
            write_json(args.output, result)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result.get("status", "passed") == "passed" else 1
    except (OSError, ValueError, KeyError, csv.Error) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
