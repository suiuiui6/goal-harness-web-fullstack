import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "render_delivery_reference.py"


def load_tool():
    spec = importlib.util.spec_from_file_location("render_delivery_reference", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_rendered_field_table_comes_from_contract_constants():
    module = load_tool()
    rendered = module.render_generated_reference()
    assert "schema_version" in rendered
    assert "web-fullstack" in rendered
    assert "2048" in rendered
    assert "2 MiB" in rendered


def test_update_preserves_manual_text_and_check_detects_drift(tmp_path):
    module = load_tool()
    target = tmp_path / "delivery-contract.md"
    target.write_text("# Manual\n\nKeep this text.\n", encoding="utf-8")
    module.update_reference(target)
    assert "Keep this text." in target.read_text(encoding="utf-8")
    assert module.reference_is_current(target)
    target.write_text(target.read_text(encoding="utf-8").replace("2048", "2047"), encoding="utf-8")
    assert not module.reference_is_current(target)
