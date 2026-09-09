from copy import deepcopy
import math
from pathlib import Path

import pytest

from delivery_contract import (
    MAX_CRITERIA,
    MAX_DELIVERY_BYTES,
    MAX_EVIDENCE,
    MAX_INVALIDATIONS,
    MAX_SLICES,
    canonical_delivery_bytes,
    validate_delivery_shape,
)
from delivery_fixtures import draft_criterion, draft_delivery, draft_slice


def issue_codes(value):
    return {(issue.code, issue.path) for issue in validate_delivery_shape(value)}


def test_draft_shape_is_valid_and_input_is_not_changed():
    delivery = draft_delivery()
    before = deepcopy(delivery)
    assert validate_delivery_shape(delivery) == []
    assert delivery == before


def test_canonical_bytes_are_deterministic_utf8_and_reject_nan():
    left = {"profile": "web-fullstack", "outcome": "note"}
    right = {"outcome": "note", "profile": "web-fullstack"}
    assert canonical_delivery_bytes(left) == canonical_delivery_bytes(right)
    assert b"note" in canonical_delivery_bytes(left)
    with pytest.raises(ValueError):
        canonical_delivery_bytes({"bad": math.nan})


@pytest.mark.parametrize(
    ("mutate", "code", "path"),
    [
        (lambda d: d.update(schema_version=True), "DELIVERY_TYPE_INVALID", "delivery.schema_version"),
        (lambda d: d.update(extra="x"), "DELIVERY_UNKNOWN_FIELD", "delivery.extra"),
        (
            lambda d: d["contract"]["approval"].update(recorded_at="2026-09-08"),
            "DELIVERY_TIME_INVALID",
            "delivery.contract.approval.recorded_at",
        ),
        (
            lambda d: d["contract"].update(delivery_target="production"),
            "DELIVERY_ENUM_INVALID",
            "delivery.contract.delivery_target",
        ),
    ],
)
def test_invalid_scalar_and_unknown_fields_are_rejected(mutate, code, path):
    delivery = draft_delivery()
    mutate(delivery)
    assert (code, path) in issue_codes(delivery)


def _fill_collection(name, limit):
    delivery = draft_delivery()
    if name == "slices":
        delivery[name] = [draft_slice(f"s-{index}") for index in range(limit)]
    elif name == "criteria":
        delivery[name] = [
            draft_criterion(f"criterion-{index}", "notes") for index in range(limit)
        ]
    elif name == "evidence":
        delivery[name] = [
            {
                "evidence_id": f"e-{index}",
                "criterion_id": "notes.persist",
                "revision": 1,
                "provenance": "observed_execution",
                "entry_id": "fixture-check",
                "cwd": ".",
                "started_at": "2026-09-08T00:00:01+00:00",
                "finished_at": "2026-09-08T00:00:02+00:00",
                "observer": "fixture-runner",
                "result": "pass",
                "exit_code": 0,
                "source_fingerprint": {
                    "algorithm": "sha256-manifest-v1",
                    "digest": "a" * 64,
                },
                "environment": {
                    "facts": {"python": "3.14.3"},
                    "observed_at": "2026-09-08T00:00:00+00:00",
                    "source": "fixture",
                    "status": "observed",
                },
                "isolation": {
                    "mode": "isolated-snapshot",
                    "snapshot_id": f"snapshot-{index}",
                    "source_digest": "b" * 64,
                    "observer": "fixture-runner",
                },
                "outputs": [],
                "invalidation_count": 0,
            }
            for index in range(limit)
        ]
    else:
        delivery[name] = [
            {
                "invalidation_id": f"i-{index}",
                "event": "workspace_edit",
                "at": "2026-09-08T00:00:03+00:00",
                "reason": "fixture change",
                "criterion_ids": [],
                "evidence_ids": [],
                "mutation_seq": index,
            }
            for index in range(limit)
        ]
    return delivery


@pytest.mark.parametrize(
    ("name", "limit"),
    [
        ("slices", MAX_SLICES),
        ("criteria", MAX_CRITERIA),
        ("evidence", MAX_EVIDENCE),
        ("invalidations", MAX_INVALIDATIONS),
    ],
)
def test_collection_limit_allows_exact_and_rejects_one_over(name, limit):
    exact = _fill_collection(name, limit)
    assert not any(issue.code == "DELIVERY_LIMIT_EXCEEDED" for issue in validate_delivery_shape(exact))
    over = _fill_collection(name, limit + 1)
    assert ("DELIVERY_LIMIT_EXCEEDED", f"delivery.{name}") in issue_codes(over)


def test_delivery_utf8_size_limit_allows_exact_and_rejects_one_over():
    delivery = draft_delivery()
    delivery["contract"]["outcome"] = ""
    base_size = len(canonical_delivery_bytes(delivery))
    delivery["contract"]["outcome"] = "x" * (MAX_DELIVERY_BYTES - base_size)
    assert len(canonical_delivery_bytes(delivery)) == MAX_DELIVERY_BYTES
    assert not any(issue.code == "DELIVERY_SIZE_EXCEEDED" for issue in validate_delivery_shape(delivery))
    delivery["contract"]["outcome"] += "x"
    assert ("DELIVERY_SIZE_EXCEEDED", "delivery") in issue_codes(delivery)


def test_delivery_import_resolves_to_candidate_source():
    import delivery_contract
    import delivery_fixtures

    candidate_root = Path(__file__).resolve().parents[1]
    assert Path(delivery_contract.__file__).resolve() == (
        candidate_root / "scripts" / "delivery_contract.py"
    ).resolve()
    assert Path(delivery_fixtures.__file__).resolve() == (
        candidate_root / "tests" / "delivery_fixtures.py"
    ).resolve()
