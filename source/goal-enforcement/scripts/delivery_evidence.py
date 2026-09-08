import hashlib
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import stat

from delivery_contract import Issue


def _issue(code, path, message):
    return Issue(code, path, message)


def _is_reparse(path):
    if path.is_symlink():
        return True
    try:
        attributes = path.lstat().st_file_attributes
    except (AttributeError, OSError):
        return False
    return bool(attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def _safe_output_path(workspace, raw_path):
    if not isinstance(raw_path, str) or not raw_path or "\x00" in raw_path or ":" in raw_path:
        return None
    windows = PureWindowsPath(raw_path)
    posix = PurePosixPath(raw_path.replace("\\", "/"))
    if windows.is_absolute() or windows.drive or windows.root or posix.is_absolute():
        return None
    if ".." in windows.parts or ".." in posix.parts:
        return None
    root = Path(workspace).resolve(strict=True)
    current = root
    if _is_reparse(root):
        return None
    for part in posix.parts:
        if part in {"", "."}:
            continue
        current = current / part
        if current.exists() and _is_reparse(current):
            return None
    try:
        resolved = current.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, ValueError):
        return None
    if _is_reparse(resolved):
        return None
    try:
        mode = resolved.stat().st_mode
    except OSError:
        return None
    if not stat.S_ISREG(mode):
        return None
    return resolved


def _digest(path):
    hasher = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            size += len(chunk)
            hasher.update(chunk)
    return size, hasher.hexdigest()


def audit_delivery_files(delivery: dict, workspace: Path) -> list[Issue]:
    issues = []
    for evidence_index, evidence in enumerate(delivery.get("evidence", [])):
        if not isinstance(evidence, dict):
            continue
        for output_index, output in enumerate(evidence.get("outputs", [])):
            path = f"delivery.evidence[{evidence_index}].outputs[{output_index}]"
            if not isinstance(output, dict):
                issues.append(_issue("DELIVERY_ARTIFACT_PATH_INVALID", path, "output must be an object"))
                continue
            resolved = _safe_output_path(workspace, output.get("path"))
            if resolved is None:
                issues.append(_issue("DELIVERY_ARTIFACT_PATH_INVALID", f"{path}.path", "unsafe or missing output path"))
                continue
            try:
                size, digest = _digest(resolved)
            except OSError as error:
                issues.append(_issue("DELIVERY_ARTIFACT_READ_FAILED", f"{path}.path", str(error)))
                continue
            if size != output.get("bytes") or digest != output.get("sha256"):
                issues.append(_issue("DELIVERY_ARTIFACT_STALE", path, "output bytes or digest changed"))
    return issues
