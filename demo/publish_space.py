"""Publish the allowlisted demo package to Moobakr's dedicated Space."""

import argparse
import hashlib
import json
from pathlib import Path

REPO = "Moobakr/calorie-lab-fewer-sensors"


def verify(folder, expected, sdk="docker"):
    manifest_path=folder/"PACKAGE_MANIFEST.json"
    if hashlib.sha256(manifest_path.read_bytes()).hexdigest()!=expected:
        raise ValueError("Package manifest differs from the reviewed package")
    manifest=json.loads(manifest_path.read_bytes())
    if manifest.get("hosting_sdk", "docker") != sdk:
        raise ValueError("Package hosting SDK differs from the requested Space SDK")
    allowed=set(manifest["files_sha256"])|{"PACKAGE_MANIFEST.json"}
    actual={path.relative_to(folder).as_posix() for path in folder.rglob("*") if path.is_file()}
    if actual!=allowed:
        raise ValueError("Upload directory contains extra or missing files")
    for name,digest in manifest["files_sha256"].items():
        path=folder/name
        if not path.resolve().is_relative_to(folder.resolve()) or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
            raise ValueError("Package hash mismatch")
    if any(name.endswith((".csv",".npz",".ipynb",".env")) or name.startswith(("data/",".git/",".venv/")) for name in allowed):
        raise ValueError("Package contains excluded research or credential files")
    if sdk == "static" and allowed != {"README.md", "index.html", "style.css", "app.js", "engine.js", "metadata.json",
                                        "PACKAGE_MANIFEST.json", *(f"models/{mode}.json" for mode in ("duration","basic","heart_rate","full"))}:
        raise ValueError("Static package must contain exactly the reviewed browser assets and JSON models")
    return sorted(allowed)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--folder",type=Path,required=True)
    parser.add_argument("--expected-manifest-sha",required=True)
    parser.add_argument("--receipt",type=Path,required=True)
    parser.add_argument("--sdk",choices=("docker","static"),default="docker")
    parser.add_argument("--check-only",action="store_true")
    args=parser.parse_args()
    files=verify(args.folder,args.expected_manifest_sha,args.sdk)
    if args.check_only:
        print(f"Offline checks passed: {len(files)} allowlisted files for {REPO}. No network writes.")
        return
    from huggingface_hub import HfApi
    from huggingface_hub.errors import HfHubHTTPError
    api=HfApi()
    if api.whoami()["name"].lower()!="moobakr":
        raise ValueError("Sign in as Moobakr before publishing")
    receipt={"repo_id":REPO,"package_manifest_sha256":args.expected_manifest_sha,"sdk":args.sdk}
    if args.receipt.exists():
        previous=json.loads(args.receipt.read_bytes())
        if any(previous.get(key)!=value for key,value in receipt.items()):
            raise ValueError("Previous deployment receipt belongs to another package")
        if api.space_info(REPO).sdk != args.sdk:
            raise ValueError("Existing Space SDK differs from the deployment receipt")
    else:
        # No hardware upgrade is requested. Refuse to overwrite a pre-existing Space.
        try:
            api.create_repo(repo_id=REPO,repo_type="space",space_sdk=args.sdk,private=False,exist_ok=False)
        except HfHubHTTPError as error:
            if error.response.status_code == 402:
                raise SystemExit("Hugging Face declined Space creation (HTTP 402). Docker/Gradio CPU hosting requires a paid plan. Use the prepared Static Space package for free browser inference. No files were uploaded.") from None
            raise
        args.receipt.write_text(json.dumps({**receipt,"status":"created_upload_pending"},indent=2)+"\n")
    commit=api.upload_folder(repo_id=REPO,repo_type="space",folder_path=str(args.folder),allow_patterns=files,
        commit_message="Deploy frozen calorie-label models with input tradeoffs and uncertainty")
    runtime=api.get_space_runtime(REPO)
    result={**receipt,"status":"uploaded_requires_verification","commit":commit.oid,
        "space_url":f"https://huggingface.co/spaces/{REPO}","runtime_stage":str(runtime.stage)}
    args.receipt.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))


if __name__=="__main__":
    main()
