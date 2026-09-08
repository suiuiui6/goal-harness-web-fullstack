import json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_context_measurement_tool_reports_three_stages():
    out = ROOT / "artifacts" / "context-measurement.json"
    result = subprocess.run([sys.executable, "-B", "tools/measure_skill_context.py", "--root", ".", "--output", str(out)], cwd=ROOT)
    assert result.returncode in (0, 2)
    report = json.loads(out.read_text(encoding="utf-8"))
    assert set(report["stages"]) == {"S1", "S2", "S3"}
    assert report["encoding"] == "o200k_base"
