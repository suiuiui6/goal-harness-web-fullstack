from copy import deepcopy
from datetime import datetime

from delivery_contract import (
    MAX_INVALIDATIONS,
    Issue,
    canonical_delivery_bytes,
    validate_delivery_shape,
)


def _issue(code, path, message):
    return Issue(code, path, message)


def _time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _unique_ids(items, path, label):
    seen = set()
    issues = []
    for index, item in enumerate(items):
        identifier = item.get(label) if isinstance(item, dict) else None
        if identifier in seen:
            issues.append(_issue("DELIVERY_REFERENCE_INVALID", f"{path}[{index}].{label}", "duplicate ID"))
        seen.add(identifier)
    return issues


def validate_delivery_links(delivery: dict) -> list[Issue]:
    shape_errors = validate_delivery_shape(delivery)
    if shape_errors:
        return shape_errors
    issues = []
    slices = delivery["slices"]
    criteria = delivery["criteria"]
    evidence = delivery["evidence"]
    invalidations = delivery["invalidations"]
    issues.extend(_unique_ids(slices, "delivery.slices", "slice_id"))
    issues.extend(_unique_ids(criteria, "delivery.criteria", "criterion_id"))
    issues.extend(_unique_ids(evidence, "delivery.evidence", "evidence_id"))
    issues.extend(_unique_ids(invalidations, "delivery.invalidations", "invalidation_id"))
    slice_ids = {item["slice_id"] for item in slices}
    criterion_ids = {item["criterion_id"] for item in criteria}
    evidence_ids = {item["evidence_id"] for item in evidence}
    criterion_by_id = {item["criterion_id"]: item for item in criteria}
    slice_by_id = {item["slice_id"]: item for item in slices}
    for item in slices:
        for dependency in item["depends_on"]:
            if dependency not in slice_ids:
                issues.append(
                    _issue(
                        "DELIVERY_REFERENCE_INVALID",
                        f"delivery.slices[{item['slice_id']}].depends_on",
                        f"unknown slice {dependency}",
                    )
                )
        for criterion_id in item["criterion_ids"]:
            criterion = criterion_by_id.get(criterion_id)
            if criterion is None or criterion["slice_id"] != item["slice_id"]:
                issues.append(
                    _issue(
                        "DELIVERY_REFERENCE_INVALID",
                        f"delivery.slices[{item['slice_id']}].criterion_ids",
                        f"criterion {criterion_id} has inconsistent ownership",
                    )
                )
        for surface_name, surface in item["surfaces"].items():
            for evidence_id in surface["evidence_ids"]:
                if evidence_id not in evidence_ids:
                    issues.append(
                        _issue(
                            "DELIVERY_REFERENCE_INVALID",
                            f"delivery.slices[{item['slice_id']}].surfaces.{surface_name}.evidence_ids",
                            f"unknown evidence {evidence_id}",
                        )
                    )
    for criterion in criteria:
        if criterion["slice_id"] not in slice_ids:
            issues.append(
                _issue(
                    "DELIVERY_REFERENCE_INVALID",
                    f"delivery.criteria[{criterion['criterion_id']}].slice_id",
                    "unknown slice",
                )
            )
        elif criterion["criterion_id"] not in slice_by_id[criterion["slice_id"]]["criterion_ids"]:
            issues.append(
                _issue(
                    "DELIVERY_REFERENCE_INVALID",
                    f"delivery.criteria[{criterion['criterion_id']}]",
                    "criterion is not listed by its slice",
                )
            )
        if criterion["revision"] != delivery["contract"]["revision"]:
            issues.append(
                _issue(
                    "DELIVERY_REVISION_INVALID",
                    f"delivery.criteria[{criterion['criterion_id']}].revision",
                    "criterion revision must match contract revision",
                )
            )
        for evidence_id in criterion["evidence_ids"]:
            matching = next((item for item in evidence if item["evidence_id"] == evidence_id), None)
            if matching is None or matching["criterion_id"] != criterion["criterion_id"]:
                issues.append(
                    _issue(
                        "DELIVERY_REFERENCE_INVALID",
                        f"delivery.criteria[{criterion['criterion_id']}].evidence_ids",
                        f"evidence {evidence_id} has inconsistent ownership",
                    )
                )
        judgment = criterion["judgment"]
        if judgment is not None and not set(judgment["evidence_ids"]).issubset(set(criterion["evidence_ids"])):
            issues.append(
                _issue(
                    "DELIVERY_REFERENCE_INVALID",
                    f"delivery.criteria[{criterion['criterion_id']}].judgment.evidence_ids",
                    "judgment references evidence outside this criterion",
                )
            )
    for item in evidence:
        if item["criterion_id"] not in criterion_ids:
            issues.append(
                _issue(
                    "DELIVERY_REFERENCE_INVALID",
                    f"delivery.evidence[{item['evidence_id']}].criterion_id",
                    "unknown criterion",
                )
            )
        if item["revision"] != delivery["contract"]["revision"]:
            issues.append(
                _issue(
                    "DELIVERY_REVISION_INVALID",
                    f"delivery.evidence[{item['evidence_id']}].revision",
                    "evidence revision must match contract revision",
                )
            )
    approval = delivery["contract"]["approval"]
    if approval["revision"] != delivery["contract"]["revision"]:
        issues.append(
            _issue("DELIVERY_REVISION_INVALID", "delivery.contract.approval.revision", "approval revision mismatch")
        )
    for item in invalidations:
        for evidence_id in item["evidence_ids"]:
            if evidence_id not in evidence_ids:
                issues.append(
                    _issue(
                        "DELIVERY_REFERENCE_INVALID",
                        f"delivery.invalidations[{item['invalidation_id']}].evidence_ids",
                        f"unknown evidence {evidence_id}",
                    )
                )
        for criterion_id in item["criterion_ids"]:
            if criterion_id not in criterion_ids:
                issues.append(
                    _issue(
                        "DELIVERY_REFERENCE_INVALID",
                        f"delivery.invalidations[{item['invalidation_id']}].criterion_ids",
                        f"unknown criterion {criterion_id}",
                    )
                )
    dependencies = {item["slice_id"]: item["depends_on"] for item in slices}
    visiting = set()
    visited = set()

    def visit(slice_id):
        if slice_id in visiting:
            issues.append(_issue("DELIVERY_CYCLE", f"delivery.slices[{slice_id}].depends_on", "dependency cycle"))
            return
        if slice_id in visited or slice_id not in dependencies:
            return
        visiting.add(slice_id)
        for dependency in dependencies[slice_id]:
            visit(dependency)
        visiting.remove(slice_id)
        visited.add(slice_id)

    for slice_id in dependencies:
        visit(slice_id)
    return issues


