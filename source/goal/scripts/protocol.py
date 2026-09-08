"""Loader and semantic helpers for the Goal Protocol v2 contract."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


_PREFIX = "invalid Goal Protocol v2: "
EXPECTED_TOP_LEVEL_KEYS = {
    "protocol_id",
    "protocol_version",
    "state_schema_versions",
    "phases",
    "transitions",
    "owners",
    "records",
    "verification_invalidation_events",
    "capabilities",
    "error_codes",
}
STATE_SCHEMA_VERSIONS = (1,)
REQUIRED_OWNER_ASSIGNMENTS = {
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
ERROR_CODES = (
    "DEPENDENCY_MISSING",
    "PROTOCOL_VERSION_MISMATCH",
    "CONFIRMATION_REQUIRED",
    "INVALID_STATE_TRANSITION",
    "STALE_VERIFICATION",
    "CAPABILITY_DISABLED",
)
CAPABILITY_REQUIREMENTS = (
    ("harness", "harness-engineering", 1, False),
    ("guard", "goal-guard", 1, False),
    ("gsd", "gsd-layer6-adapter", 1, True),
)


def _invalid(detail: str) -> ValueError:
    return ValueError(f"{_PREFIX}{detail}")


def _is_nonempty_unique_strings(value: Any) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(item, str) and bool(item) for item in value)
        and len(value) == len(set(value))
    )


def load_contract(root: str | Path) -> dict[str, Any]:
    """Load and validate ``references/protocol.json`` below a Goal Skill root."""

    path = Path(root) / "references" / "protocol.json"
    try:
        with path.open(encoding="utf-8") as stream:
            contract = json.load(stream)
    except (OSError, json.JSONDecodeError) as exc:
        raise _invalid(f"cannot load {path}: {exc}") from exc

    if not isinstance(contract, dict):
        raise _invalid("JSON root must be an object")
    validate_contract(contract)
    return contract


def validate_contract(contract: Any) -> None:
    """Raise ``ValueError`` unless *contract* is the Goal Protocol v2 contract."""

    if not isinstance(contract, dict):
        raise _invalid("JSON root must be an object")
    extras = set(contract) - EXPECTED_TOP_LEVEL_KEYS
    if extras:
        raise _invalid(f"unknown top-level keys: {', '.join(sorted(extras))}")
    if contract.get("protocol_id") != "goal-protocol":
        raise _invalid("protocol_id must be goal-protocol")
    protocol_version = contract.get("protocol_version")
    if (
        not isinstance(protocol_version, int)
        or isinstance(protocol_version, bool)
        or protocol_version != 2
    ):
        raise _invalid("protocol_version must be 2")
    schema_versions = contract.get("state_schema_versions")
    if (
        not isinstance(schema_versions, list)
        or not schema_versions
        or any(
            not isinstance(version, int)
            or isinstance(version, bool)
            or version < 1
            for version in schema_versions
        )
        or len(schema_versions) != len(set(schema_versions))
    ):
        raise _invalid("state_schema_versions must be unique positive integers")
    if tuple(schema_versions) != STATE_SCHEMA_VERSIONS:
        raise _invalid("state_schema_versions must be [1]")

    phases = contract.get("phases")
    if not _is_nonempty_unique_strings(phases):
        raise _invalid("phases must be non-empty unique strings")

    transitions = contract.get("transitions")
    if not isinstance(transitions, dict) or set(transitions) != set(phases):
        raise _invalid("transitions must define every phase exactly once")
    for source, targets in transitions.items():
        if not isinstance(targets, list):
            raise _invalid(f"transition targets for {source} must be a list")
        if any(not isinstance(target, str) or target not in phases for target in targets):
            raise _invalid(f"transition from {source} has an unknown target")
        if len(targets) != len(set(targets)):
            raise _invalid(f"transition from {source} has duplicate targets")

    owners = contract.get("owners")
    if (
        not isinstance(owners, dict)
        or not owners
        or any(not isinstance(name, str) or not name for name in owners)
    ):
        raise _invalid("owners must define protocol responsibilities")
    allowed_owner_names = set(REQUIRED_OWNER_ASSIGNMENTS.values())
    if any(
        not isinstance(owner, str) or owner not in allowed_owner_names
        for owner in owners.values()
    ):
        raise _invalid("owners contains an unknown owner")
    if owners != REQUIRED_OWNER_ASSIGNMENTS:
        raise _invalid("owners must match required assignments")

    records = contract.get("records")
    if (
        not isinstance(records, dict)
        or not records
        or any(not isinstance(name, str) or not name for name in records)
    ):
        raise _invalid("records must define protocol records")
    for name, fields in records.items():
        if not _is_nonempty_unique_strings(fields):
            raise _invalid(f"record {name} fields must be non-empty unique strings")

    if not _is_nonempty_unique_strings(
        contract.get("verification_invalidation_events")
    ):
        raise _invalid(
            "verification_invalidation_events must be non-empty unique strings"
        )

    error_codes = contract.get("error_codes")
    if not _is_nonempty_unique_strings(error_codes):
        raise _invalid("error_codes must be non-empty unique strings")
    if tuple(error_codes) != ERROR_CODES:
        raise _invalid("error_codes must match Goal Protocol v2")

    capabilities = contract.get("capabilities")
    required_capability_names = {
        name for name, _, _, _ in CAPABILITY_REQUIREMENTS
    }
    if (
        not isinstance(capabilities, dict)
        or set(capabilities) != required_capability_names
    ):
        raise _invalid("capabilities must define harness, guard, and gsd")
    for name, expected_protocol, expected_major, expected_optional in (
        CAPABILITY_REQUIREMENTS
    ):
        descriptor = capabilities[name]
        if not isinstance(descriptor, dict):
            raise _invalid(f"capability {name} must be an object")
        descriptor_keys = set(descriptor)
        if not {"required_protocol", "required_major"} <= descriptor_keys or not (
            descriptor_keys <= {"required_protocol", "required_major", "optional"}
        ):
            raise _invalid(f"capability {name} has invalid fields")
        required_protocol = descriptor.get("required_protocol")
        if not isinstance(required_protocol, str) or not required_protocol:
            raise _invalid(f"capability {name} required_protocol must be a string")
        if required_protocol != expected_protocol:
            raise _invalid(f"capability {name} required_protocol mismatch")
        required_major = descriptor.get("required_major")
        if (
            not isinstance(required_major, int)
            or isinstance(required_major, bool)
            or required_major < 1
        ):
            raise _invalid(
                f"capability {name} required_major must be a positive integer"
            )
        if required_major != expected_major:
            raise _invalid(f"capability {name} required_major mismatch")
        if "optional" in descriptor and not isinstance(descriptor["optional"], bool):
            raise _invalid(f"capability {name} optional must be a boolean")
        if descriptor.get("optional", False) is not expected_optional:
            raise _invalid(f"capability {name} optional mismatch")


def transition_allowed(contract: dict[str, Any], source: str, target: str) -> bool:
    """Return whether *source* may advance directly to *target*."""

    targets = contract.get("transitions", {}).get(source, [])
    return isinstance(targets, list) and target in targets


def required_fields(contract: dict[str, Any], record: str) -> list[str]:
    """Return a copy of the required field list for *record*."""

    fields = contract.get("records", {}).get(record)
    if not isinstance(fields, list):
        raise _invalid(f"unknown record {record}")
    return list(fields)


def capability_compatible(
    contract: dict[str, Any], name: str, descriptor: Any
) -> bool:
    """Check a discovered capability name and protocol major for compatibility."""

    requirement = contract.get("capabilities", {}).get(name)
    if not isinstance(requirement, dict) or not isinstance(descriptor, dict):
        return False
    return (
        descriptor.get("capability") == requirement.get("required_protocol")
        and descriptor.get("protocol_version") == requirement.get("required_major")
        and isinstance(descriptor.get("protocol_version"), int)
        and not isinstance(descriptor.get("protocol_version"), bool)
    )


def delivery_feature_available(
    contract: dict[str, Any], descriptor: Any
) -> bool:
    """Return whether the selected Guard supports Web full-stack delivery v1."""

    if not capability_compatible(contract, "guard", descriptor):
        return False
    features = descriptor.get("features")
    schemas = descriptor.get("state_schema_versions")
    commands = descriptor.get("commands")
    modes = descriptor.get("enforcement_modes")
    return (
        isinstance(features, list)
        and all(isinstance(item, str) for item in features)
        and "web-fullstack-delivery-v1" in features
        and isinstance(schemas, list)
        and 1 in schemas
        and isinstance(commands, list)
        and {"initialize-state", "write-state", "audit"}.issubset(commands)
        and isinstance(modes, list)
        and "audit-only-windows" in modes
    )
