import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PluginContractTests(unittest.TestCase):
    def test_default_audit_prompt_requires_workspace_resolution(self):
        manifest = json.loads(
            (ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        prompts = manifest["interface"]["defaultPrompt"]
        self.assertTrue(
            any("Resolve the intended project workspace first" in prompt for prompt in prompts)
        )
        self.assertTrue(
            any("ask me for the workspace path" in prompt for prompt in prompts)
        )

    def test_skill_refuses_ambiguous_drive_root_audit(self):
        skill = (
            ROOT / "skills" / "goal-enforcement" / "SKILL.md"
        ).read_text(encoding="utf-8")
        for token in (
            "## Resolve Workspace Before Audit",
            "Never audit a drive root",
            "ask the user for the intended workspace path",
        ):
            with self.subTest(token=token):
                self.assertIn(token, skill)


if __name__ == "__main__":
    unittest.main()
