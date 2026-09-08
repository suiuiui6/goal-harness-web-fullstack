#!/usr/bin/env python3
"""Deterministic state and lifecycle guard for governed Codex /goal work."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from contextlib import contextmanager
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIRECTORY = str(Path(__file__).resolve().parent)
if SCRIPT_DIRECTORY not in sys.path:
    sys.path.insert(0, SCRIPT_DIRECTORY)

from delivery_contract import validate_delivery_shape
from delivery_evidence import audit_delivery_files
from delivery_rules import (
    acceptance_errors,
    invalidate_delivery,
    pass_evidence_errors,
    validate_delivery_links,
    validate_delivery_transition,
)

STATE_RELATIVE_PATH = Path(".codex") / "goal-state.json"
PHASES = ("intake", "classified", "planned", "executing", "verified", "complete")
SCOPE_RESULTS = ("accepted", "rework-required", "blocked", "incomplete")
OPERATION_STATES = ("bootstrap_exited", "maintenance_continues", "in_progress")
FINGERPRINT_ALGORITHM = "sha256-manifest-v1"
FINGERPRINT_SCOPE_GIT = "tracked+nonignored-untracked"
FINGERPRINT_SCOPE_FILESYSTEM = "regular-files-excluding-governance"
CAPABILITY_DESCRIPTOR = {
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
MUTATION_TOOLS = {
    "applypatch", "apply_patch", "write", "edit", "multiedit",
    "shellcommand", "shell_command", "execcommand", "exec_command", "bash",
}
SHELL_TOOLS = {"shellcommand", "shell_command", "execcommand", "exec_command", "bash"}
READ_ONLY_COMMANDS = (
    r"^(get-content|get-childitem|select-string|test-path)\b",
    r"^(git\s+(status|diff|log|show|rev-parse|branch))\b",
    r"^(rg|findstr|where\.exe)\b",
    r"^(codex\s+(--version|features\s+list|mcp\s+(list|get)))\b",
)


@dataclass(frozen=True)
class Decision:
    allowed: bool
    code: str
    reason: str


@dataclass(frozen=True)
class StateLoadResult:
    active: bool
    state: dict[str, Any] | None = None
    error: str | None = None
    path: Path | None = None


class FingerprintError(RuntimeError):
    """Raised when workspace content cannot be fingerprinted safely."""


def nonempty_text(value: Any) -> bool:
    """Return true only for a real, non-blank string (not a stringified list)."""
    return isinstance(value, str) and bool(value.strip())


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_text(value: str) -> str:
    """Return the SHA-256 digest of exact UTF-8 text."""
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def _relative_path(root: Path, path: Path) -> str:
    try:
        relative = path.resolve(strict=False).relative_to(root.resolve(strict=False))
    except ValueError as exc:
        raise FingerprintError(f"workspace path escapes root: {path}") from exc
    return relative.as_posix()


def _is_governance_path(relative: str) -> bool:
    parts = [part for part in relative.replace("\\", "/").split("/") if part]
    return bool(parts and parts[0].lower() == ".codex")


def _git_paths(root: Path) -> list[str] | None:
    """List tracked and non-ignored untracked paths, or None for non-Git roots."""
    marker = root
    has_git_marker = False
    while True:
        git_marker = marker / ".git"
        valid_marker = False
        if git_marker.is_dir():
            valid_marker = (git_marker / "HEAD").exists() or (git_marker / "config").exists()
        elif git_marker.is_file():
            try:
                valid_marker = git_marker.read_text(encoding="utf-8", errors="replace").lstrip().lower().startswith("gitdir:")
            except OSError:
                valid_marker = False
        if valid_marker:
            has_git_marker = True
            break
        if marker.parent == marker:
            break
        marker = marker.parent
    if not has_git_marker:
        return None
    try:
        probe = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
            capture_output=True,
            check=False,
            timeout=5,
        )
    except subprocess.TimeoutExpired as exc:
        raise FingerprintError("Git workspace probe timed out") from exc
    except OSError as exc:
        raise FingerprintError(f"Git workspace probe failed: {exc}") from exc
    if probe.returncode != 0:
        if has_git_marker:
            message = probe.stderr.decode(errors="replace").strip()
            raise FingerprintError(f"Git workspace probe failed: {message or probe.returncode}")
        return None
    try:
        git_root = Path(os.fsdecode(probe.stdout.strip())).resolve(strict=True)
        relative_prefix = root.resolve(strict=True).relative_to(git_root).as_posix()
        if relative_prefix == ".":
            relative_prefix = ""
    except (OSError, RuntimeError, ValueError) as exc:
        raise FingerprintError(f"unable to resolve Git workspace root: {exc}") from exc
    try:
        result = subprocess.run(
            ["git", "-C", str(git_root), "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
            capture_output=True,
            check=False,
            timeout=5,
        )
    except subprocess.TimeoutExpired as exc:
        raise FingerprintError("Git workspace enumeration timed out") from exc
    except OSError as exc:
        raise FingerprintError(f"unable to enumerate Git workspace: {exc}") from exc
    if result.returncode != 0:
        message = result.stderr.decode(errors="replace").strip()
        raise FingerprintError(f"unable to enumerate Git workspace: {message or result.returncode}")
    paths: list[str] = []
    for raw in result.stdout.split(b"\0"):
        if not raw:
            continue
        relative = os.fsdecode(raw).replace("\\", "/")
        if relative_prefix:
            prefix = relative_prefix.rstrip("/") + "/"
            if not relative.casefold().startswith(prefix.casefold()):
                continue
            relative = relative[len(prefix):]
        if not relative or _is_governance_path(relative):
            continue
        if relative.startswith("/") or "../" in f"{relative}/":
            raise FingerprintError(f"Git returned an unsafe path: {relative}")
        paths.append(relative)
    return sorted(set(paths))


def _filesystem_paths(root: Path) -> list[str]:
    paths: list[str] = []
    root_resolved = root.resolve(strict=False)
    def walk_error(error: OSError) -> None:
        raise FingerprintError(f"unable to enumerate workspace: {error}") from error

    for directory, dirnames, filenames in os.walk(
        root_resolved, topdown=True, followlinks=False, onerror=walk_error
    ):
        dir_path = Path(directory)
        retained_dirs: list[str] = []
        for name in dirnames:
            if name.lower() in (".codex", ".git"):
                continue
            candidate = dir_path / name
            if candidate.is_symlink():
                raise FingerprintError(
                    f"workspace directory symlink is unsupported: {_relative_path(root_resolved, candidate)}"
                )
            retained_dirs.append(name)
        dirnames[:] = retained_dirs
        for name in filenames:
            path = dir_path / name
            relative = _relative_path(root_resolved, path)
            if _is_governance_path(relative):
                continue
            if not path.is_file() and not path.is_symlink():
                raise FingerprintError(f"unsupported special file in workspace: {relative}")
            if path.is_symlink():
                try:
                    path.resolve(strict=True).relative_to(root_resolved)
                except (OSError, ValueError) as exc:
                    raise FingerprintError(f"symlink escapes workspace: {relative}") from exc
            paths.append(relative)
    return sorted(set(paths))


def workspace_fingerprint(workspace: Path) -> str:
    """Hash current workspace content using a deterministic file manifest."""
    root = Path(workspace).resolve(strict=False)
    if not root.exists() or not root.is_dir():
        raise FingerprintError(f"workspace is not a directory: {root}")
    git_paths = _git_paths(root)
    paths = git_paths
    if paths is None:
        paths = _filesystem_paths(root)
    manifest: list[bytes] = []
    for relative in paths:
        path = root / Path(relative)
        try:
            resolved = path.resolve(strict=False)
            resolved.relative_to(root)
        except (OSError, ValueError) as exc:
            raise FingerprintError(f"workspace path escapes root: {relative}") from exc
        if path.is_symlink():
            if not path.exists():
                raise FingerprintError(f"dangling workspace symlink: {relative}")
            try:
                resolved_target = path.resolve(strict=True)
                resolved_target.relative_to(root)
            except (OSError, ValueError) as exc:
                raise FingerprintError(f"workspace symlink escapes root: {relative}") from exc
            if resolved_target.is_dir():
                raise FingerprintError(f"workspace directory symlink is unsupported: {relative}")
        if not path.exists():
            if git_paths is None:
                raise FingerprintError(f"workspace file disappeared during fingerprint: {relative}")
            digest = "<missing>"
        elif path.is_dir():
            digest = "<directory>"
        elif not path.is_file():
            raise FingerprintError(f"unsupported special file in workspace: {relative}")
        else:
            try:
                hasher = hashlib.sha256()
                with path.open("rb") as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                        hasher.update(chunk)
                digest = hasher.hexdigest()
            except OSError as exc:
                raise FingerprintError(f"unable to read workspace file {relative}: {exc}") from exc
        manifest.append(f"{relative}\0{digest}\n".encode("utf-8"))
    return hashlib.sha256(b"".join(manifest)).hexdigest()


def workspace_fingerprint_record(workspace: Path, *, captured_at: str | None = None) -> dict[str, str]:
    """Capture a structured fingerprint receipt for verification or closure."""
    root = Path(workspace).resolve(strict=False)
    scope = workspace_fingerprint_scope(root)
    return {
        "algorithm": FINGERPRINT_ALGORITHM,
        "value": workspace_fingerprint(root),
        "scope": scope,
        "captured_at": captured_at or utc_now(),
    }


def workspace_fingerprint_scope(workspace: Path) -> str:
    root = Path(workspace).resolve(strict=False)
    return FINGERPRINT_SCOPE_GIT if _git_paths(root) is not None else FINGERPRINT_SCOPE_FILESYSTEM


def _fingerprint_value(value: Any) -> str:
    if isinstance(value, dict):
        if value.get("algorithm") != FINGERPRINT_ALGORITHM:
            return ""
        if value.get("scope") not in (FINGERPRINT_SCOPE_GIT, FINGERPRINT_SCOPE_FILESYSTEM):
            return ""
        digest = value.get("value")
        return digest.strip() if isinstance(digest, str) else ""
    return ""


def _fingerprint_record_errors(value: Any, label: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, dict):
        return [f"{label} must be an object"]
    errors: list[str] = []
    if value.get("algorithm") != FINGERPRINT_ALGORITHM:
        errors.append(f"{label}.algorithm is unsupported")
    if value.get("scope") not in (FINGERPRINT_SCOPE_GIT, FINGERPRINT_SCOPE_FILESYSTEM):
        errors.append(f"{label}.scope is unsupported")
    digest = value.get("value")
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest.strip()):
        errors.append(f"{label}.value must be a SHA-256 hex digest")
    if not _timestamp_is_valid(value.get("captured_at")):
        errors.append(f"{label}.captured_at must be a parseable, non-future timestamp")
    return errors


def _timestamp_is_valid(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    text = value.strip()
    if not text:
        return False
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return False
    if parsed.tzinfo is None:
        return False
    return parsed <= datetime.now(timezone.utc)


def normalize_tool_name(name: str | None) -> str:
    if not isinstance(name, str):
        return ""
    return re.sub(r"[^a-z_]", "", name.lower())


def payload_command(tool_input: dict[str, Any]) -> str:
    if not isinstance(tool_input, dict):
        return ""
    for key in ("command", "cmd", "script"):
        value = tool_input.get(key)
        if isinstance(value, str):
            return value.strip()
    return ""


def has_shell_control_operator(command: str) -> bool:
    # Treat grouping/subexpression parentheses as potentially executable too:
    # PowerShell and cmd can run nested commands inside `( ... )` even when no
    # semicolon or pipeline character is present.  Conservative classification
    # avoids granting a read-only exemption to a command with hidden effects.
    return bool(re.search(r"[;&|<>\r\n`(){}]|\$\(", command))


def is_guard_command(command: str, cwd: Path | None = None) -> bool:
    if has_shell_control_operator(command):
        return False
    normalized = command.replace("\\", "/").strip()
    match = re.match(
        r"^(?:python3?|py)\s+(?P<script>(?:\"[^\"]*goal_guard\.py\"|'[^']*goal_guard\.py'|\S*goal_guard\.py))\s+"
        r"(?:pre-tool-use|post-tool-use|stop|audit|capabilities|write-state|initialize-state|rollback-layer|authorize-override|resolve-failure|recover-reservation|user-prompt-submit|session-start)\b",
        normalized,
        re.IGNORECASE,
    )
    if not match:
        return False
    script = match.group("script").strip("'\"").lower()
    canonical = Path(__file__).resolve().as_posix().lower()
    if script == canonical:
        return True
    if cwd is None:
        return False
    try:
        return (Path(cwd).resolve(strict=False) / script).resolve(strict=False).as_posix().lower() == canonical
    except OSError:
        return False


def is_read_only_command(command: str) -> bool:
    if has_shell_control_operator(command):
        return False
    value = command.strip().lower()
    if re.search(r"(?:--output(?:=|\s)|(?:^|\s)-o(?:=|\s|$))", value):
        return False
    if re.match(r"^git\s+branch\b", value):
        return bool(
            re.fullmatch(
                r"git\s+branch(?:\s+(?:--show-current|--list|-a|-r|-v|-vv))?",
                value,
                re.IGNORECASE,
            )
        )
    return any(re.search(pattern, value, re.IGNORECASE) for pattern in READ_ONLY_COMMANDS)


def is_mutation(tool_name: str, tool_input: dict[str, Any], workspace: Path | None = None) -> bool:
    name = normalize_tool_name(tool_name)
    if name not in MUTATION_TOOLS:
        return False
    if name in SHELL_TOOLS:
        command = payload_command(tool_input)
        if is_guard_command(command, workspace):
            return False
        return not is_read_only_command(command)
    return True


def is_completion(tool_name: str, tool_input: dict[str, Any]) -> bool:
    return (
        normalize_tool_name(tool_name) == "update_goal"
        and isinstance(tool_input, dict)
        and tool_input.get("status") == "complete"
    )


def targets_protected_state(tool_input: dict[str, Any]) -> bool:
    serialized = json.dumps(tool_input, ensure_ascii=False).replace("\\", "/").lower()
    serialized = re.sub(r"/+", "/", serialized)
    while "/./" in serialized:
        serialized = serialized.replace("/./", "/")
    return (
        ".codex/goal-state.json" in serialized
        or "goal-state.json" in serialized
        or ".codex/goal-state.lock" in serialized
        or ".codex/goal-state." in serialized
    )


def as_mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def state_shape_errors(state: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if "delivery" in state:
        if not isinstance(state.get("delivery"), dict):
            errors.append("delivery must be an object")
        else:
            for issue in validate_delivery_shape(state["delivery"]):
                errors.append(f"{issue.code} at {issue.path}: {issue.message}")
    for field in (
        "classification",
        "plan",
        "layers",
        "verification",
        "closure",
        "enforcement_override",
    ):
        if field in state and not isinstance(state.get(field), dict):
            errors.append(f"{field} must be an object")

    classification = state.get("classification")
    if isinstance(classification, dict) and "confirmed" in classification:
        if not isinstance(classification.get("confirmed"), bool):
            errors.append("classification.confirmed must be boolean")
    plan = state.get("plan")
    if isinstance(plan, dict):
        for field in ("required", "approved"):
            if field in plan and not isinstance(plan.get(field), bool):
                errors.append(f"plan.{field} must be boolean")
    closure = state.get("closure")
    if isinstance(closure, dict) and "recorded" in closure:
        if not isinstance(closure.get("recorded"), bool):
            errors.append("closure.recorded must be boolean")
    override = state.get("enforcement_override")
    if isinstance(override, dict):
        if "enabled" in override and not isinstance(override.get("enabled"), bool):
            errors.append("enforcement_override.enabled must be boolean")
        if "remaining_uses" in override:
            remaining_uses = override.get("remaining_uses")
            if (
                not isinstance(remaining_uses, int)
                or isinstance(remaining_uses, bool)
                or remaining_uses not in (0, 1)
            ):
                errors.append("enforcement_override.remaining_uses must be 0 or 1")
            elif override.get("enabled") is True and remaining_uses != 1:
                errors.append("enabled enforcement_override must be single-use")
            elif override.get("enabled") is False and remaining_uses != 0:
                errors.append("disabled enforcement_override cannot retain uses")
        if override.get("enabled") is True:
            if not nonempty_text(override.get("reason")):
                errors.append("enabled enforcement_override requires a reason")
            if override.get("authorized_by") != "user":
                errors.append("enabled enforcement_override requires user authorization")
            if not nonempty_text(override.get("confirmation_id")):
                errors.append("enabled enforcement_override requires confirmation_id")

    failures = state.get("open_failures")
    if failures is not None and not isinstance(failures, list):
        errors.append("open_failures must be an array")
    elif isinstance(failures, list):
        failure_ids: set[str] = set()
        for index, failure in enumerate(failures):
            prefix = f"open_failures[{index}]"
            if not isinstance(failure, dict):
                errors.append(f"{prefix} must be an object")
                continue
            failure_id = str(failure.get("id") or "").strip()
            if not failure_id:
                errors.append(f"{prefix}.id must be non-empty")
            elif failure_id in failure_ids:
                errors.append(f"duplicate failure id: {failure_id}")
            else:
                failure_ids.add(failure_id)
            if failure.get("status") not in ("open", "resolved"):
                errors.append(f"{prefix}.status must be open or resolved")

    reservations = state.get("in_flight_mutations")
    if reservations is not None and not isinstance(reservations, list):
        errors.append("in_flight_mutations must be an array")
    elif isinstance(reservations, list):
        reservation_ids: set[str] = set()
        reservation_sequences: set[int] = set()
        last_sequence = state.get("last_mutation_seq")
        for index, reservation in enumerate(reservations):
            prefix = f"in_flight_mutations[{index}]"
            if not isinstance(reservation, dict):
                errors.append(f"{prefix} must be an object")
                continue
            reservation_id = str(reservation.get("id") or "").strip()
            if not reservation_id:
                errors.append(f"{prefix}.id must be non-empty")
            elif reservation_id in reservation_ids:
                errors.append(f"duplicate reservation id: {reservation_id}")
            else:
                reservation_ids.add(reservation_id)
            if not str(reservation.get("tool") or "").strip():
                errors.append(f"{prefix}.tool must be non-empty")
            sequence = reservation.get("sequence")
            if (
                not isinstance(sequence, int)
                or isinstance(sequence, bool)
                or sequence <= 0
            ):
                errors.append(f"{prefix}.sequence must be a positive integer")
            else:
                if sequence in reservation_sequences:
                    errors.append(f"duplicate reservation sequence: {sequence}")
                else:
                    reservation_sequences.add(sequence)
                if (
                    isinstance(last_sequence, int)
                    and not isinstance(last_sequence, bool)
                    and sequence > last_sequence
                ):
                    errors.append(
                        f"{prefix}.sequence cannot exceed last_mutation_seq"
                    )

    rollback_history = state.get("rollback_history")
    if rollback_history is not None and not isinstance(rollback_history, list):
        errors.append("rollback_history must be an array")
    elif isinstance(rollback_history, list):
        required_fields = (
            "from_start_layer",
            "from_current_layer",
            "to_layer",
            "reason",
            "evidence",
            "at",
            "mutation_seq",
        )
        seen_sequences: set[int] = set()
        previous_sequence = 0
        last_sequence = state.get("last_mutation_seq")
        for index, entry in enumerate(rollback_history):
            prefix = f"rollback_history[{index}]"
            if not isinstance(entry, dict):
                errors.append(f"{prefix} must be an object")
                continue
            for field in required_fields:
                if field not in entry:
                    errors.append(f"{prefix}.{field} is required")
            for field in ("reason", "evidence", "at"):
                if field in entry and not str(entry.get(field) or "").strip():
                    errors.append(f"{prefix}.{field} must be non-empty")
            if "at" in entry and not _timestamp_is_valid(entry.get("at")):
                errors.append(f"{prefix}.at must be a parseable, non-future timestamp")
            for field in ("from_start_layer", "from_current_layer", "to_layer"):
                value = entry.get(field)
                if (
                    not isinstance(value, int)
                    or isinstance(value, bool)
                    or not 0 <= value <= 6
                ):
                    errors.append(f"{prefix}.{field} must be an integer from 0 to 6")
            from_start = entry.get("from_start_layer")
            from_current = entry.get("from_current_layer")
            to_layer = entry.get("to_layer")
            if (
                isinstance(from_start, int)
                and not isinstance(from_start, bool)
                and isinstance(from_current, int)
                and not isinstance(from_current, bool)
                and isinstance(to_layer, int)
                and not isinstance(to_layer, bool)
            ):
                if not 0 <= from_start <= from_current <= 6:
                    errors.append(f"{prefix}.from_start_layer must not exceed from_current_layer")
                if not 0 <= to_layer <= from_current:
                    errors.append(f"{prefix}.to_layer cannot be after from_current_layer")
            sequence = entry.get("mutation_seq")
            if (
                not isinstance(sequence, int)
                or isinstance(sequence, bool)
                or sequence <= 0
            ):
                errors.append(f"{prefix}.mutation_seq must be a positive integer")
            else:
                if sequence in seen_sequences:
                    errors.append(f"duplicate rollback mutation_seq: {sequence}")
                seen_sequences.add(sequence)
                if sequence <= previous_sequence:
                    errors.append("rollback_history mutation_seq must be strictly increasing")
                previous_sequence = max(previous_sequence, sequence)
                if (
                    isinstance(last_sequence, int)
                    and not isinstance(last_sequence, bool)
                    and sequence > last_sequence
                ):
                    errors.append(f"{prefix}.mutation_seq cannot exceed last_mutation_seq")
    return errors


def positive_int(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 0
    return parsed if parsed > 0 else 0


def valid_override(state: dict[str, Any]) -> bool:
    override = as_mapping(state.get("enforcement_override"))
    remaining_uses = override.get("remaining_uses")
    return bool(
        override.get("enabled") is True
        and nonempty_text(override.get("reason"))
        and override.get("authorized_by") == "user"
        and nonempty_text(override.get("confirmation_id"))
        and isinstance(remaining_uses, int)
        and not isinstance(remaining_uses, bool)
        and remaining_uses == 1
    )


def consume_override(state: dict[str, Any]) -> dict[str, Any]:
    updated = json.loads(json.dumps(state))
    override = as_mapping(updated.get("enforcement_override"))
    if valid_override(updated):
        override["remaining_uses"] = max(
            0, positive_int(override.get("remaining_uses")) - 1
        )
        if override["remaining_uses"] == 0:
            override["enabled"] = False
        updated["enforcement_override"] = override
        updated["updated_at"] = utc_now()
    return updated


def open_failures(state: dict[str, Any]) -> list[dict[str, Any]]:
    failures = state.get("open_failures") or []
    if not isinstance(failures, list):
        return []
    return [item for item in failures if isinstance(item, dict) and item.get("status", "open") == "open"]


def audit_state(state: dict[str, Any], workspace: Path | None = None) -> list[str]:
    errors: list[str] = state_shape_errors(state)
    if isinstance(state.get("delivery"), dict):
        for issue in validate_delivery_links(state["delivery"]):
            message = f"{issue.code} at {issue.path}: {issue.message}"
            if message not in errors:
                errors.append(message)
        for issue in pass_evidence_errors(state["delivery"]):
            message = f"{issue.code} at {issue.path}: {issue.message}"
            if message not in errors:
                errors.append(message)
        verification_marker = as_mapping(state.get("verification")).get("status") == "pass"
        closure_marker = as_mapping(state.get("closure")).get("recorded") is True
        acceptance_requested = (
            state.get("scope_result") == "accepted"
            or state.get("phase") in ("verified", "complete")
            or verification_marker
            or closure_marker
        )
        if acceptance_requested:
            for issue in acceptance_errors(state["delivery"]):
                message = f"{issue.code} at {issue.path}: {issue.message}"
                if message not in errors:
                    errors.append(message)
            if workspace is None:
                errors.append("DELIVERY_WORKSPACE_REQUIRED for delivery acceptance")
            else:
                for issue in audit_delivery_files(state["delivery"], workspace):
                    errors.append(f"{issue.code} at {issue.path}: {issue.message}")
                try:
                    current = workspace_fingerprint_record(workspace)
                except FingerprintError as exc:
                    errors.append(f"DELIVERY_SOURCE_STALE: {exc}")
                else:
                    for evidence in state["delivery"]["evidence"]:
                        if evidence["evidence_id"] in {
                            evidence_id
                            for criterion in state["delivery"]["criteria"]
                            if criterion["status"] == "pass"
                            for evidence_id in criterion["evidence_ids"]
                        }:
                            recorded = evidence["source_fingerprint"]
                            if (
                                recorded.get("algorithm") != current["algorithm"]
                                or recorded.get("scope") != current["scope"]
                                or recorded.get("value") != current["value"]
                            ):
                                errors.append(
                                    f"DELIVERY_SOURCE_STALE at delivery.evidence[{evidence['evidence_id']}].source_fingerprint"
                                )
    if (
        not isinstance(state.get("schema_version"), int)
        or isinstance(state.get("schema_version"), bool)
        or state.get("schema_version") != 1
    ):
        errors.append("schema_version must be 1")
    phase = state.get("phase")
    if phase not in PHASES:
        errors.append(f"Unknown phase: {phase!r}")
    if state.get("mode") not in ("bootstrap", "maintenance"):
        errors.append("mode must be bootstrap or maintenance")
    mutation_seq = state.get("last_mutation_seq", 0)
    if not isinstance(mutation_seq, int) or isinstance(mutation_seq, bool) or mutation_seq < 0:
        errors.append("last_mutation_seq must be a non-negative integer")
    if not nonempty_text(state.get("goal")):
        errors.append("goal must be non-empty")

    scope_result = state.get("scope_result")
    operation_state = state.get("operation_state")
    if scope_result not in SCOPE_RESULTS:
        errors.append("scope_result must be accepted, rework-required, blocked, or incomplete")
    if operation_state not in OPERATION_STATES:
        errors.append("operation_state must be bootstrap_exited, maintenance_continues, or in_progress")
    if operation_state == "bootstrap_exited" and state.get("mode") != "bootstrap":
        errors.append("bootstrap_exited operation_state requires bootstrap mode")
    if operation_state == "maintenance_continues" and state.get("mode") != "maintenance":
        errors.append("maintenance_continues operation_state requires maintenance mode")
    if phase != "complete" and operation_state in ("bootstrap_exited", "maintenance_continues"):
        errors.append("terminal operation_state requires complete phase")
    if phase == "complete" and operation_state not in ("bootstrap_exited", "maintenance_continues"):
        errors.append("complete phase requires a terminal operation_state")
    if phase == "complete" and scope_result != "accepted":
        errors.append("complete phase requires accepted scope_result")
    if scope_result == "accepted" and open_failures(state):
        errors.append("scope_result accepted cannot coexist with open failures")

    classification = as_mapping(state.get("classification"))
    if phase != "intake" and not nonempty_text(classification.get("rationale")):
        errors.append("classification rationale is required")
    if state.get("mode") == "bootstrap":
        confirmation_id = classification.get("confirmation_id")
        if phase not in ("intake", "classified") and classification.get("confirmed") is not True:
            errors.append("bootstrap classification must be confirmed")
        if phase != "intake" and classification.get("confirmed") is True and not nonempty_text(confirmation_id):
            errors.append("bootstrap classification confirmation_id is required")

    plan = as_mapping(state.get("plan"))
    if plan.get("required") and phase in ("planned", "executing", "verified", "complete"):
        if plan.get("approved") is not True or not nonempty_text(plan.get("path")):
            errors.append("required plan must be approved and have a path")

    start = state.get("start_layer")
    current = state.get("current_layer")
    if (
        not isinstance(start, int)
        or isinstance(start, bool)
        or not isinstance(current, int)
        or isinstance(current, bool)
        or not (0 <= start <= current <= 6)
    ):
        errors.append("start_layer/current_layer must satisfy 0 <= start <= current <= 6")
    else:
        layers = as_mapping(state.get("layers"))
        for key, record in layers.items():
            if not isinstance(record, dict):
                continue
            status = record.get("status")
            if status not in ("pass", "fail", "in_progress", "not-run"):
                errors.append(f"Layer {key} has unknown status")
            try:
                layer_number = int(key)
            except (TypeError, ValueError):
                layer_number = -1
            if status == "fail" and scope_result == "accepted" and start <= layer_number <= current:
                errors.append("scope_result accepted cannot coexist with failed layer outcomes")
        stop = current + 1 if phase in ("verified", "complete") else current
        for layer in range(start, stop):
            record = layers.get(str(layer)) or layers.get(layer) or {}
            if not isinstance(record, dict):
                errors.append(f"Layer {layer} record must be an object")
                continue
            if record.get("status") != "pass" or not nonempty_text(record.get("evidence")):
                errors.append(f"Layer {layer} requires pass status and non-empty evidence")

    current_fingerprint: str | None = None
    current_scope: str | None = None
    fingerprint_error: str | None = None
    if workspace is not None and phase in ("verified", "complete"):
        try:
            current_scope = workspace_fingerprint_scope(workspace)
            current_fingerprint = workspace_fingerprint(workspace)
        except FingerprintError as exc:
            fingerprint_error = str(exc)

    if phase in ("verified", "complete"):
        in_flight = state.get("in_flight_mutations") or []
        if in_flight:
            errors.append("in-flight mutations must settle before verification or completion")
        verification = as_mapping(state.get("verification"))
        verification_sequence = verification.get("mutation_seq")
        if (
            not isinstance(verification_sequence, int)
            or isinstance(verification_sequence, bool)
            or verification_sequence < 0
        ):
            errors.append("verification mutation_seq must be a non-negative integer")
        if verification.get("status") != "pass":
            errors.append("verified phase requires passing verification")
        if not nonempty_text(verification.get("command")):
            errors.append("verification command is required")
        if not nonempty_text(verification.get("evidence")):
            errors.append("verification evidence is required")
        if not nonempty_text(verification.get("verified_at")):
            errors.append("verification verified_at is required")
        elif not _timestamp_is_valid(verification.get("verified_at")):
            errors.append("verification verified_at must be a parseable, non-future timestamp")
        if verification.get("mutation_seq") != state.get("last_mutation_seq", 0):
            errors.append("verification is stale relative to the latest mutation")
        if open_failures(state):
            errors.append("open failures must be resolved before verification")
        command = verification.get("command") if isinstance(verification.get("command"), str) else ""
        command_hash = verification.get("command_sha256") if isinstance(verification.get("command_sha256"), str) else ""
        command_hash = command_hash.strip()
        if command_hash != sha256_text(command):
            errors.append("verification command_sha256 does not match command")
        errors.extend(_fingerprint_record_errors(verification.get("workspace_fingerprint"), "verification workspace_fingerprint"))
        expected_fingerprint = _fingerprint_value(verification.get("workspace_fingerprint"))
        if not expected_fingerprint:
            errors.append("verification workspace fingerprint is required")
        if workspace is not None:
            if expected_fingerprint:
                if as_mapping(verification.get("workspace_fingerprint")).get("scope") != current_scope:
                    errors.append("verification workspace fingerprint scope mismatch")
            if expected_fingerprint:
                if fingerprint_error:
                    errors.append(f"workspace fingerprint unavailable: {fingerprint_error}")
                elif expected_fingerprint != current_fingerprint:
                    errors.append("verification workspace fingerprint mismatch")
    if phase == "complete":
        closure = as_mapping(state.get("closure"))
        if not closure.get("recorded"):
            errors.append("complete phase requires a closure record")
        if not nonempty_text(closure.get("evidence")):
            errors.append("complete phase requires non-empty closure evidence")
        closure_fingerprint = _fingerprint_value(closure.get("workspace_fingerprint"))
        verification_record = as_mapping(state.get("verification")).get("workspace_fingerprint")
        verification_fingerprint = _fingerprint_value(verification_record)
        errors.extend(_fingerprint_record_errors(closure.get("workspace_fingerprint"), "closure workspace_fingerprint"))
        if not closure_fingerprint:
            errors.append("complete closure fingerprint is required")
        closure_record = as_mapping(closure.get("workspace_fingerprint"))
        verification_record = as_mapping(verification_record)
        if (
            closure_fingerprint
            and verification_fingerprint
            and (
                closure_fingerprint != verification_fingerprint
                or closure_record.get("algorithm") != verification_record.get("algorithm")
                or closure_record.get("scope") != verification_record.get("scope")
            )
        ):
            errors.append("closure fingerprint must match verification fingerprint")
        if workspace is not None:
            if closure_fingerprint and as_mapping(closure.get("workspace_fingerprint")).get("scope") != current_scope:
                errors.append("closure fingerprint scope mismatch")
            if closure_fingerprint:
                if fingerprint_error:
                    errors.append(f"closure workspace fingerprint unavailable: {fingerprint_error}")
                elif closure_fingerprint != current_fingerprint:
                    errors.append("closure fingerprint does not match current workspace")
    return errors


def validate_transition(
    previous: dict[str, Any] | None,
    candidate: dict[str, Any],
    workspace: Path | None = None,
) -> list[str]:
    errors = audit_state(candidate, workspace=workspace)
    if previous is None:
        if candidate.get("phase") not in ("intake", "classified"):
            errors.append("initial state must begin at intake or classified")
        return errors
    for issue in validate_delivery_transition(previous, candidate):
        errors.append(f"{issue.code} at {issue.path}: {issue.message}")
    if (
        candidate.get("delivery") is not None
        and candidate.get("scope_result") == "accepted"
    ):
        for issue in acceptance_errors(candidate["delivery"]):
            errors.append(f"{issue.code} at {issue.path}: {issue.message}")
    for field in ("goal", "mode", "start_layer"):
        if previous.get(field) != candidate.get(field):
            errors.append(f"{field} is immutable during an active goal")
    previous_classification = as_mapping(previous.get("classification"))
    candidate_classification = as_mapping(candidate.get("classification"))
    for field in ("confirmed", "confirmation_id"):
        if previous_classification.get(field) != candidate_classification.get(field):
            errors.append(f"classification.{field} is immutable during an active goal")
    previous_plan = as_mapping(previous.get("plan"))
    candidate_plan = as_mapping(candidate.get("plan"))
    if previous_plan.get("required") is True and candidate_plan.get("required") is not True:
        errors.append("plan.required cannot be disabled during an active goal")
    if previous.get("enforcement_override") != candidate.get("enforcement_override"):
        errors.append("enforcement_override may change only through interactive authorization")
    if previous.get("last_mutation_seq", 0) != candidate.get("last_mutation_seq", 0):
        errors.append("last_mutation_seq is guard-owned and immutable through write-state")
    if previous.get("open_failures", []) != candidate.get("open_failures", []):
        errors.append("open_failures is guard-owned and immutable through write-state")
    if previous.get("in_flight_mutations", []) != candidate.get("in_flight_mutations", []):
        errors.append("in_flight_mutations is guard-owned and immutable through write-state")
    if previous.get("rollback_history", []) != candidate.get("rollback_history", []):
        errors.append("rollback_history is guard-owned and immutable through write-state")
    previous_current = previous.get("current_layer")
    candidate_current = candidate.get("current_layer")
    if (
        isinstance(previous_current, int)
        and not isinstance(previous_current, bool)
        and isinstance(candidate_current, int)
        and not isinstance(candidate_current, bool)
    ):
        if candidate_current < previous_current:
            errors.append("current_layer may only decrease through rollback-layer")
        elif candidate_current > previous_current + 1:
            errors.append("current_layer advances must be adjacent")
    old_phase = previous.get("phase")
    new_phase = candidate.get("phase")
    if old_phase in PHASES and new_phase in PHASES:
        delta = PHASES.index(new_phase) - PHASES.index(old_phase)
        if delta not in (0, 1):
            errors.append("phase changes must be adjacent and forward-only")
    return errors


def evaluate_tool_call(
    state: dict[str, Any] | None,
    tool_name: str,
    tool_input: dict[str, Any] | None,
    *,
    state_error: str | None = None,
    workspace: Path | None = None,
) -> Decision:
    if not isinstance(tool_name, str) or not tool_name.strip():
        return Decision(False, "invalid-input", "Tool name must be a non-empty string")
    if tool_input is None:
        tool_input = {}
    elif not isinstance(tool_input, dict):
        return Decision(False, "invalid-input", "Tool input must be a JSON object")
    mutation = is_mutation(tool_name, tool_input, workspace)
    completion = is_completion(tool_name, tool_input)
    if state is None and state_error is None:
        return Decision(True, "inactive", "No active /goal state")
    if state_error:
        if mutation or completion:
            return Decision(False, "invalid-state", f"Active goal state is invalid: {state_error}")
        return Decision(True, "read-only", "Read-only inspection remains available")
    assert state is not None
    semantic_errors = audit_state(state, workspace=workspace)
    if semantic_errors and mutation and not completion:
        return Decision(False, "invalid-state", "; ".join(semantic_errors))

    if mutation and targets_protected_state(tool_input):
        return Decision(False, "protected-state", "Use goal_guard.py commands; direct goal-state edits are blocked")
    if valid_override(state) and (mutation or completion) and not semantic_errors:
        return Decision(True, "override", "User-authorized, single-use enforcement override")
    if not mutation and not completion:
        return Decision(True, "read-only", "Tool does not mutate governed state")

    phase = state.get("phase", "intake")
    classification = as_mapping(state.get("classification"))
    plan = as_mapping(state.get("plan"))
    if phase == "intake":
        return Decision(False, "classification-required", "Classify the goal before mutating files")
    if state.get("mode") == "bootstrap" and not classification.get("confirmed"):
        return Decision(False, "bootstrap-confirmation-required", "Obtain explicit bootstrap confirmation")
    if plan.get("required") and not plan.get("approved"):
        return Decision(False, "plan-approval-required", "Create and obtain approval for the required plan")
    if phase not in ("planned", "executing", "verified", "complete"):
        return Decision(False, "execution-phase-required", "Advance the governed state to planned/executing")

    if completion:
        failures = open_failures(state)
        if failures:
            return Decision(False, "open-failure", f"Resolve {len(failures)} open failure(s) before completion")
        verification = as_mapping(state.get("verification"))
        if workspace is None and verification.get("workspace_fingerprint"):
            return Decision(False, "workspace-required", "Workspace path is required to verify the fingerprint before completion")
        if verification.get("status") != "pass" or phase not in ("verified", "complete"):
            return Decision(False, "verification-required", "Run and record fresh passing verification")
        if verification.get("mutation_seq") != state.get("last_mutation_seq", 0):
            return Decision(False, "stale-verification", "Verification predates the latest mutation")
        closure = as_mapping(state.get("closure"))
        if closure.get("recorded") is not True or not nonempty_text(closure.get("evidence")):
            return Decision(False, "closure-required", "Record closure evidence before completion")
        errors = audit_state(state, workspace=workspace)
        if errors:
            return Decision(False, "audit-failed", "; ".join(errors))
    return Decision(True, "allowed", "Goal enforcement checks passed")


def evaluate_stop(
    state: dict[str, Any] | None,
    *,
    state_error: str | None = None,
    workspace: Path | None = None,
) -> Decision:
    if state is None and state_error is None:
        return Decision(True, "inactive", "No active /goal state")
    if state_error:
        return Decision(False, "invalid-state", f"Active goal state is invalid: {state_error}")
    assert state is not None
    structural_errors = audit_state(state, workspace=workspace)
    if structural_errors:
        return Decision(False, "audit-failed", "; ".join(structural_errors))
    if valid_override(state):
        return Decision(True, "override", "User-authorized stop override")
    if workspace is None and state.get("phase") == "complete" and as_mapping(state.get("verification")).get("workspace_fingerprint"):
        return Decision(False, "workspace-required", "Workspace path is required to verify the fingerprint before Stop")
    if state.get("phase") != "complete":
        return Decision(False, "goal-incomplete", "Active /goal has not reached audited complete state")
    return Decision(True, "complete", "Goal closure audit passed")


def resolve_failure(
    state: dict[str, Any], failure_id: str, evidence: str
) -> dict[str, Any]:
    failure_id = failure_id.strip()
    evidence = evidence.strip()
    if not failure_id or not evidence:
        raise ValueError("failure_id and resolution evidence are required")
    updated = json.loads(json.dumps(state))
    failures = updated.get("open_failures")
    if not isinstance(failures, list):
        raise ValueError("open_failures must be an array")
    for failure in failures:
        if isinstance(failure, dict) and failure.get("id") == failure_id:
            if failure.get("status", "open") != "open":
                raise ValueError("failure is not open")
            failure["status"] = "resolved"
            failure["resolution_evidence"] = evidence
            failure["resolved_at"] = utc_now()
            updated["updated_at"] = utc_now()
            return updated
    raise ValueError("open failure id not found")


def recover_reservation(
    state: dict[str, Any], reservation_id: str, evidence: str
) -> dict[str, Any]:
    reservation_id = reservation_id.strip()
    evidence = evidence.strip()
    if not reservation_id or not evidence:
        raise ValueError("reservation_id and recovery evidence are required")
    updated = json.loads(json.dumps(state))
    reservations = updated.get("in_flight_mutations")
    failures = updated.get("open_failures")
    if not isinstance(reservations, list):
        raise ValueError("in_flight_mutations must be an array")
    if not isinstance(failures, list):
        raise ValueError("open_failures must be an array")
    for index, reservation in enumerate(reservations):
        if isinstance(reservation, dict) and reservation.get("id") == reservation_id:
            recovered = reservations.pop(index)
            sequence = positive_int(recovered.get("sequence"))
            if not sequence:
                raise ValueError("reservation sequence is invalid")
            failure_id = f"failure-{sequence}"
            existing_ids = {
                failure.get("id") for failure in failures if isinstance(failure, dict)
            }
            if failure_id in existing_ids:
                suffix = 2
                while f"{failure_id}-{suffix}" in existing_ids:
                    suffix += 1
                failure_id = f"{failure_id}-{suffix}"
            failures.append(
                {
                    "id": failure_id,
                    "status": "open",
                    "command": f"recover reservation {reservation_id} ({recovered.get('tool') or 'unknown tool'})",
                    "evidence": evidence,
                    "kind": "orphan-reservation-recovery",
                    "reservation_id": reservation_id,
                    "opened_at": utc_now(),
                }
            )
            updated["scope_result"] = "rework-required"
            updated["operation_state"] = "in_progress"
            updated["updated_at"] = utc_now()
            return updated
    raise ValueError("in-flight reservation id not found")


def authorize_override(
    state: dict[str, Any], reason: str, confirmation_id: str, typed_confirmation: str
) -> dict[str, Any]:
    reason = reason.strip()
    confirmation_id = confirmation_id.strip()
    if not reason or not confirmation_id:
        raise ValueError("reason and confirmation_id are required")
    if typed_confirmation.strip() != confirmation_id:
        raise ValueError("interactive confirmation did not match")
    updated = json.loads(json.dumps(state))
    updated["enforcement_override"] = {
        "enabled": True,
        "reason": reason,
        "authorized_by": "user",
        "confirmation_id": confirmation_id,
        "remaining_uses": 1,
    }
    updated["updated_at"] = utc_now()
    return updated


def mutation_reservation_id(
    payload: dict[str, Any], tool_name: str, tool_input: dict[str, Any]
) -> str:
    for key in ("tool_use_id", "toolUseId", "tool_call_id", "toolCallId", "item_id", "itemId"):
        value = payload.get(key)
        if value:
            return str(value)
    canonical = json.dumps(
        [normalize_tool_name(tool_name), tool_input],
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return "fingerprint-" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def reserve_mutation(
    state: dict[str, Any],
    tool_name: str,
    tool_input: dict[str, Any],
    reservation_id: str,
    workspace: Path | None = None,
) -> dict[str, Any]:
    updated = json.loads(json.dumps(state))
    if not is_mutation(tool_name, tool_input, workspace):
        return updated
    updated["last_mutation_seq"] = int(updated.get("last_mutation_seq") or 0) + 1
    if updated.get("phase") in ("verified", "complete"):
        updated["phase"] = "executing"
    updated["scope_result"] = "incomplete"
    updated["operation_state"] = "in_progress"
    if isinstance(updated.get("delivery"), dict):
        updated["delivery"] = invalidate_delivery(
            updated["delivery"],
            event="workspace_edit",
            at=utc_now(),
            reason=f"guarded mutation reserved for {normalize_tool_name(tool_name)}",
            mutation_seq=updated["last_mutation_seq"],
        )
    verification = updated.setdefault("verification", {})
    if verification.get("status") == "pass":
        verification["status"] = "stale"
    updated["closure"] = {"recorded": False, "evidence": None, "workspace_fingerprint": None}
    reservations = updated.setdefault("in_flight_mutations", [])
    existing_ids = {
        reservation.get("id")
        for reservation in reservations
        if isinstance(reservation, dict)
    }
    instance_id = reservation_id
    if instance_id in existing_ids:
        instance_id = f"{reservation_id}#{updated['last_mutation_seq']}"
        suffix = 2
        while instance_id in existing_ids:
            instance_id = f"{reservation_id}#{updated['last_mutation_seq']}-{suffix}"
            suffix += 1
    reservations.append(
        {
            "id": instance_id,
            "correlation_id": reservation_id,
            "tool": normalize_tool_name(tool_name),
            "sequence": updated["last_mutation_seq"],
            "opened_at": utc_now(),
        }
    )
    updated["updated_at"] = utc_now()
    return updated

def apply_post_tool_use(
    state: dict[str, Any],
    tool_name: str,
    tool_input: dict[str, Any] | None,
    *,
    success: bool,
    failure_evidence: str | None = None,
    reservation_id: str | None = None,
    workspace: Path | None = None,
) -> dict[str, Any]:
    updated = json.loads(json.dumps(state))
    tool_input = tool_input or {}
    if not is_mutation(tool_name, tool_input, workspace):
        return updated
    reservations = updated.setdefault("in_flight_mutations", [])
    matched_reservation: dict[str, Any] | None = None
    if reservation_id:
        for index, reservation in enumerate(reservations):
            if isinstance(reservation, dict) and reservation.get("id") == reservation_id:
                matched_reservation = reservations.pop(index)
                break
        if matched_reservation is None:
            for index, reservation in enumerate(reservations):
                if (
                    isinstance(reservation, dict)
                    and reservation.get("correlation_id") == reservation_id
                ):
                    matched_reservation = reservations.pop(index)
                    break
    if matched_reservation is None:
        fallback_id = reservation_id or "post-only"
        updated = reserve_mutation(updated, tool_name, tool_input, fallback_id, workspace)
        reservations = updated.setdefault("in_flight_mutations", [])
        for index, reservation in enumerate(reservations):
            if (
                isinstance(reservation, dict)
                and reservation.get("correlation_id") == fallback_id
            ):
                matched_reservation = reservations.pop(index)
                break
    if not success:
        failures = updated.setdefault("open_failures", [])
        sequence = positive_int(
            (matched_reservation or {}).get("sequence")
        ) or updated["last_mutation_seq"]
        failure_id = f"failure-{sequence}"
        existing_ids = {
            failure.get("id") for failure in failures if isinstance(failure, dict)
        }
        if failure_id in existing_ids:
            suffix = 2
            while f"{failure_id}-{suffix}" in existing_ids:
                suffix += 1
            failure_id = f"{failure_id}-{suffix}"
        failures.append(
            {
                "id": failure_id,
                "status": "open",
                "command": payload_command(tool_input) or tool_name,
                "evidence": failure_evidence or "tool reported failure",
                "opened_at": utc_now(),
            }
        )
        updated["scope_result"] = "rework-required"
        updated["operation_state"] = "in_progress"
    override = updated.get("enforcement_override") or {}
    if valid_override(updated):
        override["remaining_uses"] = max(0, positive_int(override.get("remaining_uses")) - 1)
        if override["remaining_uses"] == 0:
            override["enabled"] = False
    updated["updated_at"] = utc_now()
    return updated


def _workspace_root(workspace: Path) -> Path:
    root = Path(workspace).resolve(strict=False)
    if not root.exists() or not root.is_dir():
        raise ValueError(f"workspace is not a directory: {root}")
    return root


def _governance_directory(workspace: Path) -> tuple[Path, Path]:
    root = _workspace_root(workspace)
    directory = root / ".codex"
    if directory.is_symlink():
        raise ValueError("workspace .codex directory must not be a symlink")
    if directory.exists() and not directory.is_dir():
        raise ValueError("workspace .codex path must be a directory")
    return root, directory


def write_goal_state(workspace: Path, state: dict[str, Any]) -> None:
    errors = audit_state(state, workspace=workspace)
    if errors:
        raise ValueError(f"candidate goal state is invalid: {'; '.join(errors)}")
    path = state_path(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            delete=False,
            dir=path.parent,
            prefix="goal-state.",
            suffix=".tmp",
        ) as temporary:
            json.dump(state, temporary, indent=2, ensure_ascii=False)
            temporary.write("\n")
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_path = Path(temporary.name)
        os.replace(temporary_path, path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


@contextmanager
def goal_state_lock(workspace: Path):
    root, directory = _governance_directory(workspace)
    directory.mkdir(parents=True, exist_ok=True)
    state_file = directory / "goal-state.json"
    if state_file.is_symlink():
        raise ValueError("goal-state.json must not be a symlink")
    lock_path = directory / "goal-state.lock"
    if lock_path.is_symlink():
        raise ValueError("goal-state.lock must not be a symlink")
    handle = lock_path.open("a+b")
    try:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        try:
            handle.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()


def state_path(workspace: Path) -> Path:
    _, directory = _governance_directory(workspace)
    path = directory / "goal-state.json"
    if path.is_symlink():
        raise ValueError("goal-state.json must not be a symlink")
    return path


def state_file_present(workspace: Path) -> bool:
    """Return true for regular, corrupt, or dangling state paths."""
    try:
        return os.path.lexists(str(state_path(workspace)))
    except (OSError, ValueError):
        try:
            root = Path(workspace).resolve(strict=False)
            if (root / ".codex").is_symlink():
                return True
            raw_path = root / STATE_RELATIVE_PATH
            return os.path.lexists(str(raw_path))
        except OSError:
            return False


def load_goal_state(workspace: Path) -> StateLoadResult:
    try:
        path = state_path(workspace)
    except (OSError, RuntimeError, ValueError) as exc:
        path = Path(workspace).resolve(strict=False) / STATE_RELATIVE_PATH
        return StateLoadResult(True, error=str(exc), path=path)
    if not path.exists():
        if os.path.lexists(str(path)):
            return StateLoadResult(True, error="state path is dangling or unreadable", path=path)
        return StateLoadResult(False, path=path)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("root must be a JSON object")
        return StateLoadResult(True, value, path=path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return StateLoadResult(True, error=str(exc), path=path)


def _canonical_initial_state(
    goal: str,
    mode: str,
    start_layer: int,
    rationale: str,
    confirmation_id: str | None = None,
    delivery: dict[str, Any] | None = None,
) -> dict[str, Any]:
    goal = str(goal or "").strip()
    rationale = str(rationale or "").strip()
    mode = str(mode or "").strip().lower()
    if not goal:
        raise ValueError("goal is required")
    if mode not in ("bootstrap", "maintenance"):
        raise ValueError("mode must be bootstrap or maintenance")
    if (
        not isinstance(start_layer, int)
        or isinstance(start_layer, bool)
        or not 0 <= start_layer <= 6
    ):
        raise ValueError("start_layer must be an integer from 0 to 6")
    if not rationale:
        raise ValueError("rationale is required")
    confirmation = str(confirmation_id or "").strip()
    if mode == "bootstrap" and not confirmation:
        raise ValueError("bootstrap initialization requires confirmation_id")
    state = {
        "schema_version": 1,
        "goal": goal,
        "mode": mode,
        "phase": "classified",
        "start_layer": start_layer,
        "current_layer": start_layer,
        "classification": {
            "confirmed": mode == "maintenance" or bool(confirmation),
            "rationale": rationale,
            "confirmation_id": confirmation or None,
        },
        "plan": {"required": False, "approved": False, "path": None},
        "layers": {},
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
        "scope_result": "incomplete" if delivery is not None else "accepted",
        "operation_state": "in_progress",
        "updated_at": utc_now(),
    }
    if delivery is not None:
        state["delivery"] = delivery
    return state


def _create_state_exclusive(workspace: Path, state: dict[str, Any]) -> None:
    """Create the canonical state without ever replacing an existing file."""
    path = state_path(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(state, indent=2, ensure_ascii=False) + "\n"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    try:
        descriptor = os.open(path, flags, 0o600)
    except FileExistsError:
        raise ValueError("active goal state already exists") from None
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            descriptor = -1
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        if descriptor != -1:
            os.close(descriptor)
        path.unlink(missing_ok=True)
        raise


def initialize_state(
    workspace: Path,
    goal: str,
    mode: str,
    start_layer: int,
    rationale: str,
    confirmation_id: str | None = None,
    delivery: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Initialize a canonical classified state exactly once for a workspace."""
    root = Path(workspace)
    candidate = _canonical_initial_state(
        goal, mode, start_layer, rationale, confirmation_id, delivery
    )
    with goal_state_lock(root):
        loaded = load_goal_state(root)
        if loaded.active:
            if loaded.error:
                raise ValueError("goal state already exists but is corrupt")
            raise ValueError("active goal state already exists")
        _create_state_exclusive(root, candidate)
    return candidate


