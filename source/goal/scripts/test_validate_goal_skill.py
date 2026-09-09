#!/usr/bin/env python3
from __future__ import annotations

import ast
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch


SKILL_ROOT = Path(__file__).resolve().parents[1]
GLOBAL_AGENTS = (
    SKILL_ROOT.parent / "deployment" / "AGENTS.md"
    if (SKILL_ROOT.parent / "deployment" / "AGENTS.md").exists()
    else Path.home() / ".codex" / "AGENTS.md"
)
ALLOWED_TOP_LEVEL = {"SKILL.md", "references", "scripts", "evals"}
VALIDATOR = SKILL_ROOT / "scripts" / "validate_goal_skill.py"
DEPLOYMENT_AGENTS = SKILL_ROOT.parent / "deployment" / "AGENTS.md"
SCRATCH_ROOT = SKILL_ROOT.parent / ".test-work"


def load_validator():
    spec = importlib.util.spec_from_file_location("validate_goal_skill", VALIDATOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@contextmanager
def copied_skill():
    SCRATCH_ROOT.mkdir(exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(dir=SCRATCH_ROOT) as directory:
            root = Path(directory) / "goal"
            shutil.copytree(
                SKILL_ROOT,
                root,
                ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", "*.pyc"),
            )
            yield root
    finally:
        try:
            SCRATCH_ROOT.rmdir()
        except OSError:
            pass


class GoalSkillContractTests(unittest.TestCase):
    def run_validator_cli(self, root: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-B", str(VALIDATOR), str(root)],
            capture_output=True,
            text=True,
            timeout=30,
        )

    def test_validator_exposes_all_protocol_validation_helpers(self) -> None:
        module = load_validator()
        self.assertTrue(hasattr(module, "load_contract"))
        self.assertTrue(hasattr(module, "required_fields"))
        self.assertTrue(hasattr(module, "validate_contract"))

    def test_protocol_mutations_are_rejected_with_stable_errors(self) -> None:
        mutations = (
            (
                "unknown transition",
                lambda payload: payload["transitions"]["intake"].append("unknown"),
                "transition from intake has an unknown target",
            ),
            (
                "duplicate record field",
                lambda payload: payload["records"]["classification_reply"].append("Goal"),
                "record classification_reply fields must be non-empty unique strings",
            ),
            (
                "missing owner",
                lambda payload: payload["owners"].pop("closure"),
                "owners must match required assignments",
            ),
            (
                "missing error code",
                lambda payload: payload["error_codes"].remove("CAPABILITY_DISABLED"),
                "error_codes must match Goal Protocol v2",
            ),
            (
                "wrong capability version",
                lambda payload: payload["capabilities"]["harness"].update(required_major=2),
                "capability harness required_major mismatch",
            ),
        )

        for name, mutate, expected in mutations:
            with self.subTest(name=name):
                with copied_skill() as root:
                    protocol_path = root / "references" / "protocol.json"
                    payload = json.loads(protocol_path.read_text(encoding="utf-8"))
                    mutate(payload)
                    protocol_path.write_text(
                        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8",
                    )
                    completed = self.run_validator_cli(root)

                output = completed.stdout + completed.stderr
                self.assertEqual(1, completed.returncode, output)
                self.assertIn(f"invalid Goal Protocol v2: {expected}", output)

    def test_output_contract_rejects_missing_protocol_field(self) -> None:
        with copied_skill() as root:
            target = root / "references" / "output-contract.md"
            target.write_text(
                target.read_text(encoding="utf-8").replace(
                    "Goal: [one-sentence summary]\n", ""
                ),
                encoding="utf-8",
            )
            completed = self.run_validator_cli(root)

        output = completed.stdout + completed.stderr
        self.assertEqual(1, completed.returncode, output)
        self.assertIn(
            "output-contract.md classification_reply missing protocol fields: Goal",
            output,
        )

    def test_output_contract_rejects_protocol_record_without_section_mapping(self) -> None:
        with copied_skill() as root:
            protocol_path = root / "references" / "protocol.json"
            payload = json.loads(protocol_path.read_text(encoding="utf-8"))
            payload["records"]["audit_record"] = ["Audit"]
            protocol_path.write_text(
                json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            completed = self.run_validator_cli(root)

        output = completed.stdout + completed.stderr
        self.assertEqual(1, completed.returncode, output)
        self.assertIn(
            "output-contract.md missing section mapping for record: audit_record",
            output,
        )

    def test_validator_rejects_missing_closed_classification_field_rule(self) -> None:
        with copied_skill() as root:
            target = root / "references" / "output-contract.md"
            text = target.read_text(encoding="utf-8").replace(
                "`Host mode` must not replace `Confirmation:` in this reply.\n",
                "",
            )
            target.write_text(text, encoding="utf-8")
            completed = self.run_validator_cli(root)

        output = completed.stdout + completed.stderr
        self.assertEqual(1, completed.returncode, output)
        self.assertIn(
            "output-contract.md missing closed classification field rule",
            output,
        )

    def test_validator_rejects_missing_dual_lookup_evidence_template(self) -> None:
        with copied_skill() as root:
            target = root / "references" / "output-contract.md"
            text = target.read_text(encoding="utf-8").replace(
                "Evidence: `[exact lookup command 1]` returned `[exact result 1]`; `[exact lookup command 2]` returned `[exact result 2]`.\n",
                "",
            )
            target.write_text(text, encoding="utf-8")
            completed = self.run_validator_cli(root)

        output = completed.stdout + completed.stderr
        self.assertEqual(1, completed.returncode, output)
        self.assertIn(
            "output-contract.md missing dual lookup Evidence template",
            output,
        )

    def test_validator_rejects_missing_stale_verification_reply_template(self) -> None:
        with copied_skill() as root:
            target = root / "references" / "output-contract.md"
            text = target.read_text(encoding="utf-8").replace(
                "Prior receipt: stale (`STALE_VERIFICATION`); `Mutation Seq` alone does not prove current bytes.\n",
                "",
            )
            target.write_text(text, encoding="utf-8")
            completed = self.run_validator_cli(root)

        output = completed.stdout + completed.stderr
        self.assertEqual(1, completed.returncode, output)
        self.assertIn(
            "output-contract.md missing stale verification reply template",
            output,
        )

    def test_validator_rejects_missing_mismatch_evidence_template(self) -> None:
        with copied_skill() as root:
            target = root / "references" / "capability-discovery.md"
            text = target.read_text(encoding="utf-8").replace(
                "Evidence: The configured Guard `capabilities` command reported protocol major [configured major]; the documented legacy path `$env:USERPROFILE\\plugins\\goal-enforcement\\scripts\\goal_guard.py capabilities` reported protocol major [legacy major]; Goal Protocol v2 requires major 1.\n",
                "",
            )
            target.write_text(text, encoding="utf-8")
            completed = self.run_validator_cli(root)

        output = completed.stdout + completed.stderr
        self.assertEqual(1, completed.returncode, output)
        self.assertIn(
            "capability-discovery.md missing mismatch Evidence template",
            output,
        )

    def test_cli_defaults_to_own_skill_root_without_positionals(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-B", str(VALIDATOR)],
            cwd=SKILL_ROOT.parent,
            capture_output=True,
            text=True,
            timeout=30,
        )

        self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
        self.assertIn("OK: goal skill structure present", completed.stdout)

    def test_cli_supports_explicit_root_and_global_agents_forms(self) -> None:
        global_agents = SKILL_ROOT.parent / "deployment" / "AGENTS.md"
        commands = (
            [str(SKILL_ROOT)],
            ["--global-agents", str(global_agents)],
            [str(SKILL_ROOT), "--global-agents", str(global_agents)],
        )
        for arguments in commands:
            with self.subTest(arguments=arguments):
                completed = subprocess.run(
                    [sys.executable, "-B", str(VALIDATOR), *arguments],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                self.assertEqual(
                    0, completed.returncode, completed.stdout + completed.stderr
                )

    def test_cli_rejects_all_other_argument_shapes(self) -> None:
        invalid_commands = (
            ["--global-agents"],
            [str(SKILL_ROOT), "--global-agents"],
            [str(SKILL_ROOT), "--wrong", str(GLOBAL_AGENTS)],
            [str(SKILL_ROOT), "--global-agents", str(GLOBAL_AGENTS), "extra"],
        )
        for arguments in invalid_commands:
            with self.subTest(arguments=arguments):
                completed = subprocess.run(
                    [sys.executable, "-B", str(VALIDATOR), *arguments],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                self.assertEqual(1, completed.returncode)
                self.assertIn("Usage:", completed.stdout)

    def test_package_top_level_is_clean(self) -> None:
        actual = {path.name for path in SKILL_ROOT.iterdir()}
        self.assertEqual(
            ALLOWED_TOP_LEVEL,
            actual,
            f"unexpected package entries: {sorted(actual - ALLOWED_TOP_LEVEL)}",
        )

    def test_skill_declares_deferred_harness_loading(self) -> None:
        text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8").lower()
        required = {
            "load `harness-engineering` after classification and required confirmation",
            "core/flow.md",
            "adapters/codex/host-map.md",
            "core/checklists.md",
            "core/exit-and-reentry.md",
            "dependency blocker",
        }
        missing = sorted(token for token in required if token not in text)
        self.assertEqual([], missing, f"missing Harness contract markers: {missing}")

    def test_skill_has_one_conditional_decision_quality_harness_route(self) -> None:
        text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        marker = "## Conditional Decision-Quality Routing"
        self.assertEqual(1, text.count(marker))
        paragraph = text[text.index(marker):text.index("## Five-Stage Runtime")]
        for token in (
            "After classification and confirmation, let Harness perform the risk check",
            "high-cost", "ambiguous", "contradictory", "irreversible",
            "topology/data-flow/security/API/migration", "pattern-copy", "upstream-assumption",
            "harness-engineering/references/decision-quality.md",
            "compact result", "existing Harness layer gate",
            "Mechanical work with an exact plan and no new contradiction skips the protocols",
            "/goal", "does not reproduce", "first-principles", "adversarial",
            "second state machine", "change goal-state.json", "sole owner",
            "gate", "rollback", "scope_result", "operation_state",
        ):
            self.assertIn(token.lower(), paragraph.lower())
        self.assertNotIn("GSD receipt", paragraph)
        self.assertNotIn("GSD uses the Harness fallback", paragraph)
        progressive = text[
            text.index("## Progressive References"):
            text.index("## Progress Persistence")
        ]
        self.assertIn("gsd-adapter.md", progressive)
        self.assertIn("approved Layer 6 proposal", progressive)
        self.assertLess(text.index("## Core Rule"), text.index(marker))
        self.assertLess(text.index(marker), text.index("## Five-Stage Runtime"))

    def test_skill_route_does_not_embed_harness_protocol(self) -> None:
        text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        paragraph = text[text.index("## Conditional Decision-Quality Routing"):text.index("## Five-Stage Runtime")]
        self.assertNotIn("Mandatory Enforcement Protocol", paragraph)
        self.assertNotIn("goal-state.lock", paragraph)
        self.assertNotIn("goal-state.candidate.json", paragraph)

    def test_decision_quality_prompts_are_repaired(self) -> None:
        payload = json.loads((SKILL_ROOT / "evals" / "behavior-evals.json").read_text(encoding="utf-8"))
        by_id = {item["id"]: item for item in payload["evals"]}
        for eval_id in ("no-visual-companion-during-layer0", "bootstrap-layer0-first-governed-mutation-state-init"):
            self.assertNotIn("????", by_id[eval_id]["prompt"], eval_id)

    def test_decision_quality_eval_ids_are_exact(self) -> None:
        payload = json.loads((SKILL_ROOT / "evals" / "behavior-evals.json").read_text(encoding="utf-8"))
        expected = {
            "decision-quality-high-risk-routing",
            "decision-quality-mechanical-skip",
            "decision-quality-meta-no-project-execution",
        }
        self.assertTrue(expected <= {item.get("id") for item in payload["evals"]})

    def test_guard_integration_is_portable_and_bounded(self) -> None:
        integration_path = SKILL_ROOT / "scripts" / "test_goal_guard_integration.py"
        for path in (
            SKILL_ROOT / "scripts" / "validate_goal_skill.py",
            Path(__file__),
            integration_path,
        ):
            self.assertNotEqual(path.read_bytes()[:3], b"\xef\xbb\xbf", f"BOM remains: {path}")
        unit_source = Path(__file__).read_text(encoding="utf-8-sig")
        old_test_name = (
            "test_goal_guard_accepts_documented_bootstrap_"
            "layer0_state_sequence"
        )
        unit_function_names = {
            node.name
            for node in ast.walk(ast.parse(unit_source))
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        self.assertNotIn(
            old_test_name,
            unit_function_names,
        )

        source = integration_path.read_text(encoding="utf-8-sig")
        self.assertNotIn('scratch_root = Path(r"C:\\tmp")', source)
        self.assertIn("GOAL_RUN_GUARD_INTEGRATION", source)
        tree = ast.parse(source)
        constants = {}
        for node in tree.body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                target = node.targets[0]
                if isinstance(target, ast.Name):
                    try:
                        constants[target.id] = ast.literal_eval(node.value)
                    except (ValueError, TypeError):
                        pass
        self.assertEqual(45.0, constants.get("INTEGRATION_DEADLINE_SECONDS"))
        self.assertEqual(10.0, constants.get("MAX_STAGE_TIMEOUT_SECONDS"))
        deadline_initializations = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name)
                and target.id == "_integration_deadline"
                for target in node.targets
            )
            and any(
                isinstance(child, ast.Call)
                and isinstance(child.func, ast.Attribute)
                and isinstance(child.func.value, ast.Name)
                and child.func.value.id == "time"
                and child.func.attr == "monotonic"
                for child in ast.walk(node.value)
            )
        ]
        self.assertEqual(
            1,
            len(deadline_initializations),
            "the integration must initialize one shared monotonic deadline",
        )

        helpers = [
            node
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == "run_stage"
        ]
        self.assertEqual(1, len(helpers), "run_stage must be a single module-level helper")
        helper = helpers[0]
        self.assertEqual(
            ["name", "argv", "input_text"],
            [argument.arg for argument in helper.args.args],
        )
        self.assertIsInstance(helper.args.defaults[-1], ast.Constant)
        self.assertIsNone(helper.args.defaults[-1].value)
        helper_calls = [node for node in ast.walk(helper) if isinstance(node, ast.Call)]
        self.assertTrue(
            any(isinstance(call.func, ast.Name) and call.func.id == "min" for call in helper_calls),
            "run_stage must cap each subprocess timeout with min(...)",
        )
        self.assertTrue(
            any(
                isinstance(call.func, ast.Attribute)
                and call.func.attr == "run"
                and any(keyword.arg == "timeout" for keyword in call.keywords)
                for call in helper_calls
            ),
            "run_stage must pass its computed timeout to subprocess.run",
        )

        def load_integration(name: str, opt_in: str):
            spec = importlib.util.spec_from_file_location(name, integration_path)
            module = importlib.util.module_from_spec(spec)
            with patch.dict(os.environ, {"GOAL_RUN_GUARD_INTEGRATION": opt_in}):
                spec.loader.exec_module(module)
            return module

        module = load_integration("test_goal_guard_integration_disabled", "0")
        self.assertFalse(module.INTEGRATION_ENABLED)
        enabled_module = load_integration("test_goal_guard_integration_enabled", "1")
        self.assertTrue(enabled_module.INTEGRATION_ENABLED)

        completed = subprocess.CompletedProcess(["guard"], 0, "ok", "")
        module._integration_deadline = 100.0
        with (
            patch.object(module.time, "monotonic", return_value=80.0),
            patch.object(module.subprocess, "run", return_value=completed) as runner,
        ):
            self.assertIs(completed, module.run_stage("audit", ["guard", "audit"]))
        self.assertEqual(10.0, runner.call_args.kwargs["timeout"])

        module._integration_deadline = 100.0
        with (
            patch.object(module.time, "monotonic", return_value=94.0),
            patch.object(module.subprocess, "run", return_value=completed) as runner,
        ):
            self.assertIs(completed, module.run_stage("audit", ["guard", "audit"]))
        self.assertEqual(6.0, runner.call_args.kwargs["timeout"])

        module._integration_deadline = 100.0
        expired = subprocess.TimeoutExpired(["guard", "audit"], timeout=6.0)
        with (
            patch.object(module.time, "monotonic", return_value=94.0),
            patch.object(module.subprocess, "run", side_effect=expired),
            self.assertRaisesRegex(AssertionError, r"^stage=audit exceeded 6\.000s$"),
        ):
            module.run_stage("audit", ["guard", "audit"])

        module._integration_deadline = 100.0
        with (
            patch.object(module.time, "monotonic", return_value=101.0),
            self.assertRaisesRegex(
                AssertionError,
                r"^stage=write-state exceeded 45\.000s$",
            ),
        ):
            module.run_stage("write-state", ["guard", "write-state"])

    def test_trigger_queries_cover_meta_near_misses(self) -> None:
        payload = json.loads(
            (SKILL_ROOT / "evals" / "trigger-queries.json").read_text(encoding="utf-8")
        )
        by_id = {item.get("id"): item for item in payload}
        negative_ids = {
            item.get("id")
            for item in payload
            if item.get("should_trigger") is False
        }
        required = {
            "meta-skill-review",
            "meta-quoted-command",
            "meta-path-inspection",
        }
        self.assertTrue(required <= negative_ids, f"missing trigger IDs: {sorted(required - negative_ids)}")
        meta_review = by_id["meta-skill-review"]["query"].lower()
        self.assertIn("/goal skill", meta_review)
        self.assertIn("评审", meta_review)
        self.assertIn("不要进入项目", meta_review)
        quoted = by_id["meta-quoted-command"]["query"].lower()
        self.assertIn("readme", quoted)
        self.assertIn("`/goal build the service`", quoted)
        self.assertIn("不要真的执行", quoted)
        path_inspection = by_id["meta-path-inspection"]["query"].lower()
        self.assertIn(r"c:\users\14156\.codex\skills\goal\skill.md", path_inspection)
        self.assertIn("文件检查", path_inspection)
        self.assertIn("不是启动项目", path_inspection)

    def test_goal_evals_have_stable_unique_ids(self) -> None:
        trigger_payload = json.loads(
            (SKILL_ROOT / "evals" / "trigger-queries.json").read_text(encoding="utf-8")
        )
        behavior_payload = json.loads(
            (SKILL_ROOT / "evals" / "behavior-evals.json").read_text(encoding="utf-8")
        )["evals"]
        for source, items in (
            ("trigger", trigger_payload),
            ("behavior", behavior_payload),
        ):
            ids = [item.get("id") for item in items]
            self.assertTrue(
                all(isinstance(eval_id, str) and eval_id.strip() for eval_id in ids),
                f"{source} eval entries must all have stable non-empty ids: {ids}",
            )
            self.assertEqual(len(ids), len(set(ids)), f"duplicate {source} eval ids: {ids}")

    def test_protocol_v2_catalog_preserves_ids_and_adds_capability_cases(self) -> None:
        triggers = json.loads(
            (SKILL_ROOT / "evals" / "trigger-queries.json").read_text(encoding="utf-8")
        )
        behaviors = json.loads(
            (SKILL_ROOT / "evals" / "behavior-evals.json").read_text(encoding="utf-8")
        )["evals"]
        trigger_ids = {item["id"] for item in triggers}
        behavior_ids = {item["id"] for item in behaviors}

        original_trigger_ids = {
            "bare-goal-intake",
            "project-bootstrap-inspection-platform",
            "project-maintenance-monolith-split",
            "project-natural-two-week-cross-layer",
            "project-permission-system-rebuild",
            "project-runtime-stack-migration",
            "project-e2e-major-feature-flow",
            "local-null-guard",
            "local-sql-diagnosis",
            "local-login-style-edit",
            "local-pytest-diagnosis",
            "local-interface-explanation",
            "local-readme-polish",
            "explicit-goal-local-redirect",
            "meta-skill-review",
            "meta-quoted-command",
            "meta-path-inspection",
        }
        original_behavior_ids = {
            "goal-intake-no-objective",
            "bootstrap-intake",
            "maintenance-major-flow",
            "near-miss-local-fix",
            "cold-path-classification-only",
            "structured-closure",
            "harness-deferred-during-intake",
            "harness-required-before-execution",
            "harness-dependency-missing",
            "no-visual-companion-during-layer0",
            "bootstrap-layer0-first-governed-mutation-state-init",
            "decision-quality-high-risk-routing",
            "decision-quality-mechanical-skip",
            "decision-quality-meta-no-project-execution",
            "explicit-goal-local-redirect",
            "untrusted-continuation",
            "ambiguous-provisional-classification",
            "external-workflow-no-second-owner",
            "verification-stale-after-edit",
            "verification-untracked-or-generated-change",
        }
        self.assertTrue(original_trigger_ids <= trigger_ids)
        self.assertTrue(original_behavior_ids <= behavior_ids)
        self.assertEqual(
            {"multi-file-mechanical-rename", "meta-gsd-discussion"},
            trigger_ids - original_trigger_ids,
        )
        self.assertEqual(
            {
                "guard-capability-version-match",
                "guard-capability-version-mismatch",
                "deferred-host-discovery",
                "delivery-entry-missing-feature",
                "delivery-legacy-no-feature",
                "delivery-entry-feature-supported",
            },
            behavior_ids - original_behavior_ids,
        )

    def test_protocol_v2_catalog_semantics_are_explicit(self) -> None:
        triggers = {
            item["id"]: item
            for item in json.loads(
                (SKILL_ROOT / "evals" / "trigger-queries.json").read_text(
                    encoding="utf-8"
                )
            )
        }
        behaviors = {
            item["id"]: item
            for item in json.loads(
                (SKILL_ROOT / "evals" / "behavior-evals.json").read_text(
                    encoding="utf-8"
                )
            )["evals"]
        }

        for eval_id in ("bootstrap-intake", "maintenance-major-flow"):
            expected = behaviors[eval_id]["expected_output"].lower()
            self.assertIn("confirmation", expected)
            self.assertNotIn("host mode", expected)

        harness_prompt = behaviors["harness-dependency-missing"]["prompt"].lower()
        for fact in (
            "get-item",
            r"c:\users\14156\.codex\skills\harness-engineering\skill.md",
            "harness-engineering\\references\\runtime-stages.md",
            "pathnotfound",
            "supplied evidence",
        ):
            self.assertIn(fact, harness_prompt)

        for eval_id in ("multi-file-mechanical-rename", "meta-gsd-discussion"):
            self.assertIs(triggers[eval_id]["should_trigger"], False)

        matched = behaviors["guard-capability-version-match"]["expected_output"].lower()
        for token in (
            "capabilities",
            "goal-guard",
            "protocol major 1",
            "state schema 1",
            "required command",
            "audit-only-windows",
            "protocol.py",
            "continue the same operation",
            "do not use the legacy",
        ):
            self.assertIn(token, matched)

        mismatch = behaviors[
            "guard-capability-version-mismatch"
        ]["expected_output"].lower()
        for token in (
            "protocol_version_mismatch",
            "dependency",
            "evidence",
            "impact",
            "next action",
            "do not execute the required mutation",
        ):
            self.assertIn(token, mismatch)

        deferred = behaviors["deferred-host-discovery"]["expected_output"].lower()
        for token in (
            "classification-only",
            "goal",
            "classification",
            "rationale",
            "confirmation",
            "next action",
            "do not run capabilities",
            "host discovery",
            "guard",
        ):
            self.assertIn(token, deferred)
        self.assertNotIn("host mode", deferred)

    def test_maintenance_major_flow_uses_semantically_equivalent_adversarial_prompt(self) -> None:
        behaviors = {
            item["id"]: item
            for item in json.loads(
                (SKILL_ROOT / "evals" / "behavior-evals.json").read_text(
                    encoding="utf-8"
                )
            )["evals"]
        }
        case = behaviors["maintenance-major-flow"]

        self.assertEqual(
            "现有仓储系统需要新增退货申请、风控复核和库存回补的完整流程，涉及数据库表、服务接口和管理后台。请按项目方式继续做到完成。",
            case["prompt"],
        )
        self.assertEqual(
            "Automatically trigger for the natural-language project request, "
            "classify as maintenance, and begin with the exact fields Goal, "
            "Classification, Rationale, Confirmation, and Next action before any "
            "optional explanation.",
            case["expected_output"],
        )
        self.assertNotIn("CRM", case["prompt"])

    def test_output_contract_carries_strict_runtime_evidence_boundaries(self) -> None:
        text = (
            SKILL_ROOT / "references" / "output-contract.md"
        ).read_text(encoding="utf-8").lower()
        classification = re.search(
            r"classification reference boundary(?P<body>.*?)(?=\n## |\Z)",
            text,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(classification)
        classification_body = classification.group("body")
        for deferred in (
            "capability-discovery.md",
            "host-modes.md",
            "scripts/protocol.py",
        ):
            self.assertRegex(
                classification_body,
                rf"(?:do not read|defer)[^.\n]*`?{re.escape(deferred)}`?",
            )

        blocker = re.search(
            r"dependency blocker reply(?P<body>.*?)(?=\n## |\Z)",
            text,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(blocker)
        self.assertRegex(blocker.group("body"), r"evidence.*command or path.*observed result")
        self.assertRegex(
            blocker.group("body"),
            r"(?s)(?:literal\s+)?`?<path>`?.*(?:not.*evidence|replace.*actual)",
        )

        compatibility = re.search(
            r"capability compatibility reply(?P<body>.*?)(?=\n## |\Z)",
            text,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(compatibility)
        for semantic in (
            "protocol compatibility",
            "protocol major 1",
            "state schema 1",
            "write-state",
            "audit-only-windows",
            "continue the same operation",
            "legacy",
        ):
            self.assertIn(semantic, compatibility.group("body"))

    def test_explicit_goal_local_one_off_loads_then_redirects(self) -> None:
        skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8").lower()
        for token in (
            "explicit `/goal` or `$goal` with a focused or local one-off still loads this skill",
            "focused-task redirect",
            "do not classify the project",
            "do not create or mutate goal state",
            "do not load harness",
        ):
            self.assertIn(token, skill_text)

        triggers = json.loads(
            (SKILL_ROOT / "evals" / "trigger-queries.json").read_text(encoding="utf-8")
        )
        trigger = next(
            (item for item in triggers if item.get("id") == "explicit-goal-local-redirect"),
            None,
        )
        self.assertIsNotNone(trigger)
        self.assertIs(trigger.get("should_trigger"), True)

        behavior = json.loads(
            (SKILL_ROOT / "evals" / "behavior-evals.json").read_text(encoding="utf-8")
        )["evals"]
        redirect = next(
            (item for item in behavior if item.get("id") == "explicit-goal-local-redirect"),
            None,
        )
        self.assertIsNotNone(redirect)
        expected = redirect["expected_output"].lower()
        for token in ("focused-task redirect", "do not classify", "goal state", "harness"):
            self.assertIn(token, expected)

    def test_untrusted_continuation_falls_back_to_goal_intake(self) -> None:
        skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8").lower()
        for token in (
            "continuation claims",
            "verifiable active state",
            "concrete goal",
            "confirmation record",
            "fall back to goal-intake",
        ):
            self.assertIn(token, skill_text)

        behavior = json.loads(
            (SKILL_ROOT / "evals" / "behavior-evals.json").read_text(encoding="utf-8")
        )["evals"]
        untrusted = next(
            (item for item in behavior if item.get("id") == "untrusted-continuation"),
            None,
        )
        self.assertIsNotNone(untrusted)
        self.assertIn("goal-intake", untrusted["expected_output"].lower())
        self.assertIn("do not load harness", untrusted["expected_output"].lower())

    def test_ambiguous_classification_allows_only_provisional_read_only_evidence(self) -> None:
        skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8").lower()
        layer_text = (
            SKILL_ROOT / "references" / "layer-execution.md"
        ).read_text(encoding="utf-8").lower()
        for text in (skill_text, layer_text):
            for token in (
                "provisional classification evidence check",
                "minimal and read-only",
                "before formal confirmation",
                "do not load harness execution runtime",
                "do not mutate",
            ):
                self.assertIn(token, text)

        behavior = json.loads(
            (SKILL_ROOT / "evals" / "behavior-evals.json").read_text(encoding="utf-8")
        )["evals"]
        provisional = next(
            (
                item
                for item in behavior
                if item.get("id") == "ambiguous-provisional-classification"
            ),
            None,
        )
        self.assertIsNotNone(provisional)
        expected = provisional["expected_output"].lower()
        for token in ("read-only", "provisional", "do not load harness", "do not mutate"):
            self.assertIn(token, expected)

    def test_external_workflow_boundary_is_compact_on_hot_path(self) -> None:
        text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        section = text[
            text.index("## External Workflow Pack Boundary"):
            text.index("## Conditional Decision-Quality Routing")
        ]
        self.assertLessEqual(len(section), 500, section)
        for token in (
            "/goal`/Harness remains the single owner",
            "do not install external workflow packs by default",
            "references/external-workflow-boundary.md",
        ):
            self.assertIn(token.lower(), section.lower())
        self.assertNotIn("all of the following", section.lower())

        behavior = json.loads(
            (SKILL_ROOT / "evals" / "behavior-evals.json").read_text(encoding="utf-8")
        )["evals"]
        external = next(
            (
                item
                for item in behavior
                if item.get("id") == "external-workflow-no-second-owner"
            ),
            None,
        )
        self.assertIsNotNone(external)
        expected = external["expected_output"].lower()
        for token in (
            "single owner",
            "no second owner",
            "do not install",
            "do not depend",
            "harness ownership",
            "capability-gap proposal",
        ):
            self.assertIn(token, expected)

    def test_external_workflow_cold_path_has_one_compact_owner_decision(self) -> None:
        text = (
            SKILL_ROOT / "references" / "external-workflow-boundary.md"
        ).read_text(encoding="utf-8").lower()
        section = re.search(
            r"controller boundary answer(?P<body>.*?)(?=\n## |\Z)",
            text,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(section)
        body = section.group("body")
        self.assertRegex(body, r"/goal.*(?:owns|owner).*(?:harness.*(?:owns|owner))")
        self.assertRegex(body, r"(?:sole|single).*workflow owners?|no second owner")
        self.assertRegex(body, r"single workflow owner|no second owner")
        self.assertRegex(
            body,
            r"(?:do not|must not).*(?:install|depend).*(?:external workflow|workflow pack)",
        )
        self.assertRegex(
            body,
            r"(?:re-evaluate|reconsider|review again).*capability[- ]gap proposal",
        )
        self.assertRegex(
            body,
            r"(?s)(?:incomplete|must explicitly).*(?:do not|must not).*(?:install|depend).*default",
        )

    def test_verification_stale_recovery_is_one_explicit_closure_prerequisite(self) -> None:
        text = (
            SKILL_ROOT / "references" / "output-contract.md"
        ).read_text(encoding="utf-8").lower()
        section = re.search(
            r"verification freshness(?P<body>.*?)(?=\n## |\Z)",
            text,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(section)
        body = section.group("body")
        self.assertRegex(
            body,
            r"(?s)stale.*(?:rerun|re-run).*(?:original\s+)?exact verification command.*after.*(?:edit|change).*immediately before closure",
        )
        self.assertRegex(body, r"(?s)fresh.*goal_guard\.py audit --workspace")
        self.assertRegex(body, r"(?s)current.*workspace fingerprint")
        self.assertRegex(
            body,
            r"(?s)audit-only-windows.*(?:advisory|does not mechanically block)",
        )
        self.assertRegex(
            body,
            r"(?s)(?:reply|response).*(?:incomplete|must explicitly).*audit-only-windows.*(?:advisory|does not mechanically block)",
        )

    def test_capability_discovery_owns_explicit_result_replies(self) -> None:
        text = (
            SKILL_ROOT / "references" / "capability-discovery.md"
        ).read_text(encoding="utf-8").lower()
        success = re.search(
            r"successful compatibility reply(?P<body>.*?)(?=\n## |\Z)",
            text,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(success)
        success_body = success.group("body")
        for semantic in (
            "configured",
            "capabilities",
            "goal-guard",
            "protocol major 1",
            "protocol compatibility",
            "schema 1",
            "required command",
            "audit-only-windows",
            "legacy",
            "blocker",
        ):
            self.assertIn(semantic, success_body)
        self.assertRegex(
            success_body,
            r"(?:continue[^.]*same operation|same operation[^.]*continue)",
        )
        self.assertRegex(success_body, r"(?s)(?:protocol compatibility|protocol checker).*(?:same operation|continues)")
        self.assertIn("```text", success_body)
        self.assertRegex(
            success_body,
            r"(?s)compatibility:.*goal-guard.*(?:protocol compatibility|protocol checker).*major 1.*schema 1.*write-state.*audit-only-windows",
        )
        self.assertRegex(
            success_body,
            r"(?s)next action:.*same operation.*legacy.*blocker",
        )

        mismatch = re.search(
            r"incompatible candidate evidence(?P<body>.*?)(?=\n## |\Z)",
            text,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(mismatch)
        self.assertRegex(
            mismatch.group("body"),
            r"(?s)each candidate.*(?:command|path|source).*observed.*(?:result|protocol major)",
        )

    def test_frontmatter_description_is_short_and_near_misses_come_first(self) -> None:
        text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        frontmatter = text.split("---", 2)[1]
        description_line = next(
            line for line in frontmatter.splitlines() if line.startswith("description:")
        )
        description = description_line.split(":", 1)[1].strip().strip('"')
        self.assertLessEqual(len(description), 500)
        self.assertTrue(description.startswith("Do not use"), description)
        near_miss_tokens = (
            "quoted",
            "path",
            "focused one-offs without an explicit command",
        )
        project_trigger_tokens = (
            "/goal",
            "$goal",
            "building a new system",
            "cross-layer",
            "按项目方式",
            "从 0 到 1",
            "端到端",
            "分阶段上线",
            "继续做到完成",
        )
        for token in near_miss_tokens + project_trigger_tokens:
            self.assertIn(token.lower(), description.lower())
        first_project_trigger = min(
            description.lower().index(token.lower()) for token in project_trigger_tokens
        )
        for token in near_miss_tokens:
            self.assertLess(
                description.lower().index(token.lower()),
                first_project_trigger,
                f"near-miss token must precede positive project triggers: {token}",
            )

    def test_continuation_evals_carry_evidence_or_expect_intake(self) -> None:
        behavior = json.loads(
            (SKILL_ROOT / "evals" / "behavior-evals.json").read_text(encoding="utf-8")
        )["evals"]
        by_id = {item["id"]: item for item in behavior}
        continuation_ids = {
            "structured-closure",
            "harness-required-before-execution",
            "harness-dependency-missing",
            "no-visual-companion-during-layer0",
            "bootstrap-layer0-first-governed-mutation-state-init",
            "decision-quality-high-risk-routing",
            "decision-quality-mechanical-skip",
            "untrusted-continuation",
            "external-workflow-no-second-owner",
        }
        self.assertTrue(continuation_ids <= set(by_id))
        for eval_id in sorted(continuation_ids):
            item = by_id[eval_id]
            prompt = item["prompt"].lower()
            expected = item["expected_output"].lower()
            evidence_backed = all(
                token in prompt
                for token in ("concrete objective", "active state", "confirmation record")
            )
            expects_intake = "goal-intake" in expected
            self.assertTrue(
                evidence_backed or expects_intake,
                f"{eval_id} claims progress without full evidence or goal-intake fallback",
            )

    def test_behavior_evals_cover_harness_handoff(self) -> None:
        payload = json.loads(
            (SKILL_ROOT / "evals" / "behavior-evals.json").read_text(encoding="utf-8")
        )
        ids = {item.get("id") for item in payload.get("evals", [])}
        required = {
            "harness-deferred-during-intake",
            "harness-required-before-execution",
            "harness-dependency-missing",
        }
        self.assertTrue(required <= ids, f"missing behavior IDs: {sorted(required - ids)}")

    def test_behavior_evals_cover_goal_intake_without_objective(self) -> None:
        payload = json.loads(
            (SKILL_ROOT / "evals" / "behavior-evals.json").read_text(encoding="utf-8")
        )
        ids = {item.get("id") for item in payload.get("evals", [])}
        self.assertIn(
            "goal-intake-no-objective",
            ids,
            "missing behavior eval for bare /goal intake",
        )

    def test_trigger_queries_cover_bare_goal_intake(self) -> None:
        payload = json.loads(
            (SKILL_ROOT / "evals" / "trigger-queries.json").read_text(encoding="utf-8")
        )
        intake_entry = next(
            (item for item in payload if item.get("id") == "bare-goal-intake"),
            None,
        )
        self.assertIsNotNone(intake_entry, "missing trigger query for bare /goal intake")
        self.assertTrue(
            intake_entry.get("should_trigger") is True,
            "bare /goal intake should still load the goal skill",
        )

    def test_skill_defines_bare_goal_intake_contract(self) -> None:
        text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8").lower()
        required = {
            "a bare `/goal` or `$goal` command without a concrete objective is goal-intake",
            "ask only for the missing project objective",
            "do not classify",
            "do not load harness",
            "do not create or mutate goal state",
        }
        missing = sorted(token for token in required if token not in text)
        self.assertEqual([], missing, f"missing goal-intake contract markers: {missing}")

    def test_output_contract_exempts_goal_intake_from_first_reply_gate(self) -> None:
        text = (SKILL_ROOT / "references" / "output-contract.md").read_text(encoding="utf-8").lower()
        required = {
            "goal-intake",
            "concrete project objective",
            "ask only for the missing project objective",
            "do not emit the classification reply",
        }
        missing = sorted(token for token in required if token not in text)
        self.assertEqual([], missing, f"missing output-contract markers: {missing}")

    def test_skill_routes_harness_via_runtime_stages(self) -> None:
        text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8").lower()
        required = {
            "harness-engineering/references/runtime-stages.md",
            "follow its load section",
            "harness-engineering/references/output-contract.md",
        }
        missing = sorted(token for token in required if token not in text)
        self.assertEqual([], missing, f"missing harness runtime-stage routing markers: {missing}")

    def test_output_contract_tracks_harness_gate_and_closure_fields(self) -> None:
        text = (SKILL_ROOT / "references" / "output-contract.md").read_text(encoding="utf-8").lower()
        required = {
            "inputs:",
            "actions:",
            "outputs:",
            "layer outcomes:",
            "pass/fail/not-run by layer",
        }
        missing = sorted(token for token in required if token not in text)
        self.assertEqual([], missing, f"missing harness-aligned output contract markers: {missing}")

    def test_skill_defers_brainstorming_and_workspace_state_until_first_harness_gate(self) -> None:
        text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8").lower()
        required = {
            "do not invoke `brainstorming`",
            "layer 0 itself owns the first design and clarification pass",
            "do not create workspace-local goal state",
            "before the first harness layer gate reply",
            "defer native codex goal state checks until after the first harness layer gate reply or progress checkpoint",
            "do not create `.codex/goal-state.lock`",
            "do not create `.codex/goal-state.candidate.json`",
            "before drafting boundary documents or other local artifacts",
        }
        missing = sorted(token for token in required if token not in text)
        self.assertEqual([], missing, f"missing runtime-drift prevention markers: {missing}")

    def test_host_modes_defer_workspace_goal_state_until_after_first_gate(self) -> None:
        text = (SKILL_ROOT / "references" / "host-modes.md").read_text(encoding="utf-8").lower()
        required = {
            "prefer native codex goal state when available",
            "persist to `.codex/goal-state.json` only after the first harness gate reply or before the first governed mutation",
            "never create candidate state or lock files as a prerequisite for simply returning the first layer 0 gate",
            "defer native codex goal state checks until after the first harness gate reply or before the first governed mutation",
            "never create `.codex/goal-state.lock` or `.codex/goal-state.candidate.json` as a prerequisite for simply returning the first layer 0 gate",
        }
        missing = sorted(token for token in required if token not in text)
        self.assertEqual([], missing, f"missing host-mode state deferral markers: {missing}")

    def test_output_contract_has_no_placeholder_decision_tokens(self) -> None:
        text = (SKILL_ROOT / "references" / "output-contract.md").read_text(encoding="utf-8")
        self.assertNotIn("[??]", text, "output-contract still contains unresolved placeholder tokens")
        self.assertIn("[决策] Verification -> [pass / fail]", text)
        self.assertIn("[决策] Dependency -> blocked", text)

    def test_global_agents_distinguishes_command_from_mention(self) -> None:
        text = GLOBAL_AGENTS.read_text(encoding="utf-8").lower()
        required = {
            "used as a command or project entry point",
            "discussion",
            "quoted",
            "skill path",
            "does not trigger",
        }
        missing = sorted(token for token in required if token not in text)
        self.assertEqual([], missing, f"missing global routing markers: {missing}")

    def test_global_agents_define_bare_goal_intake(self) -> None:
        text = GLOBAL_AGENTS.read_text(encoding="utf-8").lower()
        required = {
            "without a concrete objective",
            "goal-intake",
            "ask only for the missing project objective",
            "do not classify",
        }
        missing = sorted(token for token in required if token not in text)
        self.assertEqual([], missing, f"missing bare /goal routing markers: {missing}")

    def test_validator_keeps_minimal_hot_path_checks(self) -> None:
        module = load_validator()
        target = (SKILL_ROOT / "SKILL.md").resolve()
        original = Path.read_text
        mutations = (
            ("name: goal", "name: other", "frontmatter"),
            ("### Stage 3: Load Harness", "### Stage 3: Other", "runtime section"),
        )
        for old, new, expected in mutations:
            with self.subTest(expected=expected):
                def fake_read(path, *args, **kwargs):
                    text = original(path, *args, **kwargs)
                    return text.replace(old, new) if path.resolve() == target else text

                errors: list[str] = []
                with patch.object(Path, "read_text", autospec=True, side_effect=fake_read):
                    module.validate_skill_text(SKILL_ROOT, errors)
                self.assertTrue(any(expected in error for error in errors), errors)

    def test_skill_blocks_visual_companion_drift_during_goal_execution(self) -> None:
        text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8").lower()
        required = {
            "do not offer the visual companion",
            "do not offer mockups, diagrams, comparisons, browser visuals, or similar sidecar design aids",
            "unless the user explicitly asks for them",
            "do not invoke `brainstorming` for layer 0 or layer 1 boundary, architecture, or project-definition work",
        }
        missing = sorted(token for token in required if token not in text)
        self.assertEqual([], missing, f"missing visual-companion drift markers: {missing}")

    def test_output_contract_blocks_visual_companion_substitution(self) -> None:
        text = (SKILL_ROOT / "references" / "output-contract.md").read_text(encoding="utf-8").lower()
        required = {
            "do not replace a layer gate reply or progress checkpoint with an offer for a visual companion",
            "mockup",
            "browser preview",
        }
        missing = sorted(token for token in required if token not in text)
        self.assertEqual([], missing, f"missing output-contract visual-companion markers: {missing}")

    def test_behavior_evals_cover_visual_companion_drift(self) -> None:
        payload = json.loads(
            (SKILL_ROOT / "evals" / "behavior-evals.json").read_text(encoding="utf-8")
        )
        ids = {item.get("id") for item in payload.get("evals", [])}
        self.assertIn(
            "no-visual-companion-during-layer0",
            ids,
            "missing behavior eval for visual-companion drift prevention",
        )

    def test_behavior_evals_cover_first_layer0_governed_mutation_state_init(self) -> None:
        payload = json.loads(
            (SKILL_ROOT / "evals" / "behavior-evals.json").read_text(encoding="utf-8")
        )
        ids = {item.get("id") for item in payload.get("evals", [])}
        self.assertIn(
            "bootstrap-layer0-first-governed-mutation-state-init",
            ids,
            "missing behavior eval for first Layer 0 governed mutation state initialization",
        )

    def test_skill_routes_first_layer0_state_init_sequence_to_host_modes(self) -> None:
        skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8").lower()
        for token in (
            "references/host-modes.md",
            "first governed mutation",
        ):
            self.assertIn(token, skill_text)

        host_text = (
            SKILL_ROOT / "references" / "host-modes.md"
        ).read_text(encoding="utf-8").lower()
        required = {
            "when the first layer 0 governed mutation is about to occur in a resolved project workspace",
            "initialize workspace-local `.codex/goal-state.json` first",
            "initial `classified` state",
            "adjacent `planned` or `executing` state",
            "do not ask the user to restate the workspace path",
            "do not detour into state-schema or missing-state investigation",
        }
        missing = sorted(token for token in required if token not in host_text)
        self.assertEqual(
            [],
            missing,
            f"missing cold-path first-mutation state-init markers: {missing}",
        )

    def test_host_modes_define_first_layer0_state_bootstrap_sequence(self) -> None:
        text = (SKILL_ROOT / "references" / "host-modes.md").read_text(encoding="utf-8").lower()
        required = {
            "reuse that workspace for first-state initialization",
            "do not re-ask for the workspace path merely because `.codex/goal-state.json` is absent",
            "write an initial `classified` state, then an adjacent `planned` or `executing` state, then perform the mutation, then audit before claiming the layer 0 checkpoint or gate",
            "do not audit the drive root as a fallback for missing state",
        }
        missing = sorted(token for token in required if token not in text)
        self.assertEqual([], missing, f"missing host-mode first-state-init markers: {missing}")

    def test_output_contract_blocks_first_layer0_state_init_detour(self) -> None:
        text = (SKILL_ROOT / "references" / "output-contract.md").read_text(encoding="utf-8").lower()
        required = {
            "first governed layer 0 mutation",
            "state initialization",
            "do not turn that checkpoint into a missing-state, workspace-resolution, or schema-investigation detour",
        }
        missing = sorted(token for token in required if token not in text)
        self.assertEqual([], missing, f"missing output-contract first-state-init markers: {missing}")

    def test_skill_routes_agent_tool_contract_review_after_goal_classification(self) -> None:
        text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        required = {
            "## Agent Tool Contract Routing",
            "load `agent-tool-contract-review` after `/goal` classification and before the affected design, remediation, or acceptance work",
            "keep `/goal` responsible for project intake, Harness gates, state, and closure",
            "For MCP server implementation, load `mcp-builder` first.",
            "After the implementation surface exists, use `agent-tool-contract-review` for contract review, acceptance, and remediation planning",
            "Do not route ordinary REST controllers, internal service methods, a single existing Tool call, a one-off local fix, prompt examples, Skill path inspection, or a request to review the `/goal` Skill itself.",
        }
        missing = sorted(token for token in required if token not in text)
        self.assertEqual([], missing, f"missing Agent Tool routing markers: {missing}")

    def test_agent_tool_routing_evals_cover_positive_order_and_near_misses(self) -> None:
        payload = json.loads(
            (SKILL_ROOT / "evals" / "agent-tool-contract-routing.json").read_text(encoding="utf-8")
        )
        expected = {
            "agent-tool-project-review": ("按项目方式治理 LLM Tools 的命名、参数、错误、返回结构和副作用确认", True, None),
            "mcp-implementation-acceptance": ("从零实现 MCP server，并在实现后做 Tool 契约与运行时确认验收", True, ["mcp-builder", "agent-tool-contract-review"]),
            "ordinary-rest": ("新增普通 Spring REST Controller，不暴露给模型", False, None),
            "single-tool-call": ("调用已有天气 Tool 查询今天气温，不评审 Tool 契约", False, None),
            "skill-meta": ("只检查 agent-tool-contract-review Skill 的文件结构", False, None),
            "quoted-goal": ("README 引用 /goal 和 MCP Tool 示例，只调整文案", False, None),
        }
        by_id = {item.get("id"): item for item in payload.get("evals", [])}
        self.assertEqual(set(expected), set(by_id))
        for eval_id, (query, should_route, route_order) in expected.items():
            self.assertEqual(query, by_id[eval_id].get("query"))
            self.assertIs(should_route, by_id[eval_id].get("should_route"))
            self.assertEqual(route_order, by_id[eval_id].get("route_order"))

    def test_behavior_evals_rejects_non_object_top_level_payloads(self) -> None:
        module = load_validator()
        target = (SKILL_ROOT / "evals" / "behavior-evals.json").resolve()
        original = Path.read_text
        for malformed in ([], "scalar"):
            with self.subTest(payload_type=type(malformed).__name__):
                def fake_read(path, *args, **kwargs):
                    text = original(path, *args, **kwargs)
                    return json.dumps(malformed) if path.resolve() == target else text

                errors: list[str] = []
                with patch.object(Path, "read_text", autospec=True, side_effect=fake_read):
                    module.validate_behavior_evals(SKILL_ROOT, errors)
                self.assertTrue(any("must be a JSON object" in error for error in errors), errors)

    def test_behavior_evals_rejects_duplicate_ids(self) -> None:
        module = load_validator()
        target = (SKILL_ROOT / "evals" / "behavior-evals.json").resolve()
        original = Path.read_text

        def fake_read(path, *args, **kwargs):
            text = original(path, *args, **kwargs)
            if path.resolve() != target:
                return text
            payload = json.loads(text)
            payload["evals"][1]["id"] = payload["evals"][0]["id"]
            return json.dumps(payload)

        errors: list[str] = []
        with patch.object(Path, "read_text", autospec=True, side_effect=fake_read):
            module.validate_behavior_evals(SKILL_ROOT, errors)
        self.assertTrue(any("duplicate behavior eval id" in error for error in errors), errors)

    def test_agent_tool_routing_rejects_non_object_top_level_payloads(self) -> None:
        module = load_validator()
        target = (SKILL_ROOT / "evals" / "agent-tool-contract-routing.json").resolve()
        original = Path.read_text
        for malformed in ([], "scalar"):
            with self.subTest(payload_type=type(malformed).__name__):
                def fake_read(path, *args, **kwargs):
                    text = original(path, *args, **kwargs)
                    return json.dumps(malformed) if path.resolve() == target else text

                errors: list[str] = []
                with patch.object(Path, "read_text", autospec=True, side_effect=fake_read):
                    module.validate_agent_tool_routing(SKILL_ROOT, errors)
                self.assertTrue(
                    any("agent-tool-contract-routing.json top-level value must be an object" in error for error in errors),
                    errors,
                )
    def test_validator_rejects_mutated_agent_tool_routing_eval_semantics(self) -> None:
        module = load_validator()
        target = (SKILL_ROOT / "evals" / "agent-tool-contract-routing.json").resolve()
        original = Path.read_text

        def fake_read(path, *args, **kwargs):
            text = original(path, *args, **kwargs)
            if path.resolve() == target:
                payload = json.loads(text)
                ordinary_rest = next(item for item in payload["evals"] if item["id"] == "ordinary-rest")
                ordinary_rest["query"] = "按项目方式评审 MCP Tool 的生产契约与运行时确认"
                return json.dumps(payload, ensure_ascii=False)
            return text

        errors = []
        with patch.object(Path, "read_text", autospec=True, side_effect=fake_read):
            module.validate_agent_tool_routing(SKILL_ROOT, errors)
        self.assertTrue(any("ordinary-rest" in error and "query" in error for error in errors))

    def test_validator_rejects_unknown_agent_tool_routing_id(self) -> None:
        module = load_validator()
        target = (SKILL_ROOT / "evals" / "agent-tool-contract-routing.json").resolve()
        original = Path.read_text

        def fake_read(path, *args, **kwargs):
            text = original(path, *args, **kwargs)
            if path.resolve() == target:
                payload = json.loads(text)
                payload["evals"].append(
                    {
                        "id": "unknown-agent-tool-route",
                        "query": "unknown",
                        "should_route": False,
                    }
                )
                return json.dumps(payload, ensure_ascii=False)
            return text

        errors: list[str] = []
        with patch.object(Path, "read_text", autospec=True, side_effect=fake_read):
            module.validate_agent_tool_routing(SKILL_ROOT, errors)
        self.assertTrue(
            any(
                "unknown agent tool routing eval ids" in error
                and "unknown-agent-tool-route" in error
                for error in errors
            ),
            errors,
        )

    def test_validator_rejects_broken_local_reference_links(self) -> None:
        module = load_validator()
        targets = (
            Path("SKILL.md"),
            Path("references") / "external-workflow-boundary.md",
        )

        for relative_target in targets:
            with self.subTest(source=relative_target.name):
                with copied_skill() as root:
                    target = root / relative_target
                    target.write_text(
                        target.read_text(encoding="utf-8")
                        + "\nRead `references/does-not-exist.md`.\n",
                        encoding="utf-8",
                    )
                    errors: list[str] = []
                    module.validate_references(root, errors)
                self.assertTrue(
                    any("missing local reference link" in error for error in errors),
                    errors,
                )

    def test_trigger_catalog_rejects_id_mutations(self) -> None:
        module = load_validator()
        target = (SKILL_ROOT / "evals" / "trigger-queries.json").resolve()
        original = Path.read_text

        def remove_id(payload):
            payload[1].pop("id")

        def duplicate_id(payload):
            payload[1]["id"] = payload[0]["id"]

        def unknown_id(payload):
            payload[1]["id"] = "unknown-trigger-id"

        def missing_id(payload):
            del payload[1]

        mutations = (
            (remove_id, "non-empty string id"),
            (duplicate_id, "duplicate trigger query id"),
            (unknown_id, "unknown trigger query ids"),
            (missing_id, "missing expected trigger query ids"),
        )

        for mutate, expected in mutations:
            with self.subTest(expected=expected):
                def fake_read(path, *args, **kwargs):
                    text = original(path, *args, **kwargs)
                    if path.resolve() == target:
                        payload = json.loads(text)
                        mutate(payload)
                        return json.dumps(payload, ensure_ascii=False)
                    return text

                errors: list[str] = []
                with patch.object(Path, "read_text", autospec=True, side_effect=fake_read):
                    module.validate_trigger_queries(SKILL_ROOT, errors)
                self.assertTrue(any(expected in error for error in errors), errors)

    def test_behavior_catalog_rejects_missing_duplicate_and_unknown_ids(self) -> None:
        module = load_validator()
        target = (SKILL_ROOT / "evals" / "behavior-evals.json").resolve()
        original = Path.read_text

        def missing_id(payload):
            payload["evals"] = [
                item
                for item in payload["evals"]
                if item["id"] != "external-workflow-no-second-owner"
            ]

        def duplicate_id(payload):
            payload["evals"][1]["id"] = payload["evals"][0]["id"]

        def unknown_id(payload):
            payload["evals"].append(
                {
                    "id": "unknown-behavior-id",
                    "prompt": "unknown",
                    "expected_output": "unknown",
                    "files": [],
                }
            )

        mutations = (
            (missing_id, "missing expected eval ids"),
            (duplicate_id, "duplicate behavior eval id"),
            (unknown_id, "unknown behavior eval ids"),
        )

        for mutate, expected in mutations:
            with self.subTest(expected=expected):
                def fake_read(path, *args, **kwargs):
                    text = original(path, *args, **kwargs)
                    if path.resolve() == target:
                        payload = json.loads(text)
                        mutate(payload)
                        return json.dumps(payload, ensure_ascii=False)
                    return text

                errors: list[str] = []
                with patch.object(Path, "read_text", autospec=True, side_effect=fake_read):
                    module.validate_behavior_evals(SKILL_ROOT, errors)
                self.assertTrue(any(expected in error for error in errors), errors)

    def test_behavior_catalog_defines_verification_freshness_scenarios(self) -> None:
        payload = json.loads(
            (SKILL_ROOT / "evals" / "behavior-evals.json").read_text(encoding="utf-8")
        )
        by_id = {item["id"]: item for item in payload["evals"]}
        expected_signals = {
            "verification-stale-after-edit": {
                "stale",
                "rerun the exact verification command",
                "immediately before closure",
                "mutation seq",
                "audit-only-windows",
                "mechanical blocking",
                "current workspace content",
            },
            "verification-untracked-or-generated-change": {
                "subagent",
                "generated",
                "untracked",
                "invalidate",
                "stale",
                "re-run the exact verification command",
                "current workspace content",
            },
        }
        for eval_id, signals in expected_signals.items():
            self.assertIn(eval_id, by_id)
            output = by_id[eval_id]["expected_output"].lower()
            missing = sorted(signal for signal in signals if signal not in output)
            self.assertEqual([], missing, f"{eval_id} missing signals: {missing}")

    def test_validator_rejects_inverted_external_workflow_expectation(self) -> None:
        module = load_validator()
        target = (SKILL_ROOT / "evals" / "behavior-evals.json").resolve()
        original = Path.read_text

        def fake_read(path, *args, **kwargs):
            text = original(path, *args, **kwargs)
            if path.resolve() == target:
                payload = json.loads(text)
                item = next(
                    item
                    for item in payload["evals"]
                    if item["id"] == "external-workflow-no-second-owner"
                )
                item["expected_output"] = (
                    "Install the full gstack pack and make it a second planner and release owner."
                )
                return json.dumps(payload, ensure_ascii=False)
            return text

        errors: list[str] = []
        with patch.object(Path, "read_text", autospec=True, side_effect=fake_read):
            module.validate_behavior_evals(SKILL_ROOT, errors)
        self.assertTrue(
            any(
                "external-workflow-no-second-owner" in error
                and "expected_output" in error
                for error in errors
            ),
            errors,
        )

    def test_main_rejects_agent_context_catalog_mutations(self) -> None:
        module = load_validator()
        target = (SKILL_ROOT / "evals" / "agent-context-routing.json").resolve()
        original = Path.read_text

        def malformed(_payload):
            return []

        def wrong_route(payload):
            payload["route"] = "second-context-owner"
            return payload

        def missing_id(payload):
            payload["evals"] = [
                item for item in payload["evals"] if item["id"] != "ordinary-crud"
            ]
            return payload

        def unknown_id(payload):
            payload["evals"][0]["id"] = "unknown-context-route"
            return payload

        def duplicate_id(payload):
            payload["evals"][1]["id"] = payload["evals"][0]["id"]
            return payload

        def inverted_positive(payload):
            payload["evals"][0]["should_route"] = False
            return payload

        def inverted_negative(payload):
            payload["evals"][1]["should_route"] = True
            return payload

        mutations = (
            malformed,
            wrong_route,
            missing_id,
            unknown_id,
            duplicate_id,
            inverted_positive,
            inverted_negative,
        )

        for mutate in mutations:
            with self.subTest(mutation=mutate.__name__):
                def fake_read(path, *args, **kwargs):
                    text = original(path, *args, **kwargs)
                    if path.resolve() == target:
                        payload = mutate(json.loads(text))
                        return json.dumps(payload, ensure_ascii=False)
                    return text

                with (
                    patch.object(Path, "read_text", autospec=True, side_effect=fake_read),
                    patch.object(sys, "argv", [str(VALIDATOR), str(SKILL_ROOT)]),
                    patch.object(sys, "stdout", io.StringIO()),
                ):
                    self.assertEqual(1, module.main())

    def test_trigger_catalog_rejects_boolean_and_query_semantic_mutations(self) -> None:
        module = load_validator()
        target = (SKILL_ROOT / "evals" / "trigger-queries.json").resolve()
        original = Path.read_text
        payload = json.loads(original(target, encoding="utf-8"))

        for eval_id in (item["id"] for item in payload):
            for field in ("should_trigger", "query"):
                with self.subTest(eval_id=eval_id, field=field):
                    def fake_read(path, *args, **kwargs):
                        text = original(path, *args, **kwargs)
                        if path.resolve() == target:
                            mutated = json.loads(text)
                            item = next(item for item in mutated if item["id"] == eval_id)
                            if field == "should_trigger":
                                item[field] = not item[field]
                            else:
                                item[field] = "x"
                            return json.dumps(mutated, ensure_ascii=False)
                        return text

                    errors: list[str] = []
                    with patch.object(Path, "read_text", autospec=True, side_effect=fake_read):
                        module.validate_trigger_queries(SKILL_ROOT, errors)
                    self.assertTrue(
                        any(
                            eval_id in error
                            and (
                                "should_trigger" in error
                                if field == "should_trigger"
                                else "query" in error
                            )
                            for error in errors
                        ),
                        errors,
                    )

    def test_all_behavior_catalog_entries_reject_erased_expected_semantics(self) -> None:
        module = load_validator()
        target = (SKILL_ROOT / "evals" / "behavior-evals.json").resolve()
        original = Path.read_text
        payload = json.loads(original(target, encoding="utf-8"))

        for eval_id in (item["id"] for item in payload["evals"]):
            with self.subTest(eval_id=eval_id):
                def fake_read(path, *args, **kwargs):
                    text = original(path, *args, **kwargs)
                    if path.resolve() == target:
                        mutated = json.loads(text)
                        item = next(
                            item for item in mutated["evals"] if item["id"] == eval_id
                        )
                        item["expected_output"] = "x"
                        return json.dumps(mutated, ensure_ascii=False)
                    return text

                errors: list[str] = []
                with patch.object(Path, "read_text", autospec=True, side_effect=fake_read):
                    module.validate_behavior_evals(SKILL_ROOT, errors)
                self.assertTrue(
                    any(
                        eval_id in error and "expected_output" in error
                        for error in errors
                    ),
                    errors,
                )

    def test_local_reference_links_reject_escape_and_absolute_targets(self) -> None:
        module = load_validator()
        mutation_factories = (
            lambda _root: "references/../SKILL.md",
            lambda _root: "references/nested/../../SKILL.md",
            lambda root: (root / "references" / "host-modes.md").resolve().as_posix(),
        )

        for make_reference in mutation_factories:
            with copied_skill() as root:
                reference = make_reference(root)
                with self.subTest(reference=reference):
                    target = root / "SKILL.md"
                    target.write_text(
                        target.read_text(encoding="utf-8")
                        + f"\nRead `{reference}`.\n",
                        encoding="utf-8",
                    )
                    errors: list[str] = []
                    module.validate_references(root, errors)
                    self.assertTrue(
                        any(
                            "local reference link" in error
                            and (
                                "escapes references directory" in error
                                or "must be relative" in error
                                or "must not contain '..'" in error
                            )
                            for error in errors
                        ),
                        errors,
                    )

    def test_task4_skill_is_thin_and_defers_cold_path_details(self) -> None:
        skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertLessEqual(len(skill_text.splitlines()), 135)
        for token in (
            "Five-Stage Runtime",
            "Stage 1: Intake",
            "Stage 2: Classify",
            "Stage 3: Load Harness",
            "Stage 4: Orchestrate",
            "Stage 5: Return",
            "goal",
            "harness",
            "guard",
            "gsd",
            "protocol.json",
            "protocol-guide.md",
            "capability-discovery.md",
            "gsd-adapter.md",
        ):
            self.assertIn(token.lower(), skill_text.lower())
        for cold_path_detail in (
            "## Guard Commands",
            "sha256-manifest-v1",
            "initialize-state",
            "complete approved GSD receipt",
            "missing, invalid, disabled, or blocked GSD uses the Harness fallback",
            "ten-control findings",
            "dependency-ordered remediation batches",
            "stale-write analysis",
            "exact regression scenarios",
            "reusable acceptance templates",
            "production inventory",
            "per-Tool four-dimensional scores",
        ):
            self.assertNotIn(cold_path_detail.lower(), skill_text.lower())
        self.assertIn("Confirmation:", skill_text)
        self.assertNotIn("Host mode:", skill_text)
        self.assertRegex(
            skill_text.lower(),
            r"host.{0,80}(mutation|verification|closure)",
        )
        progressive = skill_text[
            skill_text.index("## Progressive References"):
            skill_text.index("## Progress Persistence")
        ]
        self.assertRegex(
            progressive,
            r"(?m)^\|\s*Reference\s*\|\s*Load condition\s*\|\s*$",
        )
        self.assertRegex(progressive, r"(?m)^\|\s*-+\s*\|\s*-+\s*\|\s*$")
        for reference in (
            "references/protocol.json",
            "protocol-guide.md",
            "capability-discovery.md",
            "gsd-adapter.md",
            "layer-execution.md",
            "host-modes.md",
            "output-contract.md",
            "external-workflow-boundary.md",
        ):
            self.assertIn(f"| `{reference}` |", progressive)

    def test_first_classification_turn_has_closed_terminal_reference_contract(self) -> None:
        module = load_validator()
        skill_path = (SKILL_ROOT / "SKILL.md").resolve()
        skill_text = skill_path.read_text(encoding="utf-8")
        expected_rule = (
            "Before the first active classification reply, read only "
            "`references/protocol.json`, `references/output-contract.md`, and "
            "`references/layer-execution.md`; emit the five-field reply and stop. "
            "Do not read `references/host-modes.md`, "
            "`references/capability-discovery.md`, or Harness in that turn, even "
            "when `Confirmation` is `not-required`."
        )

        stage_2 = re.search(
            r"^### Stage 2: Classify\s*$\n(?P<body>.*?)(?=^### Stage 3: Load Harness\s*$)",
            skill_text,
            flags=re.MULTILINE | re.DOTALL,
        )
        self.assertIsNotNone(stage_2)
        self.assertIn(expected_rule, stage_2.group("body"))

        progressive = skill_text[
            skill_text.index("## Progressive References"):
            skill_text.index("## Progress Persistence")
        ]
        self.assertIn("| `references/protocol.json` |", progressive)

        original = Path.read_text

        def fake_read(path, *args, **kwargs):
            text = original(path, *args, **kwargs)
            return (
                text.replace(expected_rule, "")
                if path.resolve() == skill_path
                else text
            )

        errors: list[str] = []
        with patch.object(Path, "read_text", autospec=True, side_effect=fake_read):
            module.validate_skill_text(SKILL_ROOT, errors)
        self.assertIn(
            "SKILL.md missing closed terminal classification-turn routing contract",
            errors,
        )

    def test_task4_validator_counts_physical_lines_at_hot_path_limit(self) -> None:
        module = load_validator()
        target = (SKILL_ROOT / "SKILL.md").resolve()
        original = Path.read_text
        base_lines = original(target, encoding="utf-8").splitlines()
        for physical_lines, expected_error in (
            (135, None),
            (136, None),
        ):
            with self.subTest(physical_lines=physical_lines):
                padded = "\n".join(
                    base_lines
                    + ["<!-- Task4 line-count padding -->"]
                    * (physical_lines - len(base_lines))
                ) + "\n"
                self.assertEqual(physical_lines, len(padded.splitlines()))

                def fake_read(path, *args, **kwargs):
                    return padded if path.resolve() == target else original(
                        path, *args, **kwargs
                    )

                errors: list[str] = []
                with patch.object(Path, "read_text", autospec=True, side_effect=fake_read):
                    module.validate_skill_text(SKILL_ROOT, errors)
                line_errors = [error for error in errors if "too long" in error]
                self.assertEqual([], line_errors)

    def test_task4_references_use_protocol_output_fields(self) -> None:
        output_text = (
            SKILL_ROOT / "references" / "output-contract.md"
        ).read_text(encoding="utf-8")
        self.assertIn("Code:", output_text)
        self.assertIn("Confirmation:", output_text)
        self.assertNotIn("Host mode:", output_text)
        self.assertTrue(
            (SKILL_ROOT / "references" / "protocol-guide.md").exists(),
            "missing Task4 reference: protocol-guide.md",
        )
        host_text = (
            SKILL_ROOT / "references" / "host-modes.md"
        ).read_text(encoding="utf-8")
        self.assertNotIn("Detect Once Per Goal", host_text)
        self.assertNotIn("codex features list", host_text)
        for token in (
            "capability-discovery.md",
            "hard-hook",
            "audit-only-windows",
            "Guard Commands",
        ):
            self.assertIn(token.lower(), host_text.lower())
        layer_text = (
            SKILL_ROOT / "references" / "layer-execution.md"
        ).read_text(encoding="utf-8").lower()
        self.assertIn("protocol.json", layer_text)

    def test_task5_gsd_adapter_contains_layer6_boundary_rules(self) -> None:
        adapter = SKILL_ROOT / "references" / "gsd-adapter.md"
        text = adapter.read_text(encoding="utf-8").lower() if adapter.exists() else ""
        required = {
            "`/goal` remains the unique project entry",
            "goal owns gsd activation and routing",
            "harness owns layer 6 approval, gates, rollback, closure, and receipt approval",
            "`gsd-plan-phase`, `gsd-execute-phase`, and `gsd-verify-work` are subordinate layer 6 tools only",
            "plan-phase -> execute-phase -> verify-work",
            "receipt checks are mandatory before advancing to the next gsd operation",
            "gsd must not change goal state, start_layer, or harness pass/fail decisions",
            "layer 4 planning remains forbidden for gsd in this integration",
            "`gsd-autonomous` and any autonomous execution surface remain forbidden unless the user separately approves them",
            r"<project>\.codex\gsd-layer6-pilot.local.json",
            "explicit harness layer 6 approval",
            "previous pilot cleanup was blocked or drift was preserved",
            "cleanup evidence is repaired and re-verified",
            "fall back to the original non-gsd `/goal` + harness layer 6 path",
            "audit-only-windows",
            "do not claim mechanical blocking when hooks are unavailable",
        }
        missing = sorted(token for token in required if token not in text)
        self.assertEqual([], missing, f"missing GSD adapter rules: {missing}")

    def test_task5_gsd_global_agents_is_only_a_single_deferred_pointer(self) -> None:
        text = DEPLOYMENT_AGENTS.read_text(encoding="utf-8")
        adapter_path = (
            "C:/Users/14156/.codex/skills/goal/references/gsd-adapter.md"
        )
        pointer = (
            "For an active `/goal` run that proposes GSD at Layer 6, load\n"
            f"`{adapter_path}` after Goal\n"
            "classification and Harness approval. Do not infer GSD activation from a mention."
        )
        self.assertIn(pointer, text)
        self.assertEqual(1, text.count(adapter_path))
        self.assertIn("- `Confirmation:`", text)
        self.assertNotIn("- `Host mode:`", text)
        for leaked_detail in (
            "plan-phase -> execute-phase -> verify-work",
            "gsd-autonomous",
            "gsd-layer6-pilot.local.json",
            "previous pilot cleanup",
            "drift was preserved",
            "cleanup evidence",
            "gsd is missing, disabled, invalid, or blocked",
            "fall back to the original non-gsd",
            "non-gsd `/goal` + harness layer 6 path",
        ):
            self.assertNotIn(leaked_detail, text.lower())

    def test_task5_gsd_validator_rejects_missing_adapter_rule(self) -> None:
        with copied_skill() as root:
            adapter = root / "references" / "gsd-adapter.md"
            if adapter.exists():
                text = adapter.read_text(encoding="utf-8").replace(
                    "plan-phase -> execute-phase -> verify-work",
                    "execute-phase -> plan-phase -> verify-work",
                )
                adapter.write_text(text, encoding="utf-8")
            else:
                adapter.write_text("# Incomplete GSD adapter\n", encoding="utf-8")
            completed = self.run_validator_cli(root)

        output = completed.stdout + completed.stderr
        self.assertEqual(1, completed.returncode, output)
        self.assertIn(
            "gsd-adapter.md missing required rule: plan-phase -> execute-phase -> verify-work",
            output,
        )

    def test_task5_gsd_validator_rejects_global_pointer_and_detail_drift(self) -> None:
        adapter_path = (
            "C:/Users/14156/.codex/skills/goal/references/gsd-adapter.md"
        )
        mutations = (
            (
                "duplicate pointer",
                lambda text: text.replace(
                    f"`{adapter_path}` after Goal",
                    f"`{adapter_path}` and `{adapter_path}` after Goal",
                ),
                "global AGENTS.md must contain the GSD adapter path exactly once",
            ),
            (
                "detail leakage",
                lambda text: text
                + "\nRequired operation order is `plan-phase -> execute-phase -> verify-work`.\n",
                "forbidden GSD detail in global AGENTS.md: plan-phase -> execute-phase -> verify-work",
            ),
            (
                "cleanup drift leakage",
                lambda text: text
                + "\nDo not reactivate when drift was preserved until cleanup evidence is repaired.\n",
                "forbidden GSD detail in global AGENTS.md: drift was preserved",
            ),
            (
                "fallback leakage",
                lambda text: text
                + "\nIf GSD is missing, disabled, invalid, or blocked, use the Harness path.\n",
                "forbidden GSD detail in global AGENTS.md: gsd is missing, disabled, invalid, or blocked",
            ),
        )
        for name, mutate, expected in mutations:
            with self.subTest(name=name):
                with copied_skill() as root:
                    global_agents = root.parent / "AGENTS.md"
                    global_agents.write_text(
                        mutate(DEPLOYMENT_AGENTS.read_text(encoding="utf-8")),
                        encoding="utf-8",
                    )
                    completed = subprocess.run(
                        [
                            sys.executable,
                            "-B",
                            str(VALIDATOR),
                            str(root),
                            "--global-agents",
                            str(global_agents),
                        ],
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )

                output = completed.stdout + completed.stderr
                self.assertEqual(1, completed.returncode, output)
                self.assertIn(expected, output)



if __name__ == "__main__":
    unittest.main(verbosity=2)
