#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path
from types import ModuleType


def _load_protocol_module() -> ModuleType:
    path = Path(__file__).with_name("protocol.py")
    spec = importlib.util.spec_from_file_location("goal_protocol_contract", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load protocol helpers from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_PROTOCOL = _load_protocol_module()
load_contract = _PROTOCOL.load_contract
required_fields = _PROTOCOL.required_fields
validate_contract = _PROTOCOL.validate_contract


ALLOWED_TOP_LEVEL = {"SKILL.md", "references", "scripts", "evals"}

REQUIRED_SKILL_SECTIONS = (
    "## Five-Stage Runtime",
    "### Stage 1: Intake",
    "### Stage 2: Classify",
    "### Stage 3: Load Harness",
    "### Stage 4: Orchestrate",
    "### Stage 5: Return",
)
REQUIRED_REFERENCES = (
    "external-workflow-boundary.md",
    "gsd-adapter.md",
    "host-modes.md",
    "layer-execution.md",
    "output-contract.md",
    "protocol.json",
    "protocol-guide.md",
)

TRIGGER_QUERY_EXPECTATIONS = {
    "bare-goal-intake": {
        "should_trigger": True,
        "all": ("/goal",),
    },
    "project-bootstrap-inspection-platform": {
        "should_trigger": True,
        "all": ("从 0 到 1", "设备巡检平台", "移动端", "报表导出", "分阶段上线"),
    },
    "project-maintenance-monolith-split": {
        "should_trigger": True,
        "all": ("订单系统", "单体应用", "拆成服务", "库存", "支付", "通知", "整个项目"),
    },
    "project-natural-two-week-cross-layer": {
        "should_trigger": True,
        "all": ("接下来两周", "导入", "审核", "发布", "前后端", "数据库", "验收证据", "按项目方式"),
    },
    "project-permission-system-rebuild": {
        "should_trigger": True,
        "all": ("权限系统", "资源级授权", "分层验证", "上线"),
    },
    "project-runtime-stack-migration": {
        "should_trigger": True,
        "all": ("java", "python", "前端接口契约", "部署方式", "按项目"),
    },
    "project-e2e-major-feature-flow": {
        "should_trigger": True,
        "all": ("端到端", "客户录入", "审批", "通知", "归档", "多层改动", "阶段验收", "完整项目流程"),
    },
    "local-null-guard": {
        "should_trigger": False,
        "all": ("空指针", "不用上升", "项目规划"),
    },
    "local-sql-diagnosis": {
        "should_trigger": False,
        "all": ("sql", "为什么慢", "诊断", "不要改架构"),
    },
    "local-login-style-edit": {
        "should_trigger": False,
        "all": ("登录页", "按钮颜色", "蓝色", "文案"),
    },
    "local-pytest-diagnosis": {
        "should_trigger": False,
        "all": ("pytest", "定位根因", "不要顺手重做"),
    },
    "local-interface-explanation": {
        "should_trigger": False,
        "all": ("接口返回值结构", "字段含义"),
    },
    "local-readme-polish": {
        "should_trigger": False,
        "all": ("readme", "润色", "新同事"),
    },
    "explicit-goal-local-redirect": {
        "should_trigger": True,
        "all": ("/goal", "只修复", "空指针", "对应单测", "不要做项目规划"),
    },
    "meta-skill-review": {
        "should_trigger": False,
        "all": ("/goal skill", "评审", "不要进入项目交付"),
    },
    "meta-quoted-command": {
        "should_trigger": False,
        "all": ("readme", "`/goal build the service`", "文档措辞", "不要真的执行"),
    },
    "meta-path-inspection": {
        "should_trigger": False,
        "all": (r".codex\skills\goal\skill.md", "文件检查", "不是启动项目"),
    },
    "multi-file-mechanical-rename": {
        "should_trigger": False,
        "all": ("多文件", "机械改名", "稳定契约", "不要项目规划"),
    },
    "meta-gsd-discussion": {
        "should_trigger": False,
        "all": ("gsd adapter", "审阅", "讨论", "不激活 /goal"),
    },
}
REQUIRED_TRIGGER_QUERY_IDS = set(TRIGGER_QUERY_EXPECTATIONS)

REQUIRED_POSITIVE_TRIGGER_IDS = {
    "bare-goal-intake",
}

FORBIDDEN_SKILL_TOKENS = [
    "## Mandatory Enforcement Protocol",
    "### Stage 1: Trigger",
    "## When Not to Use /goal",
    "MUST trigger when the user explicitly writes",
    "request is project-scoped, multi-turn",
]

CLOSED_CLASSIFICATION_TURN_RULE = (
    "Before the first active classification reply, read only "
    "`references/protocol.json`, `references/output-contract.md`, and "
    "`references/layer-execution.md`; emit the five-field reply and stop. "
    "Do not read `references/host-modes.md`, `references/capability-discovery.md`, "
    "or Harness in that turn, even when `Confirmation` is `not-required`."
)

REQUIRED_BEHAVIOR_EVAL_IDS = {
    "bootstrap-intake",
    "maintenance-major-flow",
    "near-miss-local-fix",
    "cold-path-classification-only",
    "structured-closure",
    "harness-deferred-during-intake",
    "harness-required-before-execution",
    "harness-dependency-missing",
    "goal-intake-no-objective",
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
    "guard-capability-version-match",
    "guard-capability-version-mismatch",
    "deferred-host-discovery",
    "delivery-entry-missing-feature",
    "delivery-legacy-no-feature",
    "delivery-entry-feature-supported",
}

BEHAVIOR_EXPECTED_OUTPUT_SEMANTICS = {
    "delivery-entry-missing-feature": {
        "all": ("capability_disabled", "dependency goal-guard", "do not initialize-state", "write delivery"),
    },
    "delivery-legacy-no-feature": {
        "all": ("legacy", "without requiring", "web-fullstack-delivery-v1"),
    },
    "delivery-entry-feature-supported": {
        "all": ("feature check passes", "delivery initialization", "continue"),
    },
    "goal-intake-no-objective": {
        "all": ("goal-intake", "ask only", "missing project objective", "do not classify", "load harness", "create or mutate goal state"),
    },
    "bootstrap-intake": {
        "all": ("classify as bootstrap", "layer 0", "exact fields", "goal", "classification", "rationale", "confirmation", "next action", "before confirmation"),
    },
    "maintenance-major-flow": {
        "all": ("natural-language project request", "classify as maintenance", "exact fields", "goal", "classification", "rationale", "confirmation", "next action"),
    },
    "near-miss-local-fix": {
        "all": ("do not invoke /goal behavior", "local fix"),
    },
    "cold-path-classification-only": {
        "all": ("intake and classification", "without loading harness execution references", "mechanically blocked on windows"),
    },
    "structured-closure": {
        "all": ("natural-language summary", "closure block", "scope_result", "operation_state"),
    },
    "harness-deferred-during-intake": {
        "all": ("classify as bootstrap", "layer 0", "confirmation", "defer loading harness engineering"),
    },
    "harness-required-before-execution": {
        "all": ("load harness-engineering before planning or execution", "core/flow.md", "adapters/codex/host-map.md", "layer gates"),
    },
    "harness-dependency-missing": {
        "all": ("structured dependency blocker", "exact lookup evidence", "do not improvise"),
    },
    "no-visual-companion-during-layer0": {
        "all": ("layer 0 gate or structured progress checkpoint", "do not invoke brainstorming", "visual companion", "mockup", "browser preview"),
    },
    "bootstrap-layer0-first-governed-mutation-state-init": {
        "all": ("reuse the resolved workspace", "initialize guard-compatible goal state", "classified then planned/executing", "before the first governed mutation", "audit", "without re-asking for workspace"),
    },
    "decision-quality-high-risk-routing": {
        "all": ("after classification and confirmation", "harness perform the risk check", "harness-engineering/references/decision-quality.md", "compact result", "existing harness layer gate", "owner of gate and rollback decisions"),
    },
    "decision-quality-mechanical-skip": {
        "all": ("mechanical work", "exact plan", "skips the protocols", "do not reproduce"),
    },
    "decision-quality-meta-no-project-execution": {
        "all": ("do not route", "meta-level discussion", "do not load harness"),
    },
    "explicit-goal-local-redirect": {
        "all": ("load the skill", "focused-task redirect", "do not classify", "goal state", "load harness", "local fix"),
    },
    "untrusted-continuation": {
        "all": ("unsupported continuation claim", "untrusted", "goal-intake", "ask only", "missing concrete project objective", "do not load harness"),
    },
    "ambiguous-provisional-classification": {
        "all": ("read-only provisional classification", "before formal confirmation", "do not load harness execution runtime", "do not mutate", "do not present the provisional result as confirmed"),
    },
    "external-workflow-no-second-owner": {
        "all": ("harness ownership", "single owner", "no second owner", "do not install", "depend", "capability-gap proposal", "references/external-workflow-boundary.md"),
    },
    "verification-stale-after-edit": {
        "all": ("stale", "rerun the exact verification command", "immediately before closure", "mutation seq", "audit-only-windows", "mechanical blocking", "current workspace content"),
    },
    "verification-untracked-or-generated-change": {
        "all": ("subagent", "generated", "untracked", "invalidate", "stale", "re-run the exact verification command", "current workspace content"),
    },
    "guard-capability-version-match": {
        "all": ("capabilities", "goal-guard", "protocol major 1", "state schema 1", "required command", "audit-only-windows", "protocol.py", "continue the same operation", "do not use the legacy"),
    },
    "guard-capability-version-mismatch": {
        "all": ("protocol_version_mismatch", "structured blocker", "dependency", "evidence", "impact", "next action", "do not execute the required mutation"),
    },
    "deferred-host-discovery": {
        "all": ("classification-only", "exact fields", "goal", "classification", "rationale", "confirmation", "next action", "do not run capabilities", "host discovery", "guard"),
    },
}

REQUIRED_META_TRIGGER_IDS = {
    "meta-skill-review",
    "meta-quoted-command",
    "meta-path-inspection",
    "multi-file-mechanical-rename",
    "meta-gsd-discussion",
}
AGENT_TOOL_ROUTE_EXPECTATIONS = {
    "agent-tool-project-review": {
        "query": "按项目方式治理 LLM Tools 的命名、参数、错误、返回结构和副作用确认",
        "should_route": True,
    },
    "mcp-implementation-acceptance": {
        "query": "从零实现 MCP server，并在实现后做 Tool 契约与运行时确认验收",
        "should_route": True,
        "route_order": ["mcp-builder", "agent-tool-contract-review"],
    },
    "ordinary-rest": {
        "query": "新增普通 Spring REST Controller，不暴露给模型",
        "should_route": False,
    },
    "single-tool-call": {
        "query": "调用已有天气 Tool 查询今天气温，不评审 Tool 契约",
        "should_route": False,
    },
    "skill-meta": {
        "query": "只检查 agent-tool-contract-review Skill 的文件结构",
        "should_route": False,
    },
    "quoted-goal": {
        "query": "README 引用 /goal 和 MCP Tool 示例，只调整文案",
        "should_route": False,
    },
}
REQUIRED_AGENT_TOOL_ROUTE_IDS = set(AGENT_TOOL_ROUTE_EXPECTATIONS)

AGENT_CONTEXT_ROUTE_EXPECTATIONS = {
    "agent-context-review": True,
    "ordinary-crud": False,
    "skill-meta": False,
    "quoted-goal": False,
}
REQUIRED_AGENT_CONTEXT_ROUTE_IDS = set(AGENT_CONTEXT_ROUTE_EXPECTATIONS)

REFERENCE_LINK_TARGET = re.compile(
    r"`([^`\r\n]+\.md)`|\(([^()\r\n]+\.md)\)|"
    r"(?<![A-Za-z0-9_./-])(references/[A-Za-z0-9_./-]+\.md)"
)


GLOBAL_AGENTS_TOKENS = [
    "## Project-Level /goal Routing",
    "MUST load and follow",
    "skills/goal/SKILL.md",
    "Classification: [bootstrap/maintenance], starting from Layer [0..6]",
    "Confirmation:",
    "Do not use `/goal`",
    "goal-intake",
    "Ask only for the missing project objective.",
    "audit-only-windows",
]

GSD_ADAPTER_TOKENS = (
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
)

GSD_ADAPTER_GLOBAL_PATH = (
    "C:/Users/14156/.codex/skills/goal/references/gsd-adapter.md"
)
GSD_ADAPTER_GLOBAL_POINTER = (
    "For an active `/goal` run that proposes GSD at Layer 6, load\n"
    f"`{GSD_ADAPTER_GLOBAL_PATH}` after Goal\n"
    "classification and Harness approval. Do not infer GSD activation from a mention."
)
GLOBAL_AGENTS_FORBIDDEN_GSD_DETAILS = (
    "plan-phase -> execute-phase -> verify-work",
    "gsd-autonomous",
    "gsd-layer6-pilot.local.json",
    "previous pilot cleanup",
    "drift was preserved",
    "cleanup evidence",
    "gsd is missing, disabled, invalid, or blocked",
    "fall back to the original non-gsd",
    "non-gsd `/goal` + harness layer 6 path",
)


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def validate_package_boundaries(root: Path, errors: list[str]) -> None:
    actual = {path.name for path in root.iterdir()}
    unexpected = sorted(actual - ALLOWED_TOP_LEVEL)
    missing = sorted(ALLOWED_TOP_LEVEL - actual)
    if unexpected:
        errors.append(f"unexpected top-level package entries: {', '.join(unexpected)}")
    if missing:
        errors.append(f"missing top-level package entries: {', '.join(missing)}")


def validate_skill_text(root: Path, errors: list[str]) -> None:
    skill_md = root / "SKILL.md"
    if not skill_md.exists():
        errors.append(f"missing {skill_md}")
        return

    text = load_text(skill_md)
    # Report hot-path size for observability; do not impose an arbitrary
    # line-count gate. Loading behavior is validated by route/event checks.
    line_count = len(text.splitlines())
    if line_count <= 0:
        errors.append("SKILL.md must not be empty")

    if not text.startswith("---\n") or "\nname: goal\n" not in text:
        errors.append("SKILL.md must have frontmatter with name: goal")

    for section in REQUIRED_SKILL_SECTIONS:
        if section not in text:
            errors.append(f"missing runtime section in SKILL.md: {section}")

    for token in FORBIDDEN_SKILL_TOKENS:
        if token in text:
            errors.append(f"forbidden hot-path token still present in SKILL.md: {token}")

    if CLOSED_CLASSIFICATION_TURN_RULE not in text:
        errors.append(
            "SKILL.md missing closed terminal classification-turn routing contract"
        )


def validate_references(root: Path, errors: list[str]) -> None:
    references_dir = root / "references"
    if not references_dir.exists():
        errors.append(f"missing references directory: {references_dir}")
        return

    for name in REQUIRED_REFERENCES:
        path = references_dir / name
        if not path.exists():
            errors.append(f"missing reference file: {path}")

    sources = [root / "SKILL.md", *sorted(references_dir.rglob("*.md"))]
    resolved_references_dir = references_dir.resolve()
    for source in sources:
        if not source.exists():
            continue
        text = load_text(source)
        for match in REFERENCE_LINK_TARGET.finditer(text):
            raw_target = next(group for group in match.groups() if group is not None)
            normalized_target = raw_target.replace("\\", "/")
            candidate = Path(normalized_target)
            is_absolute = candidate.is_absolute() or bool(
                re.match(r"^[A-Za-z]:/", normalized_target)
            )
            if not is_absolute and not normalized_target.startswith("references/"):
                continue

            resolved_target = (root / candidate).resolve()
            if is_absolute:
                errors.append(
                    f"local reference link in {source.relative_to(root)} must be relative: "
                    f"{raw_target}"
                )
                continue
            if ".." in candidate.parts:
                errors.append(
                    f"local reference link in {source.relative_to(root)} must not contain '..': "
                    f"{raw_target}"
                )
                continue
            try:
                relative_target = resolved_target.relative_to(resolved_references_dir)
            except ValueError:
                errors.append(
                    f"local reference link in {source.relative_to(root)} escapes references directory: "
                    f"{raw_target}"
                )
                continue
            if relative_target == Path(".") or not resolved_target.is_file():
                errors.append(
                    f"missing local reference link in {source.relative_to(root)}: "
                    f"{raw_target}"
                )


def validate_gsd_adapter(root: Path, errors: list[str]) -> None:
    path = root / "references" / "gsd-adapter.md"
    if not path.exists():
        errors.append(f"missing GSD adapter reference: {path}")
        return

    text = load_text(path).lower()
    for token in GSD_ADAPTER_TOKENS:
        if token not in text:
            errors.append(f"gsd-adapter.md missing required rule: {token}")


OUTPUT_CONTRACT_SECTIONS = {
    "classification_reply": "Classification Reply",
    "dependency_blocker": "Dependency Blocker Reply",
    "verification_receipt": "Verification Reply",
    "closure_record": "Closure Reply",
}

CLASSIFICATION_CLOSED_SET_RULE = (
    "`Host mode` must not replace `Confirmation:` in this reply."
)
DUAL_LOOKUP_EVIDENCE_TEMPLATE = (
    "Evidence: `[exact lookup command 1]` returned `[exact result 1]`; "
    "`[exact lookup command 2]` returned `[exact result 2]`."
)
STALE_VERIFICATION_REPLY_TEMPLATE = (
    "Prior receipt: stale (`STALE_VERIFICATION`); `Mutation Seq` alone does not "
    "prove current bytes."
)
MISMATCH_EVIDENCE_TEMPLATE = (
    "Evidence: The configured Guard `capabilities` command reported protocol major "
    "[configured major]; the documented legacy path "
    "`$env:USERPROFILE\\plugins\\goal-enforcement\\scripts\\goal_guard.py capabilities` "
    "reported protocol major [legacy major]; Goal Protocol v2 requires major 1."
)

def validate_protocol(root: Path, errors: list[str]) -> dict | None:
    try:
        return load_contract(root)
    except (ValueError, ImportError) as exc:
        errors.append(str(exc))
        return None


def _markdown_section(text: str, heading: str) -> str | None:
    match = re.search(
        rf"^## {re.escape(heading)}\s*$\n(?P<body>.*?)(?=^## |\Z)",
        text,
        flags=re.MULTILINE | re.DOTALL,
    )
    return match.group("body") if match else None


def validate_output_contract(
    root: Path, contract: dict, errors: list[str]
) -> None:
    path = root / "references" / "output-contract.md"
    if not path.exists():
        errors.append(f"missing reference file: {path}")
        return
    text = load_text(path)
    for record in contract["records"]:
        heading = OUTPUT_CONTRACT_SECTIONS.get(record)
        if heading is None:
            errors.append(
                f"output-contract.md missing section mapping for record: {record}"
            )
            continue
        section = _markdown_section(text, heading)
        if section is None:
            errors.append(f"output-contract.md missing section: {heading}")
            continue
        expected = required_fields(contract, record)
        missing = [
            field
            for field in expected
            if re.search(rf"^{re.escape(field)}:", section, re.MULTILINE) is None
        ]
        if missing:
            errors.append(
                f"output-contract.md {record} missing protocol fields: "
                + ", ".join(missing)
            )

    if CLASSIFICATION_CLOSED_SET_RULE not in text:
        errors.append("output-contract.md missing closed classification field rule")
    if DUAL_LOOKUP_EVIDENCE_TEMPLATE not in text:
        errors.append("output-contract.md missing dual lookup Evidence template")
    if STALE_VERIFICATION_REPLY_TEMPLATE not in text:
        errors.append("output-contract.md missing stale verification reply template")


def validate_capability_discovery(root: Path, errors: list[str]) -> None:
    path = root / "references" / "capability-discovery.md"
    if not path.exists():
        errors.append(f"missing reference file: {path}")
        return
    if MISMATCH_EVIDENCE_TEMPLATE not in load_text(path):
        errors.append("capability-discovery.md missing mismatch Evidence template")


def validate_trigger_queries(root: Path, errors: list[str]) -> None:
    path = root / "evals" / "trigger-queries.json"
    if not path.exists():
        errors.append(f"missing eval file: {path}")
        return
    try:
        payload = json.loads(load_text(path))
    except json.JSONDecodeError as exc:
        errors.append(f"invalid JSON in {path}: {exc}")
        return

    if not isinstance(payload, list) or not payload:
        errors.append("trigger-queries.json must be a non-empty array")
        return

    positives = 0
    negatives = 0
    positive_ids: set[str] = set()
    negative_ids: set[str] = set()
    ids: set[str] = set()
    for item in payload:
        if not isinstance(item, dict):
            errors.append("trigger-queries.json entries must be objects")
            return
        if not isinstance(item.get("query"), str) or not item["query"].strip():
            errors.append("every trigger query must have a non-empty query string")
            return
        trigger_id = item.get("id")
        if not isinstance(trigger_id, str) or not trigger_id.strip():
            errors.append("every trigger query must have a non-empty string id")
            continue
        if trigger_id in ids:
            errors.append(f"duplicate trigger query id: {trigger_id}")
        else:
            ids.add(trigger_id)
        if item.get("should_trigger") is True:
            positives += 1
            positive_ids.add(trigger_id)
        elif item.get("should_trigger") is False:
            negatives += 1
            negative_ids.add(trigger_id)
        else:
            errors.append("every trigger query must set should_trigger to true or false")
            return
        expectation = TRIGGER_QUERY_EXPECTATIONS.get(trigger_id)
        if expectation is not None:
            if item.get("should_trigger") is not expectation["should_trigger"]:
                errors.append(
                    f"trigger query {trigger_id} has the wrong should_trigger value"
                )
            query = item["query"].lower()
            missing_signals = sorted(
                signal for signal in expectation["all"] if signal not in query
            )
            if missing_signals:
                errors.append(
                    f"trigger query {trigger_id} query missing required signals: "
                    + ", ".join(missing_signals)
                )
    if positives == 0 or negatives == 0:
        errors.append("trigger-queries.json must include both trigger and non-trigger cases")
    missing_positive = REQUIRED_POSITIVE_TRIGGER_IDS - positive_ids
    if missing_positive:
        errors.append(
            "trigger-queries.json missing positive trigger ids: "
            + ", ".join(sorted(missing_positive))
        )
    missing_meta = REQUIRED_META_TRIGGER_IDS - negative_ids
    if missing_meta:
        errors.append(
            "trigger-queries.json missing meta non-trigger ids: "
            + ", ".join(sorted(missing_meta))
        )
    missing_ids = REQUIRED_TRIGGER_QUERY_IDS - ids
    if missing_ids:
        errors.append(
            "trigger-queries.json missing expected trigger query ids: "
            + ", ".join(sorted(missing_ids))
        )
    unknown_ids = ids - REQUIRED_TRIGGER_QUERY_IDS
    if unknown_ids:
        errors.append(
            "trigger-queries.json has unknown trigger query ids: "
            + ", ".join(sorted(unknown_ids))
        )


def validate_behavior_evals(root: Path, errors: list[str]) -> None:
    path = root / "evals" / "behavior-evals.json"
    if not path.exists():
        errors.append(f"missing eval file: {path}")
        return
    try:
        payload = json.loads(load_text(path))
    except json.JSONDecodeError as exc:
        errors.append(f"invalid JSON in {path}: {exc}")
        return

    if not isinstance(payload, dict):
        errors.append("behavior-evals.json must be a JSON object")
        return

    if payload.get("skill_name") != "goal":
        errors.append("behavior-evals.json skill_name must be 'goal'")
    evals = payload.get("evals")
    if not isinstance(evals, list) or not evals:
        errors.append("behavior-evals.json evals must be a non-empty array")
        return

    ids = set()
    for item in evals:
        if not isinstance(item, dict):
            errors.append("behavior eval entries must be objects")
            return
        eval_id = item.get("id")
        if not isinstance(eval_id, str) or not eval_id.strip():
            errors.append("behavior eval entries must have a non-empty string id")
            return
        if eval_id in ids:
            errors.append(f"duplicate behavior eval id: {eval_id}")
        else:
            ids.add(eval_id)
        if not isinstance(item.get("prompt"), str) or not item["prompt"].strip():
            errors.append(f"behavior eval {eval_id} must have a non-empty prompt")
        if not isinstance(item.get("expected_output"), str) or not item["expected_output"].strip():
            errors.append(f"behavior eval {eval_id} must have a non-empty expected_output")
        else:
            output = item["expected_output"].lower()
            semantics = BEHAVIOR_EXPECTED_OUTPUT_SEMANTICS.get(eval_id, {})
            missing_signals = sorted(
                signal for signal in semantics.get("all", ()) if signal not in output
            )
            if missing_signals:
                errors.append(
                    f"behavior eval {eval_id} expected_output missing required signals: "
                    + ", ".join(missing_signals)
                )
    missing = REQUIRED_BEHAVIOR_EVAL_IDS - ids
    if missing:
        errors.append(f"behavior-evals.json missing expected eval ids: {', '.join(sorted(missing))}")
    unknown = ids - REQUIRED_BEHAVIOR_EVAL_IDS
    if unknown:
        errors.append(f"behavior-evals.json has unknown behavior eval ids: {', '.join(sorted(unknown))}")


def validate_agent_context_routing(root: Path, errors: list[str]) -> None:
    path = root / "evals" / "agent-context-routing.json"
    if not path.exists():
        errors.append(f"missing eval file: {path}")
        return
    try:
        payload = json.loads(load_text(path))
    except json.JSONDecodeError as exc:
        errors.append(f"invalid JSON in {path}: {exc}")
        return

    if not isinstance(payload, dict):
        errors.append("agent-context-routing.json top-level value must be an object")
        return
    if payload.get("skill_name") != "goal":
        errors.append("agent-context-routing.json skill_name must be 'goal'")
    if payload.get("route") != "agent-context-review":
        errors.append("agent-context-routing.json route must be 'agent-context-review'")

    evals = payload.get("evals")
    if not isinstance(evals, list) or not evals:
        errors.append("agent-context-routing.json evals must be a non-empty array")
        return

    ids: set[str] = set()
    for item in evals:
        if not isinstance(item, dict):
            errors.append("Agent Context routing eval entries must be objects")
            return
        eval_id = item.get("id")
        if not isinstance(eval_id, str) or not eval_id.strip():
            errors.append("Agent Context routing eval entries must have a non-empty string id")
            continue
        if eval_id in ids:
            errors.append(f"duplicate Agent Context routing eval id: {eval_id}")
        else:
            ids.add(eval_id)
        if not isinstance(item.get("query"), str) or not item["query"].strip():
            errors.append(f"Agent Context routing eval {eval_id} must have a non-empty query")
        expected_should_route = AGENT_CONTEXT_ROUTE_EXPECTATIONS.get(eval_id)
        if expected_should_route is not None and item.get("should_route") is not expected_should_route:
            errors.append(
                f"Agent Context routing eval {eval_id} has the wrong should_route value"
            )

    missing = REQUIRED_AGENT_CONTEXT_ROUTE_IDS - ids
    if missing:
        errors.append(
            "agent-context-routing.json missing expected eval ids: "
            + ", ".join(sorted(missing))
        )
    unknown = ids - REQUIRED_AGENT_CONTEXT_ROUTE_IDS
    if unknown:
        errors.append(
            "agent-context-routing.json has unknown eval ids: "
            + ", ".join(sorted(unknown))
        )


def validate_agent_tool_routing(root: Path, errors: list[str]) -> None:
    path = root / "evals" / "agent-tool-contract-routing.json"
    if not path.exists():
        errors.append(f"missing eval file: {path}")
        return
    try:
        payload = json.loads(load_text(path))
    except json.JSONDecodeError as exc:
        errors.append(f"invalid JSON in {path}: {exc}")
        return

    if not isinstance(payload, dict):
        errors.append("agent-tool-contract-routing.json top-level value must be an object")
        return

    if payload.get("skill_name") != "goal":
        errors.append("agent-tool-contract-routing.json skill_name must be 'goal'")
    if payload.get("route") != "agent-tool-contract-review":
        errors.append("agent-tool-contract-routing.json route must be 'agent-tool-contract-review'")
    evals = payload.get("evals")
    if not isinstance(evals, list) or not evals:
        errors.append("agent-tool-contract-routing.json evals must be a non-empty array")
        return

    ids = set()
    for item in evals:
        if not isinstance(item, dict):
            errors.append("Agent Tool routing eval entries must be objects")
            return
        eval_id = item.get("id")
        if not isinstance(eval_id, str) or not eval_id.strip():
            errors.append("Agent Tool routing eval entries must have a non-empty string id")
            return
        if eval_id in ids:
            errors.append(f"duplicate Agent Tool routing eval id: {eval_id}")
            continue
        ids.add(eval_id)
        expected = AGENT_TOOL_ROUTE_EXPECTATIONS.get(eval_id)
        if expected is None:
            continue
        for field, expected_value in expected.items():
            if item.get(field) != expected_value:
                errors.append(
                    f"Agent Tool routing eval {eval_id} has the wrong {field} value"
                )

    missing = REQUIRED_AGENT_TOOL_ROUTE_IDS - ids
    if missing:
        errors.append(
            "agent-tool-contract-routing.json missing expected eval ids: "
            + ", ".join(sorted(missing))
        )
    unknown = ids - REQUIRED_AGENT_TOOL_ROUTE_IDS
    if unknown:
        errors.append(
            "agent-tool-contract-routing.json has unknown agent tool routing eval ids: "
            + ", ".join(sorted(unknown))
        )




def validate_global_agents(path: Path, errors: list[str]) -> None:
    if not path.exists():
        errors.append(f"missing global AGENTS.md: {path}")
        return
    text = load_text(path)
    for token in GLOBAL_AGENTS_TOKENS:
        if token not in text:
            errors.append(f"missing token in global AGENTS.md: {token}")
    if "- `Host mode:`" in text:
        errors.append("obsolete Goal Protocol v1 field in global AGENTS.md: Host mode")
    if text.count(GSD_ADAPTER_GLOBAL_PATH) != 1:
        errors.append(
            "global AGENTS.md must contain the GSD adapter path exactly once"
        )
    if GSD_ADAPTER_GLOBAL_POINTER not in text:
        errors.append("global AGENTS.md missing the deferred GSD adapter pointer")
    lowered = text.lower()
    for token in GLOBAL_AGENTS_FORBIDDEN_GSD_DETAILS:
        if token in lowered:
            errors.append(f"forbidden GSD detail in global AGENTS.md: {token}")


def main() -> int:
    arguments = sys.argv[1:]
    default_root = Path(__file__).resolve().parents[1]
    if not arguments:
        root = default_root
        global_agents = None
    elif len(arguments) == 1 and arguments[0] != "--global-agents":
        root = Path(arguments[0]).resolve()
        global_agents = None
    elif len(arguments) == 2 and arguments[0] == "--global-agents":
        root = default_root
        global_agents = Path(arguments[1]).resolve()
    elif len(arguments) == 3 and arguments[1] == "--global-agents":
        root = Path(arguments[0]).resolve()
        global_agents = Path(arguments[2]).resolve()
    else:
        print("Usage: python validate_goal_skill.py <skill_directory> [--global-agents <path>]")
        return 1

    errors: list[str] = []
    validate_package_boundaries(root, errors)
    contract = validate_protocol(root, errors)
    validate_skill_text(root, errors)
    validate_references(root, errors)
    validate_gsd_adapter(root, errors)
    if contract is not None:
        validate_output_contract(root, contract, errors)
    validate_capability_discovery(root, errors)
    validate_trigger_queries(root, errors)
    validate_behavior_evals(root, errors)
    validate_agent_context_routing(root, errors)
    validate_agent_tool_routing(root, errors)
    if global_agents is not None:
        validate_global_agents(global_agents, errors)

    if errors:
        print("\n".join(errors))
        return 1

    print("OK: goal skill structure present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