def rollback_layer(
    state: dict[str, Any], to_layer: int, reason: str, evidence: str
) -> dict[str, Any]:
    """Return a guard-owned state rewound to ``to_layer`` with fresh evidence gates."""
    reason = str(reason or "").strip()
    evidence = str(evidence or "").strip()
    if not reason or not evidence:
        raise ValueError("rollback reason and evidence are required")
    if (
        not isinstance(to_layer, int)
        or isinstance(to_layer, bool)
        or not 0 <= to_layer <= 6
    ):
        raise ValueError("to_layer must be an integer from 0 to 6")
    current = state.get("current_layer")
    start = state.get("start_layer")
    if (
        not isinstance(current, int)
        or isinstance(current, bool)
        or not isinstance(start, int)
        or isinstance(start, bool)
        or not 0 <= start <= current <= 6
    ):
        raise ValueError("state has invalid start_layer/current_layer")
    if to_layer > current:
        raise ValueError("rollback cannot move forward beyond current_layer")
    if state.get("phase") not in ("planned", "executing", "verified", "complete"):
        raise ValueError(
            "rollback requires a planned, executing, verified, or complete goal phase"
        )
    updated = json.loads(json.dumps(state))
    updated["phase"] = "executing"
    updated["start_layer"] = min(start, to_layer)
    updated["current_layer"] = to_layer
    layers = updated.get("layers")
    if isinstance(layers, dict):
        for key in list(layers):
            try:
                layer_number = int(key)
            except (TypeError, ValueError):
                continue
            if layer_number >= to_layer:
                del layers[key]
    else:
        updated["layers"] = {}
    sequence = int(updated.get("last_mutation_seq") or 0) + 1
    updated["last_mutation_seq"] = sequence
    verification = updated.setdefault("verification", {})
    verification["status"] = "stale"
    for field in ("command", "evidence", "verified_at", "workspace_fingerprint", "command_sha256"):
        verification[field] = None
    verification["mutation_seq"] = sequence
    updated["closure"] = {"recorded": False, "evidence": None, "workspace_fingerprint": None}
    updated["scope_result"] = "rework-required"
    updated["operation_state"] = "in_progress"
    if isinstance(updated.get("delivery"), dict):
        updated["delivery"] = invalidate_delivery(
            updated["delivery"],
            event="rollback",
            at=utc_now(),
            reason=reason,
            mutation_seq=sequence,
        )
    history = updated.setdefault("rollback_history", [])
    if not isinstance(history, list):
        raise ValueError("rollback_history must be an array")
    history.append(
        {
            "from_start_layer": start,
            "from_current_layer": current,
            "to_layer": to_layer,
            "reason": reason,
            "evidence": evidence,
            "at": utc_now(),
            "mutation_seq": sequence,
        }
    )
    updated["updated_at"] = utc_now()
    return updated


