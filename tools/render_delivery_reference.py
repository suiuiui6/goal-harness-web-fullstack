import argparse
import importlib.util
from pathlib import Path
import sys


START = "<!-- GENERATED DELIVERY FIELDS START -->"
END = "<!-- GENERATED DELIVERY FIELDS END -->"


def _contract_module(root=None):
    workspace = Path(root or Path(__file__).resolve().parents[1]).resolve()
    path = workspace / "source" / "goal-enforcement" / "scripts" / "delivery_contract.py"
    spec = importlib.util.spec_from_file_location("candidate_delivery_contract", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def render_generated_reference(root=None):
    contract = _contract_module(root)
    statuses = ", ".join(f"`{value}`" for value in sorted(contract.CRITERION_STATUSES))
    targets = ", ".join(f"`{value}`" for value in sorted(contract.DELIVERY_TARGETS))
    applicability = ", ".join(f"`{value}`" for value in sorted(contract.APPLICABILITY))
    return f"""## Generated field contract

The optional outer `delivery` value uses `schema_version=1` and
`profile=web-fullstack`. Its closed sections are `contract`, `slices`,
`criteria`, `evidence`, and `invalidations`.

| Constraint | Value |
| --- | --- |
| delivery target | {targets} |
| surface applicability | {applicability} |
| criterion status | {statuses} |
| slices | at most {contract.MAX_SLICES} |
| criteria | at most {contract.MAX_CRITERIA} |
| evidence | at most {contract.MAX_EVIDENCE} |
| invalidations | at most {contract.MAX_INVALIDATIONS} |
| canonical UTF-8 JSON | at most 2 MiB ({contract.MAX_DELIVERY_BYTES} bytes) |

The exact nested required fields and machine validation remain authoritative in
`source/goal-enforcement/scripts/delivery_contract.py`.
"""


def _block(root=None):
    return f"{START}\n{render_generated_reference(root).rstrip()}\n{END}"


def update_reference(path, root=None):
    path = Path(path)
    generated = _block(root)
    if path.exists():
        text = path.read_text(encoding="utf-8")
    else:
        text = "# Web Full-Stack Delivery Contract\n"
    if START in text and END in text:
        prefix, rest = text.split(START, 1)
        _, suffix = rest.split(END, 1)
        updated = prefix.rstrip() + "\n\n" + generated + suffix
    else:
        updated = text.rstrip() + "\n\n" + generated + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(updated, encoding="utf-8")


def reference_is_current(path, root=None):
    path = Path(path)
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8")
    if text.count(START) != 1 or text.count(END) != 1:
        return False
    return text.split(START, 1)[1].split(END, 1)[0].strip() == render_generated_reference(root).strip()


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    target = root / "source" / "goal" / "references" / "delivery-contract.md"
    if args.check:
        if not reference_is_current(target, root):
            print(f"generated delivery reference is stale: {target}", file=sys.stderr)
            return 1
        print("PASS: generated delivery reference is current")
        return 0
    update_reference(target, root)
    print(f"WROTE: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
