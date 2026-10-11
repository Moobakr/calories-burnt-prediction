"""Baseline leakage, metric selection and artifact checks on synthetic records."""

import copy
import csv
import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.dummy import DummyRegressor
from sklearn.preprocessing import StandardScaler

from calorie_estimation.baselines import (cross_validate_candidate, errors, ridge_pipeline,
                                         run_baselines, select_candidate, settings)
from calorie_estimation.config import ROOT, load_project
from calorie_estimation.evaluation import DevelopmentData, load_development
import test_evaluation


class BaselineTests(unittest.TestCase):
    def setUp(self):
        self.config, self.manifest = load_project()
        self.data = DevelopmentData(pd.DataFrame({"Duration": [1., 2., 10., 20.]}),
                                    np.array([0., 0., 100., 100.]), ("1", "2", "3", "4"),
                                    ((np.array([2, 3]), np.array([0, 1])),
                                     (np.array([0, 1]), np.array([2, 3]))))

    def test_mean_uses_training_labels_only(self):
        template = DummyRegressor(strategy="mean")
        metrics, oof = cross_validate_candidate(template, self.data)
        np.testing.assert_array_equal(oof, [100., 100., 0., 0.])
        self.assertEqual(metrics["mean_fold_mae"], 100.)
        self.assertEqual(metrics["pooled_oof"], {"mae": 100., "rmse": 100.})
        self.assertFalse(hasattr(template, "constant_"))

    def test_ridge_scaling_is_fitted_separately_inside_each_training_fold(self):
        observed = []
        original = StandardScaler.fit

        def record_fit(scaler, X, *args, **kwargs):
            observed.append(np.mean(X, axis=0).tolist())
            return original(scaler, X, *args, **kwargs)

        template = ridge_pipeline(["Duration"], self.manifest, 1.)
        with patch.object(StandardScaler, "fit", record_fit):
            _, first = cross_validate_candidate(template, self.data)
        self.assertEqual(observed, [[15.], [1.5]])
        self.assertFalse(hasattr(template.named_steps["model"], "coef_"))
        _, second = cross_validate_candidate(template, self.data)
        np.testing.assert_array_equal(first, second)

    def test_selection_uses_mean_fold_mae_and_smallest_alpha_for_exact_ties(self):
        candidates = [{"alpha": 100., "mean_fold_mae": 5., "pooled_oof": {"mae": 4.}},
                      {"alpha": 1., "mean_fold_mae": 4., "pooled_oof": {"mae": 5.}},
                      {"alpha": .1, "mean_fold_mae": 4., "pooled_oof": {"mae": 5.}}]
        self.assertEqual(select_candidate(candidates)["alpha"], .1)
        self.assertEqual(select_candidate(candidates[::-1])["alpha"], .1)

    def test_metrics_are_absolute_and_root_mean_square_errors(self):
        result = errors([1., 1.], [0., 4.])
        self.assertEqual(result["mae"], 2.)
        self.assertAlmostEqual(result["rmse"], np.sqrt(5.))
        for y, predicted in (([], []), ([1], [1, 2]), ([1], [[1]]), ([1], [np.nan])):
            with self.subTest(y=y, predicted=predicted), self.assertRaises(ValueError):
                errors(y, predicted)

    def test_invalid_grids_and_thread_settings_are_rejected(self):
        for grid in ([], [0.], [-1.], [True], [1., 1.], [np.inf], [np.nan], ["1"]):
            config = copy.deepcopy(self.config)
            config["baselines"]["ridge_alphas"] = grid
            with self.subTest(grid=grid), self.assertRaises(ValueError):
                settings(config)
        for changes in ({"threads": True}, {"threads": 2}, {"ridge_solver": "auto"}):
            config = copy.deepcopy(self.config)
            config["baselines"].update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                settings(config)

    def test_overlapping_or_incomplete_cv_is_rejected(self):
        for cv in ((self.data.cv[0], self.data.cv[0]),
                   ((np.array([0, 1, 2]), np.array([2, 3])),),
                   ((np.array([0]), np.array([1, 2])),)):
            data = DevelopmentData(self.data.X, self.data.y, self.data.ids, cv)
            with self.subTest(cv=cv), self.assertRaises(ValueError):
                cross_validate_candidate(DummyRegressor(), data)

    def test_synthetic_run_excludes_holdouts_and_persists_complete_pipelines(self):
        fixture = test_evaluation.EvaluationTests(methodName="runTest")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.create()
        temporary = tempfile.TemporaryDirectory(dir=ROOT / "runs")
        self.addCleanup(temporary.cleanup)
        run_dir = Path(temporary.name) / "run"
        result = run_baselines(fixture.prepared, fixture.splits, run_dir,
                               fixture.config, fixture.manifest,
                               {"status": "passed", "isolated_from_system_site_packages": True})
        self.assertEqual(result["development_rows"], 48)
        self.assertEqual(result["total_cv_fits"], 125)
        self.assertFalse(result["test_evaluated"])
        report = json.loads((run_dir / "metrics.json").read_text())
        with (run_dir / "development_oof.csv").open(newline="") as stream:
            oof = list(csv.DictReader(stream))
        for name in fixture.config["feature_sets"]:
            data = load_development(fixture.prepared, fixture.splits, fixture.config, fixture.manifest, name)
            self.assertEqual([row["User_ID"] for row in oof], list(data.ids))
            model = joblib.load(run_dir / f"ridge_{name}.joblib")
            self.assertEqual(model.named_steps["preprocess"].named_transformers_["numeric"].n_samples_seen_, 48)
            self.assertTrue(np.isfinite(model.predict(data.X)).all())
        mean = joblib.load(run_dir / "mean.joblib")
        self.assertEqual(mean.named_steps["model"].constant_[0, 0], np.mean(data.y))
        self.assertTrue(all(row["reload_predictions_identical"] for row in report["results"]))
        prior = (run_dir / "metrics.json").read_bytes()
        with self.assertRaisesRegex(ValueError, "already exists"):
            run_baselines(fixture.prepared, fixture.splits, run_dir, fixture.config, fixture.manifest,
                          {"status": "passed", "isolated_from_system_site_packages": True})
        self.assertEqual((run_dir / "metrics.json").read_bytes(), prior)


if __name__ == "__main__":
    unittest.main()