def render_reminder(state: dict[str, Any], enforcement_mode: str) -> str:
    phase = state.get("phase", "intake")
    layer = state.get("current_layer", "?")
    prefix = f"[GOAL ACTIVE mode={enforcement_mode} phase={phase} layer={layer}]"
    if enforcement_mode == "audit-only-windows":
        warning = "Windows lifecycle hooks are unavailable: violations are NOT mechanically blocked."
    else:
        warning = "Lifecycle hooks enforce mutation and completion gates."
    errors = audit_state(state)
    next_step = errors[0] if errors else "State audit currently passes."
    return f"{prefix}\n{warning}\nNext required check: {next_step}"


HOOK_PAYLOAD_ERROR = "__goal_guard_payload_error__"


def hook_payload() -> dict[str, Any]:
    try:
        raw = sys.stdin.read()
    except OSError as exc:
        return {HOOK_PAYLOAD_ERROR: f"unable to read hook payload: {exc}"}
    if not raw.strip():
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        return {HOOK_PAYLOAD_ERROR: f"invalid hook payload JSON: {exc.msg}"}
    if not isinstance(value, dict):
        return {HOOK_PAYLOAD_ERROR: "hook payload root must be a JSON object"}
    return value


def hook_payload_error(payload: dict[str, Any]) -> str | None:
    value = payload.get(HOOK_PAYLOAD_ERROR)
    return str(value).strip() if value else None


