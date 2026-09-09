import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "check_rule_ownership.py"
MANIFEST = ROOT / "tools" / "rule-ownership.json"


def run_check(manifest, stage="A"):
    return subprocess.run(
        [
            sys.executable,
            "-B",
            str(TOOL),
            "--root",
            str(ROOT),
            "--manifest",
            str(manifest),
            "--stage",
            stage,
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def test_stage_a_accepts_deferred_canonical_files():
    result = run_check(MANIFEST, "A")
    assert result.returncode == 0, result.stdout + result.stderr


def test_duplicate_authority_is_rejected(tmp_path):
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    duplicate = dict(data["rules"][0])
    duplicate["canonical"] = "source/goal/SKILL.md"
    data["rules"].append(duplicate)
    manifest = tmp_path / "ownership.json"
    manifest.write_text(json.dumps(data), encoding="utf-8")
    result = run_check(manifest, "A")
    assert result.returncode == 1
    assert "duplicate rule_id" in result.stderr


def test_dependency_cycle_is_rejected(tmp_path):
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    data["rules"][0]["depends_on"] = ["guard.state-write"]
    next(
        rule for rule in data["rules"] if rule["rule_id"] == "guard.state-write"
    )["depends_on"].append("goal.classification")
    manifest = tmp_path / "ownership.json"
    manifest.write_text(json.dumps(data), encoding="utf-8")
    result = run_check(manifest, "A")
    assert result.returncode == 1
    assert "dependency cycle" in result.stderr


def test_stage_d_requires_all_canonical_and_consumer_files(tmp_path):
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    data["rules"][0]["consumers"].append("source/missing-consumer.md")
    manifest = tmp_path / "ownership.json"
    manifest.write_text(json.dumps(data), encoding="utf-8")
    result = run_check(manifest, "D")
    assert result.returncode == 1
    assert "missing required path" in result.stderr