def _criterion_pass_errors(delivery, criterion):
    issues = []
    criterion_id = criterion["criterion_id"]
    evidence_by_id = {item["evidence_id"]: item for item in delivery["evidence"]}
    invalidated = {
        evidence_id
        for item in delivery["invalidations"]
        for evidence_id in item["evidence_ids"]
    }
    if not criterion["evidence_ids"]:
        return [_issue("DELIVERY_EVIDENCE_INSUFFICIENT", f"delivery.criteria[{criterion_id}]", "pass requires evidence")]
    judgment = criterion["judgment"]
    if judgment is None or judgment["result"] != "pass":
        issues.append(_issue("DELIVERY_EVIDENCE_INSUFFICIENT", f"delivery.criteria[{criterion_id}].judgment", "pass requires a passing judgment"))
        return issues
    if judgment["invalidation_count"] != len(delivery["invalidations"]):
        issues.append(_issue("DELIVERY_REVALIDATION_REQUIRED", f"delivery.criteria[{criterion_id}].judgment.invalidation_count", "judgment is from an earlier validation generation"))
    if set(judgment["evidence_ids"]) != set(criterion["evidence_ids"]):
        issues.append(_issue("DELIVERY_EVIDENCE_INSUFFICIENT", f"delivery.criteria[{criterion_id}].judgment.evidence_ids", "judgment must cover criterion evidence"))
    judgment_at = _time(judgment["at"])
    latest_invalidation = max(
        (_time(item["at"]) for item in delivery["invalidations"]),
        default=None,
    )
    for evidence_id in criterion["evidence_ids"]:
        item = evidence_by_id.get(evidence_id)
        path = f"delivery.evidence[{evidence_id}]"
        if item is None:
            issues.append(_issue("DELIVERY_REFERENCE_INVALID", path, "evidence is missing"))
            continue
        if evidence_id in invalidated:
            issues.append(_issue("DELIVERY_EVIDENCE_INVALIDATED", path, "evidence was invalidated"))
        if item["provenance"] != "observed_execution" or item["result"] != "pass":
            issues.append(_issue("DELIVERY_EVIDENCE_INSUFFICIENT", path, "pass requires observed passing execution"))
        if item["entry_id"] != criterion["verification"]["entry_id"]:
            issues.append(_issue("DELIVERY_EVIDENCE_INSUFFICIENT", path, "entry does not match criterion verification"))
        if item["invalidation_count"] != len(delivery["invalidations"]):
            issues.append(_issue("DELIVERY_REVALIDATION_REQUIRED", f"{path}.invalidation_count", "evidence is from an earlier validation generation"))
        if item["environment"]["status"] != "observed" or item["isolation"]["mode"] != "isolated-snapshot":
            issues.append(_issue("DELIVERY_EVIDENCE_INSUFFICIENT", path, "environment and isolation observation are required"))
        if not item["outputs"]:
            issues.append(_issue("DELIVERY_EVIDENCE_INSUFFICIENT", path, "at least one output is required"))
        started = _time(item["started_at"])
        finished = _time(item["finished_at"])
        if latest_invalidation is not None and started <= latest_invalidation:
            issues.append(_issue("DELIVERY_REVALIDATION_REQUIRED", f"{path}.started_at", "execution must start after the latest invalidation"))
        if judgment_at < finished:
            issues.append(_issue("DELIVERY_TIME_INVALID", f"delivery.criteria[{criterion_id}].judgment.at", "judgment must follow execution"))
    return issues


