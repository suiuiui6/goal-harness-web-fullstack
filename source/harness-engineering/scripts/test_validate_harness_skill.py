import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

sys.dont_write_bytecode = True


def _remove_module_cache_file() -> None:
    cached = globals().get("__cached__")
    if not cached:
        return
    cached_path = Path(cached)
    try:
        if cached_path.is_file():
            cached_path.unlink()
        parent = cached_path.parent
        if parent.name == "__pycache__" and parent.is_dir() and not any(parent.iterdir()):
            parent.rmdir()
    except OSError:
        pass


_remove_module_cache_file()


SCRIPT_DIR = Path(__file__).resolve().parent
BUNDLE_ROOT = SCRIPT_DIR.parent
VALIDATOR_PATH = SCRIPT_DIR / "validate_harness_skill.py"


def _portable_temp_parent() -> Path:
    """Select an existing writable directory outside the bundle under test."""
    bundle_root = BUNDLE_ROOT.resolve()
    cwd = Path.cwd().resolve()
    candidates = (cwd, cwd.parent, Path(cwd.anchor), Path(tempfile.gettempdir()).resolve())
    for candidate in candidates:
        try:
            candidate.relative_to(bundle_root)
        except ValueError:
            pass
        else:
            continue
        if not candidate.is_dir():
            continue
        probe = candidate / f".harness-test-probe-{os.getpid()}-{time.time_ns()}"
        marker = probe / "write-read-delete.txt"
        try:
            probe.mkdir()
            marker.write_text("probe", encoding="utf-8")
            if marker.read_text(encoding="utf-8") != "probe":
                raise OSError("temporary parent probe round-trip failed")
            marker.unlink()
            probe.rmdir()
            return candidate
        except OSError:
            try:
                if marker.is_file():
                    marker.unlink()
                if probe.is_dir():
                    probe.rmdir()
            except OSError:
                pass
    raise RuntimeError("no writable temporary parent outside harness bundle")


TEMP_ROOT = _portable_temp_parent()


