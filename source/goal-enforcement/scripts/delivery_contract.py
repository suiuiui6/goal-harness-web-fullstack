import json
import math
from datetime import datetime
from typing import NamedTuple


MAX_SLICES = 128
MAX_CRITERIA = 512
MAX_EVIDENCE = 2048
MAX_INVALIDATIONS = 256
MAX_DELIVERY_BYTES = 2 * 1024 * 1024

DELIVERY_TARGETS = {"local-runnable", "deployable", "deployed"}
APPLICABILITY = {"changed", "reused", "not_applicable"}
CRITERION_STATUSES = {
    "pending",
    "in_progress",
    "pass",
    "fail",
    "stale",
    "blocked",
    "not_applicable",
}


class Issue(NamedTuple):
    code: str
    path: str
    message: str


def canonical_delivery_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, RecursionError, UnicodeError) as error:
        raise ValueError("delivery is not canonical UTF-8 JSON") from error


def _issue(issues, code, path, message):
    issues.append(Issue(code, path, message))


def _object(value, path, required, issues):
    if not isinstance(value, dict):
        _issue(issues, "DELIVERY_TYPE_INVALID", path, "must be an object")
        return False
    fields = set(value)
    for name in sorted(required - fields):
        _issue(issues, "DELIVERY_REQUIRED_FIELD", f"{path}.{name}", "is required")
    for name in sorted(fields - required):
        _issue(issues, "DELIVERY_UNKNOWN_FIELD", f"{path}.{name}", "is not allowed")
    return True


def _integer(value, path, issues, minimum=0):
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        _issue(issues, "DELIVERY_TYPE_INVALID", path, f"must be an integer >= {minimum}")
        return False
    return True


def _text(value, path, issues, allow_empty=False):
    if (
        not isinstance(value, str)
        or "\x00" in value
        or (not allow_empty and not value.strip())
    ):
        _issue(issues, "DELIVERY_TEXT_INVALID", path, "must be valid non-empty text")
        return False
    return True


def _time(value, path, issues):
    if not _text(value, path, issues):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        parsed = None
    if parsed is None or parsed.tzinfo is None or parsed.utcoffset() is None:
        _issue(issues, "DELIVERY_TIME_INVALID", path, "must include a timezone")
        return None
    return parsed


def _enum(value, allowed, path, issues):
    if value not in allowed:
        _issue(issues, "DELIVERY_ENUM_INVALID", path, "has an unsupported value")


def _list(value, path, issues, *, limit=None):
    if not isinstance(value, list):
        _issue(issues, "DELIVERY_TYPE_INVALID", path, "must be an array")
        return None
    if limit is not None and len(value) > limit:
        _issue(issues, "DELIVERY_LIMIT_EXCEEDED", path, f"must contain at most {limit} items")
    return value


def _text_list(value, path, issues, *, unique=False):
    items = _list(value, path, issues)
    if items is None:
        return
    seen = set()
    for index, item in enumerate(items):
        item_path = f"{path}[{index}]"
        if _text(item, item_path, issues) and unique:
            if item in seen:
                _issue(issues, "DELIVERY_DUPLICATE_ID", item_path, "must be unique")
            seen.add(item)


def _validate_approval(value, path, issues):
    required = {"revision", "confirmation_id", "source", "recorded_at"}
    if not _object(value, path, required, issues):
        return
    _integer(value.get("revision"), f"{path}.revision", issues, 1)
    _text(value.get("confirmation_id"), f"{path}.confirmation_id", issues)
    _text(value.get("source"), f"{path}.source", issues)
    _time(value.get("recorded_at"), f"{path}.recorded_at", issues)


def _validate_contract(value, path, issues):
    required = {
        "revision",
        "outcome",
        "actors",
        "flows",
        "non_goals",
        "constraints",
        "unknowns",
        "delivery_target",
        "approval",
    }
    if not _object(value, path, required, issues):
        return
    _integer(value.get("revision"), f"{path}.revision", issues, 1)
    _text(value.get("outcome"), f"{path}.outcome", issues)
    for field in ("actors", "flows", "non_goals", "constraints", "unknowns"):
        _text_list(value.get(field), f"{path}.{field}", issues)
    _enum(value.get("delivery_target"), DELIVERY_TARGETS, f"{path}.delivery_target", issues)
    _validate_approval(value.get("approval"), f"{path}.approval", issues)


def _validate_surface(value, path, issues):
    required = {"applicability", "rationale", "evidence_ids"}
    if not _object(value, path, required, issues):
        return
    _enum(value.get("applicability"), APPLICABILITY, f"{path}.applicability", issues)
    _text(value.get("rationale"), f"{path}.rationale", issues)
    _text_list(value.get("evidence_ids"), f"{path}.evidence_ids", issues, unique=True)


