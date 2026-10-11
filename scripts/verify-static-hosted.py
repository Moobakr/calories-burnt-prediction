"""Read-only verification of the public Static Space and served model assets."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import tempfile
import urllib.request
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
REPO = "Moobakr/calorie-lab-fewer-sensors"


def read(url):
    with urllib.request.urlopen(url, timeout=45) as response:
        assert response.status == 200
        return response.read()


def verify_hosted(folder):
    info = json.loads(read(f"https://huggingface.co/api/spaces/{REPO}"))
    assert info["sdk"] == "static" and info["runtime"]["stage"] == "RUNNING", info.get("runtime")
    host = info["host"].rstrip("/")
    assert host == "https://moobakr-calorie-lab-fewer-sensors.static.hf.space", host
    manifest_bytes = (folder / "PACKAGE_MANIFEST.json").read_bytes()
    package = json.loads(manifest_bytes)
    expected = {**package["files_sha256"], "PACKAGE_MANIFEST.json":hashlib.sha256(manifest_bytes).hexdigest()}
    names = sorted(expected)
    def download(name):
        data = read(f"https://huggingface.co/spaces/{REPO}/resolve/{info['sha']}/{name}")
        assert hashlib.sha256(data).hexdigest() == expected[name], name
        return name, data
    with ThreadPoolExecutor(max_workers=4) as pool:
        files = dict(pool.map(download, names))
    def check_asset(name):
        data = read(f"{host}/{name}")
        assert hashlib.sha256(data).hexdigest() == expected[name], name
        return name
    served_names = [name for name in names if name not in ("README.md", "index.html")]
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(check_asset, served_names))
    # Static Spaces inject a creator-ID configuration script into HTML and
    # render Markdown as HTML. Check the known bootstrap, then compare HTML.
    html = read(host + "/").decode("utf-8")
    assert read(host + "/index.html").decode("utf-8") == html
    pattern = r'<head><script>window\.huggingface=\{variables:(\{[^<>]*\})\};</script>'
    injection = re.search(pattern, html)
    assert injection, "Unexpected provider HTML transformation"
    variables = json.loads(injection.group(1))
    assert set(variables) == {"SPACE_CREATOR_USER_ID"}
    assert re.fullmatch(r"[0-9a-f]{24}", variables["SPACE_CREATOR_USER_ID"])
    normalized = html[:injection.start()] + "<head>" + html[injection.end():]
    assert normalized.encode("utf-8") == files["index.html"], "Hosted page differs beyond the verified provider bootstrap"
    tree = json.loads(read(f"https://huggingface.co/api/spaces/{REPO}/tree/{info['sha']}?recursive=true"))
    repo_files = {entry["path"] for entry in tree if entry["type"] == "file"}
    assert repo_files == set(expected) | {".gitattributes"}, repo_files
    helper = importlib.util.spec_from_file_location("static_checks", ROOT / "scripts/verify-static.py")
    checks = importlib.util.module_from_spec(helper)
    helper.loader.exec_module(checks)
    with tempfile.TemporaryDirectory(prefix="hosted-static-") as temp:
        downloaded = Path(temp)
        for name, data in files.items():
            path = downloaded / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        report = checks.verify(downloaded)
    report.update(hosted_deployment="verified: public Static Space RUNNING; served inference assets match reviewed package",
                  verified_at_utc=datetime.now(timezone.utc).isoformat(),
                  hosted_revision=info["sha"], host=host, space_url=f"https://huggingface.co/spaces/{REPO}",
                  pinned_repository_file_digests_verified=len(files), served_file_digests_verified=len(served_names),
                  hosted_html_matches_after_verified_provider_creator_id_script=True,
                  public_repository_file_allowlist_verified=True,
                  browser_visual_check="unavailable: browser inventory returned no enabled browsers; rendered layout and interaction not verified")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--folder", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    report = verify_hosted(args.folder)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