def _find_state_workspace(workspace: Path) -> Path | None:
    current = Path(workspace).resolve(strict=False)
    while current != Path(current.anchor):
        if state_file_present(current):
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    return None


def nearest_state_workspace(workspace: Path) -> Path:
    """Resolve a hook cwd to its nearest governed ancestor, excluding drive root."""
    current = Path(workspace).resolve(strict=False)
    return _find_state_workspace(current) or current


def resolve_cli_workspace(workspace: str | None) -> Path:
    """Resolve an explicit workspace or a governed ancestor of the CLI cwd."""
    if workspace:
        return Path(workspace)
    resolved = _find_state_workspace(Path.cwd())
    if resolved is None:
        raise ValueError(
            "--workspace is required when no active goal state exists in the current directory or its ancestors"
        )
    return resolved


def payload_workspace(payload: dict[str, Any], explicit: str | None = None) -> Path:
    # Hook payloads are untrusted input.  Path() raises TypeError for values
    # such as objects, arrays, or numbers; convert that into a ValueError so
    # the CLI's top-level hook handler can emit a fail-closed JSON decision.
    if explicit is not None:
        raw: Any = explicit
    elif "cwd" in payload:
        raw = payload.get("cwd")
    elif "workspace" in payload:
        raw = payload.get("workspace")
    else:
        raw = os.getcwd()
    if isinstance(raw, os.PathLike):
        raw = os.fspath(raw)
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("hook workspace must be a path string")
    try:
        candidate = Path(raw)
    except (TypeError, ValueError, OSError) as exc:
        raise ValueError(f"hook workspace is invalid: {exc}") from exc
    try:
        return nearest_state_workspace(candidate)
    except (OSError, RuntimeError, ValueError) as exc:
        # Symlink loops and inaccessible paths must become a deterministic
        # hook response instead of an uncaught process exception.
        raise ValueError(f"hook workspace cannot be resolved: {exc}") from exc