def acceptance_errors(delivery: dict) -> list[Issue]:
    issues = validate_delivery_links(delivery)
    if issues:
        return issues
    required = [item for item in delivery["criteria"] if item["required"]]
    if not required:
        return [_issue("DELIVERY_REQUIRED_EMPTY", "delivery.criteria", "at least one required criterion is required")]
    for criterion in delivery["criteria"]:
        if criterion["status"] == "pass":
            issues.extend(_criterion_pass_errors(delivery, criterion))
        elif criterion["required"] and criterion["status"] not in {"not_applicable"}:
            issues.append(
                _issue(
                    "DELIVERY_REQUIRED_EMPTY",
                    f"delivery.criteria[{criterion['criterion_id']}]",
                    "required criterion is not complete",
                )
            )
        elif criterion["required"] and criterion["status"] == "not_applicable":
            if criterion["judgment"] is None or criterion["judgment"]["result"] != "not_applicable":
                issues.append(
                    _issue(
                        "DELIVERY_EVIDENCE_INSUFFICIENT",
                        f"delivery.criteria[{criterion['criterion_id']}]",
                        "not_applicable requires an explicit judgment",
                    )
                )
    return issues


def pass_evidence_errors(delivery: dict) -> list[Issue]:
    """Validate every criterion already claiming pass without requiring peers."""

    issues = validate_delivery_links(delivery)
    if issues:
        return issues
    for criterion in delivery["criteria"]:
        if criterion["status"] == "pass":
            issues.extend(_criterion_pass_errors(delivery, criterion))
    return issues


def _delivery_from_state(state):
    return state.get("delivery") if isinstance(state, dict) else None


