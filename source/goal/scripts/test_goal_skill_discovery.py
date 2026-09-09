#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import unittest
from pathlib import Path


SKILLS_ROOT = Path(
    os.environ.get("GOAL_TEST_SKILLS_ROOT", Path.home() / ".codex" / "skills")
).resolve()
EXPECTED_GOAL_SKILL = (SKILLS_ROOT / "goal" / "SKILL.md").resolve()
GOAL_FRONTMATTER = re.compile(r"(?mi)^name:\s*goal\s*$")


def is_goal_skill(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return False
    return bool(GOAL_FRONTMATTER.search(text))


class GoalSkillDiscoveryTests(unittest.TestCase):
    def test_goal_skill_is_discoverable_from_a_single_package_path(self) -> None:
        matches = sorted(
            path.resolve()
            for path in SKILLS_ROOT.rglob("SKILL.md")
            if is_goal_skill(path)
        )
        self.assertEqual(
            [EXPECTED_GOAL_SKILL],
            matches,
            f"expected only {EXPECTED_GOAL_SKILL}, found {matches}",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
