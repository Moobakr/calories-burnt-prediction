"""Small synthetic fixtures exercise integrity and deduplication failure modes."""

import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from calorie_estimation.config import ROOT, load_project
from calorie_estimation.data import csv_bytes, prepare, validate_bytes


class DataIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.config, original = load_project()
        self.manifest = copy.deepcopy(original)
        self.header = [column["name"] for column in self.manifest["columns"]]
        self.rows = [
            ["1", "female", "28", "164", "59", "9", "90", "39.5", "40"],
            ["2", "male", "30", "175", "75", "15", "100", "40.0", "100"],
            ["3", "female", "28", "164", "59", "9", "90", "39.50", "40"],
        ]

    def fixture(self, rows=None, header=None):
        rows = self.rows if rows is None else rows
        payload = csv_bytes(self.header if header is None else header, rows)
        self.manifest["sha256"] = hashlib.sha256(payload).hexdigest()
        self.manifest["expected_rows"] = len(rows)
        self.manifest["duplicate_policy"]["expected_output_rows"] = len(rows) - 1
        return payload

    def test_changed_bytes_rejected_before_processing(self):
        payload = self.fixture()
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            validate_bytes(payload + b"\n", self.manifest)

    def test_invalid_category_not_silently_mapped(self):
        self.rows[0][1] = "unknown"
        with self.assertRaisesRegex(ValueError, "unrecognized Gender"):
            validate_bytes(self.fixture(), self.manifest)

    def test_numeric_failures(self):
        for value, expected in [("NaN", "nonfinite"), ("Infinity", "nonfinite"),
                                ("bad", "invalid numeric"), ("0", "positive"), ("28.5", "integer")]:
            with self.subTest(value=value):
                self.rows[0][2] = value
                with self.assertRaisesRegex(ValueError, expected):
                    validate_bytes(self.fixture(), self.manifest)

    def test_header_and_ragged_rows_rejected(self):
        with self.assertRaisesRegex(ValueError, "header"):
            validate_bytes(self.fixture(header=list(reversed(self.header))), self.manifest)
        self.rows[0].pop()
        with self.assertRaisesRegex(ValueError, "cells"):
            validate_bytes(self.fixture(), self.manifest)

    def test_duplicate_identifiers_rejected(self):
        self.rows[1][0] = "1"
        with self.assertRaisesRegex(ValueError, "duplicate User_ID"):
            validate_bytes(self.fixture(), self.manifest)

    def test_same_features_with_different_target_are_retained(self):
        self.rows[2][-1] = "41"
        payload = self.fixture()
        self.manifest["duplicate_policy"]["expected_removed_rows"] = 0
        self.manifest["duplicate_policy"]["expected_output_rows"] = 3
        _, rows, report = validate_bytes(payload, self.manifest)
        self.assertEqual(len(rows), 3)
        self.assertEqual(report["duplicate_observations"], [])

    def test_wrong_row_count_rejected(self):
        payload = self.fixture()
        self.manifest["expected_rows"] = 4
        with self.assertRaisesRegex(ValueError, "observations"):
            validate_bytes(payload, self.manifest)

    def test_repeatable_preparation_keeps_first_and_preserves_source(self):
        payload = self.fixture()
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "raw.csv"
            source.write_bytes(payload)
            destination = Path(directory) / "processed"
            first = prepare(source, destination, self.manifest, {"fixture": "test"})
            output = (destination / "modeling_table.csv").read_bytes()
            second = prepare(source, destination, self.manifest, {"fixture": "test"})
            self.assertEqual(first, second)
            self.assertEqual(output, csv_bytes(self.header, self.rows[:2]))
            self.assertEqual(source.read_bytes(), payload)
            self.assertEqual(first["removed_rows"][0]["removed_id"], "3")
            self.assertEqual(first["removed_rows"][0]["kept_id"], "1")
            self.assertEqual(first["removed_rows"][0]["removed_csv_row"], 4)
            saved = json.loads((destination / "preparation_manifest.json").read_text())
            self.assertEqual(saved["modeling_table_sha256"], hashlib.sha256(output).hexdigest())
            self.assertFalse(saved["partitions_created"])

    def test_preparation_cannot_overwrite_source(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "modeling_table.csv"
            source.write_bytes(self.fixture())
            with self.assertRaisesRegex(ValueError, "overwrite"):
                prepare(source, directory, self.manifest, {})

    def test_feature_sets_exclude_identifier_and_target(self):
        for name in ("User_ID", "Calories"):
            altered = copy.deepcopy(self.config)
            altered["feature_sets"]["basic"].append(name)
            with patch("calorie_estimation.config.tomllib.load", return_value=altered):
                with self.assertRaisesRegex(ValueError, "Invalid predictor"):
                    load_project()

    def test_installed_cli_finds_project_from_another_directory(self):
        # Run after editable install so execution does not rely on a particular cwd.
        with tempfile.TemporaryDirectory() as directory:
            completed = subprocess.run([sys.executable, "-m", "calorie_estimation", "doctor"],
                                       cwd=directory, text=True, capture_output=True)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            report = json.loads(completed.stdout)
            self.assertIn("configs/project.toml", report["project_fingerprints"])


if __name__ == "__main__":
    unittest.main()