def hook_tool(payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    raw_name = payload.get("tool_name") if "tool_name" in payload else payload.get("toolName")
    if not isinstance(raw_name, str) or not raw_name.strip():
        return "", {HOOK_PAYLOAD_ERROR: "hook tool_name must be a non-empty string"}
    if "tool_input" in payload:
        raw_input = payload.get("tool_input")
    elif "toolInput" in payload:
        raw_input = payload.get("toolInput")
    else:
        raw_input = {}
    if not isinstance(raw_input, dict):
        return raw_name, {HOOK_PAYLOAD_ERROR: "hook tool_input must be a JSON object"}
    return raw_name, raw_input


def emit(value: dict[str, Any]) -> None:
    print(json.dumps(value, ensure_ascii=False), flush=True)


def run_pre_tool_use(workspace: str | None) -> int:
    payload = hook_payload()
    if (payload_error := hook_payload_error(payload)):
        emit({"decision": "block", "reason": payload_error, "systemMessage": payload_error})
        return 0
    root = payload_workspace(payload, workspace)
    name, tool_input = hook_tool(payload)
    if (tool_error := hook_payload_error(tool_input)):
        emit({"decision": "block", "reason": tool_error, "systemMessage": tool_error})
        return 0
    if not state_file_present(root):
        if targets_protected_state(tool_input):
            reason = "Use goal_guard.py commands; direct goal-state edits are blocked"
            emit({"decision": "block", "reason": reason, "systemMessage": reason})
            return 0
        decision = evaluate_tool_call(None, name, tool_input)
        if decision.allowed:
            emit({})
        else:
            emit({"decision": "block", "reason": decision.reason, "systemMessage": decision.reason})
        return 0
    with goal_state_lock(root):
        loaded = load_goal_state(root)
        decision = evaluate_tool_call(
            loaded.state, name, tool_input, state_error=loaded.error, workspace=root
        )
        if decision.allowed and loaded.state is not None:
            updated = loaded.state
            if decision.code == "override":
                updated = consume_override(updated)
            if is_mutation(name, tool_input, root):
                reservation_id = mutation_reservation_id(payload, name, tool_input)
                updated = reserve_mutation(updated, name, tool_input, reservation_id, root)
            if updated != loaded.state:
                write_goal_state(root, updated)
    if decision.allowed:
        emit({"systemMessage": decision.reason} if decision.code == "override" else {})
        return 0
    emit({"decision": "block", "reason": decision.reason, "systemMessage": decision.reason})
    return 0


def payload_success(payload: dict[str, Any]) -> tuple[bool, str | None]:
    for key in ("is_error", "isError"):
        if key in payload:
            value = payload.get(key)
            if not isinstance(value, bool):
                return False, f"{key} must be boolean"
            if value:
                return False, str(payload.get("error") or "tool reported error")
    response = payload.get("tool_response") or payload.get("toolResponse") or {}
    if isinstance(response, dict):
        code = response.get("exit_code", response.get("exitCode"))
        if code not in (None, 0, "0"):
            return False, f"exit code {code}"
    return True, None


def run_post_tool_use(workspace: str | None) -> int:
    payload = hook_payload()
    if (payload_error := hook_payload_error(payload)):
        emit({"systemMessage": payload_error})
        return 0
    root = payload_workspace(payload, workspace)
    if not state_file_present(root):
        emit({})
        return 0
    with goal_state_lock(root):
        loaded = load_goal_state(root)
        if not loaded.active:
            emit({})
            return 0
        if loaded.error or loaded.state is None:
            emit({"systemMessage": f"[GOAL STATE INVALID] {loaded.error or 'missing object'}"})
            return 0
        semantic_errors = audit_state(loaded.state, workspace=root)
        if semantic_errors:
            emit({"systemMessage": f"[GOAL STATE INVALID] {'; '.join(semantic_errors)}"})
            return 0
        name, tool_input = hook_tool(payload)
        if (tool_error := hook_payload_error(tool_input)):
            emit({"systemMessage": tool_error})
            return 0
        success, evidence = payload_success(payload)
        reservation_id = mutation_reservation_id(payload, name, tool_input)
        updated = apply_post_tool_use(
            loaded.state,
            name,
            tool_input,
            success=success,
            failure_evidence=evidence,
            reservation_id=reservation_id,
            workspace=root,
        )
        if updated != loaded.state:
            write_goal_state(root, updated)
    emit({})
    return 0


def run_reminder(workspace: str | None, mode: str) -> int:
    payload = hook_payload()
    if (payload_error := hook_payload_error(payload)):
        emit({"systemMessage": payload_error})
        return 0
    loaded = load_goal_state(payload_workspace(payload, workspace))
    if not loaded.active:
        emit({})
    elif loaded.error:
        emit({"systemMessage": f"[GOAL STATE INVALID] {loaded.error}"})
    else:
        emit({"systemMessage": render_reminder(loaded.state or {}, mode)})
    return 0


def run_resolve_failure(
    workspace: str | None, failure_id: str, evidence: str
) -> int:
    try:
        root = resolve_cli_workspace(workspace)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    with goal_state_lock(root):
        loaded = load_goal_state(root)
        if not loaded.active or loaded.error or loaded.state is None:
            print("A valid active goal state is required", file=sys.stderr)
            return 2
        try:
            updated = resolve_failure(loaded.state, failure_id, evidence)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        write_goal_state(root, updated)
    print("PASS: failure resolution recorded")
    return 0


def run_recover_reservation(
    workspace: str | None, reservation_id: str, evidence: str
) -> int:
    try:
        root = resolve_cli_workspace(workspace)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    with goal_state_lock(root):
        loaded = load_goal_state(root)
        if not loaded.active or loaded.error or loaded.state is None:
            print("A valid active goal state is required", file=sys.stderr)
            return 2
        try:
            updated = recover_reservation(loaded.state, reservation_id, evidence)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        write_goal_state(root, updated)
    print("PASS: orphan reservation recovery recorded as an open failure")
    return 0


def run_authorize_override(
    workspace: str | None, reason: str, confirmation_id: str
) -> int:
    if not sys.stdin.isatty():
        print("authorize-override requires an interactive human terminal", file=sys.stderr)
        return 2
    try:
        root = resolve_cli_workspace(workspace)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    typed = input(f"Type confirmation id {confirmation_id!r}: ")
    with goal_state_lock(root):
        loaded = load_goal_state(root)
        if not loaded.active or loaded.error or loaded.state is None:
            print("A valid active goal state is required", file=sys.stderr)
            return 2
        try:
            updated = authorize_override(loaded.state, reason, confirmation_id, typed)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        write_goal_state(root, updated)
    print("PASS: single-use override authorized interactively")
    return 0


def run_write_state(
    workspace: str | None,
    candidate_file: str,
    expected_state_sha256: str | None = None,
) -> int:
    try:
        root = resolve_cli_workspace(workspace)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    try:
        candidate = json.loads(Path(candidate_file).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Invalid candidate state: {exc}", file=sys.stderr)
        return 2
    if not isinstance(candidate, dict):
        print("Invalid candidate state: root must be an object", file=sys.stderr)
        return 2
    with goal_state_lock(root):
        current_bytes = state_path(root).read_bytes() if state_path(root).exists() else b""
        loaded = load_goal_state(root)
        if not loaded.active:
            print("No active goal state; run initialize-state before write-state", file=sys.stderr)
            return 2
        if loaded.error:
            print(f"Current goal state is invalid: {loaded.error}", file=sys.stderr)
            return 2
        transition_errors = validate_transition(loaded.state, candidate, workspace=root)
        if transition_errors and "delivery" not in loaded.state and "delivery" in candidate:
            for error in transition_errors:
                print(f"FAIL: {error}")
            return 1
        delivery_mode = "delivery" in loaded.state or "delivery" in candidate
        if delivery_mode:
            if (
                not isinstance(expected_state_sha256, str)
                or not re.fullmatch(r"[0-9a-f]{64}", expected_state_sha256)
            ):
                print("FAIL: DELIVERY_STATE_STALE expected current state SHA-256 is required")
                return 1
            current_sha256 = hashlib.sha256(current_bytes).hexdigest()
            if current_sha256 != expected_state_sha256:
                print("FAIL: DELIVERY_STATE_STALE current state bytes changed")
                return 1
        errors = validate_transition(loaded.state, candidate, workspace=root)
        if errors:
            for error in errors:
                print(f"FAIL: {error}")
            return 1
        candidate["updated_at"] = utc_now()
        write_goal_state(root, candidate)
    print("PASS: goal state transition recorded")
    return 0


def run_initialize_state(
    workspace: str | None,
    goal: str,
    mode: str,
    start_layer: int,
    rationale: str,
    confirmation_id: str | None,
    delivery_file: str | None = None,
) -> int:
    if not workspace:
        print("--workspace is required for initialize-state", file=sys.stderr)
        return 2
    try:
        root = resolve_cli_workspace(workspace)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    try:
        delivery = None
        if delivery_file:
            delivery = json.loads(Path(delivery_file).read_text(encoding="utf-8"))
            if not isinstance(delivery, dict) or delivery.get("profile") != "web-fullstack":
                raise ValueError("delivery file must contain a web-fullstack delivery object")
            delivery_errors = [
                *validate_delivery_shape(delivery),
                *validate_delivery_links(delivery),
            ]
            if delivery_errors:
                first = delivery_errors[0]
                raise ValueError(f"{first.code} at {first.path}: {first.message}")
        initialize_state(root, goal, mode, start_layer, rationale, confirmation_id, delivery)
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print("PASS: classified goal state initialized")
    return 0


def run_rollback_layer(
    workspace: str | None, to_layer: int, reason: str, evidence: str
) -> int:
    try:
        root = resolve_cli_workspace(workspace)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    with goal_state_lock(root):
        loaded = load_goal_state(root)
        if not loaded.active or loaded.error or loaded.state is None:
            print("A valid active goal state is required", file=sys.stderr)
            return 2
        # Rollback is the recovery path for drift, so it must not require the
        # fingerprint that the rollback is about to invalidate.
        errors = audit_state(loaded.state)
        if errors:
            print(f"Current goal state is invalid: {'; '.join(errors)}", file=sys.stderr)
            return 2
        try:
            updated = rollback_layer(loaded.state, to_layer, reason, evidence)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        write_goal_state(root, updated)
    print(f"PASS: goal state rolled back to layer {to_layer}")
    return 0


def run_stop(workspace: str | None) -> int:
    payload = hook_payload()
    if not payload and workspace is None:
        message = "Stop hook payload is required to resolve the governed workspace"
        emit({"decision": "block", "reason": message, "systemMessage": message})
        return 0
    if (payload_error := hook_payload_error(payload)):
        emit({"decision": "block", "reason": payload_error, "systemMessage": payload_error})
        return 0
    root = payload_workspace(payload, workspace)
    if not state_file_present(root):
        emit({})
        return 0
    with goal_state_lock(root):
        loaded = load_goal_state(root)
        decision = evaluate_stop(loaded.state, state_error=loaded.error, workspace=root)
        if decision.allowed and loaded.state is not None:
            updated = loaded.state
            if decision.code == "override":
                updated = consume_override(updated)
            if updated != loaded.state:
                write_goal_state(root, updated)
    if decision.allowed:
        emit({})
    else:
        emit({"decision": "block", "reason": decision.reason, "systemMessage": decision.reason})
    return 0


def run_audit(workspace: str | None) -> int:
    try:
        root = resolve_cli_workspace(workspace)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if not state_file_present(root):
        print("No active .codex/goal-state.json", file=sys.stderr)
        return 2
    with goal_state_lock(root):
        loaded = load_goal_state(root)
        if loaded.error:
            print(f"Invalid goal state: {loaded.error}", file=sys.stderr)
            return 2
        errors = audit_state(loaded.state or {}, workspace=root)
    if not loaded.active:
        print("No active .codex/goal-state.json", file=sys.stderr)
        return 2
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print("PASS: goal state audit")
    return 0


def run_capabilities() -> int:
    print(json.dumps(CAPABILITY_DESCRIPTOR, sort_keys=True))
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    sub = root.add_subparsers(dest="command", required=True)
    sub.add_parser("capabilities")
    for command in ("pre-tool-use", "post-tool-use", "stop", "audit"):
        item = sub.add_parser(command)
        item.add_argument("--workspace")
    writer = sub.add_parser("write-state")
    writer.add_argument("--workspace")
    writer.add_argument("--file", required=True)
    writer.add_argument("--expected-state-sha256")
    initializer = sub.add_parser("initialize-state")
    initializer.add_argument("--workspace")
    initializer.add_argument("--goal", required=True)
    initializer.add_argument("--mode", required=True, choices=("bootstrap", "maintenance"))
    initializer.add_argument("--start-layer", required=True, type=int)
    initializer.add_argument("--rationale", required=True)
    initializer.add_argument("--confirmation-id")
    initializer.add_argument("--delivery-file")
    rollback = sub.add_parser("rollback-layer")
    rollback.add_argument("--workspace")
    rollback.add_argument("--to-layer", required=True, type=int)
    rollback.add_argument("--reason", required=True)
    rollback.add_argument("--evidence", required=True)
    override = sub.add_parser("authorize-override")
    override.add_argument("--workspace")
    override.add_argument("--reason", required=True)
    override.add_argument("--confirmation-id", required=True)
    resolver = sub.add_parser("resolve-failure")
    resolver.add_argument("--workspace")
    resolver.add_argument("--failure-id", required=True)
    resolver.add_argument("--evidence", required=True)
    recovery = sub.add_parser("recover-reservation")
    recovery.add_argument("--workspace")
    recovery.add_argument("--reservation-id", required=True)
    recovery.add_argument("--evidence", required=True)
    for command in ("user-prompt-submit", "session-start"):
        item = sub.add_parser(command)
        item.add_argument("--workspace")
        item.add_argument("--mode", default="hard-hook")
    return root


def _dispatch(args: argparse.Namespace) -> int:
    if args.command == "capabilities":
        return run_capabilities()
    if args.command == "pre-tool-use":
        return run_pre_tool_use(args.workspace)
    if args.command == "post-tool-use":
        return run_post_tool_use(args.workspace)
    if args.command == "write-state":
        return run_write_state(
            args.workspace, args.file, args.expected_state_sha256
        )
    if args.command == "initialize-state":
        return run_initialize_state(
            args.workspace,
            args.goal,
            args.mode,
            args.start_layer,
            args.rationale,
            args.confirmation_id,
            args.delivery_file,
        )
    if args.command == "rollback-layer":
        return run_rollback_layer(
            args.workspace, args.to_layer, args.reason, args.evidence
        )
    if args.command == "authorize-override":
        return run_authorize_override(
            args.workspace, args.reason, args.confirmation_id
        )
    if args.command == "resolve-failure":
        return run_resolve_failure(
            args.workspace, args.failure_id, args.evidence
        )
    if args.command == "recover-reservation":
        return run_recover_reservation(
            args.workspace, args.reservation_id, args.evidence
        )
    if args.command == "stop":
        return run_stop(args.workspace)
    if args.command == "audit":
        return run_audit(args.workspace)
    return run_reminder(args.workspace, args.mode)


def main() -> int:
    args = parser().parse_args()
    try:
        return _dispatch(args)
    except (OSError, RuntimeError, ValueError, EOFError) as exc:
        message = f"goal guard refused operation: {exc}"
        if args.command in {"pre-tool-use", "post-tool-use", "stop", "user-prompt-submit", "session-start"}:
            response = {"reason": message, "systemMessage": message}
            if args.command in {"pre-tool-use", "stop"}:
                response["decision"] = "block"
            emit(response)
            return 0
        print(message, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
