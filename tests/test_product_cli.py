import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_cli(*args):
    return subprocess.run([sys.executable, "-B", "-m", "goal_harness", *args], capture_output=True, text=True)


def test_cli_help_lists_product_commands():
    result = run_cli("--help")
    assert result.returncode == 0
    for command in ("validate", "capability-check", "delivery-audit"):
        assert command in result.stdout


def test_validate_delegates_to_candidate_goal_and_harness_validators():
    result = run_cli("validate", "--root", ".")
    assert result.returncode == 0
    assert "Goal validator" in result.stdout
    assert "Harness validator" in result.stdout


def test_capability_check_reports_audit_only_windows():
    result = run_cli("capability-check", "--root", ".")
    assert result.returncode == 0
    assert "audit-only-windows" in result.stdout


def test_delivery_audit_requires_workspace_and_reports_guard_result(tmp_path):
    guard = ROOT / "source" / "goal-enforcement" / "scripts" / "goal_guard.py"
    initialized = subprocess.run([
        sys.executable, "-B", str(guard), "initialize-state",
        "--workspace", str(tmp_path), "--goal", "CI audit fixture",
        "--mode", "maintenance", "--start-layer", "4",
        "--rationale", "isolated test state",
    ], capture_output=True, text=True)
    assert initialized.returncode == 0, initialized.stdout + initialized.stderr
    result = run_cli("delivery-audit", "--root", str(tmp_path), "--guard", str(guard))
    assert result.returncode == 0
    assert "goal state audit" in result.stdout.lower()
