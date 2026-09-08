from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_fixture_assets_and_runner_exist():
    for path in ("fixtures/web-notes/server.py", "fixtures/web-notes/index.html", "fixtures/web-notes/README.md", "tools/run_fullstack_fixture.py"):
        assert (ROOT / path).exists()

def test_fixture_declares_auth_persistence_and_local_bind():
    text = (ROOT / "fixtures/web-notes/server.py").read_text(encoding="utf-8")
    for marker in ("127.0.0.1", "sqlite3", "401", "/api/notes"):
        assert marker in text
