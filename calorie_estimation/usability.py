"""Prepare and summarize a small, private usability round; no model/data access."""

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import statistics
import subprocess
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "study"
FROZEN_FILES = ("study/protocol.json", "study/README.md", "study/PARTICIPANT_GUIDE.md",
                "study/MODERATOR_GUIDE.md", "study/RESULTS_TEMPLATE.md",
                "study/templates/sessions.csv", "study/templates/issues.csv", "calorie_estimation/usability.py")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def protocol():
    return json.loads((STUDY / "protocol.json").read_bytes())


def private_directory(value):
    path = Path(value).resolve()
    parent = (STUDY / "private").resolve()
    if path == parent or not path.is_relative_to(parent):
        raise ValueError("Response folders must be inside ignored study/private/")
    return path


def initialize(directory):
    path = private_directory(directory)
    path.mkdir(parents=True, exist_ok=False)
    for name in ("sessions.csv", "issues.csv"):
        shutil.copyfile(STUDY / "templates" / name, path / name)
    return {"status": "blank_templates_created", "directory": str(path), "participant_results": 0}


def load_rows(path, plan):
    with (STUDY / "templates/sessions.csv").open(encoding="utf-8-sig", newline="") as stream:
        expected = next(csv.reader(stream))
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != expected:
            raise ValueError("CSV header differs from the response template")
        rows = []
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise ValueError("A response row has extra or missing cells")
            rows.append({key: value.strip() for key, value in row.items()})
    seen = set()
    for row in rows:
        code = row["participant_id"]
        if code in seen:
            raise ValueError("Duplicate participant code")
        seen.add(code)
        cohort = row["cohort"]
        pattern = r"P[0-9]{2,}" if cohort == "main" else r"PILOT[0-9]{2,}"
        if cohort not in ("main", "pilot") or not re.fullmatch(pattern, code) or int(re.search(r"[0-9]+", code).group()) < 1:
            raise ValueError("Use P01 onward for main, PILOT01 onward for pilot")
        if row["session_status"] == "withdrawn":
            if any(value for key, value in row.items() if key not in ("participant_id", "cohort", "session_status")):
                raise ValueError("Erase all outcomes, notes and other data from withdrawn rows")
            continue
        if row["consent"] != "yes" or row["session_status"] not in ("completed", "partial"):
            raise ValueError("Retained sessions require consent=yes and completed/partial status")
        if row["device"] not in ("desktop", "mobile", "tablet") or row["ml_familiarity"] not in ("yes", "no", ""):
            raise ValueError("Invalid device or ML-familiarity value")
        if row["app_revision"] != plan["space_revision"]:
            raise ValueError("Do not pool sessions from a different app revision")
        number = int(re.search(r"[0-9]+", code).group())
        order = "T1,T2,T3,T4" if cohort == "pilot" or number % 2 else "T2,T1,T3,T4"
        if row["task_order"] != order:
            raise ValueError("Task order differs from the fixed odd/even rule; disclose a protocol revision")
        for task in plan["tasks"]:
            outcome, seconds = row[f"{task}_outcome"], row[f"{task}_seconds"]
            if outcome not in plan["outcomes"]:
                raise ValueError("Missing or unsupported task outcome")
            if outcome == "not_attempted":
                if seconds:
                    raise ValueError("Skipped tasks must have blank times")
            else:
                try:
                    time = float(seconds)
                except ValueError:
                    raise ValueError("Attempted tasks require finite elapsed seconds") from None
                if not math.isfinite(time) or not 0 < time <= plan["time_caps_seconds"][task]:
                    raise ValueError("Task time is nonfinite or outside its fixed cap")
        omitted = any(row[f"{task}_outcome"] == "not_attempted" for task in plan["tasks"])
        if omitted != (row["session_status"] == "partial"):
            raise ValueError("Partial status must match skipped/not-reached tasks")
        for task, fields in (("t3", plan["comprehension_fields"][:2]), ("t4", plan["comprehension_fields"][2:])):
            outcome = row[f"{task}_outcome"]
            scores = [row[field] for field in fields]
            if any(score not in ("0", "1", "") for score in scores):
                raise ValueError("Comprehension scores must be 0, 1 or blank")
            if outcome == "not_attempted":
                if any(scores):
                    raise ValueError("Unattempted comprehension tasks must have blank scores")
            if outcome == "unassisted" and scores != ["1", "1"]:
                raise ValueError("Unassisted comprehension completion requires both initial answers correct")
        for field in plan["rating_fields"]:
            if row[field] not in ("", "1", "2", "3", "4", "5"):
                raise ValueError("Custom ratings must be integers 1–5 or blank")
    retained = [row for row in rows if row["cohort"] == "main" and row["session_status"] != "withdrawn"]
    if len(retained) > plan["target_main_participants"]:
        raise ValueError("More main participants than the fixed target; review a separate protocol/round")
    return rows


