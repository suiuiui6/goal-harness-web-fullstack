import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_source_integration_manifest_has_goal_and_harness_owners():
    manifest = json.loads((ROOT / "tools/source-integrations.json").read_text(encoding="utf-8"))
    assert manifest["integration_repo"] == "suiuiui6/goal-harness-web-fullstack"
    assert {item["name"] for item in manifest["sources"]} == {"goal", "harness-engineering"}
    for item in manifest["sources"]:
        assert item["repository"].startswith("https://github.com/suiuiui6/")
        assert item["ref"]
        assert item["canonical_path"]
        assert item["integration_path"]
        assert item["compatibility"]

def test_source_drift_checker_passes_current_pinned_snapshot():
    result = subprocess.run([sys.executable, "-B", "tools/check_source_integrations.py", "--root", "."], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS" in result.stdout
