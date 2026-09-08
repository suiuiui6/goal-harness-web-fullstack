import argparse
import json
from pathlib import Path
import sys


STAGES = {"A": 0, "B": 1, "C": 2, "D": 3}


def validate(root: Path, manifest_path: Path, stage: str) -> list[str]:
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        return [f"invalid ownership manifest: {error}"]
    rules = data.get("rules") if isinstance(data, dict) else None
    if data.get("schema_version") != 1 or not isinstance(rules, list):
        return ["ownership manifest requires schema_version=1 and a rules array"]
    errors = []
    by_id = {}
    for index, rule in enumerate(rules):
        prefix = f"rules[{index}]"
        if not isinstance(rule, dict):
            errors.append(f"{prefix} must be an object")
            continue
        rule_id = rule.get("rule_id")
        if not isinstance(rule_id, str) or not rule_id.strip():
            errors.append(f"{prefix}.rule_id must be non-empty")
            continue
        if rule_id in by_id:
            errors.append(f"duplicate rule_id: {rule_id}")
        by_id[rule_id] = rule
        required_from = rule.get("required_from")
        if required_from not in STAGES:
            errors.append(f"{rule_id}: invalid required_from")
            continue
        if STAGES[required_from] <= STAGES[stage]:
            paths = [rule.get("canonical"), *(rule.get("consumers") or [])]
            for relative in paths:
                if not isinstance(relative, str) or not relative:
                    errors.append(f"{rule_id}: invalid required path")
                    continue
                path = Path(relative)
                if path.is_absolute() or ".." in path.parts:
                    errors.append(f"{rule_id}: path escapes workspace: {relative}")
                elif not (root / path).is_file():
                    errors.append(f"{rule_id}: missing required path: {relative}")
    visiting = set()
    visited = set()

    def visit(rule_id):
        if rule_id in visiting:
            errors.append(f"dependency cycle includes {rule_id}")
            return
        if rule_id in visited or rule_id not in by_id:
            return
        visiting.add(rule_id)
        dependencies = by_id[rule_id].get("depends_on", [])
        if not isinstance(dependencies, list):
            errors.append(f"{rule_id}: depends_on must be an array")
        else:
            for dependency in dependencies:
                if dependency not in by_id:
                    errors.append(f"{rule_id}: unknown dependency {dependency}")
                else:
                    visit(dependency)
        visiting.remove(rule_id)
        visited.add(rule_id)

    for rule_id in by_id:
        visit(rule_id)
    return sorted(set(errors))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--stage", choices=tuple(STAGES), default="D")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    manifest = (args.manifest or root / "tools" / "rule-ownership.json").resolve()
    errors = validate(root, manifest, args.stage)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print(f"PASS: {len(json.loads(manifest.read_text(encoding='utf-8'))['rules'])} rule owners valid at stage {args.stage}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
