#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from typing import Sequence


INTEGRATION_DEADLINE_SECONDS = 45.0
MAX_STAGE_TIMEOUT_SECONDS = 10.0
INTEGRATION_ENABLED = os.environ.get("GOAL_RUN_GUARD_INTEGRATION") == "1"
_integration_deadline = None


def run_stage(
    name: str,
    argv: Sequence[str],
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    if _integration_deadline is None:
        raise AssertionError("integration deadline was not initialized")
    remaining = _integration_deadline - time.monotonic()
    if remaining <= 0:
        raise AssertionError(
            f"stage={name} exceeded {INTEGRATION_DEADLINE_SECONDS:.3f}s"
        )
    stage_timeout = min(MAX_STAGE_TIMEOUT_SECONDS, remaining)
    try:
        return subprocess.run(
            argv,
            input=input_text,
            capture_output=True,
            text=True,
            check=False,
            timeout=stage_timeout,
        )
    except subprocess.TimeoutExpired as error:
        raise AssertionError(
            f"stage={name} exceeded {stage_timeout:.3f}s"
        ) from error


@unittest.skipUnless(
    INTEGRATION_ENABLED,
    "set GOAL_RUN_GUARD_INTEGRATION=1 to run goal guard integration",
)
class GoalGuardIntegrationTests(unittest.TestCase):
    def test_goal_guard_accepts_documented_bootstrap_layer0_state_sequence(self) -> None:
        global _integration_deadline
        _integration_deadline = time.monotonic() + INTEGRATION_DEADLINE_SECONDS

        guard = Path.home() / "plugins" / "goal-enforcement" / "scripts" / "goal_guard.py"
        if not guard.exists():
            self.skipTest(f"goal guard not installed at {guard}")

        base_state = {
            "schema_version": 1,
            "goal": "Bootstrap Layer 0 state-init rehearsal",
            "mode": "bootstrap",
            "start_layer": 0,
            "current_layer": 0,
            "classification": {
                "rationale": "Bootstrap execution confirmed; first Layer 0 governed mutation is next.",
                "confirmed": True,
                "confirmation_id": "layer0-sequence-confirmation",
            },
            "plan": {
                "required": False,
                "approved": False,
                "path": "",
            },
            "layers": {},
            "verification": {
                "status": "not-run",
                "command": "",
                "evidence": "",
                "verified_at": "",
                "mutation_seq": 0,
            },
            "closure": {
                "recorded": False,
                "evidence": None,
            },
            "enforcement_override": {
                "enabled": False,
                "reason": None,
                "authorized_by": None,
                "confirmation_id": None,
                "remaining_uses": 0,
            },
            "open_failures": [],
            "in_flight_mutations": [],
            "last_mutation_seq": 0,
            "scope_result": "accepted",
            "operation_state": "in_progress",
        }

        scratch_root = Path(__file__).resolve().parent
        scratch_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch_root) as temp_dir:
            workspace = Path(temp_dir)
            classified = dict(base_state)
            classified["phase"] = "classified"
            planned = json.loads(json.dumps(classified))
            planned["phase"] = "planned"

            planned_file = workspace / "planned.json"
            executing = json.loads(json.dumps(planned))
            executing["phase"] = "executing"
            planned_file.write_text(json.dumps(planned, indent=2), encoding="utf-8")
            executing_file = workspace / "executing.json"
            executing_file.write_text(json.dumps(executing, indent=2), encoding="utf-8")

            initialization = run_stage(
                "initialize-state",
                [
                    sys.executable,
                    str(guard),
                    "initialize-state",
                    "--workspace",
                    str(workspace),
                    "--goal",
                    base_state["goal"],
                    "--mode",
                    "bootstrap",
                    "--start-layer",
                    "0",
                    "--rationale",
                    base_state["classification"]["rationale"],
                    "--confirmation-id",
                    "layer0-sequence-confirmation",
                ],
            )
            self.assertEqual(
                0,
                initialization.returncode,
                initialization.stderr or initialization.stdout,
            )

            first_transition = run_stage(
                "write-state-planned",
                [
                    sys.executable,
                    str(guard),
                    "write-state",
                    "--workspace",
                    str(workspace),
                    "--file",
                    str(planned_file),
                ],
            )
            self.assertEqual(
                0,
                first_transition.returncode,
                first_transition.stderr or first_transition.stdout,
            )
            self.assertIn(
                "PASS: goal state transition recorded",
                first_transition.stdout,
            )

            second_transition = run_stage(
                "write-state-executing",
                [
                    sys.executable,
                    str(guard),
                    "write-state",
                    "--workspace",
                    str(workspace),
                    "--file",
                    str(executing_file),
                ],
            )
            self.assertEqual(
                0,
                second_transition.returncode,
                second_transition.stderr or second_transition.stdout,
            )
            self.assertIn(
                "PASS: goal state transition recorded",
                second_transition.stdout,
            )

            tool_payload = json.dumps(
                {
                    "cwd": str(workspace),
                    "tool_name": "apply_patch",
                    "tool_input": {
                        "target": str(
                            workspace / "work" / "layer-0-capability-boundary.md"
                        ),
                    },
                }
            )
            pre_tool = run_stage(
                "pre-tool-use",
                [
                    sys.executable,
                    str(guard),
                    "pre-tool-use",
                    "--workspace",
                    str(workspace),
                ],
                input_text=tool_payload,
            )
            self.assertEqual(
                0,
                pre_tool.returncode,
                pre_tool.stderr or pre_tool.stdout,
            )
            self.assertNotIn('"decision": "block"', pre_tool.stdout)

            post_tool = run_stage(
                "post-tool-use",
                [
                    sys.executable,
                    str(guard),
                    "post-tool-use",
                    "--workspace",
                    str(workspace),
                ],
                input_text=tool_payload,
            )
            self.assertEqual(
                0,
                post_tool.returncode,
                post_tool.stderr or post_tool.stdout,
            )

            audit = run_stage(
                "audit",
                [
                    sys.executable,
                    str(guard),
                    "audit",
                    "--workspace",
                    str(workspace),
                ],
            )
            self.assertEqual(0, audit.returncode, audit.stderr or audit.stdout)
            self.assertIn("PASS: goal state audit", audit.stdout)


if __name__ == "__main__":
    unittest.main()
