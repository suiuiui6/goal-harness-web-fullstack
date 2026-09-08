import copy
import importlib.util
from pathlib import Path

import pytest


GOAL_ROOT = Path(__file__).resolve().parents[1]
MALFORMED_PROTOCOL_ROOT = (
    Path(__file__).resolve().parent / "fixtures" / "malformed-protocol"
)
PROTOCOL_PATH = Path(__file__).resolve().with_name("protocol.py")
PROTOCOL_SPEC = importlib.util.spec_from_file_location(
    "goal_protocol_under_test", PROTOCOL_PATH
)
assert PROTOCOL_SPEC is not None and PROTOCOL_SPEC.loader is not None
PROTOCOL_MODULE = importlib.util.module_from_spec(PROTOCOL_SPEC)
PROTOCOL_SPEC.loader.exec_module(PROTOCOL_MODULE)

capability_compatible = PROTOCOL_MODULE.capability_compatible
delivery_feature_available = PROTOCOL_MODULE.delivery_feature_available
load_contract = PROTOCOL_MODULE.load_contract
required_fields = PROTOCOL_MODULE.required_fields
transition_allowed = PROTOCOL_MODULE.transition_allowed
validate_contract = PROTOCOL_MODULE.validate_contract


def test_delivery_feature_requires_complete_descriptor(contract):
    descriptor = {
        "capability": "goal-guard",
        "protocol_version": 1,
        "state_schema_versions": [1],
        "commands": ["initialize-state", "write-state", "audit"],
        "enforcement_modes": ["audit-only-windows"],
        "features": ["web-fullstack-delivery-v1"],
    }
    assert delivery_feature_available(contract, descriptor)
    for field in ("features", "commands", "state_schema_versions", "enforcement_modes"):
        missing = copy.deepcopy(descriptor)
        missing[field] = []
        assert not delivery_feature_available(contract, missing)


def test_delivery_feature_rejects_major_only_descriptor(contract):
    descriptor = {"capability": "goal-guard", "protocol_version": 1}
    assert capability_compatible(contract, "guard", descriptor)
    assert not delivery_feature_available(contract, descriptor)


EXPECTED_PHASES = [
    "intake",
    "classified",
    "planned",
    "executing",
    "verified",
    "complete",
]
EXPECTED_TRANSITIONS = {
    "intake": ["classified"],
    "classified": ["planned", "executing"],
    "planned": ["executing"],
    "executing": ["verified"],
    "verified": ["complete"],
    "complete": [],
}
EXPECTED_OWNERS = {
    "intake": "goal",
    "classification": "goal",
    "confirmation": "goal",
    "handoff": "goal",
    "planning": "harness",
    "layer_execution": "harness",
    "gates": "harness",
    "rollback": "harness",
    "closure": "harness",
    "atomic_state": "guard",
    "mutation_receipts": "guard",
    "workspace_freshness": "guard",
    "layer6_operations": "gsd",
}
EXPECTED_RECORDS = {
    "classification_reply": [
        "Goal",
        "Classification",
        "Rationale",
        "Confirmation",
        "Next action",
    ],
    "dependency_blocker": [
        "Code",
        "Dependency",
        "Evidence",
        "Impact",
        "Next action",
    ],
    "verification_receipt": [
        "Command",
        "Evidence",
        "Verified At",
        "Mutation Seq",
        "Workspace Fingerprint",
        "Next action",
    ],
    "closure_record": [
        "Mode",
        "Start Layer",
        "Touched Layers",
        "Layer Outcomes",
        "Evidence Pointers",
        "Rollback Decisions",
        "scope_result",
        "operation_state",
    ],
}
EXPECTED_ERRORS = {
    "DEPENDENCY_MISSING",
    "PROTOCOL_VERSION_MISMATCH",
    "CONFIRMATION_REQUIRED",
    "INVALID_STATE_TRANSITION",
    "STALE_VERIFICATION",
    "CAPABILITY_DISABLED",
}


@pytest.fixture
def contract():
    return load_contract(GOAL_ROOT)


def test_contract_defines_protocol_v2_state_machine(contract):
    assert contract["protocol_id"] == "goal-protocol"
    assert contract["protocol_version"] == 2
    assert contract["state_schema_versions"] == [1]
    assert contract["phases"] == EXPECTED_PHASES
    assert contract["transitions"] == EXPECTED_TRANSITIONS
    assert validate_contract(contract) is None


def test_contract_defines_exact_ownership_and_records(contract):
    assert contract["owners"] == EXPECTED_OWNERS
    assert contract["records"] == EXPECTED_RECORDS
    for name, fields in EXPECTED_RECORDS.items():
        assert required_fields(contract, name) == fields


def test_contract_defines_invalidation_events_errors_and_capabilities(contract):
    assert contract["verification_invalidation_events"] == [
        "workspace_edit",
        "subagent_edit",
        "generated_source",
        "new_untracked_source",
        "rollback",
    ]
    assert set(contract["error_codes"]) == EXPECTED_ERRORS
    assert len(contract["error_codes"]) == len(EXPECTED_ERRORS)
    assert contract["capabilities"] == {
        "harness": {"required_protocol": "harness-engineering", "required_major": 1},
        "guard": {"required_protocol": "goal-guard", "required_major": 1},
        "gsd": {
            "required_protocol": "gsd-layer6-adapter",
            "required_major": 1,
            "optional": True,
        },
    }


