import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
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


def _select_temp_parent() -> Path:
    bundle_root = BUNDLE_ROOT.resolve()
    candidates = [Path.cwd(), Path.cwd().parent, Path(Path.cwd().anchor), Path(tempfile.gettempdir())]
    checked: set[Path] = set()
    failures: list[str] = []
    for candidate in candidates:
        try:
            candidate = candidate.resolve()
        except OSError as exc:
            failures.append(f"{candidate}: {exc}")
            continue
        if (
            candidate in checked
            or candidate == bundle_root
            or candidate.is_relative_to(bundle_root)
            or bundle_root.is_relative_to(candidate)
        ):
            continue
        checked.add(candidate)
        if not candidate.is_dir() or not os.access(candidate, os.W_OK):
            failures.append(f"{candidate}: not writable")
            continue
        probe: Path | None = None
        try:
            probe = Path(tempfile.mkdtemp(prefix="behavior-evals-", dir=candidate))
            nested = probe / "nested"
            nested.mkdir()
            marker = nested / "probe.txt"
            marker.write_text("ok", encoding="utf-8")
            if marker.read_text(encoding="utf-8") != "ok":
                raise OSError("temporary-parent probe read-back mismatch")
            return candidate
        except (OSError, PermissionError) as exc:
            failures.append(f"{candidate}: {exc}")
        finally:
            if probe is not None:
                shutil.rmtree(probe, ignore_errors=False)
    raise RuntimeError("no writable temporary parent found: " + "; ".join(failures))


TEMP_ROOT = _select_temp_parent()
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import behavior_evals


