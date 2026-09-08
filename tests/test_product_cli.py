import subprocess
import sys


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


def test_delivery_audit_requires_workspace_and_reports_guard_result():
    result = run_cli("delivery-audit", "--root", ".")
    assert result.returncode == 0
    assert "goal state audit" in result.stdout.lower()
