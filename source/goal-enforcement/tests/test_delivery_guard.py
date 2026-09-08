import json
import hashlib
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


from delivery_fixtures import draft_delivery
from delivery_fixtures import accepted_delivery
import goal_guard


ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / "scripts" / "goal_guard.py"


def run_guard(tmp_path, *args):
    return subprocess.run(
        [sys.executable, "-B", str(GUARD), args[0], "--workspace", str(tmp_path), *args[1:]],
        capture_output=True,
        text=True,
        check=False,
    )


def write_state(tmp_path, state, expected=None):
    candidate = tmp_path / ".codex" / "candidate.json"
    candidate.parent.mkdir(exist_ok=True)
    candidate.write_text(json.dumps(state), encoding="utf-8")
    arguments = ["write-state", "--file", str(candidate)]
    if expected is not None:
        arguments.extend(["--expected-state-sha256", expected])
    return run_guard(tmp_path, *arguments)


def test_descriptor_advertises_delivery_feature():
    result = subprocess.run(
        [sys.executable, "-B", str(GUARD), "capabilities"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    descriptor = json.loads(result.stdout)
    assert "web-fullstack-delivery-v1" in descriptor["features"]


def test_legacy_initial_state_retains_accepted(tmp_path):
    result = run_guard(
        tmp_path,
        "initialize-state",
        "--goal",
        "legacy",
        "--mode",
        "maintenance",
        "--start-layer",
        "4",
        "--rationale",
        "legacy regression",
    )
    assert result.returncode == 0
    state = json.loads((tmp_path / ".codex" / "goal-state.json").read_text())
    assert state["scope_result"] == "accepted"
    assert "delivery" not in state


def test_delivery_draft_initializes_incomplete(tmp_path):
    delivery = tmp_path / "delivery.json"
    delivery.write_text(json.dumps(draft_delivery()), encoding="utf-8")
    result = run_guard(
        tmp_path,
        "initialize-state",
        "--goal",
        "delivery",
        "--mode",
        "maintenance",
        "--start-layer",
        "4",
        "--rationale",
        "delivery regression",
        "--delivery-file",
        str(delivery),
    )
    assert result.returncode == 0
    state = json.loads((tmp_path / ".codex" / "goal-state.json").read_text())
    assert state["scope_result"] == "incomplete"
    assert state["delivery"]["profile"] == "web-fullstack"


def test_invalid_delivery_does_not_create_state(tmp_path):
    delivery = tmp_path / "delivery.json"
    delivery.write_text('{"profile":"web-fullstack"}', encoding="utf-8")
    result = run_guard(
        tmp_path,
        "initialize-state",
        "--goal",
        "delivery",
        "--mode",
        "maintenance",
        "--start-layer",
        "4",
        "--rationale",
        "invalid delivery regression",
        "--delivery-file",
        str(delivery),
    )
    assert result.returncode == 1
    assert not (tmp_path / ".codex" / "goal-state.json").exists()


def test_existing_state_bytes_are_preserved_on_delivery_initialize(tmp_path):
    first = run_guard(
        tmp_path,
        "initialize-state",
        "--goal",
        "legacy",
        "--mode",
        "maintenance",
        "--start-layer",
        "4",
        "--rationale",
        "existing state",
    )
    assert first.returncode == 0
    path = tmp_path / ".codex" / "goal-state.json"
    before = path.read_bytes()
    delivery = tmp_path / "delivery.json"
    delivery.write_text(json.dumps(draft_delivery()), encoding="utf-8")
    second = run_guard(
        tmp_path,
        "initialize-state",
        "--goal",
        "delivery",
        "--mode",
        "maintenance",
        "--start-layer",
        "4",
        "--rationale",
        "must not replace",
        "--delivery-file",
        str(delivery),
    )
    assert second.returncode == 1
    assert path.read_bytes() == before


def test_concurrent_delivery_initialization_has_one_winner(tmp_path):
    delivery = tmp_path / "delivery.json"
    delivery.write_text(json.dumps(draft_delivery()), encoding="utf-8")

    def initialize(index):
        return run_guard(
            tmp_path,
            "initialize-state",
            "--goal",
            f"delivery-{index}",
            "--mode",
            "maintenance",
            "--start-layer",
            "4",
            "--rationale",
            "concurrent initialization",
            "--delivery-file",
            str(delivery),
        ).returncode

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(initialize, range(2)))
    assert sorted(results) == [0, 1]


def test_delivery_draft_initialize_audit_execute_first_mutation(tmp_path):
    delivery = tmp_path / "delivery.json"
    delivery.write_text(json.dumps(draft_delivery()), encoding="utf-8")
    initialized = run_guard(
        tmp_path,
        "initialize-state",
        "--goal",
        "delivery draft lifecycle",
        "--mode",
        "maintenance",
        "--start-layer",
        "4",
        "--rationale",
        "P1 lifecycle regression",
        "--delivery-file",
        str(delivery),
    )
    assert initialized.returncode == 0
    assert run_guard(tmp_path, "audit").returncode == 0
    state_path = tmp_path / ".codex" / "goal-state.json"
    planned = json.loads(state_path.read_text(encoding="utf-8"))
    planned["phase"] = "planned"
    digest = hashlib.sha256(state_path.read_bytes()).hexdigest()
    assert write_state(tmp_path, planned, digest).returncode == 0
    executing = json.loads(state_path.read_text(encoding="utf-8"))
    executing["phase"] = "executing"
    executing["layers"] = {"4": {"status": "in_progress", "evidence": "draft lifecycle"}}
    digest = hashlib.sha256(state_path.read_bytes()).hexdigest()
    assert write_state(tmp_path, executing, digest).returncode == 0
    (tmp_path / "first-source.txt").write_text("first governed mutation", encoding="utf-8")
    assert run_guard(tmp_path, "audit").returncode == 0
    current = json.loads(state_path.read_text(encoding="utf-8"))
    assert current["scope_result"] == "incomplete"
    assert current["delivery"]["criteria"] == []


def test_delivery_write_requires_current_state_digest(tmp_path):
    delivery = tmp_path / "delivery.json"
    delivery.write_text(json.dumps(draft_delivery()), encoding="utf-8")
    assert run_guard(
        tmp_path,
        "initialize-state",
        "--goal",
        "cas",
        "--mode",
        "maintenance",
        "--start-layer",
        "4",
        "--rationale",
        "CAS regression",
        "--delivery-file",
        str(delivery),
    ).returncode == 0
    state_path = tmp_path / ".codex" / "goal-state.json"
    candidate = json.loads(state_path.read_text(encoding="utf-8"))
    candidate["phase"] = "planned"
    assert write_state(tmp_path, candidate).returncode == 1
    assert "DELIVERY_STATE_STALE" in (write_state(tmp_path, candidate, "0" * 64).stdout)


def test_two_candidates_from_same_digest_have_one_winner(tmp_path):
    delivery = tmp_path / "delivery.json"
    delivery.write_text(json.dumps(draft_delivery()), encoding="utf-8")
    assert run_guard(
        tmp_path,
        "initialize-state",
        "--goal",
        "cas",
        "--mode",
        "maintenance",
        "--start-layer",
        "4",
        "--rationale",
        "CAS regression",
        "--delivery-file",
        str(delivery),
    ).returncode == 0
    state_path = tmp_path / ".codex" / "goal-state.json"
    digest = hashlib.sha256(state_path.read_bytes()).hexdigest()
    first = json.loads(state_path.read_text(encoding="utf-8"))
    first["phase"] = "planned"
    second = json.loads(state_path.read_text(encoding="utf-8"))
    second["phase"] = "planned"
    second["layers"] = {"4": {"status": "in_progress", "evidence": "second"}}
    assert write_state(tmp_path, first, digest).returncode == 0
    before = state_path.read_bytes()
    result = write_state(tmp_path, second, digest)
    assert result.returncode == 1
    assert "DELIVERY_STATE_STALE" in result.stdout
    assert state_path.read_bytes() == before


def test_legacy_state_cannot_add_delivery(tmp_path):
    assert run_guard(
        tmp_path,
        "initialize-state",
        "--goal",
        "legacy",
        "--mode",
        "maintenance",
        "--start-layer",
        "4",
        "--rationale",
        "binding regression",
    ).returncode == 0
    state_path = tmp_path / ".codex" / "goal-state.json"
    candidate = json.loads(state_path.read_text(encoding="utf-8"))
    candidate["delivery"] = draft_delivery()
    result = write_state(tmp_path, candidate)
    assert result.returncode == 1
    assert "DELIVERY_BINDING_IMMUTABLE" in result.stdout


def delivery_state(delivery):
    return {
        "schema_version": 1,
        "goal": "delivery unit state",
        "mode": "maintenance",
        "phase": "executing",
        "start_layer": 4,
        "current_layer": 4,
        "classification": {
            "confirmed": True,
            "rationale": "delivery unit state",
            "confirmation_id": None,
        },
        "plan": {"required": False, "approved": False, "path": None},
        "layers": {"4": {"status": "in_progress", "evidence": "unit state"}},
        "verification": {
            "status": "missing",
            "command": None,
            "evidence": None,
            "verified_at": None,
            "mutation_seq": 0,
            "workspace_fingerprint": None,
            "command_sha256": None,
        },
        "closure": {"recorded": False, "evidence": None, "workspace_fingerprint": None},
        "open_failures": [],
        "in_flight_mutations": [],
        "last_mutation_seq": 0,
        "rollback_history": [],
        "enforcement_override": {
            "enabled": False,
            "reason": None,
            "authorized_by": None,
            "confirmation_id": None,
            "remaining_uses": 0,
        },
        "scope_result": "incomplete",
        "operation_state": "in_progress",
        "updated_at": "2026-09-08T00:00:00+00:00",
        "delivery": delivery,
    }


def test_mutation_reservation_invalidates_delivery_in_same_candidate(tmp_path):
    state = delivery_state(accepted_delivery())
    updated = goal_guard.reserve_mutation(
        state,
        "Write",
        {"path": str(tmp_path / "source.py"), "content": "changed"},
        "reservation-1",
        tmp_path,
    )
    assert len(updated["delivery"]["invalidations"]) == 1
    assert updated["delivery"]["criteria"][0]["status"] == "stale"
    assert updated["last_mutation_seq"] == 1


def test_rollback_invalidates_delivery_in_same_candidate():
    state = delivery_state(accepted_delivery())
    updated = goal_guard.rollback_layer(state, 4, "recheck", "upstream evidence changed")
    assert len(updated["delivery"]["invalidations"]) == 1
    assert updated["delivery"]["invalidations"][0]["event"] == "rollback"
    assert updated["delivery"]["criteria"][0]["status"] == "stale"


def test_empty_delivery_rejected_when_acceptance_requested(tmp_path):
    delivery = tmp_path / "delivery.json"
    delivery.write_text(json.dumps(draft_delivery()), encoding="utf-8")
    assert run_guard(
        tmp_path,
        "initialize-state",
        "--goal",
        "empty acceptance",
        "--mode",
        "maintenance",
        "--start-layer",
        "4",
        "--rationale",
        "acceptance regression",
        "--delivery-file",
        str(delivery),
    ).returncode == 0
    state_path = tmp_path / ".codex" / "goal-state.json"
    candidate = json.loads(state_path.read_text(encoding="utf-8"))
    candidate["scope_result"] = "accepted"
    digest = hashlib.sha256(state_path.read_bytes()).hexdigest()
    result = write_state(tmp_path, candidate, digest)
    assert result.returncode == 1
    assert "DELIVERY_REQUIRED_EMPTY" in result.stdout
    assert json.loads(state_path.read_text(encoding="utf-8"))["scope_result"] == "incomplete"


def test_complete_delivery_can_be_explicitly_accepted(tmp_path):
    delivery_value = accepted_delivery()
    evidence_file = tmp_path / ".codex" / "evidence" / "result.json"
    evidence_file.parent.mkdir(parents=True)
    evidence_file.write_bytes(b"{}")
    fingerprint = goal_guard.workspace_fingerprint_record(tmp_path)
    delivery_value["evidence"][0]["source_fingerprint"] = fingerprint
    delivery = tmp_path / ".codex" / "delivery.json"
    delivery.parent.mkdir(parents=True, exist_ok=True)
    delivery.write_text(json.dumps(delivery_value), encoding="utf-8")
    assert run_guard(
        tmp_path,
        "initialize-state",
        "--goal",
        "accepted delivery",
        "--mode",
        "maintenance",
        "--start-layer",
        "4",
        "--rationale",
        "acceptance regression",
        "--delivery-file",
        str(delivery),
    ).returncode == 0
    state_path = tmp_path / ".codex" / "goal-state.json"
    candidate = json.loads(state_path.read_text(encoding="utf-8"))
    candidate["scope_result"] = "accepted"
    digest = hashlib.sha256(state_path.read_bytes()).hexdigest()
    result = write_state(tmp_path, candidate, digest)
    assert result.returncode == 0, result.stdout + result.stderr


def test_each_acceptance_marker_checks_empty_delivery():
    base = delivery_state(draft_delivery())
    variants = []
    scope = json.loads(json.dumps(base))
    scope["scope_result"] = "accepted"
    variants.append(scope)
    phase = json.loads(json.dumps(base))
    phase["phase"] = "verified"
    variants.append(phase)
    verification = json.loads(json.dumps(base))
    verification["verification"]["status"] = "pass"
    variants.append(verification)
    closure = json.loads(json.dumps(base))
    closure["closure"]["recorded"] = True
    variants.append(closure)
    for candidate in variants:
        assert any(
            "DELIVERY_REQUIRED_EMPTY" in error
            for error in goal_guard.audit_state(candidate)
        )


def test_guard_rejects_invalidated_old_evidence_on_acceptance(tmp_path):
    delivery = goal_guard.invalidate_delivery(
        accepted_delivery(),
        event="workspace_edit",
        at="2026-09-08T00:00:04+00:00",
        reason="source changed then restored",
        mutation_seq=1,
    )
    delivery["criteria"][0]["status"] = "pass"
    candidate = delivery_state(delivery)
    candidate["scope_result"] = "accepted"
    errors = goal_guard.audit_state(candidate, workspace=tmp_path)
    assert any("DELIVERY_EVIDENCE_INVALIDATED" in error for error in errors)
