"""Validate a frozen input and prepare an auditable derived table, without fitting."""

import csv
from decimal import Decimal, InvalidOperation
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile


def atomic_write(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(dir=path.parent, prefix=".writing-")
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(content)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def write_json(path, value):
    atomic_write(path, (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8"))


def csv_bytes(header, rows):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def validate_bytes(content, manifest):
    """Read a single byte snapshot so the validated hash and rows match."""
    digest = hashlib.sha256(content).hexdigest()
    if digest != manifest["sha256"]:
        raise ValueError("CSV SHA-256 differs from the audited manifest. Review the new input before use.")
    columns = manifest["columns"]
    header = [column["name"] for column in columns]
    reader = csv.reader(io.StringIO(content.decode("utf-8-sig"), newline=""), strict=True)
    if next(reader, None) != header:
        raise ValueError(f"CSV header must be exactly {header}")
    id_index = header.index(manifest["id_column"])
    seen_ids = set()
    seen_observations = {}
    rows, duplicate_log = [], []
    counts = {c["name"]: {} for c in columns if c["type"] == "category"}
    ranges = {c["name"]: [None, None] for c in columns if c["type"] != "category"}
    for source_row, row in enumerate(reader, start=2):
        if len(row) != len(header):
            raise ValueError(f"CSV row {source_row}: expected {len(header)} cells, got {len(row)}")
        typed = []
        for column, value in zip(columns, row):
            name = column["name"]
            if column["type"] == "category":
                if value not in column["categories"]:
                    raise ValueError(f"CSV row {source_row}: unrecognized {name} {value!r}")
                counts[name][value] = counts[name].get(value, 0) + 1
                typed.append(value)
            else:
                try:
                    number = Decimal(value)
                except InvalidOperation as error:
                    raise ValueError(f"CSV row {source_row}: invalid numeric {name}") from error
                if not number.is_finite():
                    raise ValueError(f"CSV row {source_row}: nonfinite {name}")
                if column.get("positive") and number <= 0:
                    raise ValueError(f"CSV row {source_row}: {name} must be positive")
                if column["type"] == "integer" and number != number.to_integral_value():
                    raise ValueError(f"CSV row {source_row}: {name} must be an integer")
                typed.append(number)
                lower, upper = ranges[name]
                ranges[name] = [number if lower is None else min(lower, number),
                                number if upper is None else max(upper, number)]
        identity = typed[id_index]
        if identity in seen_ids:
            raise ValueError(f"CSV row {source_row}: duplicate {manifest['id_column']} {row[id_index]}")
        seen_ids.add(identity)
        key = tuple(v for i, v in enumerate(typed) if i != id_index)
        if key in seen_observations:
            kept_row, kept_id = seen_observations[key]
            duplicate_log.append({
                "removed_csv_row": source_row, "removed_id": row[id_index],
                "kept_csv_row": kept_row, "kept_id": kept_id,
                "reason": "identical observation excluding identifier, including target",
            })
        else:
            seen_observations[key] = (source_row, row[id_index])
        rows.append(row)
    if len(rows) != manifest["expected_rows"]:
        raise ValueError(f"Expected {manifest['expected_rows']} observations; found {len(rows)}")
    policy = manifest["duplicate_policy"]
    if len(duplicate_log) != policy["expected_removed_rows"]:
        raise ValueError("Duplicate count differs from the audited manifest")
    if len(rows) - len(duplicate_log) != policy["expected_output_rows"]:
        raise ValueError("Prepared row count differs from the audited manifest")
    report = {
        "status": "passed", "sha256": digest, "rows": len(rows), "columns": header,
        "unique_ids": len(seen_ids), "duplicate_observations": duplicate_log,
        "category_counts": counts,
        "numeric_ranges": {k: [float(v) for v in pair] for k, pair in ranges.items()},
    }
    return header, rows, report


def validate_file(path, manifest):
    return validate_bytes(Path(path).read_bytes(), manifest)


def prepare(source, output_dir, manifest, provenance):
    source, output_dir = Path(source), Path(output_dir)
    outputs = [output_dir / filename for filename in (
        "modeling_table.csv", "deduplication_log.csv", "preparation_manifest.json")]
    if source.resolve() in [path.resolve() for path in outputs]:
        raise ValueError("Output would overwrite the raw input")
    header, rows, validation = validate_file(source, manifest)
    removed = {item["removed_csv_row"] for item in validation["duplicate_observations"]}
    kept = [row for position, row in enumerate(rows, start=2) if position not in removed]
    table = csv_bytes(header, kept)
    log_header = ["removed_csv_row", "removed_id", "kept_csv_row", "kept_id", "reason"]
    log = csv_bytes(log_header, ([item[k] for k in log_header]
                               for item in validation["duplicate_observations"]))
    report = {
        "schema_version": 1, "dataset_id": manifest["dataset_id"],
        "source_sha256": validation["sha256"], "source_rows": len(rows),
        "output_rows": len(kept), "removed_rows": validation["duplicate_observations"],
        "modeling_table_sha256": hashlib.sha256(table).hexdigest(),
        "deduplication_log_sha256": hashlib.sha256(log).hexdigest(),
        "policy": manifest["duplicate_policy"], "project_fingerprints": provenance,
        "transformations": "Only deterministic duplicate removal; raw cell text and column order preserved",
        "partitions_created": False, "models_fitted": False,
    }
    # Commit marker is the manifest, written last; consumers must check its hashes.
    atomic_write(outputs[0], table)
    atomic_write(outputs[1], log)
    write_json(outputs[2], report)
    return report
