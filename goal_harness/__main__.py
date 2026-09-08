import argparse
import subprocess
import sys
from pathlib import Path

def run(label: str, command: list[str], cwd: Path) -> int:
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
    print(f"{label}: {'PASS' if result.returncode == 0 else 'FAIL'}")
    if result.stdout.strip(): print(result.stdout.strip())
    if result.stderr.strip(): print(result.stderr.strip(), file=sys.stderr)
    return result.returncode

def main() -> int:
    parser = argparse.ArgumentParser(prog="goal-harness", description="Evidence-first delivery governance for AI coding agents")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("validate", "capability-check", "delivery-audit"):
        command = commands.add_parser(name); command.add_argument("--root", default=".")
    args = parser.parse_args(); root = Path(args.root).resolve(); python = sys.executable
    if args.command == "validate":
        goal = run("Goal validator", [python, "-B", "source/goal/scripts/validate_goal_skill.py", "source/goal"], root)
        harness = run("Harness validator", [python, "-B", "source/harness-engineering/scripts/validate_harness_skill.py", "source/harness-engineering"], root)
        return goal or harness
    guard = root / "source" / "goal-enforcement" / "scripts" / "goal_guard.py"
    if args.command == "capability-check": return run("Guard capability", [python, "-B", str(guard), "capabilities"], root)
    return run("Delivery audit", [python, "-B", str(guard), "audit", "--workspace", str(root)], root)

if __name__ == "__main__": raise SystemExit(main())
