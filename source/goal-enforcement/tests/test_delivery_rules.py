from copy import deepcopy

import pytest

from delivery_fixtures import (
    accepted_delivery,
    draft_criterion,
    draft_delivery,
    draft_slice,
    observed_evidence,
    passing_judgment,
)
from delivery_rules import (
    acceptance_errors,
    invalidate_delivery,
    validate_delivery_links,
    validate_delivery_transition,
)


def codes(issues):
    return {issue.code for issue in issues}


def state(delivery=None):
    value = {"phase": "executing", "scope_result": "incomplete"}
    if delivery is not None:
        value["delivery"] = delivery
    return value


def test_empty_required_cannot_pass():
    assert "DELIVERY_REQUIRED_EMPTY" in codes(acceptance_errors(draft_delivery()))


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        (
            lambda d: d.update(
                slices=[
                    {**draft_slice("a"), "depends_on": ["b"]},
                    {**draft_slice("b"), "depends_on": ["a"]},
                ]
            ),
            "DELIVERY_CYCLE",
        ),
        (
            lambda d: d.update(slices=[draft_slice("a", ["missing"])]),
            "DELIVERY_REFERENCE_INVALID",
        ),
        (
            lambda d: d.update(slices=[draft_slice("a"), draft_slice("a")]),
            "DELIVERY_REFERENCE_INVALID",
        ),
        (
            lambda d: d.update(
                slices=[draft_slice("a")],
                criteria=[draft_criterion("c", "a")],
            ),
            "DELIVERY_REFERENCE_INVALID",
        ),
    ],
)
def test_links_reject_cycles_dangling_duplicates_and_one_way_ownership(mutate, expected):
    delivery = draft_delivery()
    mutate(delivery)
    assert expected in codes(validate_delivery_links(delivery))


def test_revision_and_approval_must_match():
    delivery = accepted_delivery()
    delivery["contract"]["approval"]["revision"] = 2
    delivery["criteria"][0]["revision"] = 2
    assert "DELIVERY_REVISION_INVALID" in codes(validate_delivery_links(delivery))


def test_legacy_binding_is_immutable():
    errors = validate_delivery_transition(state(), state(draft_delivery()))
    assert "DELIVERY_BINDING_IMMUTABLE" in codes(errors)


def test_active_delivery_cannot_be_removed_or_changed():
    previous = state(draft_delivery())
    assert "DELIVERY_BINDING_IMMUTABLE" in codes(validate_delivery_transition(previous, state()))
    candidate = deepcopy(previous)
    candidate["delivery"]["profile"] = "other"
    assert "DELIVERY_BINDING_IMMUTABLE" in codes(validate_delivery_transition(previous, candidate))


def test_same_revision_cannot_lower_required_or_replace_evidence():
    previous = state(accepted_delivery())
    lowered = deepcopy(previous)
    lowered["delivery"]["criteria"][0]["required"] = False
    assert "DELIVERY_APPROVAL_REQUIRED" in codes(validate_delivery_transition(previous, lowered))
    replaced = deepcopy(previous)
    replaced["delivery"]["evidence"][0]["finished_at"] = "2026-09-08T00:00:04+00:00"
    assert "DELIVERY_INVALIDATION_HISTORY_CHANGED" in codes(validate_delivery_transition(previous, replaced))


def test_new_revision_with_matching_confirmation_is_allowed():
    previous = state(accepted_delivery())
    candidate = deepcopy(previous)
    candidate["delivery"]["contract"]["revision"] = 2
    candidate["delivery"]["contract"]["outcome"] = "The owner can persist and delete a note."
    candidate["delivery"]["contract"]["approval"] = {
        "revision": 2,
        "confirmation_id": "fixture-approval-2",
        "source": "fixture://approval/2",
        "recorded_at": "2026-09-08T00:01:00+00:00",
    }
    candidate["delivery"]["criteria"][0]["revision"] = 2
    candidate["delivery"]["criteria"][0]["status"] = "pending"
    candidate["delivery"]["criteria"][0]["evidence_ids"] = []
    candidate["delivery"]["criteria"][0]["judgment"] = None
    assert "DELIVERY_APPROVAL_REQUIRED" not in codes(validate_delivery_transition(previous, candidate))