def freeze(directory):
    directory = private_directory(directory)
    plan = protocol()
    rows = load_rows(directory / "sessions.csv", plan)
    if any(row["cohort"] == "main" for row in rows):
        raise ValueError("Freeze before recording any main participant, including a withdrawal")
    command = ["git", "-c", f"safe.directory={ROOT.as_posix()}", "rev-parse", "HEAD"]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    status = subprocess.run(["git", "-c", f"safe.directory={ROOT.as_posix()}", "status", "--porcelain", "--", *FROZEN_FILES],
                            cwd=ROOT, capture_output=True, text=True)
    value = {"protocol_version": plan["protocol_version"], "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
             "source_commit": result.stdout.strip() if result.returncode == 0 else "unavailable: source archive",
             "source_study_files_clean": not status.stdout.strip() if status.returncode == 0 else None,
             "files_sha256": {name: digest(ROOT / name) for name in FROZEN_FILES},
             "space_revision": plan["space_revision"], "package_manifest_sha256": plan["package_manifest_sha256"],
             "registration": "local hash/timestamp record; not an external preregistration"}
    with (directory / "protocol-freeze.json").open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, indent=2) + "\n")
    return {"status": "frozen_before_main_rows", "freeze_sha256": digest(directory / "protocol-freeze.json")}


def summarize_rows(rows, plan):
    retained = [row for row in rows if row["cohort"] == "main" and row["session_status"] != "withdrawn"]
    n, target = len(retained), plan["target_main_participants"]
    value = {"status": "not_started" if n == 0 else "incomplete" if n < target else "ready_for_manual_report_review",
             "main_participants": n, "target_main_participants": target,
             "pilot_rows_excluded": sum(row["cohort"] == "pilot" for row in rows),
             "main_withdrawals_excluded": sum(row["cohort"] == "main" and row["session_status"] == "withdrawn" for row in rows),
             "completed_sessions": sum(row["session_status"] == "completed" for row in retained),
             "partial_sessions": sum(row["session_status"] == "partial" for row in retained),
             "tasks": {}, "comprehension": {}, "custom_ratings": {}, "mix": {},
             "interpretation": "Formative convenience sample; no causal benefit, calorie accuracy or population usability claim."}
    for field in ("device", "ml_familiarity"):
        value["mix"][field] = {label or "not_recorded": sum(row[field] == label for row in retained)
                               for label in sorted({row[field] for row in retained})}
    for task in plan["tasks"]:
        counts = {outcome: sum(row[f"{task}_outcome"] == outcome for row in retained) for outcome in plan["outcomes"]}
        times = [float(row[f"{task}_seconds"]) for row in retained if row[f"{task}_outcome"] == "unassisted"]
        value["tasks"][task] = {"counts": counts, "participant_denominator": n,
                               "unassisted_fraction": counts["unassisted"] / n if n else None,
                               "unassisted_time_count": len(times),
                               "unassisted_median_seconds": statistics.median(times) if times else None}
    for field in plan["comprehension_fields"]:
        correct = sum(row[field] == "1" for row in retained)
        recorded = sum(row[field] in ("0", "1") for row in retained)
        value["comprehension"][field] = {"correct_before_help": correct, "recorded_answers": recorded,
                                         "missing_answers": n-recorded, "participant_denominator": n,
                                         "correct_fraction_all_retained": correct / n if n else None}
    for field in plan["rating_fields"]:
        ratings = [int(row[field]) for row in retained if row[field]]
        value["custom_ratings"][field] = {"response_count": len(ratings), "missing_count": n-len(ratings),
                                          "median": statistics.median(ratings) if ratings else None,
                                          "min": min(ratings) if ratings else None, "max": max(ratings) if ratings else None}
    counts = {task: value["tasks"][task]["counts"]["unassisted"] for task in ("t1", "t2")}
    counts.update({field: entry["correct_before_help"] for field, entry in value["comprehension"].items()})
    value["iteration_review_triggered"] = {key: count < plan["iteration_threshold_count"] if n == target else None
                                            for key, count in counts.items()}
    return value