def _validate_slice(value, path, issues):
    required = {"slice_id", "outcome", "criterion_ids", "depends_on", "surfaces"}
    if not _object(value, path, required, issues):
        return
    _text(value.get("slice_id"), f"{path}.slice_id", issues)
    _text(value.get("outcome"), f"{path}.outcome", issues)
    _text_list(value.get("criterion_ids"), f"{path}.criterion_ids", issues, unique=True)
    _text_list(value.get("depends_on"), f"{path}.depends_on", issues, unique=True)
    surfaces = value.get("surfaces")
    names = {"data", "api", "ui", "authorization", "deployment"}
    if _object(surfaces, f"{path}.surfaces", names, issues):
        for name in sorted(names):
            _validate_surface(surfaces.get(name), f"{path}.surfaces.{name}", issues)


def _validate_verification(value, path, issues):
    required = {"entry_id", "cwd", "kind", "entry", "environment_keys"}
    if not _object(value, path, required, issues):
        return
    _text(value.get("entry_id"), f"{path}.entry_id", issues)
    _text(value.get("cwd"), f"{path}.cwd", issues)
    _enum(value.get("kind"), {"command", "tool", "manual"}, f"{path}.kind", issues)
    _text_list(value.get("entry"), f"{path}.entry", issues)
    _text_list(value.get("environment_keys"), f"{path}.environment_keys", issues, unique=True)


def _validate_judgment(value, path, issues):
    required = {"result", "reason", "source", "at", "evidence_ids", "invalidation_count"}
    if not _object(value, path, required, issues):
        return
    _enum(value.get("result"), {"pass", "fail", "blocked", "not_applicable"}, f"{path}.result", issues)
    _text(value.get("reason"), f"{path}.reason", issues)
    _text(value.get("source"), f"{path}.source", issues)
    _time(value.get("at"), f"{path}.at", issues)
    _text_list(value.get("evidence_ids"), f"{path}.evidence_ids", issues, unique=True)
    _integer(value.get("invalidation_count"), f"{path}.invalidation_count", issues)


def _validate_criterion(value, path, issues):
    required = {
        "criterion_id",
        "slice_id",
        "outcome",
        "revision",
        "required",
        "status",
        "applicability_rationale",
        "verification",
        "evidence_ids",
        "judgment",
    }
    if not _object(value, path, required, issues):
        return
    _text(value.get("criterion_id"), f"{path}.criterion_id", issues)
    _text(value.get("slice_id"), f"{path}.slice_id", issues)
    _text(value.get("outcome"), f"{path}.outcome", issues)
    _integer(value.get("revision"), f"{path}.revision", issues, 1)
    if not isinstance(value.get("required"), bool):
        _issue(issues, "DELIVERY_TYPE_INVALID", f"{path}.required", "must be boolean")
    _enum(value.get("status"), CRITERION_STATUSES, f"{path}.status", issues)
    _text(value.get("applicability_rationale"), f"{path}.applicability_rationale", issues, allow_empty=True)
    _validate_verification(value.get("verification"), f"{path}.verification", issues)
    _text_list(value.get("evidence_ids"), f"{path}.evidence_ids", issues, unique=True)
    judgment = value.get("judgment")
    if judgment is not None:
        _validate_judgment(judgment, f"{path}.judgment", issues)


def _validate_fingerprint(value, path, issues):
    required = {"algorithm", "value", "scope", "captured_at"}
    if not _object(value, path, required, issues):
        return
    _enum(value.get("algorithm"), {"sha256-manifest-v1"}, f"{path}.algorithm", issues)
    digest = value.get("value")
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        _issue(issues, "DELIVERY_HASH_INVALID", f"{path}.value", "must be a lowercase SHA-256")
    _enum(
        value.get("scope"),
        {"tracked+nonignored-untracked", "regular-files-excluding-governance"},
        f"{path}.scope",
        issues,
    )
    _time(value.get("captured_at"), f"{path}.captured_at", issues)


def _validate_environment(value, path, issues):
    required = {"facts", "observed_at", "source", "status"}
    if not _object(value, path, required, issues):
        return
    facts = value.get("facts")
    if not isinstance(facts, dict):
        _issue(issues, "DELIVERY_TYPE_INVALID", f"{path}.facts", "must be an object")
    else:
        for key, fact in facts.items():
            _text(key, f"{path}.facts", issues)
            if not isinstance(fact, (str, int, float, bool)) or (
                isinstance(fact, float) and not math.isfinite(fact)
            ):
                _issue(issues, "DELIVERY_TYPE_INVALID", f"{path}.facts.{key}", "must be a finite scalar")
    _time(value.get("observed_at"), f"{path}.observed_at", issues)
    _text(value.get("source"), f"{path}.source", issues)
    _enum(value.get("status"), {"observed", "unknown"}, f"{path}.status", issues)


def _validate_isolation(value, path, issues):
    required = {"mode", "snapshot_id", "source_digest", "observer"}
    if not _object(value, path, required, issues):
        return
    _enum(value.get("mode"), {"isolated-snapshot", "unproven"}, f"{path}.mode", issues)
    _text(value.get("snapshot_id"), f"{path}.snapshot_id", issues)
    _text(value.get("source_digest"), f"{path}.source_digest", issues)
    _text(value.get("observer"), f"{path}.observer", issues)


