"""Selection, paired uncertainty and protection of the final release boundary."""

import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from scipy.stats import bootstrap

from calorie_estimation.config import file_hash, load_project
from calorie_estimation.final_evaluation import (claim_release, competitiveness, paired_bootstrap,
    run_final_evaluation, select_primary, settings, test_frame, validate_intervals)


class FinalEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.config, self.manifest = load_project()

    def test_primary_uses_development_only_with_documented_ties(self):
        rows = [{"name": name, "algorithm": "ridge", "input_columns": fields, "mean_fold_mae": mae,
                 "audit_mae": audit, "test_mae": audit} for name, fields, mae, audit in
                (("z", ["Age"], 1., 50.), ("a", ["Age"], 1., 100.), ("full", ["Age", "Duration"], 1., 0.))]
        self.assertEqual(select_primary(rows), "a")
        rows[0]["mean_fold_mae"] = .99
        self.assertEqual(select_primary(rows), "z")
        rows.append({"name":"mean", "algorithm":"mean", "input_columns":[], "mean_fold_mae":0.})
        self.assertEqual(select_primary(rows), "z")

    def test_bootstrap_pairing_preserves_proportional_errors_and_shared_indices(self):
        y = np.zeros(6)
        full = np.array([1., 2., 4., 7., 12., 20.])
        result, draws, indices = paired_bootstrap(y, {"full":full, "reduced":2*full, "same":full},
                                                  [("reduced","full"),("same","full")], seed=4, draws=100)
        np.testing.assert_array_equal(draws["reduced_vs_full_relative"], np.ones(100))
        np.testing.assert_array_equal(draws["same_vs_full_relative"], np.zeros(100))
        self.assertEqual(result[0]["relative_change_interval_95"], [1.,1.])
        self.assertEqual(result[1]["competitiveness_decision"], "competitive")
        repeated = paired_bootstrap(y, {"full":full,"reduced":2*full}, [("reduced","full")], seed=4, draws=100)
        np.testing.assert_array_equal(indices, repeated[2])

    def test_percentile_interval_matches_independent_scipy_paired_bootstrap(self):
        a = np.array([1., 4., 3., 2., 10., 8.])
        b = np.array([2., 2., 4., 4., 6., 12.])
        result, _, _ = paired_bootstrap(np.zeros(6), {"a":a,"b":b}, [("a","b")], draws=200)
        reference = bootstrap((a,b), lambda x,z: (np.mean(x)-np.mean(z))/np.mean(z),
                              paired=True, vectorized=False, n_resamples=200,
                              method="percentile", random_state=np.random.default_rng(2026))
        np.testing.assert_allclose(result[0]["relative_change_interval_95"],
                                   [reference.confidence_interval.low, reference.confidence_interval.high], atol=1e-14)

    def test_zero_reference_error_does_not_drop_undefined_draws(self):
        result, _, _ = paired_bootstrap([0.,0.], {"a":[1.,1.],"b":[0.,0.]}, [("a","b")], draws=50)
        self.assertIsNone(result[0]["relative_mae_change"])
        self.assertIsNone(result[0]["relative_change_interval_95"])
        self.assertEqual(result[0]["undefined_relative_resamples"],50)
        self.assertEqual(result[0]["competitiveness_decision"],"undefined")
        result, _, _ = paired_bootstrap([0.,0.], {"a":[1.,1.],"b":[0.,1.]}, [("a","b")], draws=50)
        self.assertIsNotNone(result[0]["relative_mae_change"])
        self.assertIsNone(result[0]["relative_change_interval_95"])

    def test_margin_boundaries_and_crossing_are_not_significance_claims(self):
        self.assertEqual(competitiveness([-.2,.1]),"competitive")
        self.assertEqual(competitiveness([.1,.2]),"inconclusive")
        self.assertEqual(competitiveness([.10001,.2]),"fails_margin")
        self.assertEqual(competitiveness(None),"undefined")
        with self.assertRaises(ValueError):
            competitiveness([.2,.1])

    def test_invalid_or_misaligned_bootstrap_input_is_rejected(self):
        for y,predictions,pairs in (([],{"a":[],"b":[]},[("a","b")]),
            ([0.],{"a":[0.,1.],"b":[1.]},[("a","b")]),
            ([0.],{"a":[np.nan],"b":[1.]},[("a","b")]),
            ([0.],{"a":[1.]},[("a","missing")])):
            with self.subTest(y=y), self.assertRaises(ValueError):
                paired_bootstrap(y,predictions,pairs,draws=10)

    def test_test_loader_excludes_development_and_calibration_and_orders_ids(self):
        records=[{"User_ID":str(i),"Gender":"female","Age":"20","Calories":str(i)} for i in (10,2,3,4)]
        membership={"10":("test",None),"2":("test",None),"3":("development",0),"4":("calibration",None)}
        ids, frame=test_frame(records,membership)
        self.assertEqual(ids,("2","10"))
        np.testing.assert_array_equal(frame.Calories,[2,10])

    def test_release_record_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"release.json"
            claim_release(path,{"run":"first"})
            with self.assertRaises(ValueError):
                claim_release(path,{"run":"second"})
            self.assertEqual(json.loads(path.read_text()),{"run":"first"})

    def test_existing_release_blocks_another_directory_before_data_analysis(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/"runs").mkdir()
            claim_release(root/"runs/final-test-access.json",{"run":"first"})
            with patch("calorie_estimation.final_evaluation.ROOT",root), patch("calorie_estimation.final_evaluation.verify_splits") as verify:
                with self.assertRaisesRegex(ValueError,"already released"):
                    run_final_evaluation(root,root,root/"runs/a",root/"runs/b",root/"runs/c",root/"runs/new",
                        self.config,self.manifest,{"status":"passed","isolated_from_system_site_packages":True})
                verify.assert_not_called()

    def test_interval_binding_rejects_model_changes_and_audit_refitting(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            jobs=[]
            bindings={}
            for family in ("ridge","xgboost"):
                for feature in ("duration","basic","heart_rate","full"):
                    name=f"{family}_{feature}"
                    path=root/f"{name}.joblib"
                    path.write_bytes(b"frozen artifact")
                    jobs.append(({"name":name,"algorithm":family,"artifact":path.name},root))
                    bindings[name]={"model_artifact":path.name,"model_sha256":file_hash(path),
                        "calibration_roles_sha256":"roles", "nominal_coverage":.9,"fit_rows":1500,"rank_one_based":1351,
                        "audit_labels_used_for_quantile":False,"refit_using_audit_allowed":False,"threshold":2.}
            report={"status":"passed","test_evaluated":False,"audit_labels_used_for_quantiles":False,
                "model_selection_using_calibration":False,"calibration_roles_sha256":"roles",
                "results":[{"name":name,"threshold":copy.deepcopy(value)} for name,value in bindings.items()]}
            intervals={"status":"frozen","test_evaluated":False,"nominal_coverage":.9,"models":bindings}
            validate_intervals(report,intervals,jobs)
            changed=copy.deepcopy(intervals)
            changed["models"]["ridge_full"]["refit_using_audit_allowed"]=True
            with self.assertRaises(ValueError):
                validate_intervals(report,changed,jobs)
            (root/"ridge_full.joblib").write_bytes(b"changed model")
            with self.assertRaises(ValueError):
                validate_intervals(report,intervals,jobs)

    def test_planned_bootstrap_settings_cannot_silently_change(self):
        for changes in ({"bootstrap_seed":1},{"bootstrap_resamples":True},{"competitive_relative_mae_margin":.2}):
            config=copy.deepcopy(self.config)
            config["evaluation"].update(changes)
            with self.assertRaises(ValueError):
                settings(config)
        self.assertEqual(len(settings(self.config)["planned_pairs"]),4)


if __name__ == "__main__":
    unittest.main()