def test_invalidation_is_append_only_and_marks_pass_stale():
    delivery = accepted_delivery()
    invalidated = invalidate_delivery(
        delivery,
        event="workspace_edit",
        at="2026-09-08T00:00:04+00:00",
        reason="source changed",
        mutation_seq=1,
    )
    assert delivery["invalidations"] == []
    assert invalidated["criteria"][0]["status"] == "stale"
    assert invalidated["invalidations"][0]["evidence_ids"] == ["E1"]
    changed = state(deepcopy(invalidated))
    changed["delivery"]["invalidations"][0]["reason"] = "rewritten"
    assert "DELIVERY_INVALIDATION_HISTORY_CHANGED" in codes(
        validate_delivery_transition(state(invalidated), changed)
    )


def test_reverted_source_cannot_resurrect_invalidated_evidence():
    delivery = invalidate_delivery(
        accepted_delivery(),
        event="workspace_edit",
        at="2026-09-08T00:00:04+00:00",
        reason="source changed then restored",
        mutation_seq=1,
    )
    delivery["criteria"][0]["status"] = "pass"
    assert {"DELIVERY_EVIDENCE_INVALIDATED", "DELIVERY_REVALIDATION_REQUIRED"} & codes(
        acceptance_errors(delivery)
    )


def test_fresh_execution_after_invalidation_can_pass():
    delivery = invalidate_delivery(
        accepted_delivery(),
        event="workspace_edit",
        at="2026-09-08T00:00:04+00:00",
        reason="source changed",
        mutation_seq=1,
    )
    evidence = observed_evidence(
        "E2",
        invalidation_count=1,
        started_at="2026-09-08T00:00:05+00:00",
        finished_at="2026-09-08T00:00:06+00:00",
    )
    delivery["evidence"].append(evidence)
    delivery["criteria"][0].update(
        status="pass",
        evidence_ids=["E2"],
        judgment=passing_judgment("E2", 1, "2026-09-08T00:00:07+00:00"),
    )
    assert acceptance_errors(delivery) == []


def test_new_judgment_does_not_revive_old_execution():
    delivery = invalidate_delivery(
        accepted_delivery(),
        event="workspace_edit",
        at="2026-09-08T00:00:04+00:00",
        reason="source changed",
        mutation_seq=1,
    )
    delivery["criteria"][0].update(
        status="pass",
        evidence_ids=["E1"],
        judgment=passing_judgment("E1", 1, "2026-09-08T00:00:07+00:00"),
    )
    assert "DELIVERY_EVIDENCE_INVALIDATED" in codes(acceptance_errors(delivery))


def test_invalidation_during_verification_requires_rerun():
    delivery = invalidate_delivery(
        accepted_delivery(),
        event="workspace_edit",
        at="2026-09-08T00:00:04+00:00",
        reason="first change",
        mutation_seq=1,
    )
    delivery["evidence"].append(
        observed_evidence(
            "E2",
            invalidation_count=1,
            started_at="2026-09-08T00:00:05+00:00",
            finished_at="2026-09-08T00:00:07+00:00",
        )
    )
    delivery = invalidate_delivery(
        delivery,
        event="environment_change",
        at="2026-09-08T00:00:06+00:00",
        reason="dependency changed during verification",
        mutation_seq=1,
    )
    delivery["criteria"][0].update(
        status="pass",
        evidence_ids=["E2"],
        judgment=passing_judgment("E2", 2, "2026-09-08T00:00:08+00:00"),
    )
    assert "DELIVERY_REVALIDATION_REQUIRED" in codes(acceptance_errors(delivery))


def test_full_invalidation_history_cannot_be_deleted_or_reordered():
    invalidated = invalidate_delivery(
        accepted_delivery(),
        event="workspace_edit",
        at="2026-09-08T00:00:04+00:00",
        reason="source changed",
        mutation_seq=1,
    )
    candidate = deepcopy(invalidated)
    candidate["invalidations"] = []
    assert "DELIVERY_INVALIDATION_HISTORY_CHANGED" in codes(
        validate_delivery_transition(state(invalidated), state(candidate))
    )


def test_invalidation_capacity_rejects_without_mutating_input():
    delivery = draft_delivery()
    delivery["invalidations"] = [
        {
            "invalidation_id": f"I{index}",
            "event": "workspace_edit",
            "at": "2026-09-08T00:00:04+00:00",
            "reason": "source changed",
            "criterion_ids": [],
            "evidence_ids": [],
            "mutation_seq": index,
        }
        for index in range(256)
    ]
    before = deepcopy(delivery)
    with pytest.raises(ValueError):
        invalidate_delivery(
            delivery,
            event="workspace_edit",
            at="2026-09-08T00:00:05+00:00",
            reason="one too many",
            mutation_seq=257,
        )
    assert delivery == before
