"""Allowlisted Docker Space package from the frozen final selection; no training."""

import json
from pathlib import Path
import shutil
import zipfile

from .config import ROOT, file_hash
from .data import write_json
from .evaluation import load_development

LABELS = {"Gender":("Recorded gender", "category"), "Age":("Age", "years"), "Height":("Height", "cm"),
          "Weight":("Weight", "kg"), "Duration":("Session duration", "minutes"),
          "Heart_Rate":("Session heart rate", "bpm"), "Body_Temp":("Recorded temperature", "°C")}


def package_demo(destination, config, manifest):
    destination = Path(destination).resolve()
    if not destination.is_relative_to((ROOT/"runs").resolve()) or destination == (ROOT/"runs").resolve() or destination.exists():
        raise ValueError("Choose a new demo package directory under ignored runs/")
    selection_path = ROOT/"docs/FINAL_SELECTION.json"
    results_path = ROOT/"docs/FINAL_EVALUATION_METRICS.json"
    selected = json.loads(selection_path.read_bytes())
    results = json.loads(results_path.read_bytes())
    if file_hash(selection_path) != results["selection_manifest_sha256"] or results["verification"]["status"] != "passed":
        raise ValueError("Final selection/evaluation snapshot failed verification")
    source = ROOT/"runs/input-comparison-v1"
    if file_hash(source/"metrics.json") != selected["source_runs_sha256"]["comparison"]:
        raise ValueError("Frozen source model run changed")
    development = load_development(ROOT/config["processed_dir"], ROOT/config["split_dir"], config, manifest, "full")
    fields = {}
    for column in manifest["columns"]:
        name = column["name"]
        if column["role"] != "input":
            continue
        label, unit = LABELS[name]
        fields[name] = {"label":label,"unit":unit}
        if column["type"] == "category":
            fields[name]["categories"] = column["categories"]
        else:
            values = development.X[name]
            fields[name].update(min=float(values.min()),max=float(values.max()),integer=column["type"]=="integer")
    systems = {}
    for mode in config["feature_sets"]:
        name = f"xgboost_{mode}"
        frozen = next(row for row in selected["systems"] if row["name"]==name)
        result = next(row for row in results["results"] if row["name"]==name)
        binding = frozen["threshold"]
        if (binding["model_sha256"] != file_hash(source/binding["model_artifact"])
                or binding["model_sha256"] != result["model_sha256"]
                or frozen["input_columns"] != config["feature_sets"][mode]
                or binding["threshold"] != result["interval_threshold"]):
            raise ValueError("Frozen predictor/interval binding changed")
        systems[mode] = {"name":name,"artifact":binding["model_artifact"],"model_sha256":binding["model_sha256"],
            "input_columns":frozen["input_columns"],"threshold":binding["threshold"],
            "test_mae":result["test"]["overall"]["mae"],"test_coverage":result["test"]["overall"]["coverage"],
            "duration_groups":[row for row in result["test"]["groups"] if row["axis"]=="duration"]}
    destination.mkdir(parents=True)
    for folder in ("bundle","demo","calorie_estimation"):
        (destination/folder).mkdir()
    (destination/"calorie_estimation/__init__.py").write_text("",encoding="utf-8")
    shutil.copyfile(ROOT/"calorie_estimation/demo_app.py",destination/"calorie_estimation/demo_app.py")
    for name in ("index.html","style.css","app.js"):
        shutil.copyfile(ROOT/"demo"/name,destination/"demo"/name)
    for name,target in (("Dockerfile","Dockerfile"),("SPACE_README.md","README.md")):
        shutil.copyfile(ROOT/"demo"/name,destination/target)
    for system in systems.values():
        shutil.copyfile(source/system["artifact"],destination/"bundle"/system["artifact"])
    dependencies = {line.split("==")[0]:line for line in (ROOT/"requirements.lock.txt").read_text().splitlines() if "==" in line}
    runtime = ("numpy","pandas","scikit-learn","xgboost","scipy","joblib","threadpoolctl","python-dateutil","pytz","tzdata","six")
    (destination/"requirements.txt").write_text("\n".join([dependencies[name] for name in runtime]+["waitress==3.0.2"])+"\n",encoding="utf-8")
    value = {"schema_version":1,"primary_mode":"heart_rate","fields":fields,"systems":systems,
        "final_selection_sha256":file_hash(selection_path),"final_evaluation_sha256":file_hash(results_path),
        "intervals_sha256":selected["intervals_sha256"],"range_source":"development observations only",
        "examples":[{"label":"15-minute session","values":{"Gender":"female","Age":35,"Height":165,"Weight":62,"Duration":15,"Heart_Rate":98,"Body_Temp":40.0}},
                    {"label":"Longer session","values":{"Gender":"male","Age":60,"Height":180,"Weight":85,"Duration":28,"Heart_Rate":115,"Body_Temp":40.7}}]}
    write_json(destination/"bundle/manifest.json",value)
    write_json(destination/"PACKAGE_MANIFEST.json", {"status":"prepared","training_fits":0,"test_scoring_runs":0,
        "files_sha256":{path.relative_to(destination).as_posix():file_hash(path) for path in sorted(destination.rglob("*")) if path.is_file()}})
    archive = destination.with_suffix(".zip")
    with zipfile.ZipFile(archive,"w",zipfile.ZIP_DEFLATED) as zipped:
        for path in sorted(destination.rglob("*")):
            if path.is_file():
                zipped.write(path,path.relative_to(destination).as_posix())
    return {"status":"passed","directory":str(destination),"archive":str(archive),"models":4,"training_fits":0}


if __name__ == "__main__":
    import argparse
    from .config import load_project
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,default=ROOT/"runs/demo-space-v1")
    args=parser.parse_args()
    config,manifest=load_project()
    print(json.dumps(package_demo(args.output,config,manifest),indent=2))
