import importlib.util
import json
import os
from pathlib import Path
import shutil
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
VALIDATOR_PATH = SCRIPT_DIR / "contract_consistency.py"


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


def load_validator_module():
    spec = importlib.util.spec_from_file_location("contract_consistency", VALIDATOR_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ContractConsistencyTests(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        cls.validator = load_validator_module()

    def copy_bundle(self, destination: Path) -> Path:
        target = destination / "harness-engineering"
        shutil.copytree(
            BUNDLE_ROOT,
            target,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        return target

    def load_catalog(self, root: Path = BUNDLE_ROOT) -> dict:
        return json.loads((root / "evals" / "contract-invariants.json").read_text(encoding="utf-8"))

    def test_current_bundle_satisfies_contract_invariants(self):
        self.assertEqual([], self.validator.validate_contract_consistency(BUNDLE_ROOT))

    def test_relative_catalog_path_override_resolves_from_root(self):
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as temp_dir:
            root = self.copy_bundle(Path(temp_dir))
            errors = self.validator.validate_contract_consistency(
                root,
                Path("evals/contract-invariants.json"),
            )
            self.assertEqual([], errors)

    def test_catalog_stays_shared_contract_focused(self):
        catalog = self.load_catalog()
        invariants = {invariant["id"]: invariant["documents"] for invariant in catalog["invariants"]}

        self.assertEqual(
            {
                "entry-classification",
                "evidence-before-advance",
                "minimal-rollback",
                "layer5-product-contract",
                "closure-fields",
                "runtime-writeback",
                "decision-quality-contract",
            },
            set(invariants),
        )

        all_paths = [
            document["path"]
            for documents in invariants.values()
            for document in documents
        ]
        self.assertFalse(any(path.startswith("adapters/") for path in all_paths), all_paths)

        entry_paths = {document["path"] for document in invariants["entry-classification"]}
        self.assertTrue(
            {"SPEC.md", "PHASES.md", "core/flow.md", "references/runtime-stages.md"}.issubset(entry_paths),
            entry_paths,
        )
        entry_groups = [
            token
            for document in invariants["entry-classification"]
            for group in document["required_any"]
            for token in group
        ]
        self.assertFalse(any("start layer" in token.casefold() for token in entry_groups), entry_groups)
        self.assertFalse(any("smallest valid start layer" in token.casefold() for token in entry_groups), entry_groups)

        evidence_paths = {document["path"] for document in invariants["evidence-before-advance"]}
        self.assertIn("CHECKS.md", evidence_paths)

        rollback_paths = {document["path"] for document in invariants["minimal-rollback"]}
        self.assertIn("core/exit-and-reentry.md", rollback_paths)

        closure_paths = {document["path"] for document in invariants["closure-fields"]}
        self.assertIn("references/output-contract.md", closure_paths)

        decision_quality_paths = {
            document["path"] for document in invariants["decision-quality-contract"]
        }
        self.assertTrue(
            {
                "references/decision-quality.md",
                "core/checklists.md",
                "CHECKS.md",
                "references/output-contract.md",
            }.issubset(decision_quality_paths),
            decision_quality_paths,
        )

    def test_harmless_doc_paraphrase_still_passes(self):
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as temp_dir:
            root = self.copy_bundle(Path(temp_dir))
            phases_path = root / "PHASES.md"
            phases_text = phases_path.read_text(encoding="utf-8")
            self.assertEqual(
                1,
                phases_text.count("## Phase 0: Intake and Entry Classification"),
            )
            phases_text = phases_text.replace(
                "## Phase 0: Intake and Entry Classification",
                "## Phase 0: Work Intake and Mode Classification",
                1,
            )
            self.assertEqual(
                1,
                phases_text.count(
                    "Let runtime facts override stale documents; write back or roll back immediately."
                ),
            )
            phases_text = phases_text.replace(
                "Let runtime facts override stale documents; write back or roll back immediately.",
                "Let runtime findings override stale docs; write back or roll back right away.",
                1,
            )
            phases_path.write_text(phases_text, encoding="utf-8")

            errors = self.validator.validate_contract_consistency(root)

            self.assertEqual([], errors)

    def test_missing_mirrored_concept_reports_invariant_and_path(self):
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as temp_dir:
            root = self.copy_bundle(Path(temp_dir))
            flow_path = root / "core" / "flow.md"
            flow_path.write_text(
                flow_path.read_text(encoding="utf-8").replace(
                    "minimum rollback scope", "rollback scope", 1
                ),
                encoding="utf-8",
            )

            errors = self.validator.validate_contract_consistency(root)

            self.assertTrue(
                any("minimal-rollback" in error and "core/flow.md" in error for error in errors),
                errors,
            )

    def test_missing_referenced_document_reports_invariant_and_path(self):
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as temp_dir:
            root = self.copy_bundle(Path(temp_dir))
            target = root / "core" / "exit-and-reentry.md"
            target.unlink()

            errors = self.validator.validate_contract_consistency(root)

            self.assertTrue(
                any(
                    "minimal-rollback" in error and "core/exit-and-reentry.md" in error
                    for error in errors
                ),
                errors,
            )

    def test_decision_quality_invariant_detects_missing_falsifier(self):
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as temp_dir:
            root = self.copy_bundle(Path(temp_dir))
            decision_quality_path = root / "references" / "decision-quality.md"
            decision_quality_path.write_text(
                decision_quality_path.read_text(encoding="utf-8").replace(
                    "Falsifier:", "Invalidator:", 1
                ),
                encoding="utf-8",
            )

            errors = self.validator.validate_contract_consistency(root)

            self.assertTrue(
                any(
                    "decision-quality" in error and "decision-quality.md" in error
                    for error in errors
                ),
                errors,
            )

    def test_duplicate_invariant_id_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as temp_dir:
            root = self.copy_bundle(Path(temp_dir))
            catalog = self.load_catalog(root)
            catalog["invariants"].append(dict(catalog["invariants"][0]))
            (root / "evals" / "contract-invariants.json").write_text(
                json.dumps(catalog, indent=2) + "\n",
                encoding="utf-8",
            )

            errors = self.validator.validate_contract_consistency(root)

            self.assertTrue(any("duplicate invariant id" in error for error in errors), errors)

    def test_invalid_document_rule_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as temp_dir:
            root = self.copy_bundle(Path(temp_dir))
            catalog = self.load_catalog(root)
            catalog["invariants"][0]["documents"][0]["path"] = 7
            catalog["invariants"][0]["documents"][1]["required_any"] = "bootstrap mode"
            (root / "evals" / "contract-invariants.json").write_text(
                json.dumps(catalog, indent=2) + "\n",
                encoding="utf-8",
            )

            errors = self.validator.validate_contract_consistency(root)

            self.assertTrue(any("must define a non-empty string path" in error for error in errors), errors)
            self.assertTrue(any("must define non-empty required_any" in error for error in errors), errors)

    def test_required_any_alternatives_and_groups_have_expected_semantics(self):
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as temp_dir:
            root = Path(temp_dir)
            (root / "evals").mkdir()
            (root / "doc.md").write_text("beta\ngamma\n", encoding="utf-8")
            (root / "evals" / "contract-invariants.json").write_text(
                json.dumps(
                    {
                        "version": 1,
                        "invariants": [
                            {
                                "id": "semantics",
                                "documents": [
                                    {
                                        "path": "doc.md",
                                        "required_any": [["alpha", "beta"], ["gamma"]],
                                    }
                                ],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            self.assertEqual([], self.validator.validate_contract_consistency(root))

            (root / "doc.md").write_text("beta\n", encoding="utf-8")
            errors = self.validator.validate_contract_consistency(root)
            self.assertTrue(any("semantics" in error and "doc.md" in error for error in errors), errors)

    def test_malformed_document_rule_does_not_suppress_valid_sibling_drift(self):
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as temp_dir:
            root = self.copy_bundle(Path(temp_dir))
            catalog = self.load_catalog(root)
            catalog["invariants"][2]["documents"][0]["path"] = 7
            (root / "evals" / "contract-invariants.json").write_text(
                json.dumps(catalog, indent=2) + "\n",
                encoding="utf-8",
            )
            flow_path = root / "core" / "flow.md"
            flow_path.write_text(
                flow_path.read_text(encoding="utf-8").replace(
                    "minimum rollback scope", "rollback scope", 1
                ),
                encoding="utf-8",
            )

            errors = self.validator.validate_contract_consistency(root)

            self.assertTrue(any("must define a non-empty string path" in error for error in errors), errors)
            self.assertTrue(
                any("minimal-rollback" in error and "core/flow.md" in error for error in errors),
                errors,
            )

    def test_invalid_or_missing_catalog_version_is_rejected(self):
        for version in (None, 2):
            with self.subTest(version=version):
                with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as temp_dir:
                    root = self.copy_bundle(Path(temp_dir))
                    catalog = self.load_catalog(root)
                    if version is None:
                        catalog.pop("version")
                    else:
                        catalog["version"] = version
                    (root / "evals" / "contract-invariants.json").write_text(
                        json.dumps(catalog, indent=2) + "\n",
                        encoding="utf-8",
                    )

                    errors = self.validator.validate_contract_consistency(root)

                    self.assertTrue(any("catalog version must be 1" in error for error in errors), errors)

    def test_missing_invariants_list_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as temp_dir:
            root = self.copy_bundle(Path(temp_dir))
            catalog = self.load_catalog(root)
            catalog.pop("invariants")
            (root / "evals" / "contract-invariants.json").write_text(
                json.dumps(catalog, indent=2) + "\n",
                encoding="utf-8",
            )

            errors = self.validator.validate_contract_consistency(root)

            self.assertTrue(any("catalog invariants must be a" in error for error in errors), errors)

    def test_empty_invariants_list_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as temp_dir:
            root = self.copy_bundle(Path(temp_dir))
            catalog = self.load_catalog(root)
            catalog["invariants"] = []
            (root / "evals" / "contract-invariants.json").write_text(
                json.dumps(catalog, indent=2) + "\n",
                encoding="utf-8",
            )

            errors = self.validator.validate_contract_consistency(root)

            self.assertTrue(any("catalog invariants must be a non-empty list" in error for error in errors), errors)

    def test_missing_catalog_path_returns_error(self):
        missing_path = BUNDLE_ROOT / "evals" / "missing-contract-invariants.json"
        errors = self.validator.validate_contract_consistency(BUNDLE_ROOT, missing_path)
        self.assertTrue(any("missing catalog:" in error for error in errors), errors)

    def test_malformed_json_catalog_returns_error(self):
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as temp_dir:
            root = self.copy_bundle(Path(temp_dir))
            catalog_path = root / "evals" / "contract-invariants.json"
            catalog_path.write_text("{\n", encoding="utf-8")

            errors = self.validator.validate_contract_consistency(root)

            self.assertTrue(any("invalid catalog json" in error for error in errors), errors)

    def test_malformed_top_level_catalog_is_reported_without_crashing(self):
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as temp_dir:
            root = self.copy_bundle(Path(temp_dir))
            (root / "evals" / "contract-invariants.json").write_text("[1, 2, 3]\n", encoding="utf-8")

            errors = self.validator.validate_contract_consistency(root)

            self.assertTrue(
                any("catalog top-level value must be an object" in error for error in errors),
                errors,
            )

    def test_mixed_case_match_still_passes(self):
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as temp_dir:
            root = self.copy_bundle(Path(temp_dir))
            flow_path = root / "core" / "flow.md"
            flow_path.write_text(
                flow_path.read_text(encoding="utf-8").replace(
                    "minimum rollback scope", "MiNiMuM RoLlBaCk ScOpE", 1
                ),
                encoding="utf-8",
            )

            self.assertEqual([], self.validator.validate_contract_consistency(root))


if __name__ == "__main__":
    unittest.main()
