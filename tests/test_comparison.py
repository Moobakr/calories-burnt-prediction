"""Synthetic tests of matched searches, input tradeoffs and baseline provenance."""

import copy
import json
from pathlib import Path
import tempfile
import unittest

import joblib
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

from calorie_estimation.baselines import run_baselines
from calorie_estimation.comparison import (evaluate_search, input_tradeoffs, load_baseline_run, sample_candidates,
                                           select_candidate, settings, xgb_pipeline)
from calorie_estimation.config import ROOT, load_project
from calorie_estimation.data import write_json
from calorie_estimation.evaluation import DevelopmentData, load_development, verify_splits
import test_evaluation


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.config, self.manifest = load_project()

    def test_sampling_is_deterministic_unique_and_shared_across_input_sets(self):
        protocol = settings(self.config)
        first = sample_candidates(protocol)
        self.assertEqual(first, sample_candidates(protocol))
        self.assertEqual(len(first), 30)
        self.assertEqual(len({json.dumps(candidate, sort_keys=True) for candidate in first}), 30)
        for candidate in first:
            for parameter, value in candidate.items():
                self.assertIn(value, protocol["search_space"][parameter])
        changed = copy.deepcopy(protocol)
        changed["search_seed"] += 1
        self.assertNotEqual(first, sample_candidates(changed))

    def test_invalid_search_protocols_are_rejected(self):
        for changes in ({"search_seed": True}, {"model_seed": -1}, {"n_candidates": 31}, {"threads": 2},
                        {"tree_method": "approx"}, {"latency_repeats": 1}, {"latency_batch_sizes": [True, 100]}):
            config = copy.deepcopy(self.config)
            config["comparison"].update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                settings(config)
        for key, values in (("n_estimators", [1.5]), ("max_depth", [0]), ("reg_alpha", [-1]),
                            ("subsample", [1.1]), ("learning_rate", [np.nan]), ("reg_lambda", [1., 1.])):
            config = copy.deepcopy(self.config)
            config["comparison"]["search_space"][key] = values
            with self.subTest(key=key), self.assertRaises(ValueError):
                settings(config)
        config = copy.deepcopy(self.config)
        config["comparison"]["search_space"] = {key: values[:1] for key, values in config["comparison"]["search_space"].items()}
        with self.assertRaisesRegex(ValueError, "smaller"):
            settings(config)

    def test_exact_score_ties_choose_the_lower_sampled_index(self):
        candidates = [{"candidate_index": 3, "mean_fold_mae": 1.}, {"candidate_index": 2, "mean_fold_mae": 2.},
                      {"candidate_index": 1, "mean_fold_mae": 1.}]
        self.assertEqual(select_candidate(candidates)["candidate_index"], 1)
        self.assertEqual(select_candidate(candidates[::-1])["candidate_index"], 1)

    def test_input_tradeoffs_use_the_full_model_from_the_same_algorithm(self):
        results = []
        for algorithm, full in (("ridge", 10.), ("xgboost", 2.)):
            for name, value in (("basic", full * 1.5), ("full", full)):
                results.append({"algorithm": algorithm, "feature_set": name,
                                "input_columns": self.config["feature_sets"][name],
                                "mean_fold_mae": value, "mean_fold_rmse": value * 2})
        rows = input_tradeoffs(results)
        for row in rows:
            self.assertEqual(row["relative_mae_change_vs_full"], .5 if row["feature_set"] == "basic" else 0.)
            self.assertEqual(row["requires_heart_rate"], row["feature_set"] == "full")
            self.assertEqual(row["requires_temperature"], row["feature_set"] == "full")
            self.assertEqual(row["competitiveness_decision"], "deferred_until_reserved_test")
        for result in results:
            result["mean_fold_mae"] = 0.
        self.assertTrue(all(row["relative_mae_change_vs_full"] is None for row in input_tradeoffs(results)))

    def test_synthetic_search_is_reproducible_and_pipeline_keeps_numeric_units(self):
        X = pd.DataFrame({"Duration": np.arange(1, 21, dtype=float)})
        data = DevelopmentData(X, X.Duration.to_numpy() ** 2, tuple(str(i) for i in range(20)),
                               ((np.arange(10, 20), np.arange(10)), (np.arange(10), np.arange(10, 20))))
        candidates = [{"n_estimators": 2, "max_depth": 1}, {"n_estimators": 3, "max_depth": 2}]
        with threadpool_limits(limits=1):
            scores, selected, oof = evaluate_search(data, ["Duration"], self.manifest, candidates, 45)
            _, repeated, repeated_oof = evaluate_search(data, ["Duration"], self.manifest, candidates, 45)
            self.assertEqual(selected["candidate_index"], repeated["candidate_index"])
            np.testing.assert_array_equal(oof, repeated_oof)
            self.assertEqual(len(scores), 2)
            model = xgb_pipeline(["Duration"], self.manifest, selected["parameters"], 45)
            model.fit(data.X, data.y)
            np.testing.assert_array_equal(model.named_steps["preprocess"].transform(X).ravel(), X.Duration)
            self.assertEqual(model.named_steps["model"].n_jobs, 1)
            self.assertEqual(model.named_steps["model"].random_state, 45)
            self.assertIsNone(model.named_steps["model"].early_stopping_rounds)
            with tempfile.TemporaryDirectory() as temporary:
                path = Path(temporary) / "model.joblib"
                joblib.dump(model, path)
                np.testing.assert_array_equal(joblib.load(path).predict(X), model.predict(X))

    def test_baseline_comparison_rejects_changed_predictions_protocol_and_features(self):
        fixture = test_evaluation.EvaluationTests(methodName="runTest")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.create()
        temporary = tempfile.TemporaryDirectory(dir=ROOT / "runs")
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name) / "baselines"
        run_baselines(fixture.prepared, fixture.splits, root, fixture.config, fixture.manifest,
                      {"status": "passed", "isolated_from_system_site_packages": True})
        data = load_development(fixture.prepared, fixture.splits, fixture.config, fixture.manifest, "duration")
        _, _, split = verify_splits(fixture.prepared, fixture.splits, fixture.config, fixture.manifest)
        report, rows = load_baseline_run(root, data, fixture.config, fixture.manifest, split)
        self.assertEqual([row["User_ID"] for row in rows], list(data.ids))
        changed = copy.deepcopy(split)
        changed["protocol"]["cv_seed"] += 1
        with self.assertRaisesRegex(ValueError, "protocol"):
            load_baseline_run(root, data, fixture.config, fixture.manifest, changed)
        altered = copy.deepcopy(report)
        altered["results"][1]["input_columns"] = ["Calories"]
        write_json(root / "metrics.json", altered)
        with self.assertRaisesRegex(ValueError, "feature"):
            load_baseline_run(root, data, fixture.config, fixture.manifest, split)
        write_json(root / "metrics.json", report)
        with (root / "development_oof.csv").open("ab") as stream:
            stream.write(b"\n")
        with self.assertRaisesRegex(ValueError, "hash"):
            load_baseline_run(root, data, fixture.config, fixture.manifest, split)


if __name__ == "__main__":
    unittest.main()