def test_state_transition_queries_follow_contract(contract):
    for source, targets in EXPECTED_TRANSITIONS.items():
        for target in EXPECTED_PHASES:
            assert transition_allowed(contract, source, target) is (target in targets)
    assert transition_allowed(contract, "unknown", "classified") is False
    assert transition_allowed(contract, "intake", "unknown") is False


def test_capability_compatibility_checks_name_and_major(contract):
    assert capability_compatible(
        contract,
        "harness",
        {"capability": "harness-engineering", "protocol_version": 1},
    )
    assert not capability_compatible(
        contract,
        "harness",
        {"capability": "wrong-name", "protocol_version": 1},
    )
    assert not capability_compatible(
        contract,
        "harness",
        {"capability": "harness-engineering", "protocol_version": 2},
    )
    assert not capability_compatible(contract, "unknown", {})


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda value: value["transitions"]["intake"].append("unknown"),
            "transition",
        ),
        (
            lambda value: value["records"]["classification_reply"].append("Goal"),
            "record",
        ),
        (lambda value: value.pop("owners"), "owners"),
        (lambda value: value.pop("error_codes"), "error_codes"),
        (
            lambda value: value["capabilities"]["guard"].update(
                {"required_major": "1"}
            ),
            "capability",
        ),
    ],
)
def test_invalid_contract_variants_are_rejected(contract, mutate, message):
    invalid = copy.deepcopy(contract)
    mutate(invalid)
    with pytest.raises(ValueError, match=rf"^invalid Goal Protocol v2: .*{message}"):
        validate_contract(invalid)


def test_load_contract_rejects_malformed_json():
    with pytest.raises(
        ValueError,
        match=(
            r"^invalid Goal Protocol v2: cannot load .*"
            r"Expecting property name enclosed in double quotes"
        ),
    ):
        load_contract(MALFORMED_PROTOCOL_ROOT)


def test_validate_contract_rejects_non_object_json_root():
    with pytest.raises(ValueError, match=r"^invalid Goal Protocol v2: JSON root"):
        validate_contract([])


def test_validation_is_structural_not_a_second_protocol_contract(contract):
    structurally_valid = copy.deepcopy(contract)
    structurally_valid["phases"] = ["alpha", "omega"]
    structurally_valid["transitions"] = {"alpha": ["omega"], "omega": []}
    structurally_valid["records"] = {"alternate_record": ["Alternate Field"]}
    structurally_valid["verification_invalidation_events"] = ["alternate_event"]

    assert validate_contract(structurally_valid) is None


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda value: value.update({"state_schema_versions": [7]}),
            r"state_schema_versions must be \[1\]",
        ),
        (
            lambda value: value["owners"].pop("closure"),
            "owners must match required assignments",
        ),
        (
            lambda value: value["error_codes"].__setitem__(
                0, "ALTERNATE_ERROR"
            ),
            "error_codes must match Goal Protocol v2",
        ),
        (
            lambda value: value["capabilities"]["harness"].update(
                {"required_protocol": "alternate-harness"}
            ),
            "capability harness required_protocol mismatch",
        ),
        (
            lambda value: value["capabilities"]["harness"].update(
                {"required_major": 7}
            ),
            "capability harness required_major mismatch",
        ),
        (
            lambda value: value["capabilities"]["harness"].update(
                {"optional": True}
            ),
            "capability harness optional mismatch",
        ),
        (
            lambda value: value["capabilities"]["gsd"].update(
                {"optional": False}
            ),
            "capability gsd optional mismatch",
        ),
    ],
)
def test_contract_rejects_safety_invariant_mutations(contract, mutate, message):
    invalid = copy.deepcopy(contract)
    mutate(invalid)

    with pytest.raises(ValueError, match=rf"^invalid Goal Protocol v2: {message}$"):
        validate_contract(invalid)


def test_capability_errors_follow_requirement_order(contract):
    invalid = copy.deepcopy(contract)
    invalid["capabilities"]["harness"]["required_protocol"] = "wrong-harness"
    invalid["capabilities"]["guard"]["required_major"] = 2
    invalid["capabilities"]["gsd"]["optional"] = False

    with pytest.raises(
        ValueError,
        match=(
            r"^invalid Goal Protocol v2: "
            r"capability harness required_protocol mismatch$"
        ),
    ):
        validate_contract(invalid)


def test_contract_rejects_non_integer_protocol_version(contract):
    invalid = copy.deepcopy(contract)
    invalid["protocol_version"] = 2.0

    with pytest.raises(ValueError, match=r"^invalid Goal Protocol v2: protocol_version"):
        validate_contract(invalid)


def test_contract_rejects_non_string_error_code(contract):
    invalid = copy.deepcopy(contract)
    invalid["error_codes"][0] = {"not": "a string"}

    with pytest.raises(ValueError, match=r"^invalid Goal Protocol v2: error_codes"):
        validate_contract(invalid)


def test_contract_rejects_unknown_top_level_keys(contract):
    invalid = copy.deepcopy(contract)
    invalid["unknown_top_level"] = True

    with pytest.raises(
        ValueError,
        match=(
            r"^invalid Goal Protocol v2: unknown top-level keys: "
            r"unknown_top_level$"
        ),
    ):
        validate_contract(invalid)


@pytest.mark.parametrize("owner", [1, []])
def test_contract_rejects_non_string_owner_with_stable_error(contract, owner):
    invalid = copy.deepcopy(contract)
    invalid["owners"]["closure"] = owner

    with pytest.raises(
        ValueError,
        match=r"^invalid Goal Protocol v2: owners contains an unknown owner$",
    ):
        validate_contract(invalid)
