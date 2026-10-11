"""Protocol and leakage checks use synthetic data, never benchmark model fits."""

import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
import pandas as pd
from sklearn.exceptions import NotFittedError

from calorie_estimation.config import load_project
from calorie_estimation.data import csv_bytes, prepare, write_json
from calorie_estimation.evaluation import allocate, create_splits, load_development, verify_splits
from calorie_estimation.preprocessing import make_preprocessor


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        config, manifest = load_project()
        self.config, self.manifest = copy.deepcopy(config), copy.deepcopy(manifest)
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.prepared, self.splits = self.root / "prepared", self.root / "splits"
        self.header = [column["name"] for column in manifest["columns"]]
        self.rows = [[str(i + 1), "female" if i % 2 else "male", str(20 + i % 60),
                      "170", "65", str(1 + i % 30), str(70 + i % 50), "39.5", str(i + 2)]
                     for i in range(80)]
        duplicate = self.rows[0].copy()
        duplicate[0] = "999"
        payload = csv_bytes(self.header, self.rows + [duplicate])
        self.manifest.update(sha256=hashlib.sha256(payload).hexdigest(), expected_rows=81,
                             expected_modeling_table_sha256=hashlib.sha256(csv_bytes(self.header, self.rows)).hexdigest())
        self.manifest["duplicate_policy"].update(expected_removed_rows=1, expected_output_rows=80)
        source = self.root / "raw.csv"
        source.write_bytes(payload)
        prepare(source, self.prepared, self.manifest, {"fixture": "synthetic"})

    def create(self):
        return create_splits(self.prepared, self.splits, self.config, self.manifest, {"fixture": "synthetic"})

    def test_partition_coverage_and_cv_are_disjoint(self):
        self.create()
        _, membership, report = verify_splits(self.prepared, self.splits, self.config, self.manifest)
        sets = {name: {identity for identity, value in membership.items() if value[0] == name}
                for name in ("development", "calibration", "test")}
        self.assertEqual(set.union(*sets.values()), {str(i) for i in range(1, 81)})
        self.assertFalse(sets["development"] & sets["calibration"])
        self.assertFalse(sets["development"] & sets["test"])
        self.assertFalse(sets["calibration"] & sets["test"])
        self.assertNotIn("999", membership)
        data = load_development(self.prepared, self.splits, self.config, self.manifest, "full")
        seen = []
        for train, valid in data.cv:
            self.assertFalse(set(train) & set(valid))
            self.assertEqual(set(train) | set(valid), set(range(len(data.ids))))
            self.assertTrue({data.ids[i] for i in train} <= sets["development"])
            self.assertTrue({data.ids[i] for i in valid} <= sets["development"])
            seen.extend(valid.tolist())
        self.assertEqual(sorted(seen), list(range(len(data.ids))))
        self.assertLessEqual(max(report["cv_validation_counts"]) - min(report["cv_validation_counts"]), 1)

    def test_rounding_is_explicit_for_real_dataset_size(self):
        ids = [str(i) for i in range(1, 15000)]
        _, _, counts = allocate(ids, self.config["evaluation"])
        self.assertEqual(counts, {"development": 8999, "calibration": 3000, "test": 3000})

    def test_assignment_ignores_source_order(self):
        ids = [row[0] for row in self.rows]
        first, _, _ = allocate(ids, self.config["evaluation"])
        second, _, _ = allocate(list(reversed(ids)), self.config["evaluation"])
        self.assertEqual(first, second)

    def test_changed_seed_is_not_silently_overwritten(self):
        self.create()
        original = (self.splits / "assignments.csv").read_bytes()
        self.config["evaluation"]["split_seed"] += 1
        with self.assertRaisesRegex(ValueError, "Existing frozen"):
            self.create()
        self.assertEqual((self.splits / "assignments.csv").read_bytes(), original)
        with self.assertRaisesRegex(ValueError, "protocol"):
            verify_splits(self.prepared, self.splits, self.config, self.manifest)

    def test_invalid_protocols_and_repeated_ids_are_rejected(self):
        for changes in ({"test_fraction": 0.3}, {"cv_folds": 1}, {"cv_folds": 100},
                        {"split_seed": True}, {"calibration_fraction": float("nan")}):
            with self.subTest(changes=changes):
                settings = {**self.config["evaluation"], **changes}
                with self.assertRaises(ValueError):
                    allocate([row[0] for row in self.rows], settings)
        with self.assertRaisesRegex(ValueError, "Repeated IDs"):
            allocate(["1", "1.0"], self.config["evaluation"])

    def test_all_feature_sets_share_ids_and_folds_without_target_or_id(self):
        self.create()
        reference = None
        for name, columns in self.config["feature_sets"].items():
            data = load_development(self.prepared, self.splits, self.config, self.manifest, name)
            self.assertEqual(list(data.X.columns), columns)
            self.assertNotIn("Calories", data.X)
            self.assertNotIn("User_ID", data.X)
            if reference is not None:
                self.assertEqual(data.ids, reference.ids)
                np.testing.assert_array_equal(data.y, reference.y)
                for actual, expected in zip(data.cv, reference.cv):
                    np.testing.assert_array_equal(actual[0], expected[0])
                    np.testing.assert_array_equal(actual[1], expected[1])
            reference = data

    def test_development_loader_rejects_target_as_a_feature(self):
        self.create()
        self.config["feature_sets"]["basic"].append("Calories")
        with self.assertRaisesRegex(ValueError, "Feature set"):
            load_development(self.prepared, self.splits, self.config, self.manifest, "basic")

    def test_tampering_with_table_and_local_manifest_cannot_bypass_frozen_digest(self):
        path = self.prepared / "modeling_table.csv"
        path.write_bytes(path.read_bytes().replace(b",39.5,", b",39.6,", 1))
        report_path = self.prepared / "preparation_manifest.json"
        report = json.loads(report_path.read_bytes())
        report["modeling_table_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        write_json(report_path, report)
        with self.assertRaisesRegex(ValueError, "frozen derived-data fingerprint"):
            self.create()

    def test_changed_preparation_manifest_is_detected(self):
        self.create()
        path = self.prepared / "preparation_manifest.json"
        path.write_bytes(path.read_bytes() + b"\n")
        with self.assertRaisesRegex(ValueError, "Prepared inputs changed"):
            verify_splits(self.prepared, self.splits, self.config, self.manifest)

    def test_assignment_tampering_detected_even_if_local_hash_is_updated(self):
        self.create()
        path = self.splits / "assignments.csv"
        path.write_bytes(path.read_bytes().replace(b"development", b"calibration", 1))
        report_path = self.splits / "split_manifest.json"
        report = json.loads(report_path.read_bytes())
        report["assignments_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        write_json(report_path, report)
        with self.assertRaisesRegex(ValueError, "deterministic protocol"):
            verify_splits(self.prepared, self.splits, self.config, self.manifest)

    def test_repeated_split_creation_is_byte_identical(self):
        self.create()
        first = {p.name: p.read_bytes() for p in self.splits.iterdir()}
        self.create()
        self.assertEqual(first, {p.name: p.read_bytes() for p in self.splits.iterdir()})

    def test_existing_bundle_cannot_be_rebound_to_another_dataset(self):
        self.create()
        original = (self.splits / "split_manifest.json").read_bytes()
        self.manifest["dataset_id"] = "revised-dataset"
        path = self.prepared / "preparation_manifest.json"
        preparation = json.loads(path.read_bytes())
        preparation["dataset_id"] = "revised-dataset"
        write_json(path, preparation)
        with self.assertRaisesRegex(ValueError, "frozen data identity"):
            self.create()
        self.assertEqual((self.splits / "split_manifest.json").read_bytes(), original)

    def test_false_cv_sizes_in_manifest_are_detected(self):
        self.create()
        path = self.splits / "split_manifest.json"
        report = json.loads(path.read_bytes())
        report["cv_validation_counts"][0] += 1
        write_json(path, report)
        with self.assertRaisesRegex(ValueError, "CV sizes"):
            verify_splits(self.prepared, self.splits, self.config, self.manifest)


class PreprocessingTests(unittest.TestCase):
    def setUp(self):
        _, self.manifest = load_project()

    def test_scaling_learns_only_from_fit_rows(self):
        transformer = make_preprocessor(["Age"], self.manifest, scale_numeric=True)
        train = pd.DataFrame({"Age": [20.0, 40.0]})
        validation = pd.DataFrame({"Age": [1000.0]})
        transformer.fit(train)
        np.testing.assert_array_equal(transformer.named_transformers_["numeric"].mean_, [30.0])
        np.testing.assert_allclose(transformer.transform(validation), [[97.0]])
        np.testing.assert_array_equal(transformer.named_transformers_["numeric"].mean_, [30.0])

    def test_preprocessors_are_independent_and_start_unfitted(self):
        first = make_preprocessor(["Age"], self.manifest, scale_numeric=True)
        second = make_preprocessor(["Age"], self.manifest, scale_numeric=True)
        with self.assertRaises(NotFittedError):
            first.transform(pd.DataFrame({"Age": [30.0]}))
        first.fit(pd.DataFrame({"Age": [20.0, 40.0]}))
        second.fit(pd.DataFrame({"Age": [60.0, 80.0]}))
        np.testing.assert_array_equal(first.named_transformers_["numeric"].mean_, [30.0])
        np.testing.assert_array_equal(second.named_transformers_["numeric"].mean_, [70.0])

    def test_unknown_categories_are_rejected(self):
        transformer = make_preprocessor(["Gender"], self.manifest, scale_numeric=False)
        transformer.fit(pd.DataFrame({"Gender": ["female", "male"]}))
        with self.assertRaisesRegex(ValueError, "unknown categories"):
            transformer.transform(pd.DataFrame({"Gender": ["unknown"]}))

    def test_identifier_and_target_are_rejected(self):
        for feature in ("User_ID", "Calories"):
            with self.assertRaisesRegex(ValueError, "declared input"):
                make_preprocessor([feature], self.manifest, scale_numeric=True)

    def test_tree_path_preserves_numeric_units(self):
        transformer = make_preprocessor(["Duration"], self.manifest, scale_numeric=False)
        values = pd.DataFrame({"Duration": [1.0, 10.0, 30.0]})
        np.testing.assert_array_equal(transformer.fit_transform(values).ravel(), [1.0, 10.0, 30.0])


if __name__ == "__main__":
    unittest.main()
