"""Synthetic study-tool fixtures only; these are not participant observations."""

import csv
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from calorie_estimation import usability as study


class UsabilityTests(unittest.TestCase):
    def setUp(self):
        self.plan = study.protocol()

    def row(self, code="P01", cohort="main"):
        columns = next(csv.reader((study.STUDY / "templates/sessions.csv").read_text().splitlines()))
        row = dict.fromkeys(columns, "")
        row.update(participant_id=code, cohort=cohort, consent="yes", session_status="completed",
                   device="desktop", ml_familiarity="no", app_revision=self.plan["space_revision"],
                   task_order="T1,T2,T3,T4" if cohort == "pilot" or int(code[1:]) % 2 else "T2,T1,T3,T4",
                   notes="IDENTIFYING_NOTE_MUST_NOT_BE_EXPORTED")
        for task in self.plan["tasks"]:
            row[f"{task}_outcome"], row[f"{task}_seconds"] = "unassisted", "10"
        for field in self.plan["comprehension_fields"]:
            row[field] = "1"
        for field in self.plan["rating_fields"]:
            row[field] = "4"
        return row

    def write_rows(self, path, rows):
        columns = next(csv.reader((study.STUDY / "templates/sessions.csv").read_text().splitlines()))
        with Path(path).open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)

    def test_partial_failure_assistance_and_missing_answers_keep_denominators(self):
        a, b = self.row(), self.row("P02")
        b.update(session_status="partial", t1_outcome="technical_failure", t1_seconds="30",
                 t2_outcome="assisted", t2_seconds="60", t3_outcome="failed", t3_seconds="120",
                 c_interval="0", c_limitations="0", t4_outcome="not_attempted", t4_seconds="",
                 c_tradeoff="", c_long_sessions="", q_ease="")
        value = study.summarize_rows([a, b, self.row("PILOT01", "pilot")], self.plan)
        self.assertEqual(value["main_participants"], 2)
        self.assertEqual(value["pilot_rows_excluded"], 1)
        self.assertEqual(value["tasks"]["t1"]["unassisted_fraction"], .5)
        self.assertEqual(value["tasks"]["t2"]["counts"]["assisted"], 1)
        self.assertEqual(value["tasks"]["t2"]["unassisted_median_seconds"], 10)
        self.assertEqual(value["comprehension"]["c_tradeoff"]["missing_answers"], 1)
        self.assertEqual(value["comprehension"]["c_tradeoff"]["correct_fraction_all_retained"], .5)
        self.assertEqual(value["custom_ratings"]["q_ease"]["response_count"], 1)
        self.assertTrue(all(flag is None for flag in value["iteration_review_triggered"].values()))
        report = json.dumps(value) + study.markdown(value)
        self.assertNotIn("IDENTIFYING_NOTE", report)
        self.assertNotIn("P01", report)

    def test_empty_data_produces_no_estimated_outcomes(self):
        value = study.summarize_rows([], self.plan)
        self.assertEqual(value["status"], "not_started")
        self.assertIsNone(value["tasks"]["t1"]["unassisted_fraction"])
        self.assertIsNone(value["custom_ratings"]["q_clarity"]["median"])
        self.assertIn("not estimable", study.markdown(value))

    def test_skipped_individual_question_remains_missing_not_an_invented_answer(self):
        row = self.row()
        row.update(t3_outcome="failed", c_interval="1", c_limitations="")
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "sessions.csv"
            self.write_rows(path, [row])
            value = study.summarize_rows(study.load_rows(path, self.plan), self.plan)
            self.assertEqual(value["comprehension"]["c_interval"]["correct_before_help"], 1)
            self.assertEqual(value["comprehension"]["c_limitations"]["recorded_answers"], 0)
            self.assertEqual(value["comprehension"]["c_limitations"]["missing_answers"], 1)

    def test_iteration_threshold_is_five_of_six_and_pilot_does_not_improve_it(self):
        rows = [self.row(f"P{index:02}") for index in range(1, 7)]
        for row in rows[-2:]:
            row.update(t1_outcome="failed", t1_seconds="180")
        rows[-1].update(t2_outcome="assisted", t2_seconds="50")
        value = study.summarize_rows([*rows, self.row("PILOT01", "pilot")], self.plan)
        self.assertTrue(value["iteration_review_triggered"]["t1"])
        self.assertFalse(value["iteration_review_triggered"]["t2"])
        self.assertEqual(value["tasks"]["t1"]["counts"]["unassisted"], 4)

    def test_withdrawal_retains_no_measurements_and_does_not_enter_denominator(self):
        row = dict.fromkeys(self.row(), "")
        row.update(participant_id="P02", cohort="main", session_status="withdrawn")
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "sessions.csv"
            self.write_rows(path, [self.row(), row])
            value = study.summarize_rows(study.load_rows(path, self.plan), self.plan)
            self.assertEqual(value["main_withdrawals_excluded"], 1)
            self.assertEqual(value["main_participants"], 1)
            row["notes"] = "must erase"
            self.write_rows(path, [row])
            with self.assertRaisesRegex(ValueError, "Erase"):
                study.load_rows(path, self.plan)

    def test_invalid_revision_duplicate_consent_scores_times_and_order_rejected(self):
        updates = ({"app_revision":"other"}, {"consent":"no"}, {"t1_seconds":"nan"},
                   {"t2_seconds":"181"}, {"q_clarity":"6"}, {"c_interval":"0"},
                   {"task_order":"T2,T1,T3,T4"}, {"session_status":"partial"})
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "sessions.csv"
            for change in updates:
                row = self.row()
                row.update(change)
                self.write_rows(path, [row])
                with self.subTest(change=change), self.assertRaises(ValueError):
                    study.load_rows(path, self.plan)
            self.write_rows(path, [self.row(), self.row()])
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                study.load_rows(path, self.plan)

    def test_fixed_target_does_not_allow_unplanned_extra_sessions(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "sessions.csv"
            self.write_rows(path, [self.row(f"P{index:02}") for index in range(1, 8)])
            with self.assertRaisesRegex(ValueError, "fixed target"):
                study.load_rows(path, self.plan)

    def test_local_freeze_is_exclusive_and_blocks_post_freeze_changes(self):
        with tempfile.TemporaryDirectory(dir=study.STUDY / "private", prefix="test_") as temp:
            directory = Path(temp) / "round"
            study.initialize(directory)
            study.freeze(directory)
            with self.assertRaises(FileExistsError):
                study.freeze(directory)
            with self.assertRaises(FileExistsError):
                study.initialize(directory)
            record = json.loads((directory / "protocol-freeze.json").read_bytes())
            record["files_sha256"]["study/protocol.json"] = "changed"
            (directory / "protocol-freeze.json").write_text(json.dumps(record), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "changed after freeze"):
                study.summarize(directory, study.ROOT / "runs/unwritten-test-output")

    def test_main_rows_cannot_be_frozen_after_collection_and_private_path_is_required(self):
        with tempfile.TemporaryDirectory(dir=study.STUDY / "private", prefix="test_") as temp:
            directory = Path(temp) / "round"
            study.initialize(directory)
            self.write_rows(directory / "sessions.csv", [self.row()])
            with self.assertRaisesRegex(ValueError, "Freeze before"):
                study.freeze(directory)
        with self.assertRaisesRegex(ValueError, "inside ignored"):
            study.private_directory(study.ROOT / "docs")

    def test_complete_file_workflow_preserves_destinations_and_omits_private_notes(self):
        with tempfile.TemporaryDirectory(dir=study.STUDY / "private", prefix="test_") as temp, \
                tempfile.TemporaryDirectory(dir=study.ROOT / "runs", prefix="test_") as output_temp:
            directory = Path(temp) / "round"
            study.initialize(directory)
            study.freeze(directory)
            empty = Path(output_temp) / "empty"
            self.assertEqual(study.summarize(directory, empty)["status"], "not_started")
            self.write_rows(directory / "sessions.csv", [self.row(f"P{i:02}") for i in range(1, 7)])
            output = Path(output_temp) / "aggregate"
            self.assertEqual(study.summarize(directory, output)["main_participants"], 6)
            report = (output / "summary.json").read_text(encoding="utf-8")
            self.assertNotIn("IDENTIFYING_NOTE", report)
            self.assertNotIn("P01", report)
            with self.assertRaises(FileExistsError):
                study.summarize(directory, output)

    def test_portable_kit_can_freeze_without_git_installed(self):
        with tempfile.TemporaryDirectory(dir=study.STUDY / "private", prefix="test_") as temp:
            directory = Path(temp) / "round"
            study.initialize(directory)
            with patch.object(study.subprocess, "run", side_effect=FileNotFoundError):
                study.freeze(directory)
            record = json.loads((directory / "protocol-freeze.json").read_bytes())
            self.assertEqual(record["source_commit"], "unavailable: Git not installed")
            self.assertIsNone(record["source_study_files_clean"])


if __name__ == "__main__":
    unittest.main()