def load_validator():
    spec = importlib.util.spec_from_file_location("validate_harness_skill", VALIDATOR_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class HarnessSkillValidatorTests(unittest.TestCase):
    def setUp(self):
        self.validator = load_validator()

    def copy_bundle(self, destination: Path) -> Path:
        target = destination / "harness-engineering"
        shutil.copytree(
            BUNDLE_ROOT,
            target,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        return target

    def test_repository_bundle_passes_complete_validation(self):
        self.assertEqual([], self.validator.validate_bundle(BUNDLE_ROOT))

    def test_invalid_frontmatter_name_is_reported(self):
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as temp_dir:
            root = self.copy_bundle(Path(temp_dir))
            skill = root / "SKILL.md"
            skill.write_text(
                skill.read_text(encoding="utf-8").replace(
                    "name: harness-engineering", "name: wrong-name", 1
                ),
                encoding="utf-8",
            )

            errors = self.validator.validate_bundle(root)

            self.assertTrue(
                any("frontmatter name must be harness-engineering" in error for error in errors),
                errors,
            )

    def test_broken_skill_resource_link_is_reported(self):
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as temp_dir:
            root = self.copy_bundle(Path(temp_dir))
            skill = root / "SKILL.md"
            skill.write_text(
                skill.read_text(encoding="utf-8")
                + "\n- Read `references/missing-resource.md` for this branch.\n",
                encoding="utf-8",
            )

            errors = self.validator.validate_bundle(root)

            self.assertTrue(
                any("missing linked resource" in error for error in errors),
                errors,
            )

    def test_skill_routes_decision_quality_reference(self):
        skill = (BUNDLE_ROOT / "SKILL.md").read_text(encoding="utf-8")

        self.assertEqual(1, skill.count("`references/decision-quality.md`"))

    def test_decision_quality_route_is_required(self):
        self.assertIn("references/decision-quality.md", self.validator.REQUIRED_SKILL_ROUTES)
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as temp_dir:
            root = self.copy_bundle(Path(temp_dir))
            skill = root / "SKILL.md"
            skill.write_text(
                skill.read_text(encoding="utf-8").replace(
                    "`references/decision-quality.md`",
                    "`references/decision-quality-removed.md`",
                    1,
                ),
                encoding="utf-8",
            )

            errors = self.validator.validate_bundle(root)

            self.assertTrue(
                any(
                    "decision-quality" in error and "removed" in error
                    for error in errors
                ),
                errors,
            )

    def test_decision_quality_evidence_blocks_share_canonical_labels(self):
        paths = (
            BUNDLE_ROOT / "references" / "decision-quality.md",
            BUNDLE_ROOT / "references" / "output-contract.md",
        )
        canonical_labels = (
            "Decision quality:\n",
            "  Trigger:",
            "  Protocol: first_principles|adversarial|both|skipped",
            "  Constraints:",
            "  Assumptions:",
            "  Falsifier:",
            "  Falsifiers / probes:",
            "  Decision:",
            "  Result: pass|stay|rollback|blocked",
            "  Residual risk:",
        )

        for path in paths:
            self.assertTrue(path.is_file())
            text = path.read_text(encoding="utf-8")
            for marker in canonical_labels:
                self.assertIn(marker, text, path.name)

    def test_decision_quality_reference_contains_canonical_protocol_markers(self):
        reference = BUNDLE_ROOT / "references" / "decision-quality.md"

        self.assertTrue(reference.is_file())
        text = reference.read_text(encoding="utf-8")
        for marker in (
            "## First-principles trigger",
            "## Adversarial trigger and minimum review",
            "Decision quality:",
            "pass | stay | rollback | blocked",
            "local or requires upstream rollback",
            "final closure",
            "high-risk assumption",
            "unverified path",
        ):
            self.assertIn(marker, text)

    def test_missing_decision_quality_reference_is_reported(self):
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as temp_dir:
            root = self.copy_bundle(Path(temp_dir))
            (root / "references" / "decision-quality.md").unlink(missing_ok=True)

            errors = self.validator.validate_bundle(root)

            self.assertTrue(
                any("decision-quality.md" in error for error in errors),
                errors,
            )

    def test_generated_python_cache_is_reported(self):
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as temp_dir:
            root = self.copy_bundle(Path(temp_dir))
            cache = root / "scripts" / "__pycache__" / "generated.pyc"
            cache.parent.mkdir(parents=True)
            cache.write_bytes(b"generated")

            errors = self.validator.validate_bundle(root)

            self.assertTrue(
                any("generated cache artifact" in error for error in errors),
                errors,
            )

    def test_public_validator_reports_contract_drift(self):
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as temp_dir:
            root = self.copy_bundle(Path(temp_dir))
            contract = root / "references" / "output-contract.md"
            contract.write_text(
                contract.read_text(encoding="utf-8").replace(
                    "scope_result", "scope-outcome"
                ),
                encoding="utf-8",
            )

            errors = self.validator.validate_bundle(root)

            self.assertTrue(
                any("closure-fields" in error for error in errors),
                errors,
            )

    def test_validator_cli_does_not_generate_python_cache(self):
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as temp_dir:
            root = self.copy_bundle(Path(temp_dir))
            result = subprocess.run(
                [sys.executable, str(root / "scripts" / "validate_harness_skill.py"), str(root)],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertFalse((root / "scripts" / "__pycache__").exists())

    def test_behavior_catalog_deletion_is_reported(self):
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as temp_dir:
            root = self.copy_bundle(Path(temp_dir))
            catalog = root / "evals" / "codex-behavior-evals.json"
            payload = json.loads(catalog.read_text(encoding="utf-8"))
            payload["evals"].pop()
            catalog.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

            errors = self.validator.validate_bundle(root)

            self.assertTrue(any("missing behavior eval ids" in error for error in errors), errors)
            self.assertTrue(any("exactly 22" in error for error in errors), errors)

    def test_behavior_catalog_id_drift_reports_missing_and_extra(self):
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as temp_dir:
            root = self.copy_bundle(Path(temp_dir))
            catalog = root / "evals" / "claude-behavior-evals.json"
            payload = json.loads(catalog.read_text(encoding="utf-8"))
            payload["evals"][0]["id"] = 999
            catalog.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

            errors = self.validator.validate_bundle(root)

            self.assertTrue(any("missing behavior eval ids" in error and "101" in error for error in errors), errors)
            self.assertTrue(any("unexpected behavior eval ids" in error and "999" in error for error in errors), errors)

    def test_behavior_catalog_duplicate_id_is_reported(self):
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as temp_dir:
            root = self.copy_bundle(Path(temp_dir))
            catalog = root / "evals" / "claude-behavior-evals.json"
            payload = json.loads(catalog.read_text(encoding="utf-8"))
            payload["evals"][0]["id"] = 1
            catalog.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

            errors = self.validator.validate_bundle(root)

            self.assertTrue(any("duplicate behavior eval id: 1" in error for error in errors), errors)

    def test_plain_unittest_discover_does_not_generate_python_cache(self):
        if os.environ.get("HARNESS_SKIP_NESTED_DISCOVER") == "1":
            self.skipTest("avoid recursive nested unittest discovery")

        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as temp_dir:
            root = self.copy_bundle(Path(temp_dir))
            env = dict(os.environ)
            env["HARNESS_SKIP_NESTED_DISCOVER"] = "1"
            result = subprocess.run(
                [sys.executable, "-m", "unittest", "discover", "-p", "test_*.py", "-v"],
                cwd=root / "scripts",
                capture_output=True,
                text=True,
                check=False,
                env=env,
            )

            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertFalse((root / "scripts" / "__pycache__").exists())


if __name__ == "__main__":
    unittest.main()