def _validate_output(value, path, issues):
    required = {"path", "sha256", "bytes"}
    if not _object(value, path, required, issues):
        return
    _text(value.get("path"), f"{path}.path", issues)
    digest = value.get("sha256")
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        _issue(issues, "DELIVERY_HASH_INVALID", f"{path}.sha256", "must be a lowercase SHA-256")
    _integer(value.get("bytes"), f"{path}.bytes", issues)


def _validate_evidence(value, path, issues):
    required = {
        "evidence_id",
        "criterion_id",
        "revision",
        "provenance",
        "entry_id",
        "cwd",
        "started_at",
        "finished_at",
        "observer",
        "result",
        "exit_code",
        "source_fingerprint",
        "environment",
        "isolation",
        "outputs",
        "invalidation_count",
    }
    if not _object(value, path, required, issues):
        return
    for field in ("evidence_id", "criterion_id", "entry_id", "cwd", "observer"):
        _text(value.get(field), f"{path}.{field}", issues)
    _integer(value.get("revision"), f"{path}.revision", issues, 1)
    _enum(value.get("provenance"), {"agent_declaration", "observed_execution"}, f"{path}.provenance", issues)
    started = _time(value.get("started_at"), f"{path}.started_at", issues)
    finished = _time(value.get("finished_at"), f"{path}.finished_at", issues)
    if started is not None and finished is not None and finished < started:
        _issue(issues, "DELIVERY_TIME_INVALID", f"{path}.finished_at", "must not precede started_at")
    _enum(value.get("result"), {"pass", "fail", "blocked"}, f"{path}.result", issues)
    exit_code = value.get("exit_code")
    if exit_code is not None:
        _integer(exit_code, f"{path}.exit_code", issues, -(2**31))
    _validate_fingerprint(value.get("source_fingerprint"), f"{path}.source_fingerprint", issues)
    _validate_environment(value.get("environment"), f"{path}.environment", issues)
    _validate_isolation(value.get("isolation"), f"{path}.isolation", issues)
    outputs = _list(value.get("outputs"), f"{path}.outputs", issues)
    if outputs is not None:
        for index, output in enumerate(outputs):
            _validate_output(output, f"{path}.outputs[{index}]", issues)
    _integer(value.get("invalidation_count"), f"{path}.invalidation_count", issues)


def _validate_invalidation(value, path, issues):
    required = {
        "invalidation_id",
        "event",
        "at",
        "reason",
        "criterion_ids",
        "evidence_ids",
        "mutation_seq",
    }
    if not _object(value, path, required, issues):
        return
    for field in ("invalidation_id", "event", "reason"):
        _text(value.get(field), f"{path}.{field}", issues)
    _time(value.get("at"), f"{path}.at", issues)
    _text_list(value.get("criterion_ids"), f"{path}.criterion_ids", issues, unique=True)
    _text_list(value.get("evidence_ids"), f"{path}.evidence_ids", issues, unique=True)
    _integer(value.get("mutation_seq"), f"{path}.mutation_seq", issues)


def validate_delivery_shape(value: object) -> list[Issue]:
    issues = []
    required = {
        "schema_version",
        "profile",
        "contract",
        "slices",
        "criteria",
        "evidence",
        "invalidations",
    }
    if not _object(value, "delivery", required, issues):
        return issues
    try:
        encoded = canonical_delivery_bytes(value)
    except ValueError:
        _issue(issues, "DELIVERY_ENCODING_INVALID", "delivery", "must be canonical UTF-8 JSON")
    else:
        if len(encoded) > MAX_DELIVERY_BYTES:
            _issue(issues, "DELIVERY_SIZE_EXCEEDED", "delivery", f"must be at most {MAX_DELIVERY_BYTES} bytes")
    if value.get("schema_version") != 1 or isinstance(value.get("schema_version"), bool):
        _issue(issues, "DELIVERY_TYPE_INVALID", "delivery.schema_version", "must equal integer 1")
    if value.get("profile") != "web-fullstack":
        _issue(issues, "DELIVERY_ENUM_INVALID", "delivery.profile", "must equal web-fullstack")
    _validate_contract(value.get("contract"), "delivery.contract", issues)
    collections = (
        ("slices", MAX_SLICES, _validate_slice),
        ("criteria", MAX_CRITERIA, _validate_criterion),
        ("evidence", MAX_EVIDENCE, _validate_evidence),
        ("invalidations", MAX_INVALIDATIONS, _validate_invalidation),
    )
    for name, limit, validator in collections:
        items = _list(value.get(name), f"delivery.{name}", issues, limit=limit)
        if items is not None:
            for index, item in enumerate(items):
                validator(item, f"delivery.{name}[{index}]", issues)
    return issues
