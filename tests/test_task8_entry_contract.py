from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GOAL = ROOT / "source" / "goal"
HARNESS = ROOT / "source" / "harness-engineering"


def test_goal_and_harness_entries_share_web_fullstack_scope_without_upgrading_local_api():
    goal = (GOAL / "SKILL.md").read_text(encoding="utf-8")
    harness = (HARNESS / "SKILL.md").read_text(encoding="utf-8")
    assert "Web full-stack" in goal
    assert "Web full-stack" in harness
    assert "local API" in goal


def test_capability_discovery_routes_legacy_and_delivery_feature_branches():
    text = (GOAL / "references" / "capability-discovery.md").read_text(encoding="utf-8")
    assert "legacy" in text.lower()
    assert "delivery_feature_available" in text
    assert "CAPABILITY_DISABLED" in text
    assert "web-fullstack-delivery-v1" in text
    assert "initialize-state" in text


def test_host_modes_documents_delivery_cas_handoff():
    text = (GOAL / "references" / "host-modes.md").read_text(encoding="utf-8")
    assert "--expected-state-sha256" in text
    assert "raw state" in text.lower() or "原始 state" in text
    assert "re-read" in text.lower() or "重读" in text


def test_behavior_change_record_exists_with_review_sources():
    path = ROOT / "docs" / "superpowers" / "reviews" / "2026-09-08-web-fullstack-behavior-changes.md"
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    for marker in ("Task 8", "user review", "capability-discovery", "legacy"):
        assert marker.lower() in text.lower()
