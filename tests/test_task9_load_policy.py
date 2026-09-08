import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "source" / "harness-engineering"


def test_load_policy_has_closed_shape_and_delivery_routes():
    path = HARNESS / "references" / "load-policy.json"
    assert path.exists()
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert set(payload) == {"version", "stages", "routes"}
    assert payload["version"] == 1
    assert set(payload["stages"]) == {
        "classification", "handoff", "before_mutation", "gate", "rollback",
        "specialist", "closure",
    }
    ids = set()
    for route in payload["routes"]:
        assert set(route) == {"id", "stage", "trigger", "reads", "must_precede", "excludes"}
        assert route["id"] not in ids
        ids.add(route["id"])
        assert route["stage"] in payload["stages"]
        assert isinstance(route["reads"], list)
        assert isinstance(route["must_precede"], list)
        assert isinstance(route["excludes"], list)
    assert "web-fullstack-delivery" in ids


def test_domain_routing_and_runtime_stages_reference_policy():
    routing = (HARNESS / "references" / "domain-routing.md").read_text(encoding="utf-8")
    runtime = (HARNESS / "references" / "runtime-stages.md").read_text(encoding="utf-8")
    assert "load-policy.json" in routing
    assert "web-fullstack-delivery" in routing
    assert "load-policy.json" in runtime