class BehaviorEvalTests(unittest.TestCase):
    maxDiff = None

    def copy_evals(self, destination: Path) -> Path:
        root = destination / "bundle"
        (root / "evals").mkdir(parents=True)
        for filename in ("codex-behavior-evals.json", "claude-behavior-evals.json"):
            shutil.copy2(BUNDLE_ROOT / "evals" / filename, root / "evals" / filename)
        return root

    def load_eval_file(self, root: Path, filename: str) -> dict:
        return json.loads((root / "evals" / filename).read_text(encoding="utf-8"))

    def test_current_eval_definitions_are_valid_and_globally_unique(self):
        definitions, errors = behavior_evals.load_eval_definitions(BUNDLE_ROOT)

        self.assertEqual([], errors)
        self.assertEqual(22, len(definitions))
        self.assertEqual(set(range(1, 12)) | set(range(101, 112)), {definition["id"] for definition in definitions})
        self.assertEqual(22, len({definition["name"] for definition in definitions}))
        self.assertEqual({"codex", "claude-code"}, {definition["host"] for definition in definitions})

    def test_duplicate_eval_id_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as temp_dir:
            root = self.copy_evals(Path(temp_dir))
            claude_catalog = self.load_eval_file(root, "claude-behavior-evals.json")
            claude_catalog["evals"][0]["id"] = 1
            (root / "evals" / "claude-behavior-evals.json").write_text(
                json.dumps(claude_catalog, indent=2) + "\n",
                encoding="utf-8",
            )

            _, errors = behavior_evals.load_eval_definitions(root)

            self.assertTrue(any("duplicate behavior eval id" in error for error in errors), errors)

    def test_boolean_eval_id_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as temp_dir:
            root = self.copy_evals(Path(temp_dir))
            codex_catalog = self.load_eval_file(root, "codex-behavior-evals.json")
            codex_catalog["evals"][0]["id"] = True
            (root / "evals" / "codex-behavior-evals.json").write_text(
                json.dumps(codex_catalog, indent=2) + "\n",
                encoding="utf-8",
            )

            _, errors = behavior_evals.load_eval_definitions(root)

            self.assertIn("codex-behavior-evals.json eval[0] must have integer id", errors)

    def test_grade_response_returns_pass_for_matching_expectations(self):
        definitions, errors = behavior_evals.load_eval_definitions(BUNDLE_ROOT)
        self.assertEqual([], errors)
        eval_definition = next(
            definition for definition in definitions if definition["name"] == "codex-explicit-invocation"
        )

        result = behavior_evals.grade_response(
            eval_definition,
            "Classification: bootstrap\nstarting from Layer 0\nRequired reads: SPEC.md\nPlease read these files before implementation.",
        )

        self.assertEqual("pass", result["status"])
        self.assertEqual(1, result["eval_id"])
        self.assertEqual("codex-explicit-invocation", result["eval_name"])
        self.assertEqual("codex", result["host"])
        self.assertEqual({"passed": 3, "failed": 0, "total": 3, "pass_rate": 1.0}, result["summary"])
        self.assertEqual(3, len(result["expectations"]))
        self.assertTrue(all(expectation["passed"] for expectation in result["expectations"]))
        self.assertTrue(
            any("matched required terms" in expectation["evidence"] for expectation in result["expectations"])
        )
        self.assertEqual(
            {"eval_id", "eval_name", "host", "status", "expectations", "summary"},
            set(result),
        )

    def test_grade_response_returns_fail_for_forbidden_content(self):
        definitions, errors = behavior_evals.load_eval_definitions(BUNDLE_ROOT)
        self.assertEqual([], errors)
        eval_definition = next(
            definition for definition in definitions if definition["name"] == "codex-near-miss-local-fix"
        )

        result = behavior_evals.grade_response(
            eval_definition,
            "This is a local repair, but Classification: bootstrap and starting from Layer 0 anyway.",
        )

        self.assertEqual("fail", result["status"])
        self.assertEqual({"passed": 1, "failed": 1, "total": 2, "pass_rate": 0.5}, result["summary"])
        self.assertTrue(
            any("forbidden terms present" in expectation["evidence"] for expectation in result["expectations"]),
            result["expectations"],
        )

    def test_high_risk_complete_response_passes(self):
        definitions, errors = behavior_evals.load_eval_definitions(BUNDLE_ROOT)
        self.assertEqual([], errors)
        eval_definition = next(
            definition for definition in definitions if definition["name"] == "decision-quality-irreversible-migration"
        )

        response = """Protocol: both
Constraints: public contract and irreversible migration.
Assumptions: compatibility is preserved.
Falsifier: rollback probe fails.
Decision: proceed only with evidence.
Three threats and executable probes:
Threat 1: concurrent writer test.
Threat 2 and executable probe: rollback restoration test.
Threat 3 and executable probe: mixed-version client test.
Residual risk: operational timing remains.
Result: stay"""

        result = behavior_evals.grade_response(eval_definition, response)

        self.assertEqual("pass", result["status"])

    def test_missing_probe_response_fails_even_when_threat_is_identified(self):
        definitions, errors = behavior_evals.load_eval_definitions(BUNDLE_ROOT)
        self.assertEqual([], errors)
        eval_definition = next(
            definition for definition in definitions if definition["name"] == "decision-quality-missing-probe"
        )

        result = behavior_evals.grade_response(
            eval_definition,
            "Result: pass; threat identified but probe not run.",
        )

        self.assertEqual("fail", result["status"])

    def test_three_threats_without_executable_probes_fails(self):
        definitions, errors = behavior_evals.load_eval_definitions(BUNDLE_ROOT)
        self.assertEqual([], errors)
        eval_definition = next(
            definition for definition in definitions if definition["id"] == 5
        )

        result = behavior_evals.grade_response(
            eval_definition,
            "Protocol: both; three threats identified; Residual risk: known; Result: stay.",
        )

        self.assertEqual("fail", result["status"])

    def test_three_threats_with_unrun_probes_fails(self):
        definitions, errors = behavior_evals.load_eval_definitions(BUNDLE_ROOT)
        self.assertEqual([], errors)
        eval_definition = next(definition for definition in definitions if definition["id"] == 5)
        result = behavior_evals.grade_response(
            eval_definition,
            "Protocol: both; three threats; executable probes were not run; Residual risk: known; Result: pass.",
        )
        self.assertEqual("fail", result["status"])

    def test_mechanical_skip_with_protocol_terms_fails(self):
        definitions, errors = behavior_evals.load_eval_definitions(BUNDLE_ROOT)
        self.assertEqual([], errors)
        eval_definition = next(
            definition for definition in definitions if definition["id"] == 106
        )

        result = behavior_evals.grade_response(
            eval_definition,
            "Protocol: skipped; first-principles and adversarial review still ran.",
        )

        self.assertEqual("fail", result["status"])

    def test_goal_eval_prompts_load_separately_without_replacement_markers(self):
        goal_catalog = json.loads(
            (Path.home() / ".codex" / "skills" / "goal" / "evals" / "behavior-evals.json").read_text(encoding="utf-8")
        )
        self.assertIsInstance(goal_catalog.get("evals"), list)
        self.assertTrue(goal_catalog["evals"])
        for definition in goal_catalog["evals"]:
            self.assertNotIn("????", definition.get("prompt", ""))

    def test_grade_response_does_not_treat_layer_number_as_substring_match(self):
        eval_definition = {
            "id": 999,
            "name": "layer-phrase-match",
            "host": "codex",
            "expectations": [{"text": "requires layer 5", "all": ["Layer 5"], "any": [], "none": []}],
        }

        result = behavior_evals.grade_response(eval_definition, "Classification: maintenance starting from Layer 50.")

        self.assertEqual("fail", result["status"])
        self.assertEqual(["missing required terms: ['Layer 5']"], [item["evidence"] for item in result["expectations"]])

    def test_grade_response_does_not_treat_mode_label_as_substring_match(self):
        eval_definition = {
            "id": 1000,
            "name": "mode-phrase-match",
            "host": "codex",
            "expectations": [{"text": "requires bootstrap", "all": ["bootstrap"], "any": [], "none": []}],
        }

        result = behavior_evals.grade_response(eval_definition, "This is not bootstrap; keep the local fix narrow.")

        self.assertEqual("fail", result["status"])
        self.assertEqual(["missing required terms: ['bootstrap']"], [item["evidence"] for item in result["expectations"]])

    def test_grade_response_ignores_chinese_negated_ascii_terms(self):
        eval_definition = {
            "id": 1001,
            "name": "chinese-negated-mode-phrases",
            "host": "codex",
            "expectations": [
                {"text": "requires bootstrap and layer 0", "all": ["bootstrap", "Layer 0"], "any": [], "none": []}
            ],
        }

        result = behavior_evals.grade_response(
            eval_definition,
            "不是 bootstrap，也不是 Layer 0；继续保持局部修复。",
        )

        self.assertEqual("fail", result["status"])
        self.assertEqual(["missing required terms: ['bootstrap', 'Layer 0']"], [item["evidence"] for item in result["expectations"]])

    def test_grade_response_ignores_chinese_negated_cjk_terms(self):
        eval_definition = {
            "id": 1002,
            "name": "chinese-negated-first-principles",
            "host": "codex",
            "expectations": [
                {"text": "requires first-principles review", "all": [], "any": ["第一性原理"], "none": []}
            ],
        }

        result = behavior_evals.grade_response(
            eval_definition,
            "不需要第一性原理。Constraints: preserve the public contract.",
        )

        self.assertEqual("fail", result["status"])
        self.assertEqual(["matched none of: ['第一性原理']"], [item["evidence"] for item in result["expectations"]])

    def test_grade_response_keeps_later_positive_cjk_substring(self):
        eval_definition = {
            "id": 1003,
            "name": "later-positive-first-principles",
            "host": "codex",
            "expectations": [
                {"text": "requires first-principles review", "all": [], "any": ["第一性原理"], "none": []}
            ],
        }

        result = behavior_evals.grade_response(
            eval_definition,
            "not 第一性原理 but 第一性原理 is checked",
        )

        self.assertEqual("pass", result["status"])

    def test_grade_response_ignores_bare_chinese_negation_before_cjk_term(self):
        eval_definition = {
            "id": 1004,
            "name": "bare-chinese-negation",
            "host": "codex",
            "expectations": [
                {"text": "requires first-principles review", "all": [], "any": ["第一性原理"], "none": []}
            ],
        }

        result = behavior_evals.grade_response(eval_definition, "不第一性原理")

        self.assertEqual("fail", result["status"])

    def test_grade_response_ignores_chinese_should_not_before_cjk_term(self):
        eval_definition = {
            "id": 1005,
            "name": "chinese-should-not-negation",
            "host": "codex",
            "expectations": [
                {"text": "requires first-principles review", "all": [], "any": ["第一性原理"], "none": []}
            ],
        }

        result = behavior_evals.grade_response(eval_definition, "不应第一性原理")

        self.assertEqual("fail", result["status"])

    def test_grade_response_ignores_chinese_negation_with_intervening_verb(self):
        eval_definition = {
            "id": 1006,
            "name": "chinese-verb-negation",
            "host": "codex",
            "expectations": [
                {"text": "requires first-principles review", "all": [], "any": ["第一性原理"], "none": []}
            ],
        }

        result = behavior_evals.grade_response(eval_definition, "不要运行第一性原理")

        self.assertEqual("fail", result["status"])

    def test_grade_response_keeps_positive_cjk_term_after_chinese_negated_occurrence(self):
        eval_definition = {
            "id": 1007,
            "name": "mixed-chinese-negation",
            "host": "codex",
            "expectations": [
                {"text": "requires first-principles review", "all": [], "any": ["第一性原理"], "none": []}
            ],
        }

        result = behavior_evals.grade_response(
            eval_definition,
            "不要运行第一性原理，但后来运行第一性原理。",
        )

        self.assertEqual("pass", result["status"])

    def test_missing_response_is_not_run(self):
        definitions, errors = behavior_evals.load_eval_definitions(BUNDLE_ROOT)
        self.assertEqual([], errors)
        eval_definition = next(definition for definition in definitions if definition["id"] == 101)

        result = behavior_evals.grade_response(eval_definition, None)

        self.assertEqual("not-run", result["status"])
        self.assertEqual({"passed": 0, "failed": 0, "total": 0, "pass_rate": None}, result["summary"])
        self.assertEqual([], result["expectations"])

    def test_load_recorded_responses_returns_empty_result_for_none_manifest(self):
        self.assertEqual(({}, []), behavior_evals.load_recorded_responses(None))

    def test_load_recorded_responses_resolves_paths(self):
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as temp_dir:
            root = Path(temp_dir)
            evidence_dir = root / "fixtures"
            evidence_dir.mkdir()
            response_path = evidence_dir / "response.md"
            response_path.write_text("Classification: bootstrap", encoding="utf-8")
            manifest_dir = root / "evals"
            manifest_dir.mkdir()
            manifest_path = manifest_dir / "recorded-responses.example.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "responses": [
                            {
                                "eval_id": 1,
                                "response_path": "../fixtures/response.md",
                                "model": "example-model",
                                "timestamp": "2000-01-01T00:00:00Z",
                            }
                        ]
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            responses, errors = behavior_evals.load_recorded_responses(manifest_path)

            self.assertEqual([], errors)
            self.assertEqual(response_path.resolve(), responses[1]["resolved_path"])

    def test_load_recorded_responses_rejects_manifest_without_responses_list(self):
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as temp_dir:
            root = Path(temp_dir)
            manifest_path = root / "recorded-responses.example.json"
            manifest_path.write_text(json.dumps({"items": []}, indent=2) + "\n", encoding="utf-8")

            responses, errors = behavior_evals.load_recorded_responses(manifest_path)

            self.assertEqual({}, responses)
            self.assertEqual(["recorded response manifest must contain a responses list"], errors)

    def test_load_recorded_responses_rejects_manifest_entry_without_response_path(self):
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as temp_dir:
            root = Path(temp_dir)
            manifest_path = root / "recorded-responses.example.json"
            manifest_path.write_text(
                json.dumps({"responses": [{"eval_id": 1}]}, indent=2) + "\n",
                encoding="utf-8",
            )

            responses, errors = behavior_evals.load_recorded_responses(manifest_path)

            self.assertEqual({}, responses)
            self.assertIn("recorded response 1 must have response_path", errors)

    def test_load_recorded_responses_rejects_duplicate_eval_id(self):
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as temp_dir:
            root = Path(temp_dir)
            response_path = root / "response.md"
            response_path.write_text("ok", encoding="utf-8")
            manifest_path = root / "recorded-responses.example.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "responses": [
                            {"eval_id": 1, "response_path": "response.md"},
                            {"eval_id": 1, "response_path": "response.md"},
                        ]
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            responses, errors = behavior_evals.load_recorded_responses(manifest_path)

            self.assertEqual({1}, set(responses))
            self.assertIn("duplicate recorded response eval_id: 1", errors)


if __name__ == "__main__":
    unittest.main()
