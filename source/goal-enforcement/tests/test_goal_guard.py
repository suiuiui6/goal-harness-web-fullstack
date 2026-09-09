import importlib.util
import json
from concurrent.futures import ThreadPoolExecutor
import sys
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "scripts" / "goal_guard.py"
SPEC = importlib.util.spec_from_file_location("goal_guard", MODULE_PATH)
goal_guard = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = goal_guard
SPEC.loader.exec_module(goal_guard)


def state(**updates):
    value = {
        "schema_version": 1,
        "goal": "Ship a governed project",
        "mode": "maintenance",
        "phase": "executing",
        "start_layer": 6,
        "current_layer": 6,
        "classification": {"confirmed": True, "rationale": "Local feature"},
        "plan": {"required": False, "approved": False, "path": None},
        "layers": {},
        "verification": {
            "status": "missing",
            "command": None,
            "evidence": None,
            "verified_at": None,
        },
        "closure": {"recorded": False, "evidence": None},
        "open_failures": [],
        "in_flight_mutations": [],
        "last_mutation_seq": 0,
        "enforcement_override": {
            "enabled": False,
            "reason": None,
            "authorized_by": None,
            "confirmation_id": None,
            "remaining_uses": 0,
        },
        "scope_result": "accepted",
        "operation_state": "in_progress",
    }
    value.update(updates)
    return value


