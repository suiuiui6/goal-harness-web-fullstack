import hashlib
from pathlib import Path

import pytest

from delivery_evidence import audit_delivery_files
from delivery_fixtures import accepted_delivery


def write_output(root: Path, content=b"{}"):
    output = root / ".codex" / "evidence" / "result.json"
    output.parent.mkdir(parents=True)
    output.write_bytes(content)
    return output


def test_matching_artifact_digest_and_bytes_pass(tmp_path):
    delivery = accepted_delivery()
    write_output(tmp_path)
    assert audit_delivery_files(delivery, tmp_path) == []


def test_same_length_artifact_tampering_is_stale(tmp_path):
    delivery = accepted_delivery()
    output = write_output(tmp_path)
    output.write_bytes(b"[]")
    errors = audit_delivery_files(delivery, tmp_path)
    assert any(error.code == "DELIVERY_ARTIFACT_STALE" for error in errors)


@pytest.mark.parametrize("path", ["/absolute.json", r"\server\share\result.json", "../outside.json", "C:result.json", "nested/../outside.json"])
def test_unsafe_output_paths_are_rejected(tmp_path, path):
    delivery = accepted_delivery()
    delivery["evidence"][0]["outputs"][0]["path"] = path
    errors = audit_delivery_files(delivery, tmp_path)
    assert any(error.code == "DELIVERY_ARTIFACT_PATH_INVALID" for error in errors)


def test_directory_link_ancestor_is_rejected_when_supported(tmp_path):
    delivery = accepted_delivery()
    outside = tmp_path.parent / "outside-evidence"
    outside.mkdir()
    linked = tmp_path / ".codex"
    try:
        linked.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("directory links are unavailable in this test environment")
    errors = audit_delivery_files(delivery, tmp_path)
    assert any(error.code == "DELIVERY_ARTIFACT_PATH_INVALID" for error in errors)
