from __future__ import annotations

import json
import sys
from pathlib import Path


ROUTE_MARKERS = (
    "## Agent Tool Contract Routing",
    "load `agent-tool-contract-review` after `/goal` classification and before the affected design, remediation, or acceptance work",
    "keep `/goal` responsible for project intake, Harness gates, state, and closure",
    "For MCP server implementation, load `mcp-builder` first.",
    "After the implementation surface exists, use `agent-tool-contract-review` for contract review, acceptance, and remediation planning",
    "Do not route ordinary REST controllers, internal service methods, a single existing Tool call, a one-off local fix, prompt examples, Skill path inspection, or a request to review the `/goal` Skill itself.",
)

EXPECTED_ROUTES = {
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


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[1])
    skill = (root / "SKILL.md").read_text(encoding="utf-8")
    missing = [marker for marker in ROUTE_MARKERS if marker not in skill]
    if missing:
        print("RED: missing Agent Tool routing markers: " + ", ".join(missing))
        return 1
    routing = json.loads((root / "evals" / "agent-tool-contract-routing.json").read_text(encoding="utf-8"))
    evals = routing.get("evals", [])
    by_id = {item.get("id"): item for item in evals if isinstance(item, dict)}
    missing_ids = set(EXPECTED_ROUTES) - set(by_id)
    if missing_ids:
        print("RED: missing Agent Tool routing eval ids: " + ", ".join(sorted(missing_ids)))
        return 1
    for eval_id, expected in EXPECTED_ROUTES.items():
        actual = by_id[eval_id]
        for field, expected_value in expected.items():
            if actual.get(field) != expected_value:
                print(f"RED: Agent Tool routing eval {eval_id} has the wrong {field} value")
                return 1
    print("PASS: agent-tool-contract-review routing contract is present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
