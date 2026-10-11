"""Frozen ID-based partitions and development-only cross-validation inputs."""

import copy
from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING
import hashlib
import json
from pathlib import Path

from .data import atomic_write, csv_bytes, validate_bytes, write_json

METHOD = "sha256-id-ranking-v1"
PARTITIONS = ("development", "calibration", "test")


def sha256(content):
    return hashlib.sha256(content).hexdigest()


def protocol(evaluation):
    fractions = [Decimal(str(evaluation[f"{name}_fraction"])) for name in PARTITIONS]
    if any(not f.is_finite() or not 0 < f < 1 for f in fractions) or sum(fractions) != 1:
        raise ValueError("Partition fractions must be positive, finite, and sum to one")
    for name in ("split_seed", "cv_seed", "cv_folds"):
        value = evaluation[name]
        if type(value) is not int or value < (2 if name == "cv_folds" else 0):
            raise ValueError(f"Invalid {name}")
    return {"method": METHOD, "split_seed": evaluation["split_seed"],
            "cv_seed": evaluation["cv_seed"], "cv_folds": evaluation["cv_folds"],
            "fractions": dict(zip(PARTITIONS, map(float, fractions))),
            "rounding": "ceil calibration and test; development receives the remainder"}


def partition_counts(n, settings):
    fractions = settings["fractions"]
    calibration = int((n * Decimal(str(fractions["calibration"]))).to_integral_value(rounding=ROUND_CEILING))
    test = int((n * Decimal(str(fractions["test"]))).to_integral_value(rounding=ROUND_CEILING))
    counts = {"development": n - calibration - test, "calibration": calibration, "test": test}
    if min(counts.values()) < 1 or counts["development"] < settings["cv_folds"]:
        raise ValueError("Too few records for the requested partitions and CV folds")
    return counts


def canonical_id(value):
    number = Decimal(str(value))
    if not number.is_finite() or number <= 0 or number != number.to_integral_value():
        raise ValueError("IDs must be positive integers")
    return str(int(number))


def allocate(ids, evaluation):
    """Hash only ID and seed: labels, features and source row order do not enter."""
    ids = [canonical_id(value) for value in ids]
    if len(set(ids)) != len(ids):
        raise ValueError("Repeated IDs require participant-aware evaluation; this protocol requires unique IDs")
    settings = protocol(evaluation)
    counts = partition_counts(len(ids), settings)

    def rank(identity, purpose, seed):
        return (sha256(f"calorie-estimation:v1:{purpose}:{seed}:{identity}".encode("utf-8")), int(identity))

    ranked = sorted(ids, key=lambda identity: rank(identity, "partition", settings["split_seed"]))
    membership, start = {}, 0
    for partition in PARTITIONS:
        stop = start + counts[partition]
        membership.update({identity: (partition, None) for identity in ranked[start:stop]})
        start = stop
    development = [identity for identity in ids if membership[identity][0] == "development"]
    development.sort(key=lambda identity: rank(identity, "cv", settings["cv_seed"]))
    for index, identity in enumerate(development):
        membership[identity] = ("development", index % settings["cv_folds"])
    return membership, settings, counts


def membership_bytes(membership, id_column):
    return csv_bytes([id_column, "partition", "cv_validation_fold"],
                     ((identity, membership[identity][0],
                       "" if membership[identity][1] is None else membership[identity][1])
                      for identity in sorted(membership, key=int)))


def load_prepared(prepared_dir, manifest):
    """Bind the derived file to a tracked digest, not just its editable local manifest."""
    prepared_dir = Path(prepared_dir)
    preparation_bytes = (prepared_dir / "preparation_manifest.json").read_bytes()
    preparation = json.loads(preparation_bytes)
    table = (prepared_dir / "modeling_table.csv").read_bytes()
    expected_hash = manifest["expected_modeling_table_sha256"]
    if preparation["dataset_id"] != manifest["dataset_id"] or preparation["source_sha256"] != manifest["sha256"]:
        raise ValueError("Preparation manifest does not refer to the audited source")
    if sha256(table) != expected_hash or preparation["modeling_table_sha256"] != expected_hash:
        raise ValueError("Prepared table differs from the frozen derived-data fingerprint")
    if sha256((prepared_dir / "deduplication_log.csv").read_bytes()) != preparation["deduplication_log_sha256"]:
        raise ValueError("Deduplication log differs from its preparation manifest")
    expected_rows = manifest["duplicate_policy"]["expected_output_rows"]
    if preparation["output_rows"] != expected_rows:
        raise ValueError("Unexpected prepared row count")
    derived_manifest = copy.deepcopy(manifest)
    derived_manifest.update(sha256=expected_hash, expected_rows=expected_rows)
    derived_manifest["duplicate_policy"].update(expected_removed_rows=0, expected_output_rows=expected_rows)
    header, rows, _ = validate_bytes(table, derived_manifest)
    records = [dict(zip(header, row)) for row in rows]
    return records, {"modeling_table_sha256": expected_hash,
                     "preparation_manifest_sha256": sha256(preparation_bytes)}