def validate_delivery_transition(previous: dict, candidate: dict) -> list[Issue]:
    previous_delivery = _delivery_from_state(previous)
    candidate_delivery = _delivery_from_state(candidate)
    if previous_delivery is None and candidate_delivery is not None:
        return [_issue("DELIVERY_BINDING_IMMUTABLE", "delivery", "legacy state cannot add delivery")]
    if previous_delivery is not None and candidate_delivery is None:
        return [_issue("DELIVERY_BINDING_IMMUTABLE", "delivery", "active delivery cannot be removed")]
    if previous_delivery is None:
        return []
    issues = validate_delivery_links(candidate_delivery)
    if candidate_delivery.get("schema_version") != previous_delivery.get("schema_version") or candidate_delivery.get("profile") != previous_delivery.get("profile"):
        issues.append(_issue("DELIVERY_BINDING_IMMUTABLE", "delivery", "profile and schema are immutable"))
    old_invalidations = previous_delivery["invalidations"]
    if candidate_delivery["invalidations"][: len(old_invalidations)] != old_invalidations:
        issues.append(_issue("DELIVERY_INVALIDATION_HISTORY_CHANGED", "delivery.invalidations", "invalidation history is append-only"))
    candidate_evidence = {item["evidence_id"]: item for item in candidate_delivery["evidence"]}
    for item in previous_delivery["evidence"]:
        if candidate_evidence.get(item["evidence_id"]) != item:
            issues.append(_issue("DELIVERY_INVALIDATION_HISTORY_CHANGED", f"delivery.evidence[{item['evidence_id']}]", "historical evidence cannot be replaced"))
    old_revision = previous_delivery["contract"]["revision"]
    new_revision = candidate_delivery["contract"]["revision"]
    if new_revision < old_revision:
        issues.append(_issue("DELIVERY_REVISION_INVALID", "delivery.contract.revision", "revision cannot decrease"))
    elif new_revision == old_revision:
        if canonical_delivery_bytes(candidate_delivery["contract"]) != canonical_delivery_bytes(previous_delivery["contract"]):
            issues.append(_issue("DELIVERY_APPROVAL_REQUIRED", "delivery.contract", "semantic contract changes require a new revision and confirmation"))
        old_required = {item["criterion_id"] for item in previous_delivery["criteria"] if item["required"]}
        new_required = {item["criterion_id"] for item in candidate_delivery["criteria"] if item["required"]}
        if not old_required.issubset(new_required):
            issues.append(_issue("DELIVERY_APPROVAL_REQUIRED", "delivery.criteria", "required criteria cannot be lowered"))
    else:
        approval = candidate_delivery["contract"]["approval"]
        if approval["revision"] != new_revision or approval["confirmation_id"] == previous_delivery["contract"]["approval"]["confirmation_id"]:
            issues.append(_issue("DELIVERY_APPROVAL_REQUIRED", "delivery.contract.approval", "new revision requires a new confirmation"))
    return issues


def invalidate_delivery(
    delivery: dict,
    *,
    event: str,
    at: str,
    reason: str,
    mutation_seq: int,
) -> dict:
    if len(delivery.get("invalidations", [])) >= MAX_INVALIDATIONS:
        raise ValueError("delivery invalidation history is at capacity")
    if validate_delivery_shape(delivery) or validate_delivery_links(delivery):
        raise ValueError("delivery must be valid before invalidation")
    updated = deepcopy(delivery)
    evidence_ids = [
        item["evidence_id"]
        for item in updated["evidence"]
        if item["evidence_id"]
        not in {old for entry in updated["invalidations"] for old in entry["evidence_ids"]}
    ]
    criterion_ids = [
        item["criterion_id"] for item in updated["criteria"] if item["status"] == "pass"
    ]
    for criterion in updated["criteria"]:
        if criterion["criterion_id"] in criterion_ids:
            criterion["status"] = "stale"
    updated["invalidations"].append(
        {
            "invalidation_id": f"I{len(updated['invalidations']) + 1}",
            "event": event,
            "at": at,
            "reason": reason,
            "criterion_ids": criterion_ids,
            "evidence_ids": evidence_ids,
            "mutation_seq": mutation_seq,
        }
    )
    if validate_delivery_shape(updated) or validate_delivery_links(updated):
        raise ValueError("invalidation would produce an invalid delivery")
    return updated
