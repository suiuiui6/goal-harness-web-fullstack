from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_public_project_contract_is_complete():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for token in ("Quick start", "python -m goal_harness", "audit-only-windows", "not-run", "CONTRIBUTING.md", "MIT"):
        assert token in readme
    for path in ("LICENSE", "CHANGELOG.md", "CONTRIBUTING.md", "SECURITY.md", "pyproject.toml", ".github/workflows/ci.yml"):
        assert (ROOT / path).is_file()