def create_splits(prepared_dir, split_dir, config, manifest, provenance):
    records, input_hashes = load_prepared(prepared_dir, manifest)
    id_column = manifest["id_column"]
    membership, settings, counts = allocate([row[id_column] for row in records], config["evaluation"])
    payload = membership_bytes(membership, id_column)
    split_dir = Path(split_dir)
    assignment_path = split_dir / "assignments.csv"
    # Never silently reseed, repartition, or overwrite a corrupted frozen allocation.
    if assignment_path.exists() and assignment_path.read_bytes() != payload:
        raise ValueError("Existing frozen assignments differ; review a protocol change in a new output directory")
    manifest_path = split_dir / "split_manifest.json"
    if manifest_path.exists():
        previous = json.loads(manifest_path.read_bytes())
        if previous["protocol"] != settings:
            raise ValueError("Existing split protocol differs; use a new output directory for an explicit protocol revision")
        if (previous["dataset_id"] != manifest["dataset_id"]
                or previous["source_sha256"] != manifest["sha256"]
                or previous["modeling_table_sha256"] != input_hashes["modeling_table_sha256"]):
            raise ValueError("Existing frozen data identity differs; use a new output directory for revised data")
    fold_sizes = [sum(value == ("development", fold) for value in membership.values())
                  for fold in range(settings["cv_folds"])]
    report = {"schema_version": 1, "status": "passed", "dataset_id": manifest["dataset_id"],
              "source_sha256": manifest["sha256"], **input_hashes,
              "assignments_sha256": sha256(payload), "protocol": settings,
              "partition_counts": counts, "cv_validation_counts": fold_sizes,
              "cv_training_counts": [counts["development"] - size for size in fold_sizes],
              "checks": {"each_id_assigned_once": True, "partitions_disjoint": True,
                         "cv_development_only": True, "each_development_id_validated_once": True},
              "project_fingerprints": provenance, "models_fitted": False,
              "holdout_labels_used_for_selection": False, "test_evaluated": False}
    atomic_write(assignment_path, payload)
    write_json(manifest_path, report)
    return report


def verify_splits(prepared_dir, split_dir, config, manifest):
    records, input_hashes = load_prepared(prepared_dir, manifest)
    split_dir = Path(split_dir)
    report = json.loads((split_dir / "split_manifest.json").read_bytes())
    membership, settings, counts = allocate([row[manifest["id_column"]] for row in records], config["evaluation"])
    payload = (split_dir / "assignments.csv").read_bytes()
    if report["protocol"] != settings or report["partition_counts"] != counts:
        raise ValueError("Split manifest differs from the configured evaluation protocol")
    if report["dataset_id"] != manifest["dataset_id"] or report["source_sha256"] != manifest["sha256"]:
        raise ValueError("Split manifest refers to another dataset")
    if any(report[key] != value for key, value in input_hashes.items()):
        raise ValueError("Prepared inputs changed after splitting; verify and regenerate the split bundle")
    if sha256(payload) != report["assignments_sha256"]:
        raise ValueError("Frozen assignments have changed")
    if payload != membership_bytes(membership, manifest["id_column"]):
        raise ValueError("Assignments do not match the deterministic protocol")
    fold_sizes = [sum(value == ("development", fold) for value in membership.values())
                  for fold in range(settings["cv_folds"])]
    if (report["cv_validation_counts"] != fold_sizes
            or report["cv_training_counts"] != [counts["development"] - size for size in fold_sizes]):
        raise ValueError("Reported CV sizes do not match frozen assignments")
    return records, membership, report


@dataclass(frozen=True)
class DevelopmentData:
    X: object
    y: object
    ids: tuple
    cv: tuple


def load_development(prepared_dir, split_dir, config, manifest, feature_set):
    """Return only development X/y and matched fold indices for later search APIs."""
    import numpy as np
    import pandas as pd

    features = config["feature_sets"][feature_set]
    allowed = {column["name"] for column in manifest["columns"] if column["role"] == "input"}
    if not features or len(features) != len(set(features)) or not set(features) <= allowed:
        raise ValueError("Feature set contains a target, identifier, or unknown input")
    records, membership, report = verify_splits(prepared_dir, split_dir, config, manifest)
    by_id = {canonical_id(row[manifest["id_column"]]): row for row in records}
    ids = tuple(sorted((identity for identity in membership if membership[identity][0] == "development"), key=int))
    X = pd.DataFrame([{name: by_id[identity][name] for name in features} for identity in ids], columns=features)
    for column in manifest["columns"]:
        if column["name"] in features and column["type"] != "category":
            X[column["name"]] = pd.to_numeric(X[column["name"]], errors="raise")
    y = np.asarray([float(by_id[identity][manifest["target_column"]]) for identity in ids])
    fold_ids = np.asarray([membership[identity][1] for identity in ids])
    cv = tuple((np.flatnonzero(fold_ids != fold), np.flatnonzero(fold_ids == fold))
               for fold in range(report["protocol"]["cv_folds"]))
    return DevelopmentData(X, y, ids, cv)