def markdown(value):
    n = value["main_participants"]
    lines = ["# Usability aggregate summary", "", f"Status: **{value['status']}**. Retained main sessions: **{n}/{value['target_main_participants']}**.",
             f"Pilot rows excluded: {value['pilot_rows_excluded']}; main withdrawals excluded: {value['main_withdrawals_excluded']}.", "",
             "Partial sessions and technical failures remain in every main participant denominator.", "",
             "| Task | Unassisted / n | Assisted | Failed | Technical failure | Not attempted | Unassisted median seconds (count) |",
             "| --- | --- | --- | --- | --- | --- | --- |"]
    for task, item in value["tasks"].items():
        c = item["counts"]
        timing = "not estimable" if item["unassisted_median_seconds"] is None else f"{item['unassisted_median_seconds']:g} ({item['unassisted_time_count']})"
        lines.append(f"| {task.upper()} | {c['unassisted']}/{n} | {c['assisted']} | {c['failed']} | {c['technical_failure']} | {c['not_attempted']} | {timing} |")
    lines += ["", "| Comprehension item | Correct before help / n | Recorded answers | Missing | Review triggered at six? |",
              "| --- | --- | --- | --- | --- |"]
    for field, item in value["comprehension"].items():
        trigger = value["iteration_review_triggered"][field]
        lines.append(f"| {field} | {item['correct_before_help']}/{n} | {item['recorded_answers']} | {item['missing_answers']} | {'pending' if trigger is None else 'yes' if trigger else 'no'} |")
    lines += ["", "Navigation review triggers: " + ", ".join(f"{key}={'pending' if flag is None else 'yes' if flag else 'no'}" for key, flag in value["iteration_review_triggered"].items() if key in ("t1", "t2")), "",
              "| Custom rating (1–5; not SUS) | Responses | Missing | Median | Range |", "| --- | --- | --- | --- | --- |"]
    for field, item in value["custom_ratings"].items():
        lines.append(f"| {field} | {item['response_count']} | {item['missing_count']} | {item['median'] if item['median'] is not None else 'not estimable'} | {str(item['min'])+'–'+str(item['max']) if item['min'] is not None else 'not estimable'} |")
    lines += ["", "Device/ML-familiarity mix: " + json.dumps(value["mix"], ensure_ascii=False), "",
              value["interpretation"], "", "Add actual recruitment, deviations, observed issues, pilot changes and limitations using study/RESULTS_TEMPLATE.md. No participant codes or notes are exported here.", ""]
    return "\n".join(lines)


def summarize(directory, output):
    directory, output = private_directory(directory), Path(output).resolve()
    runs = (ROOT / "runs").resolve()
    if output == runs or not output.is_relative_to(runs):
        raise ValueError("Write aggregate drafts to a new ignored runs/ directory for manual review")
    freeze_path = directory / "protocol-freeze.json"
    record = json.loads(freeze_path.read_bytes())
    expected = {name: digest(ROOT / name) for name in FROZEN_FILES}
    if record["files_sha256"] != expected:
        raise ValueError("Study protocol, guides or analysis code changed after freeze; review a separate version/round")
    plan = protocol()
    if record["space_revision"] != plan["space_revision"]:
        raise ValueError("Frozen app revision changed")
    rows = load_rows(directory / "sessions.csv", plan)
    value = summarize_rows(rows, plan)
    value.update(protocol_version=plan["protocol_version"], space_revision=plan["space_revision"],
                 protocol_freeze_sha256=digest(freeze_path),
                 note="Automatic aggregate draft only; qualitative issues and recruitment must be reviewed manually.")
    output.mkdir(parents=True, exist_ok=False)
    (output / "summary.json").write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    (output / "summary.md").write_text(markdown(value), encoding="utf-8")
    return {"status": value["status"], "main_participants": value["main_participants"], "output": str(output)}


def check_demo():
    plan = protocol()
    with urllib.request.urlopen("https://huggingface.co/api/spaces/Moobakr/calorie-lab-fewer-sensors", timeout=20) as response:
        info = json.load(response)
    if info["sha"] != plan["space_revision"] or info["sdk"] != "static" or info["runtime"]["stage"] != "RUNNING":
        raise ValueError("Demo differs from the planned running revision; pause and review the study")
    return {"status": "running_revision_matches_protocol", "revision": info["sha"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("init", "freeze", "summarize"):
        command = sub.add_parser(name)
        command.add_argument("--directory", type=Path, required=True)
        if name == "summarize":
            command.add_argument("--output", type=Path, required=True)
    sub.add_parser("check-demo")
    args = parser.parse_args()
    try:
        if args.command == "init":
            result = initialize(args.directory)
        elif args.command == "freeze":
            result = freeze(args.directory)
        elif args.command == "summarize":
            result = summarize(args.directory, args.output)
        else:
            result = check_demo()
    except (ValueError, OSError, KeyError) as error:
        parser.exit(2, f"Study operation stopped: {error}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