class ToolDecisionTests(unittest.TestCase):
    def test_payload_workspace_resolves_nearest_active_ancestor(self):
        project = (Path.cwd() / "nested-governed-project").resolve()
        child = project / "src" / "feature"

        def present(path):
            return path == project

        with patch.object(goal_guard, "state_file_present", side_effect=present):
            resolved = goal_guard.payload_workspace({"cwd": str(child)})

        self.assertEqual(project, resolved)

    def test_no_goal_state_allows_mutation(self):
        decision = goal_guard.evaluate_tool_call(None, "apply_patch", {})
        self.assertTrue(decision.allowed)
        self.assertEqual("inactive", decision.code)

    def test_corrupt_active_state_blocks_mutation_but_allows_reads(self):
        blocked = goal_guard.evaluate_tool_call(
            None, "apply_patch", {}, state_error="invalid JSON"
        )
        allowed = goal_guard.evaluate_tool_call(
            None, "read_file", {}, state_error="invalid JSON"
        )
        self.assertFalse(blocked.allowed)
        self.assertEqual("invalid-state", blocked.code)
        self.assertTrue(allowed.allowed)

    def test_intake_blocks_mutation(self):
        decision = goal_guard.evaluate_tool_call(
            state(phase="intake"), "apply_patch", {"patch": "..."}
        )
        self.assertFalse(decision.allowed)
        self.assertEqual("classification-required", decision.code)

    def test_unconfirmed_bootstrap_blocks_mutation(self):
        decision = goal_guard.evaluate_tool_call(
            state(
                mode="bootstrap",
                phase="classified",
                classification={"confirmed": False, "rationale": "New system"},
            ),
            "apply_patch",
            {},
        )
        self.assertFalse(decision.allowed)
        self.assertEqual("bootstrap-confirmation-required", decision.code)

    def test_unapproved_required_plan_blocks_mutation(self):
        decision = goal_guard.evaluate_tool_call(
            state(
                phase="classified",
                plan={"required": True, "approved": False, "path": None},
            ),
            "shell_command",
            {"command": "npm install express"},
        )
        self.assertFalse(decision.allowed)
        self.assertEqual("plan-approval-required", decision.code)

    def test_executing_phase_allows_mutation(self):
        decision = goal_guard.evaluate_tool_call(
            state(), "apply_patch", {"patch": "..."}
        )
        self.assertTrue(decision.allowed)

    def test_read_only_command_is_allowed_before_classification(self):
        decision = goal_guard.evaluate_tool_call(
            state(phase="intake"),
            "shell_command",
            {"command": "git status --short"},
        )
        self.assertTrue(decision.allowed)

    def test_chained_read_command_is_treated_as_mutation(self):
        decision = goal_guard.evaluate_tool_call(
            state(phase="intake"),
            "shell_command",
            {"command": "git status; Remove-Item app.py"},
        )
        self.assertFalse(decision.allowed)
        self.assertEqual("classification-required", decision.code)

    def test_chained_guard_command_is_treated_as_mutation(self):
        decision = goal_guard.evaluate_tool_call(
            state(phase="intake"),
            "shell_command",
            {"command": "python goal_guard.py audit; Remove-Item app.py"},
        )
        self.assertFalse(decision.allowed)
        self.assertEqual("classification-required", decision.code)

    def test_direct_guard_command_is_allowed(self):
        decision = goal_guard.evaluate_tool_call(
            state(phase="intake"),
            "shell_command",
            {"command": f"python {MODULE_PATH} audit --workspace C:/repo"},
        )
        self.assertTrue(decision.allowed)

    def test_capabilities_is_a_non_mutating_guard_command(self):
        absolute_script = MODULE_PATH.resolve()
        commands = (
            f'python "{absolute_script}" capabilities',
            f'python "{absolute_script.as_posix()}" capabilities',
        )
        for command in commands:
            with self.subTest(command=command):
                self.assertTrue(goal_guard.is_guard_command(command))
                self.assertFalse(
                    goal_guard.is_mutation(
                        "shell_command", {"command": command}
                    )
                )

    def test_untrusted_same_named_guard_script_is_not_exempt(self):
        decision = goal_guard.evaluate_tool_call(
            state(phase="intake"),
            "shell_command",
            {"command": "python C:/evil/goal_guard.py audit"},
        )
        self.assertFalse(decision.allowed)
        self.assertEqual("classification-required", decision.code)

    def test_guard_lock_path_is_protected(self):
        decision = goal_guard.evaluate_tool_call(
            state(),
            "shell_command",
            {"command": "Remove-Item .codex/goal-state.lock"},
        )
        self.assertFalse(decision.allowed)
        self.assertEqual("protected-state", decision.code)

    def test_guard_lock_path_variants_are_protected(self):
        for target in (".codex/./goal-state.lock", ".codex//goal-state.lock"):
            with self.subTest(target=target):
                decision = goal_guard.evaluate_tool_call(
                    state(), "shell_command", {"command": f"Remove-Item {target}"}
                )
                self.assertFalse(decision.allowed)
                self.assertEqual("protected-state", decision.code)

    def test_semantically_invalid_state_blocks_mutation(self):
        malformed = state(schema_version=2, last_mutation_seq="bad")
        decision = goal_guard.evaluate_tool_call(malformed, "apply_patch", {})
        self.assertFalse(decision.allowed)
        self.assertEqual("invalid-state", decision.code)

    def test_command_substitution_is_treated_as_mutation(self):
        commands = (
            "Get-Content $(Set-Content -Path app.py -Value owned)",
            "git status $(touch app.py)",
            "git status `touch app.py`",
            "python goal_guard.py audit --workspace $(touch app.py)",
        )
        for command in commands:
            with self.subTest(command=command):
                decision = goal_guard.evaluate_tool_call(
                    state(phase="intake"), "shell_command", {"command": command}
                )
                self.assertFalse(decision.allowed)

    def test_malformed_layer_record_blocks_without_crashing(self):
        malformed = state(
            phase="verified",
            layers={"6": "bad"},
            verification={
                "status": "pass",
                "command": "python -m unittest",
                "evidence": "tests passed",
                "verified_at": "2026-07-11T12:00:00Z",
                "mutation_seq": 0,
            },
        )
        decision = goal_guard.evaluate_tool_call(malformed, "apply_patch", {})
        self.assertFalse(decision.allowed)
        self.assertEqual("invalid-state", decision.code)

    def test_redirection_and_git_output_flags_are_mutations(self):
        commands = (
            "Get-Content source.txt > app.py",
            "git status --porcelain=v1 > state.txt",
            "git diff --output=app.patch",
            "git show -o out",
            "git branch -D old-branch",
            "git branch newbranch",
            "git branch -Mnewbranch",
        )
        for command in commands:
            with self.subTest(command=command):
                decision = goal_guard.evaluate_tool_call(
                    state(phase="intake"), "shell_command", {"command": command}
                )
                self.assertFalse(decision.allowed)

    def test_malformed_nested_state_blocks_without_crashing(self):
        malformed = state(enforcement_override="bad", plan="bad")
        decision = goal_guard.evaluate_tool_call(malformed, "apply_patch", {})
        self.assertFalse(decision.allowed)
        self.assertEqual("invalid-state", decision.code)

    def test_completion_requires_verification_and_closure(self):
        decision = goal_guard.evaluate_tool_call(
            state(), "update_goal", {"status": "complete"}
        )
        self.assertFalse(decision.allowed)
        self.assertEqual("verification-required", decision.code)

    def test_completion_allowed_with_passing_verification_and_closure(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            fingerprint = goal_guard.workspace_fingerprint_record(workspace)
            command = "python -m unittest"
            decision = goal_guard.evaluate_tool_call(
                state(
                    phase="verified",
                    layers={"6": {"status": "pass", "evidence": "layer 6 verified"}},
                    verification={
                        "status": "pass",
                        "command": command,
                        "command_sha256": goal_guard.sha256_text(command),
                        "evidence": "12 tests passed",
                        "verified_at": "2026-07-11T12:00:00Z",
                        "mutation_seq": 0,
                        "workspace_fingerprint": fingerprint,
                    },
                    closure={
                        "recorded": True,
                        "evidence": "closure record",
                        "workspace_fingerprint": fingerprint,
                    },
                ),
                "update_goal",
                {"status": "complete"},
                workspace=workspace,
            )
            self.assertTrue(decision.allowed)

    def test_completion_without_workspace_fingerprint_is_rejected(self):
        decision = goal_guard.evaluate_tool_call(
            state(
                phase="complete",
                layers={"6": {"status": "pass", "evidence": "layer 6 verified"}},
                verification={
                    "status": "pass",
                    "command": "python -m unittest",
                    "command_sha256": goal_guard.sha256_text("python -m unittest"),
                    "evidence": "12 tests passed",
                    "verified_at": "2026-07-11T12:00:00Z",
                    "mutation_seq": 0,
                },
                closure={"recorded": True, "evidence": "closure record"},
                operation_state="maintenance_continues",
            ),
            "update_goal",
            {"status": "complete"},
        )
        self.assertFalse(decision.allowed)
        self.assertEqual("audit-failed", decision.code)

    def test_override_with_multiple_remaining_uses_is_rejected(self):
        decision = goal_guard.evaluate_tool_call(
            state(
                phase="intake",
                enforcement_override={
                    "enabled": True,
                    "reason": "Emergency",
                    "authorized_by": "user",
                    "confirmation_id": "confirm-1",
                    "remaining_uses": 2,
                },
            ),
            "apply_patch",
            {},
        )
        self.assertFalse(decision.allowed)
        self.assertEqual("invalid-state", decision.code)

    def test_string_false_override_enabled_is_rejected(self):
        decision = goal_guard.evaluate_tool_call(
            state(
                phase="intake",
                enforcement_override={
                    "enabled": "false",
                    "reason": "Emergency",
                    "authorized_by": "user",
                    "confirmation_id": "confirm-1",
                    "remaining_uses": 1,
                },
            ),
            "apply_patch",
            {},
        )
        self.assertFalse(decision.allowed)
        self.assertEqual("invalid-state", decision.code)

    def test_non_object_tool_input_is_rejected(self):
        decision = goal_guard.evaluate_tool_call(state(), "apply_patch", ["x"])
        self.assertFalse(decision.allowed)
        self.assertEqual("invalid-input", decision.code)

    def test_override_requires_a_nonempty_reason(self):
        invalid = goal_guard.evaluate_tool_call(
            state(
                phase="intake",
                enforcement_override={
                    "enabled": True,
                    "reason": "  ",
                    "authorized_by": "user",
                    "confirmation_id": "confirm-1",
                    "remaining_uses": 1,
                },
            ),
            "apply_patch",
            {},
        )
        valid = goal_guard.evaluate_tool_call(
            state(
                phase="intake",
                enforcement_override={
                    "enabled": True,
                    "reason": "User-authorized emergency repair",
                    "authorized_by": "user",
                    "confirmation_id": "confirm-1",
                    "remaining_uses": 1,
                },
            ),
            "apply_patch",
            {},
        )
        self.assertFalse(invalid.allowed)
        self.assertTrue(valid.allowed)
        self.assertEqual("override", valid.code)


    def test_malformed_override_counter_is_rejected_without_crashing(self):
        decision = goal_guard.evaluate_tool_call(
            state(
                phase="intake",
                enforcement_override={
                    "enabled": True,
                    "reason": "Emergency",
                    "authorized_by": "user",
                    "confirmation_id": "confirm-1",
                    "remaining_uses": "not-a-number",
                },
            ),
            "apply_patch",
            {},
        )
        self.assertFalse(decision.allowed)
        self.assertEqual("invalid-state", decision.code)

    def test_numeric_string_override_counter_is_rejected(self):
        decision = goal_guard.evaluate_tool_call(
            state(
                phase="intake",
                enforcement_override={
                    "enabled": True,
                    "reason": "Emergency",
                    "authorized_by": "user",
                    "confirmation_id": "confirm-1",
                    "remaining_uses": "1",
                },
            ),
            "apply_patch",
            {},
        )
        self.assertFalse(decision.allowed)

    def test_override_without_user_authorization_is_rejected(self):
        decision = goal_guard.evaluate_tool_call(
            state(
                phase="intake",
                enforcement_override={
                    "enabled": True,
                    "reason": "Agent wants to move faster",
                    "authorized_by": "agent",
                    "confirmation_id": "self-issued",
                    "remaining_uses": 1,
                },
            ),
            "apply_patch",
            {},
        )
        self.assertFalse(decision.allowed)

    def test_override_cannot_modify_protected_goal_state(self):
        decision = goal_guard.evaluate_tool_call(
            state(
                enforcement_override={
                    "enabled": True,
                    "reason": "Emergency",
                    "authorized_by": "user",
                    "confirmation_id": "confirm-1",
                    "remaining_uses": 1,
                }
            ),
            "apply_patch",
            {"patch": "*** Update File: .codex/goal-state.json"},
        )
        self.assertFalse(decision.allowed)
        self.assertEqual("protected-state", decision.code)

    def test_direct_goal_state_edits_are_blocked(self):
        decision = goal_guard.evaluate_tool_call(
            state(),
            "apply_patch",
            {"patch": "*** Update File: .codex/goal-state.json"},
        )
        self.assertFalse(decision.allowed)
        self.assertEqual("protected-state", decision.code)

    def test_open_failure_blocks_completion(self):
        decision = goal_guard.evaluate_tool_call(
            state(
                phase="verified",
                open_failures=[{"id": "failure-1", "status": "open"}],
                verification={
                    "status": "pass",
                    "command": "python -m unittest",
                    "evidence": "12 tests passed",
                    "verified_at": "2026-07-11T12:00:00Z",
                    "mutation_seq": 0,
                },
                closure={"recorded": True, "evidence": "closure record"},
            ),
            "update_goal",
            {"status": "complete"},
        )
        self.assertFalse(decision.allowed)
        self.assertEqual("open-failure", decision.code)

    def test_stale_verification_after_mutation_blocks_completion(self):
        decision = goal_guard.evaluate_tool_call(
            state(
                phase="verified",
                last_mutation_seq=4,
                verification={
                    "status": "pass",
                    "command": "python -m unittest",
                    "evidence": "12 tests passed",
                    "verified_at": "2026-07-11T12:00:00Z",
                    "mutation_seq": 3,
                },
                closure={"recorded": True, "evidence": "closure record"},
            ),
            "update_goal",
            {"status": "complete"},
        )
        self.assertFalse(decision.allowed)
        self.assertEqual("stale-verification", decision.code)


class StopDecisionTests(unittest.TestCase):
    def test_malformed_state_cannot_use_override_to_stop(self):
        malformed = state(
            phase="complete",
            enforcement_override={
                "enabled": True,
                "reason": "Emergency",
                "authorized_by": "user",
                "confirmation_id": "confirm-1",
                "remaining_uses": 1,
            },
            scope_result="unknown",
        )
        decision = goal_guard.evaluate_stop(malformed)
        self.assertFalse(decision.allowed)
        self.assertEqual("audit-failed", decision.code)
    def test_override_is_consumed_before_stop_or_completion(self):
        overridden = state(
            enforcement_override={
                "enabled": True,
                "reason": "Emergency",
                "authorized_by": "user",
                "confirmation_id": "confirm-1",
                "remaining_uses": 1,
            }
        )
        consumed = goal_guard.consume_override(overridden)
        self.assertFalse(consumed["enforcement_override"]["enabled"])
        self.assertEqual(0, consumed["enforcement_override"]["remaining_uses"])

    def test_incomplete_active_goal_blocks_stop(self):
        decision = goal_guard.evaluate_stop(state())
        self.assertFalse(decision.allowed)
        self.assertEqual("goal-incomplete", decision.code)

    def test_audited_complete_goal_allows_stop(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            fingerprint = goal_guard.workspace_fingerprint_record(workspace)
            command = "python -m unittest"
            complete = state(
                phase="complete",
                layers={"6": {"status": "pass", "evidence": "layer 6 verified"}},
                verification={
                    "status": "pass",
                    "command": command,
                    "command_sha256": goal_guard.sha256_text(command),
                    "evidence": "20 tests passed",
                    "verified_at": "2026-07-11T12:00:00Z",
                    "mutation_seq": 0,
                    "workspace_fingerprint": fingerprint,
                },
                closure={
                    "recorded": True,
                    "evidence": "closure record",
                    "workspace_fingerprint": fingerprint,
                },
                operation_state="maintenance_continues",
            )
            decision = goal_guard.evaluate_stop(complete, workspace=workspace)
            self.assertTrue(decision.allowed)

    def test_string_false_closure_recorded_is_rejected(self):
        complete = state(
            phase="complete",
            layers={"6": {"status": "pass", "evidence": "layer 6 verified"}},
            verification={
                "status": "pass",
                "command": "python -m unittest",
                "command_sha256": goal_guard.sha256_text("python -m unittest"),
                "evidence": "20 tests passed",
                "verified_at": "2026-07-11T12:00:00Z",
                "mutation_seq": 0,
            },
            closure={"recorded": "false", "evidence": "closure record"},
            operation_state="maintenance_continues",
        )
        self.assertTrue(any("closure.recorded" in e for e in goal_guard.audit_state(complete)))

    def test_stop_without_workspace_fingerprint_is_rejected(self):
        complete = state(
            phase="complete",
            layers={"6": {"status": "pass", "evidence": "layer 6 verified"}},
            verification={
                "status": "pass",
                "command": "python -m unittest",
                "command_sha256": goal_guard.sha256_text("python -m unittest"),
                "evidence": "20 tests passed",
                "verified_at": "2026-07-11T12:00:00Z",
                "mutation_seq": 0,
            },
            closure={"recorded": True, "evidence": "closure record"},
            operation_state="maintenance_continues",
        )
        decision = goal_guard.evaluate_stop(complete)
        self.assertFalse(decision.allowed)
        self.assertEqual("audit-failed", decision.code)


class TransitionTests(unittest.TestCase):
    def test_write_state_cannot_rewrite_guard_owned_history(self):
        previous = state(
            last_mutation_seq=10,
            open_failures=[{"id": "failure-1", "status": "open"}],
        )
        candidate = state(
            phase="verified",
            last_mutation_seq=0,
            open_failures=[],
            layers={"6": {"status": "pass", "evidence": "layer 6"}},
            verification={
                "status": "pass",
                "command": "python -m unittest",
                "evidence": "forged",
                "verified_at": "2026-07-11T12:00:00Z",
                "mutation_seq": 0,
            },
        )
        errors = goal_guard.validate_transition(previous, candidate)
        self.assertTrue(any("last_mutation_seq" in error for error in errors))
        self.assertTrue(any("open_failures" in error for error in errors))

    def test_resolve_failure_requires_evidence(self):
        current = state(open_failures=[{"id": "failure-1", "status": "open"}])
        with self.assertRaises(ValueError):
            goal_guard.resolve_failure(current, "failure-1", "")
        updated = goal_guard.resolve_failure(current, "failure-1", "root cause fixed")
        self.assertEqual("resolved", updated["open_failures"][0]["status"])
        self.assertEqual([], goal_guard.open_failures(updated))

    def test_write_state_cannot_install_override(self):
        previous = state()
        candidate = state(
            enforcement_override={
                "enabled": True,
                "reason": "Self-issued",
                "authorized_by": "user",
                "confirmation_id": "confirm-1",
                "remaining_uses": 1,
            }
        )
        errors = goal_guard.validate_transition(previous, candidate)
        self.assertTrue(any("override" in error for error in errors))

    def test_interactive_override_requires_matching_confirmation(self):
        with self.assertRaises(ValueError):
            goal_guard.authorize_override(state(), "Emergency", "confirm-1", "wrong")
        updated = goal_guard.authorize_override(
            state(), "Emergency", "confirm-1", "confirm-1"
        )
        self.assertTrue(updated["enforcement_override"]["enabled"])
        self.assertEqual(1, updated["enforcement_override"]["remaining_uses"])

    def test_phase_jump_is_rejected(self):
        previous = state(phase="classified")
        candidate = state(phase="verified")
        errors = goal_guard.validate_transition(previous, candidate)
        self.assertTrue(any("adjacent" in error for error in errors))

    def test_goal_identity_fields_are_immutable(self):
        previous = state(phase="executing")
        candidate = state(phase="verified", goal="Different goal")
        errors = goal_guard.validate_transition(previous, candidate)
        self.assertTrue(any("goal" in error for error in errors))

    def test_write_state_cannot_jump_or_lower_current_layer(self):
        previous = state(start_layer=0, current_layer=2)
        lowered = state(
            start_layer=0,
            current_layer=1,
            layers={
                "0": {"status": "pass", "evidence": "layer 0"},
                "1": {"status": "pass", "evidence": "layer 1"},
            },
        )
        jumped = state(
            start_layer=0,
            current_layer=4,
            layers={str(i): {"status": "pass", "evidence": f"layer {i}"} for i in range(5)},
        )
        lowered_errors = goal_guard.validate_transition(previous, lowered)
        jumped_errors = goal_guard.validate_transition(previous, jumped)
        self.assertTrue(any("current_layer" in error for error in lowered_errors))
        self.assertTrue(any("current_layer" in error for error in jumped_errors))

    def test_write_state_cannot_disable_required_plan(self):
        previous = state(
            plan={"required": True, "approved": True, "path": "plan.md"}
        )
        candidate = state(
            plan={"required": False, "approved": False, "path": None}
        )
        errors = goal_guard.validate_transition(previous, candidate)
        self.assertTrue(any("plan.required" in error for error in errors))

    def test_write_state_cannot_forge_bootstrap_confirmation(self):
        previous = state(
            mode="bootstrap",
            phase="classified",
            classification={"confirmed": False, "rationale": "New system"},
        )
        candidate = state(
            mode="bootstrap",
            phase="classified",
            classification={"confirmed": True, "rationale": "New system"},
        )
        errors = goal_guard.validate_transition(previous, candidate)
        self.assertTrue(any("confirmation" in error for error in errors))

    def test_adjacent_valid_transition_is_allowed(self):
        previous = state(phase="executing")
        candidate = state(
            phase="verified",
            layers={"6": {"status": "pass", "evidence": "layer 6 verified"}},
            verification={
                "status": "pass",
                "command": "python -m unittest",
                "command_sha256": goal_guard.sha256_text("python -m unittest"),
                "evidence": "22 tests passed",
                "verified_at": "2026-07-11T12:00:00Z",
                "mutation_seq": 0,
                "workspace_fingerprint": {
                    "algorithm": "sha256-manifest-v1",
                    "value": "0" * 64,
                    "scope": "regular-files-excluding-governance",
                    "captured_at": "2026-07-11T12:00:00Z",
                },
            },
        )
        self.assertEqual([], goal_guard.validate_transition(previous, candidate))


class ReservationTests(unittest.TestCase):
    def test_pre_reservation_immediately_blocks_completion_and_stop(self):
        ready = state(
            phase="verified",
            layers={"6": {"status": "pass", "evidence": "layer 6"}},
            verification={
                "status": "pass",
                "command": "python -m unittest",
                "evidence": "tests passed",
                "verified_at": "2026-07-11T12:00:00Z",
                "mutation_seq": 0,
            },
            closure={"recorded": True, "evidence": "closure"},
        )
        reserved = goal_guard.reserve_mutation(
            ready, "apply_patch", {"patch": "app.py"}, "tool-1"
        )
        self.assertEqual(1, reserved["last_mutation_seq"])
        self.assertEqual("executing", reserved["phase"])
        self.assertEqual(1, len(reserved["in_flight_mutations"]))
        completion = goal_guard.evaluate_tool_call(
            reserved, "update_goal", {"status": "complete"}
        )
        self.assertFalse(completion.allowed)
        self.assertFalse(goal_guard.evaluate_stop(reserved).allowed)

    def test_post_reconciles_reservation_without_double_increment(self):
        reserved = goal_guard.reserve_mutation(
            state(), "apply_patch", {"patch": "app.py"}, "tool-1"
        )
        updated = goal_guard.apply_post_tool_use(
            reserved,
            "apply_patch",
            {"patch": "app.py"},
            success=True,
            reservation_id="tool-1",
        )
        self.assertEqual(1, updated["last_mutation_seq"])
        self.assertEqual([], updated["in_flight_mutations"])

    def test_concurrent_failed_reservations_use_distinct_failure_ids(self):
        reserved = goal_guard.reserve_mutation(
            state(), "apply_patch", {"patch": "app.py"}, "tool-1"
        )
        reserved = goal_guard.reserve_mutation(
            reserved, "apply_patch", {"patch": "tests.py"}, "tool-2"
        )
        first = goal_guard.apply_post_tool_use(
            reserved,
            "apply_patch",
            {"patch": "app.py"},
            success=False,
            failure_evidence="first failed",
            reservation_id="tool-1",
        )
        second = goal_guard.apply_post_tool_use(
            first,
            "apply_patch",
            {"patch": "tests.py"},
            success=False,
            failure_evidence="second failed",
            reservation_id="tool-2",
        )
        self.assertEqual(
            ["failure-1", "failure-2"],
            [failure["id"] for failure in second["open_failures"]],
        )
        resolved = goal_guard.resolve_failure(second, "failure-1", "fixed first")
        resolved = goal_guard.resolve_failure(resolved, "failure-2", "fixed second")
        self.assertEqual([], goal_guard.open_failures(resolved))

    def test_identical_fallback_fingerprints_get_unique_reservation_instances(self):
        tool_input = {"patch": "same patch"}
        correlation_id = goal_guard.mutation_reservation_id(
            {}, "apply_patch", tool_input
        )
        reserved = goal_guard.reserve_mutation(
            state(), "apply_patch", tool_input, correlation_id
        )
        reserved = goal_guard.reserve_mutation(
            reserved, "apply_patch", tool_input, correlation_id
        )
        reservation_ids = [item["id"] for item in reserved["in_flight_mutations"]]
        self.assertEqual(2, len(set(reservation_ids)))
        self.assertEqual([], goal_guard.audit_state(reserved))
        first = goal_guard.apply_post_tool_use(
            reserved,
            "apply_patch",
            tool_input,
            success=True,
            reservation_id=correlation_id,
        )
        self.assertEqual(1, len(first["in_flight_mutations"]))
        second = goal_guard.apply_post_tool_use(
            first,
            "apply_patch",
            tool_input,
            success=True,
            reservation_id=correlation_id,
        )
        self.assertEqual([], second["in_flight_mutations"])

    def test_recover_reservation_requires_evidence_and_opens_failure(self):
        reserved = goal_guard.reserve_mutation(
            state(), "apply_patch", {"patch": "app.py"}, "tool-orphan"
        )
        with self.assertRaises(ValueError):
            goal_guard.recover_reservation(reserved, "tool-orphan", "")
        recovered = goal_guard.recover_reservation(
            reserved, "tool-orphan", "agent process crashed before PostToolUse"
        )
        self.assertEqual([], recovered["in_flight_mutations"])
        self.assertEqual("failure-1", recovered["open_failures"][0]["id"])
        self.assertEqual("open", recovered["open_failures"][0]["status"])
        self.assertIn("crashed", recovered["open_failures"][0]["evidence"])


class PostToolUseTests(unittest.TestCase):
    def test_payload_success_rejects_non_boolean_error_flag(self):
        success, evidence = goal_guard.payload_success({"is_error": "false"})
        self.assertFalse(success)
        self.assertIn("is_error", evidence or "")

    def test_successful_mutation_invalidates_old_verification(self):
        current = state(
            phase="verified",
            last_mutation_seq=2,
            verification={
                "status": "pass",
                "command": "python -m unittest",
                "evidence": "18 tests passed",
                "verified_at": "2026-07-11T12:00:00Z",
                "mutation_seq": 2,
            },
            closure={"recorded": True, "evidence": "old closure"},
        )
        updated = goal_guard.apply_post_tool_use(
            current, "apply_patch", {"patch": "*** Update File: app.py"}, success=True
        )
        self.assertEqual(3, updated["last_mutation_seq"])
        self.assertEqual("executing", updated["phase"])
        self.assertEqual("stale", updated["verification"]["status"])
        self.assertFalse(updated["closure"]["recorded"])

    def test_failed_mutation_opens_failure(self):
        updated = goal_guard.apply_post_tool_use(
            state(),
            "shell_command",
            {"command": "python -m unittest"},
            success=False,
            failure_evidence="exit code 1",
        )
        self.assertEqual(1, len(updated["open_failures"]))
        self.assertEqual("open", updated["open_failures"][0]["status"])
        self.assertEqual("exit code 1", updated["open_failures"][0]["evidence"])


class HookConfigTests(unittest.TestCase):
    def test_mutation_matchers_cover_supported_tool_names(self):
        config_path = Path(__file__).parents[1] / "hooks.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))["hooks"]
        for event in ("PreToolUse", "PostToolUse"):
            matcher = config[event][0]["matcher"]
            for tool in (
                "apply_patch",
                "shell_command",
                "exec_command",
                "update_goal",
                "Write",
                "Edit",
                "MultiEdit",
                "Bash",
            ):
                self.assertIn(tool, matcher)

    def test_hook_commands_use_plugin_relative_engine_path(self):
        config_path = Path(__file__).parents[1] / "hooks.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))["hooks"]
        for groups in config.values():
            for group in groups:
                for hook in group["hooks"]:
                    self.assertIn("./scripts/goal_guard.py", hook["command"])


class HookCliTests(unittest.TestCase):
    def test_pre_hook_capabilities_command_preserves_existing_state(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            current = state()
            goal_guard.write_goal_state(workspace, current)
            path = goal_guard.state_path(workspace)
            before = path.read_bytes()
            command = f'python "{MODULE_PATH.resolve().as_posix()}" capabilities'
            payload = {
                "cwd": str(workspace),
                "tool_name": "shell_command",
                "tool_input": {"command": command},
            }
            with patch.object(goal_guard, "hook_payload", return_value=payload), patch.object(
                goal_guard, "emit"
            ) as emit_mock:
                self.assertEqual(0, goal_guard.run_pre_tool_use(str(workspace)))
            emit_mock.assert_called_once_with({})
            self.assertEqual(before, path.read_bytes())

    def test_pre_hook_blocks_malformed_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, str(MODULE_PATH), "pre-tool-use"],
                cwd=directory,
                input="{not-json",
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, result.returncode)
            output = json.loads(result.stdout)
            self.assertEqual("block", output["decision"])
            self.assertIn("payload", output["reason"].lower())

    def test_pre_hook_blocks_symlinked_governance_layout(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            workspace = Path(directory)
            try:
                (workspace / ".codex").symlink_to(Path(outside), target_is_directory=True)
            except OSError:
                self.skipTest("symlink creation is unavailable on this Windows host")
            result = subprocess.run(
                [sys.executable, str(MODULE_PATH), "pre-tool-use"],
                input=json.dumps(
                    {
                        "cwd": str(workspace),
                        "tool_name": "apply_patch",
                        "tool_input": {"patch": "x"},
                    }
                ),
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, result.returncode)
            self.assertEqual("block", json.loads(result.stdout)["decision"])

    def test_pre_hook_blocks_non_object_tool_input(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            (workspace / ".codex").mkdir()
            goal_guard.write_goal_state(workspace, state())
            result = subprocess.run(
                [sys.executable, str(MODULE_PATH), "pre-tool-use"],
                input=json.dumps(
                    {
                        "cwd": str(workspace),
                        "tool_name": "apply_patch",
                        "tool_input": ["*** Update File: .codex/goal-state.json"],
                    }
                ),
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, result.returncode)
            output = json.loads(result.stdout)
            self.assertEqual("block", output["decision"])
            self.assertIn("tool_input", output["reason"])

    def test_pre_hook_reads_stdin_and_emits_block_decision(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            state_dir = workspace / ".codex"
            state_dir.mkdir()
            current = state(phase="intake")
            (state_dir / "goal-state.json").write_text(
                json.dumps(current), encoding="utf-8"
            )
            payload = {
                "cwd": str(workspace),
                "tool_name": "apply_patch",
                "tool_input": {"patch": "*** Update File: app.py"},
            }
            result = subprocess.run(
                [sys.executable, str(MODULE_PATH), "pre-tool-use"],
                input=json.dumps(payload),
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, result.returncode)
            self.assertEqual("block", json.loads(result.stdout)["decision"])

    def test_post_hook_reports_semantically_invalid_state(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            state_dir = workspace / ".codex"
            state_dir.mkdir()
            invalid = state(last_mutation_seq="bad")
            (state_dir / "goal-state.json").write_text(
                json.dumps(invalid), encoding="utf-8"
            )
            payload = {
                "cwd": str(workspace),
                "tool_name": "apply_patch",
                "tool_input": {"patch": "x"},
            }
            result = subprocess.run(
                [sys.executable, str(MODULE_PATH), "post-tool-use"],
                input=json.dumps(payload),
                text=True,
                capture_output=True,
                check=False,
            )
            output = json.loads(result.stdout)
            self.assertIn("INVALID", output["systemMessage"])

    def test_post_hook_reports_invalid_active_state(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            state_dir = workspace / ".codex"
            state_dir.mkdir()
            (state_dir / "goal-state.json").write_text("{bad", encoding="utf-8")
            payload = {
                "cwd": str(workspace),
                "tool_name": "apply_patch",
                "tool_input": {"patch": "x"},
            }
            result = subprocess.run(
                [sys.executable, str(MODULE_PATH), "post-tool-use"],
                input=json.dumps(payload),
                text=True,
                capture_output=True,
                check=False,
            )
            output = json.loads(result.stdout)
            self.assertIn("systemMessage", output)
            self.assertIn("INVALID", output["systemMessage"])

    def test_allowed_stop_emits_empty_object_without_exception(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            state_dir = workspace / ".codex"
            state_dir.mkdir()
            command = "python -m unittest"
            fingerprint = goal_guard.workspace_fingerprint_record(workspace)
            complete = state(
                phase="complete",
                layers={"6": {"status": "pass", "evidence": "layer 6"}},
                verification={
                    "status": "pass",
                    "command": command,
                    "evidence": "tests passed",
                    "verified_at": "2026-07-11T12:00:00Z",
                    "mutation_seq": 0,
                    "workspace_fingerprint": fingerprint,
                    "command_sha256": goal_guard.sha256_text(command),
                },
                closure={"recorded": True, "evidence": "closure recorded", "workspace_fingerprint": fingerprint},
                operation_state="maintenance_continues",
            )
            (state_dir / "goal-state.json").write_text(
                json.dumps(complete), encoding="utf-8"
            )
            result = subprocess.run(
                [sys.executable, str(MODULE_PATH), "stop"],
                input=json.dumps({"cwd": str(workspace)}),
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual({}, json.loads(result.stdout))

    def test_stop_hook_blocks_empty_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, str(MODULE_PATH), "stop"],
                cwd=directory,
                input="",
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, result.returncode)
            output = json.loads(result.stdout)
            self.assertEqual("block", output["decision"])
            self.assertIn("payload", output["reason"].lower())

    def test_recover_reservation_cli_requires_and_records_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            reserved = goal_guard.reserve_mutation(
                state(), "apply_patch", {"patch": "app.py"}, "tool-orphan"
            )
            goal_guard.write_goal_state(workspace, reserved)
            result = subprocess.run(
                [
                    sys.executable,
                    str(MODULE_PATH),
                    "recover-reservation",
                    "--workspace",
                    str(workspace),
                    "--reservation-id",
                    "tool-orphan",
                    "--evidence",
                    "confirmed interrupted hook lifecycle",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            recovered = goal_guard.load_goal_state(workspace).state
            self.assertEqual([], recovered["in_flight_mutations"])
            self.assertEqual("open", recovered["open_failures"][0]["status"])


class InitializationTests(unittest.TestCase):
    def test_initialize_maintenance_creates_canonical_classified_state(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            result = subprocess.run(
                [
                    sys.executable,
                    str(MODULE_PATH),
                    "initialize-state",
                    "--workspace",
                    str(workspace),
                    "--goal",
                    "Maintain service",
                    "--mode",
                    "maintenance",
                    "--start-layer",
                    "4",
                    "--rationale",
                    "Existing service change",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            loaded = goal_guard.load_goal_state(workspace)
            self.assertTrue(loaded.active)
            self.assertEqual([], goal_guard.audit_state(loaded.state or {}))
            self.assertEqual("classified", loaded.state["phase"])
            self.assertEqual(4, loaded.state["start_layer"])
            self.assertEqual(4, loaded.state["current_layer"])
            self.assertEqual([], loaded.state["rollback_history"])

    def test_initialize_bootstrap_requires_and_records_confirmation(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            missing = subprocess.run(
                [
                    sys.executable,
                    str(MODULE_PATH),
                    "initialize-state",
                    "--workspace",
                    str(workspace),
                    "--goal",
                    "New system",
                    "--mode",
                    "bootstrap",
                    "--start-layer",
                    "0",
                    "--rationale",
                    "Greenfield",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(0, missing.returncode)
            confirmed = subprocess.run(
                [
                    sys.executable,
                    str(MODULE_PATH),
                    "initialize-state",
                    "--workspace",
                    str(workspace),
                    "--goal",
                    "New system",
                    "--mode",
                    "bootstrap",
                    "--start-layer",
                    "0",
                    "--rationale",
                    "Greenfield",
                    "--confirmation-id",
                    "bootstrap-confirm-1",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, confirmed.returncode, confirmed.stderr)
            state_value = goal_guard.load_goal_state(workspace).state
            self.assertTrue(state_value["classification"]["confirmed"])
            self.assertEqual(
                "bootstrap-confirm-1",
                state_value["classification"]["confirmation_id"],
            )

    def test_initialize_rejects_existing_or_corrupt_state(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            first = goal_guard.initialize_state(
                workspace, "Goal", "maintenance", 2, "Reason"
            )
            self.assertEqual("Goal", first["goal"])
            second = subprocess.run(
                [
                    sys.executable,
                    str(MODULE_PATH),
                    "initialize-state",
                    "--workspace",
                    str(workspace),
                    "--goal",
                    "Other",
                    "--mode",
                    "maintenance",
                    "--start-layer",
                    "1",
                    "--rationale",
                    "Other reason",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(0, second.returncode)

            corrupt_workspace = workspace / "corrupt"
            (corrupt_workspace / ".codex").mkdir(parents=True)
            (corrupt_workspace / ".codex" / "goal-state.json").write_text(
                "{bad", encoding="utf-8"
            )
            corrupt = subprocess.run(
                [
                    sys.executable,
                    str(MODULE_PATH),
                    "initialize-state",
                    "--workspace",
                    str(corrupt_workspace),
                    "--goal",
                    "Other",
                    "--mode",
                    "maintenance",
                    "--start-layer",
                    "1",
                    "--rationale",
                    "Other reason",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(0, corrupt.returncode)


class RollbackTests(unittest.TestCase):
    def test_cross_start_rollback_lowers_start_and_invalidates_downstream_evidence(self):
        current = state(
            start_layer=4,
            current_layer=4,
            layers={
                "2": {"status": "pass", "evidence": "layer 2"},
                "3": {"status": "pass", "evidence": "layer 3"},
                "4": {"status": "pass", "evidence": "layer 4"},
            },
            last_mutation_seq=3,
            verification={
                "status": "pass",
                "command": "tests",
                "evidence": "passed",
                "verified_at": "2026-07-11T12:00:00Z",
                "mutation_seq": 3,
            },
            closure={"recorded": True, "evidence": "old closure"},
        )
        updated = goal_guard.rollback_layer(current, 2, "bad assumption", "reopened evidence")
        self.assertEqual("executing", updated["phase"])
        self.assertEqual(2, updated["start_layer"])
        self.assertEqual(2, updated["current_layer"])
        self.assertEqual({}, updated["layers"])
        self.assertEqual("stale", updated["verification"]["status"])
        self.assertFalse(updated["closure"]["recorded"])
        self.assertEqual("rework-required", updated["scope_result"])
        self.assertEqual("in_progress", updated["operation_state"])
        self.assertEqual(4, updated["last_mutation_seq"])
        self.assertEqual(1, len(updated["rollback_history"]))
        self.assertEqual(4, updated["rollback_history"][0]["from_start_layer"])
        self.assertIsNone(updated["verification"]["command"])
        self.assertIsNone(updated["verification"]["evidence"])
        self.assertIsNone(updated["verification"]["verified_at"])

    def test_same_start_rollback_clears_target_and_downstream_records(self):
        current = state(
            start_layer=2,
            current_layer=4,
            layers={
                "2": {"status": "pass", "evidence": "layer 2"},
                "3": {"status": "pass", "evidence": "layer 3"},
            },
        )
        updated = goal_guard.rollback_layer(current, 2, "rework", "new evidence")
        self.assertEqual(2, updated["start_layer"])
        self.assertEqual({}, updated["layers"])

    def test_rollback_rejects_forward_out_of_bounds_and_missing_evidence(self):
        current = state(start_layer=2, current_layer=4)
        with self.assertRaises(ValueError):
            goal_guard.rollback_layer(current, 5, "reason", "evidence")
        with self.assertRaises(ValueError):
            goal_guard.rollback_layer(current, -1, "reason", "evidence")
        with self.assertRaises(ValueError):
            goal_guard.rollback_layer(current, 2, "", "evidence")
        with self.assertRaises(ValueError):
            goal_guard.rollback_layer(current, 2, "reason", "")

    def test_write_state_cannot_forge_rollback_history(self):
        previous = state(rollback_history=[])
        candidate = state(rollback_history=[{
            "from_start_layer": 6,
            "from_current_layer": 6,
            "to_layer": 4,
            "reason": "forged",
            "evidence": "forged",
            "at": "2026-07-11T12:00:00Z",
            "mutation_seq": 1,
        }])
        errors = goal_guard.validate_transition(previous, candidate)
        self.assertTrue(any("rollback_history" in error for error in errors))

    def test_rollback_history_requires_unique_increasing_mutation_sequences(self):
        malformed = state(
            rollback_history=[
                {"from_start_layer": 4, "from_current_layer": 4, "to_layer": 2,
                 "reason": "r", "evidence": "e", "at": "t", "mutation_seq": 2},
                {"from_start_layer": 2, "from_current_layer": 2, "to_layer": 1,
                 "reason": "r", "evidence": "e", "at": "t", "mutation_seq": 2},
            ],
            last_mutation_seq=2,
        )
        errors = goal_guard.audit_state(malformed)
        self.assertTrue(any("rollback_history" in error for error in errors))


class DocumentationTests(unittest.TestCase):
    def test_initialization_requirement_covers_all_layers(self):
        docs = (
            Path(__file__).resolve().parents[2]
            / "goal"
            / "references"
            / "host-modes.md"
        ).read_text(encoding="utf-8")
        self.assertRegex(docs, r"first governed mutation.*any layer|all layers.*initialize-state")


class MissingStateGuardTests(unittest.TestCase):
    def test_write_state_requires_initialize_state_when_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            candidate = workspace / "candidate.json"
            candidate.write_text(json.dumps(state(phase="classified")), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(MODULE_PATH), "write-state", "--workspace", str(workspace), "--file", str(candidate)],
                text=True, capture_output=True, check=False,
            )
            self.assertNotEqual(0, result.returncode)
            self.assertFalse((workspace / ".codex" / "goal-state.json").exists())

    def test_missing_state_hooks_do_not_create_guard_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            payload = {"cwd": str(workspace), "tool_name": "apply_patch", "tool_input": {"patch": "x"}}
            result = subprocess.run(
                [sys.executable, str(MODULE_PATH), "pre-tool-use"],
                input=json.dumps(payload), text=True, capture_output=True, check=False,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertFalse((workspace / ".codex").exists())

    def test_missing_state_hook_blocks_direct_state_edit(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            payload = {"cwd": str(workspace), "tool_name": "apply_patch", "tool_input": {"patch": "*** Update File: .codex/goal-state.json"}}
            result = subprocess.run(
                [sys.executable, str(MODULE_PATH), "pre-tool-use"],
                input=json.dumps(payload), text=True, capture_output=True, check=False,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertIn("goal-state", json.loads(result.stdout).get("reason", ""))

    def test_rollback_can_recover_from_workspace_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            (workspace / "source.txt").write_text("one", encoding="utf-8")
            fingerprint = goal_guard.workspace_fingerprint_record(workspace)
            current = state(
                phase="verified", start_layer=2, current_layer=2,
                layers={"2": {"status": "pass", "evidence": "layer 2"}},
                verification={
                    "status": "pass", "command": "tests", "evidence": "passed",
                    "verified_at": "2026-09-02T00:00:00Z", "mutation_seq": 0,
                    "workspace_fingerprint": fingerprint,
                    "command_sha256": goal_guard.sha256_text("tests"),
                },
                closure={"recorded": False, "evidence": None},
            )
            goal_guard.write_goal_state(workspace, current)
            (workspace / "source.txt").write_text("drift", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(MODULE_PATH), "rollback-layer", "--workspace", str(workspace), "--to-layer", "2", "--reason", "drift", "--evidence", "reopen"],
                text=True, capture_output=True, check=False,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            recovered = goal_guard.load_goal_state(workspace).state
            self.assertEqual("stale", recovered["verification"]["status"])


class ConcurrencyTests(unittest.TestCase):
    def test_locked_read_modify_write_does_not_lose_updates(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            goal_guard.write_goal_state(workspace, state())

            def increment(_):
                with goal_guard.goal_state_lock(workspace):
                    loaded = goal_guard.load_goal_state(workspace)
                    current = loaded.state
                    current["last_mutation_seq"] += 1
                    goal_guard.write_goal_state(workspace, current)

            with ThreadPoolExecutor(max_workers=6) as pool:
                list(pool.map(increment, range(12)))

            loaded = goal_guard.load_goal_state(workspace)
            self.assertEqual(12, loaded.state["last_mutation_seq"])
            leftovers = list((workspace / ".codex").glob("goal-state.*.tmp"))
            self.assertEqual([], leftovers)


class AuditTests(unittest.TestCase):
    def test_layer_advancement_requires_pass_evidence(self):
        errors = goal_guard.audit_state(
            state(
                start_layer=2,
                current_layer=4,
                layers={
                    "2": {"status": "pass", "evidence": "topology.md"},
                    "3": {"status": "pass", "evidence": ""},
                },
            )
        )
        self.assertTrue(any("Layer 3" in error for error in errors))

    def test_verified_state_requires_current_layer_evidence(self):
        errors = goal_guard.audit_state(
            state(
                phase="verified",
                verification={
                    "status": "pass",
                    "command": "python -m unittest",
                    "evidence": "tests passed",
                    "verified_at": "2026-07-11T12:00:00Z",
                    "mutation_seq": 0,
                },
            )
        )
        self.assertTrue(any("Layer 6" in error for error in errors))

    def test_complete_state_requires_timestamp_and_closure_evidence(self):
        errors = goal_guard.audit_state(
            state(
                phase="complete",
                layers={"6": {"status": "pass", "evidence": "layer 6"}},
                verification={
                    "status": "pass",
                    "command": "python -m unittest",
                    "evidence": "tests passed",
                    "verified_at": None,
                    "mutation_seq": 0,
                },
                closure={"recorded": True, "evidence": ""},
            )
        )
        self.assertTrue(any("verified_at" in error for error in errors))
        self.assertTrue(any("closure evidence" in error for error in errors))

    def test_malformed_failure_and_reservation_entries_fail_closed(self):
        malformed_failures = state(open_failures=["malformed"])
        malformed_reservations = state(in_flight_mutations=["malformed"])
        self.assertTrue(
            any("open_failures[0]" in error for error in goal_guard.audit_state(malformed_failures))
        )
        self.assertTrue(
            any(
                "in_flight_mutations[0]" in error
                for error in goal_guard.audit_state(malformed_reservations)
            )
        )
        self.assertFalse(
            goal_guard.evaluate_tool_call(
                malformed_failures, "apply_patch", {"patch": "x"}
            ).allowed
        )
        self.assertFalse(
            goal_guard.evaluate_tool_call(
                malformed_reservations, "apply_patch", {"patch": "x"}
            ).allowed
        )

    def test_failure_and_reservation_identifiers_must_be_unique(self):
        duplicate_failures = state(
            open_failures=[
                {"id": "failure-1", "status": "resolved"},
                {"id": "failure-1", "status": "open"},
            ]
        )
        duplicate_reservations = state(
            last_mutation_seq=2,
            in_flight_mutations=[
                {"id": "tool-1", "tool": "apply_patch", "sequence": 1},
                {"id": "tool-1", "tool": "apply_patch", "sequence": 2},
            ],
        )
        self.assertTrue(
            any("duplicate failure id" in error for error in goal_guard.audit_state(duplicate_failures))
        )
        self.assertTrue(
            any(
                "duplicate reservation id" in error
                for error in goal_guard.audit_state(duplicate_reservations)
            )
        )

    def test_rollback_history_validates_timestamp_and_layer_order(self):
        malformed = state(
            last_mutation_seq=1,
            rollback_history=[
                {
                    "from_start_layer": 6,
                    "from_current_layer": 2,
                    "to_layer": 1,
                    "reason": "drift",
                    "evidence": "reopen",
                    "at": "not-a-timestamp",
                    "mutation_seq": 1,
                }
            ],
        )
        errors = goal_guard.audit_state(malformed)
        self.assertTrue(any("rollback_history[0].at" in error for error in errors))
        self.assertTrue(any("from_start_layer" in error for error in errors))

    def test_valid_executing_state_passes_audit(self):
        self.assertEqual([], goal_guard.audit_state(state()))

    def test_non_boolean_gate_fields_fail_closed(self):
        bootstrap = state(
            mode="bootstrap",
            phase="executing",
            classification={
                "confirmed": "false",
                "confirmation_id": "confirm-1",
                "rationale": "New system",
            },
        )
        plan = state(
            phase="planned",
            plan={"required": True, "approved": "false", "path": "plan.md"},
        )
        self.assertTrue(any("classification.confirmed" in e for e in goal_guard.audit_state(bootstrap)))
        self.assertTrue(any("plan.approved" in e for e in goal_guard.audit_state(plan)))

    def test_loader_distinguishes_missing_and_corrupt_state(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            missing = goal_guard.load_goal_state(workspace)
            self.assertFalse(missing.active)
            self.assertIsNone(missing.error)

            state_dir = workspace / ".codex"
            state_dir.mkdir()
            (state_dir / "goal-state.json").write_text("{bad", encoding="utf-8")
            corrupt = goal_guard.load_goal_state(workspace)
            self.assertTrue(corrupt.active)
            self.assertIsNotNone(corrupt.error)

    def test_symlinked_governance_directory_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            workspace = Path(directory)
            try:
                (workspace / ".codex").symlink_to(Path(outside), target_is_directory=True)
            except OSError:
                self.skipTest("symlink creation is unavailable on this Windows host")
            with self.assertRaises(ValueError):
                with goal_guard.goal_state_lock(workspace):
                    pass

    def test_symlinked_state_file_is_reported_as_invalid(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            workspace = Path(directory)
            (workspace / ".codex").mkdir()
            target = Path(outside) / "goal-state.json"
            target.write_text(json.dumps(state()), encoding="utf-8")
            try:
                (workspace / ".codex" / "goal-state.json").symlink_to(target)
            except OSError:
                self.skipTest("symlink creation is unavailable on this Windows host")
            loaded = goal_guard.load_goal_state(workspace)
            self.assertTrue(loaded.active)
            self.assertIn("symlink", (loaded.error or "").lower())

    def test_cli_audit_without_workspace_does_not_guess_cwd(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, str(MODULE_PATH), "audit"],
                cwd=directory,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(2, result.returncode)
            self.assertIn("workspace", result.stderr.lower())

    def test_cli_capabilities_is_stable_json_without_workspace(self):
        expected = {
            "capability": "goal-guard",
            "protocol_version": 1,
            "state_schema_versions": [1],
            "commands": [
                "audit",
                "initialize-state",
                "post-tool-use",
                "pre-tool-use",
                "recover-reservation",
                "resolve-failure",
                "rollback-layer",
                "stop",
                "write-state",
            ],
            "enforcement_modes": ["hard-hook", "audit-only-windows"],
            "features": ["web-fullstack-delivery-v1"],
        }
        result = subprocess.run(
            [sys.executable, str(MODULE_PATH), "capabilities"],
            cwd=Path(MODULE_PATH.resolve().anchor),
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, result.returncode)
        self.assertEqual(expected, json.loads(result.stdout))
        self.assertEqual(json.dumps(expected, sort_keys=True) + "\n", result.stdout)
        self.assertEqual("", result.stderr)

    def test_windows_reminder_never_claims_hard_enforcement(self):
        reminder = goal_guard.render_reminder(
            state(phase="classified"), "audit-only-windows"
        )
        self.assertIn("audit-only-windows", reminder)
        self.assertIn("NOT mechanically blocked", reminder)


class FingerprintAndClosureTests(unittest.TestCase):
    def _temporary_directory(self):
        return tempfile.TemporaryDirectory()

    def _verified_state(self, workspace, *, phase="verified", closure=None):
        fingerprint = goal_guard.workspace_fingerprint_record(workspace)
        command = "python -m unittest"
        verification = {
            "status": "pass",
            "command": command,
            "evidence": "tests passed",
            "verified_at": "2026-09-02T00:00:00Z",
            "mutation_seq": 0,
            "workspace_fingerprint": fingerprint,
            "command_sha256": goal_guard.sha256_text(command),
        }
        if closure is None:
            closure = {"recorded": True, "evidence": "closure recorded",
                       "workspace_fingerprint": fingerprint}
        return state(
            phase=phase,
            layers={"6": {"status": "pass", "evidence": "layer 6"}},
            verification=verification,
            closure=closure,
            operation_state="maintenance_continues" if phase == "complete" else "in_progress",
        )

    def test_workspace_fingerprint_tracks_content_but_excludes_guard_state(self):
        with self._temporary_directory() as directory:
            workspace = Path(directory)
            source = workspace / "source.txt"
            source.write_text("one", encoding="utf-8")
            before = goal_guard.workspace_fingerprint(workspace)
            (workspace / ".codex").mkdir()
            (workspace / ".codex" / "goal-state.json").write_text("guard", encoding="utf-8")
            self.assertEqual(before, goal_guard.workspace_fingerprint(workspace))
            source.write_text("two", encoding="utf-8")
            self.assertNotEqual(before, goal_guard.workspace_fingerprint(workspace))

    def test_workspace_fingerprint_rejects_directory_symlink(self):
        with self._temporary_directory() as directory, tempfile.TemporaryDirectory() as target:
            workspace = Path(directory)
            target_path = Path(target)
            (target_path / "source.txt").write_text("outside", encoding="utf-8")
            try:
                (workspace / "linked").symlink_to(target_path, target_is_directory=True)
            except OSError:
                self.skipTest("symlink creation is unavailable on this Windows host")
            with self.assertRaises(goal_guard.FingerprintError):
                goal_guard.workspace_fingerprint(workspace)

    def test_git_fingerprint_honors_ignore_rules(self):
        with self._temporary_directory() as directory:
            workspace = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=workspace, check=True)
            (workspace / ".gitignore").write_text("ignored.log\n", encoding="utf-8")
            (workspace / "tracked.txt").write_text("tracked", encoding="utf-8")
            (workspace / "ignored.log").write_text("one", encoding="utf-8")
            before = goal_guard.workspace_fingerprint(workspace)
            (workspace / "ignored.log").write_text("two", encoding="utf-8")
            self.assertEqual(before, goal_guard.workspace_fingerprint(workspace))
            (workspace / "tracked.txt").write_text("changed", encoding="utf-8")
            self.assertNotEqual(before, goal_guard.workspace_fingerprint(workspace))

    def test_nested_git_workspace_fingerprint_uses_subdirectory_scope(self):
        with self._temporary_directory() as directory:
            repository = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
            nested = repository / "sub"
            nested.mkdir()
            source = nested / "source.txt"
            source.write_text("one", encoding="utf-8")
            before = goal_guard.workspace_fingerprint(nested)
            source.write_text("two", encoding="utf-8")
            self.assertNotEqual(before, goal_guard.workspace_fingerprint(nested))

    def test_workspace_audit_requires_and_matches_verification_fingerprint(self):
        with self._temporary_directory() as directory:
            workspace = Path(directory)
            (workspace / "source.txt").write_text("one", encoding="utf-8")
            valid = self._verified_state(workspace)
            self.assertEqual([], goal_guard.audit_state(valid, workspace=workspace))
            missing = self._verified_state(workspace)
            missing["verification"].pop("workspace_fingerprint")
            self.assertTrue(any("fingerprint" in e for e in goal_guard.audit_state(missing, workspace=workspace)))
            (workspace / "source.txt").write_text("two", encoding="utf-8")
            errors = goal_guard.audit_state(valid, workspace=workspace)
            self.assertTrue(any("fingerprint" in e for e in errors))

            decision = goal_guard.evaluate_tool_call(
                valid, "update_goal", {"status": "complete"}, workspace=workspace
            )
            self.assertFalse(decision.allowed)
            self.assertEqual("audit-failed", decision.code)

    def test_complete_closure_fingerprint_must_match_verification_and_workspace(self):
        with self._temporary_directory() as directory:
            workspace = Path(directory)
            (workspace / "source.txt").write_text("one", encoding="utf-8")
            valid = self._verified_state(workspace, phase="complete")
            self.assertEqual([], goal_guard.audit_state(valid, workspace=workspace))
            mismatch = self._verified_state(
                workspace,
                phase="complete",
                closure={"recorded": True, "evidence": "closure", "workspace_fingerprint": {"algorithm": "sha256-manifest-v1", "value": "wrong", "scope": "tracked+nonignored-untracked", "captured_at": "2026-09-02T00:00:00Z"}},
            )
            self.assertTrue(any("closure fingerprint" in e for e in goal_guard.audit_state(mismatch, workspace=workspace)))

    def test_verified_at_must_be_parseable_and_not_future(self):
        malformed = state(
            phase="verified",
            layers={"6": {"status": "pass", "evidence": "layer 6"}},
            verification={
                "status": "pass", "command": "tests", "evidence": "passed",
                "verified_at": "not-a-timestamp", "mutation_seq": 0,
            },
        )
        self.assertTrue(any("verified_at" in e for e in goal_guard.audit_state(malformed)))

    def test_fingerprint_receipt_timestamp_and_digest_are_validated(self):
        malformed = state(
            phase="verified",
            layers={"6": {"status": "pass", "evidence": "layer 6"}},
            verification={
                "status": "pass", "command": "tests", "evidence": "passed",
                "verified_at": "2026-09-02T00:00:00Z", "mutation_seq": 0,
                "command_sha256": goal_guard.sha256_text("tests"),
                "workspace_fingerprint": {
                    "algorithm": "sha256-manifest-v1",
                    "scope": "tracked+nonignored-untracked",
                    "value": "bad",
                    "captured_at": "not-a-timestamp",
                },
            },
        )
        errors = goal_guard.audit_state(malformed)
        self.assertTrue(any("workspace_fingerprint.value" in e for e in errors))
        self.assertTrue(any("captured_at" in e for e in errors))

    def test_scope_and_operation_state_must_match_phase_mode_and_layer_outcomes(self):
        invalid_complete = state(
            mode="maintenance", phase="complete",
            layers={"6": {"status": "pass", "evidence": "layer 6"}},
            verification={
                "status": "pass", "command": "tests", "evidence": "passed",
                "verified_at": "2026-09-02T00:00:00Z", "mutation_seq": 0,
            },
            closure={"recorded": True, "evidence": "closure"},
            scope_result="accepted", operation_state="bootstrap_exited",
        )
        self.assertTrue(any("operation_state" in e for e in goal_guard.audit_state(invalid_complete)))
        failed_scope = state(
            layers={"6": {"status": "fail", "evidence": "failed gate"}},
            scope_result="accepted", operation_state="in_progress",
        )
        self.assertTrue(any("scope_result" in e for e in goal_guard.audit_state(failed_scope)))


if __name__ == "__main__":
    unittest.main()
