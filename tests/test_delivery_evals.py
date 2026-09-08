import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_delivery_cases_keep_all_wf_and_sc_ids():
    cases = json.loads((ROOT / "tests" / "delivery-cases.json").read_text(encoding="utf-8"))
    ids = {item["id"] for item in cases}
    assert {f"WF-{i:02d}" for i in range(1, 18)} <= ids
    assert {f"SC-{i:02d}" for i in range(1, 9)} <= ids


def test_contract_eval_reports_not_run_levels_without_events():
    output = ROOT / "artifacts" / "evals" / "test-contract.json"
    result = subprocess.run(
        [sys.executable, "-B", "tools/delivery_evals.py", "--cases", "tests/delivery-cases.json",
         "--level", "contract", "--output", str(output)],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert result.returncode == 0
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["level"] == "contract"
    assert report["status"] in {"pass", "fail"}
    assert report["command"]
    assert report["exit_code"] == 0
    assert report["limitations"]
    assert "observed" not in report["provenance"]
