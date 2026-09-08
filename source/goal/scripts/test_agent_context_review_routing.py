from __future__ import annotations

import json
import sys
from pathlib import Path


ROUTE_MARKERS = (
    "agent-context-review",
    "Agent history",
    "RAG context",
    "tool outputs",
    "context-window budgets",
    "session isolation",
    "side-effect confirmation",
)


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[1])
    skill = (root / "SKILL.md").read_text(encoding="utf-8")
    missing = [marker for marker in ROUTE_MARKERS if marker not in skill]
    if missing:
        print("RED: missing routing markers: " + ", ".join(missing))
        return 1
    routing = json.loads((root / "evals" / "agent-context-routing.json").read_text(encoding="utf-8"))
    required = {"agent-context-review", "ordinary-crud", "skill-meta", "quoted-goal"}
    ids = {item.get("id") for item in routing.get("evals", [])}
    missing_ids = required - ids
    if missing_ids:
        print("RED: missing routing eval ids: " + ", ".join(sorted(missing_ids)))
        return 1
    print("PASS: agent-context-review routing contract is present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
