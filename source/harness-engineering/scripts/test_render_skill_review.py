from pathlib import Path
import shutil
import subprocess
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

from render_skill_review import build_review


SCRIPT_DIR = Path(__file__).resolve().parent
BUNDLE_ROOT = SCRIPT_DIR.parent


class RenderSkillReviewTests(unittest.TestCase):
    def copy_bundle(self, destination: Path) -> Path:
        target = destination / "harness-engineering"
        shutil.copytree(
            BUNDLE_ROOT,
            target,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        return target

    def test_missing_live_responses_are_rendered_as_not_run(self):
        report, errors = build_review(
            BUNDLE_ROOT,
            generated_at="2026-07-12T00:00:00Z",
        )
        self.assertEqual([], errors)
        self.assertIn("Overall behavior status: `not-run`", report)
        self.assertIn("codex-explicit-invocation", report)
        self.assertNotIn("pass/fail", report)

    def test_missing_benchmark_is_reported_without_becoming_a_failure(self):
        missing = BUNDLE_ROOT / "evals" / "missing-benchmark.json"
        report, errors = build_review(
            BUNDLE_ROOT,
            benchmark_path=missing,
            generated_at="2026-07-12T00:00:00Z",
        )
        self.assertTrue(any("benchmark" in error for error in errors), errors)
        self.assertIn("External benchmark: `not-run`", report)

    def test_renderer_cli_does_not_generate_python_cache(self):
        with tempfile.TemporaryDirectory(dir=BUNDLE_ROOT.parent) as temp_dir:
            root = self.copy_bundle(Path(temp_dir))
            output_path = root / "docs" / "reviews" / "smoke-review.md"
            result = subprocess.run(
                [
                    sys.executable,
                    str(root / "scripts" / "render_skill_review.py"),
                    str(root),
                    "--output",
                    str(output_path),
                ],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertFalse((root / "scripts" / "__pycache__").exists())
            self.assertTrue(output_path.is_file())


if __name__ == "__main__":
    unittest.main()
