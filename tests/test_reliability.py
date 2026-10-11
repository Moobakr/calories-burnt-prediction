"""Finite-sample ranks, calibration separation and matched stress tests."""

import copy
import unittest

import numpy as np
import pandas as pd
from sklearn.dummy import DummyRegressor

from calorie_estimation.config import load_project
from calorie_estimation.reliability import (calibration_roles, conformal_threshold, group_masks, noise_conditions,
    noise_matrix, noise_summary, noisy_prediction, score_predictions, settings, subset_frame)


class ReliabilityTests(unittest.TestCase):
    def setUp(self):
        self.config, _ = load_project()
        self.frame = pd.DataFrame({"Gender": ["female", "male", "female", "male"],
            "Age": [20, 39, 40, 79], "Duration": [1, 10, 11, 30], "Heart_Rate": [80., 90., 100., 110.],
            "Body_Temp": [38., 38.5, 39., 39.5]})

    def test_finite_sample_quantile_uses_exact_order_statistic_without_interpolation(self):
        result = conformal_threshold(np.arange(1500), np.zeros(1500), .9)
        self.assertEqual(result, {"fit_rows":1500, "rank_one_based":1351, "threshold":1350.})
        self.assertEqual(conformal_threshold(np.arange(10), np.zeros(10))["threshold"], 9.)
        self.assertTrue(np.isinf(conformal_threshold([1.], [0.])["threshold"]))
        self.assertEqual(conformal_threshold([2.] * 20, [1.] * 20)["threshold"], 1.)

    def test_invalid_residuals_and_coverage_are_rejected(self):
        for y, predicted, nominal in (([],[],.9), ([1],[1,2],.9), ([1],[np.nan],.9), ([np.inf],[1],.9),
                                       ([1],[1],True), ([1],[1],1.), ([1],[1],np.nan)):
            with self.subTest(y=y, nominal=nominal), self.assertRaises(ValueError):
                conformal_threshold(y, predicted, nominal)

    def test_calibration_roles_are_balanced_disjoint_order_invariant_and_exclude_other_partitions(self):
        membership = {str(i): ("calibration", None) for i in range(1, 3001)}
        membership.update({"4000": ("development",0), "5000":("test",None)})
        roles = calibration_roles(membership,46)
        self.assertEqual(sum(value == "interval_fit" for value in roles.values()),1500)
        self.assertEqual(sum(value == "interval_audit" for value in roles.values()),1500)
        self.assertEqual(roles, calibration_roles(dict(reversed(list(membership.items()))),46))
        self.assertNotEqual(roles, calibration_roles(membership,47))
        self.assertNotIn("4000",roles)
        self.assertNotIn("5000",roles)

    def test_analysis_loader_rejects_test_rows_and_cross_partition_requests(self):
        records = [{"User_ID":str(i), "Gender":"female", "Age":"20", "Calories":"1"} for i in range(1,4)]
        membership = {"1":("development",0),"2":("calibration",None),"3":("test",None)}
        for ids, partition in ((("3",),"test"), (("3",),"calibration"), (("1",),"calibration"), (("2","2"),"calibration")):
            with self.subTest(ids=ids, partition=partition), self.assertRaises(ValueError):
                subset_frame(records,ids,membership,partition)
        frame = subset_frame(records,("2",),membership,"calibration")
        self.assertEqual(list(frame.index),["2"])

    def test_group_bands_cover_boundaries_and_preserve_unexpected_tail_records(self):
        for axis in ("gender","age","duration"):
            masks = [mask for key,_,mask in group_masks(self.frame) if key == axis]
            np.testing.assert_array_equal(np.sum(masks,axis=0),np.ones(4))
        tail = self.frame.copy()
        tail.loc[0,"Age"] = 85
        outside = next(mask for axis,label,mask in group_masks(tail) if axis == "age" and label == "outside_predefined_bands")
        np.testing.assert_array_equal(outside,[True,False,False,False])

    def test_interval_coverage_includes_boundaries_and_group_counts(self):
        y, prediction = np.array([1.,2.,3.,4.]),np.array([0.,2.,4.,7.])
        result = score_predictions(y,prediction,self.frame,1.)
        self.assertEqual(result["overall"]["coverage"],.75)
        self.assertEqual(result["overall"]["mean_width"],2.)
        self.assertEqual(result["overall"]["negative_lower_bounds"],1)
        self.assertEqual(result["overall"]["mae"],1.25)
        for axis in ("gender","age","duration"):
            rows = [row for row in result["groups"] if row["axis"] == axis]
            self.assertEqual(sum(row["n"] for row in rows),4)
            self.assertEqual(sum(row.get("covered",0) for row in rows),3)

    def test_noise_draws_are_reproducible_matched_across_magnitudes_and_separate_streams(self):
        first = noise_matrix(47,"development","Heart_Rate",20,4)
        np.testing.assert_array_equal(first,noise_matrix(47,"development","Heart_Rate",20,4))
        self.assertFalse(np.array_equal(first,noise_matrix(47,"interval_audit","Heart_Rate",20,4)))
        self.assertFalse(np.array_equal(first,noise_matrix(47,"development","Body_Temp",20,4)))
        np.testing.assert_allclose(5*first,2*first*2.5,rtol=1e-15)

    def test_sensor_not_used_by_a_model_does_not_change_predictions_or_input_frame(self):
        model = DummyRegressor(strategy="mean").fit(self.frame[["Age"]],[1.,2.,3.,4.])
        X = self.frame[["Age"]].copy()
        original = X.copy()
        predicted = noisy_prediction(model,X,{"column":"Heart_Rate","sd":5.},np.ones(4))
        np.testing.assert_array_equal(predicted,model.predict(X))
        pd.testing.assert_frame_equal(X,original)

    def test_noise_summary_reports_draw_spread_and_fixed_threshold_coverage(self):
        y=np.zeros(4)
        noisy=np.array([[0.,1.,2.,3.],[1.,2.,3.,4.]])
        result=noise_summary(y,noisy,self.frame,np.zeros(4),2.)
        self.assertEqual(result["mean_mae"],2.)
        self.assertEqual(result["mae_change_from_clean"],2.)
        self.assertAlmostEqual(result["sd_mae_across_draws"],np.sqrt(.5))
        self.assertEqual(result["mean_coverage"],.625)
        self.assertEqual(result["mean_width"],4.)

    def test_invalid_reliability_settings_are_rejected(self):
        for change in ({"nominal_coverage":.95},{"noise_draws":1},{"threads":True},
                       {"noise_seed":True},{"calibration_role_seed":-1},{"heart_rate_noise_sd":[1.,2.]}):
            config=copy.deepcopy(self.config)
            config["reliability"].update(change)
            with self.subTest(change=change),self.assertRaises(ValueError):
                settings(config)
        self.assertEqual(len(noise_conditions(settings(self.config))),4)


if __name__ == "__main__":
    unittest.main()
