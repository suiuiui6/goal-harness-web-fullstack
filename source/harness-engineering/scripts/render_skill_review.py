import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True

from behavior_evals import grade_response, load_eval_definitions, load_recorded_responses
from contract_consistency import validate_contract_consistency


REVIEW_DATE = "2026-07-12"


def _benchmark_summary(path: Path | None) -> tuple[list[str], list[str]]:
    if path is None:
        return ["External benchmark: `not-run`"], []
    if not path.is_file():
        return ["External benchmark: `not-run`"], [f"missing benchmark: {path}"]

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        metadata = data["metadata"]
        summary = data["run_summary"]
        with_skill = summary["with_skill"]["pass_rate"]["mean"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        return ["External benchmark: `fail`"], [f"invalid benchmark {path}: {exc}"]

    return [
        "External benchmark: `pass`",
        f"- Evidence: `{path}`",
        f"- Model: `{metadata.get('executor_model', 'unknown')}`",
        f"- With-skill mean pass rate: `{with_skill}`",
    ], []


def _behavior_status(grades: list[dict]) -> str:
    if not grades:
        return "not-run"
    if any(grade["status"] == "fail" for grade in grades):
        return "fail"
    if all(grade["status"] == "pass" for grade in grades):
        return "pass"
    return "not-run"


def build_review(
    root: Path,
    response_manifest: Path | None = None,
    benchmark_path: Path | None = None,
    generated_at: str | None = None,
) -> tuple[str, list[str]]:
    root = root.resolve()
    generated_at = generated_at or datetime.now(timezone.utc).isoformat()

    invariant_errors = validate_contract_consistency(root)
    definitions, definition_errors = load_eval_definitions(root)
    responses, response_errors = load_recorded_responses(response_manifest)
    errors = [*invariant_errors, *definition_errors, *response_errors]

    grades: list[dict] = []
    for definition in definitions:
        recorded = responses.get(definition["id"])
        response_text = None
        evidence_path = None
        if recorded is not None:
            evidence_path = recorded["resolved_path"]
            try:
                response_text = evidence_path.read_text(encoding="utf-8")
            except OSError as exc:
                errors.append(f"invalid recorded response {evidence_path}: {exc}")
                evidence_path = None
        grade = grade_response(definition, response_text)
        grade["evidence_path"] = evidence_path
        grades.append(grade)

    behavior_status = _behavior_status(grades)
    benchmark_lines, benchmark_errors = _benchmark_summary(benchmark_path)
    errors.extend(benchmark_errors)

    lines = [
        f"# Harness Engineering Skill Review Log - {REVIEW_DATE}",
        "",
        f"Generated at: `{generated_at}`",
        "",
        "## Bundle Quality Gate",
        "",
        f"Contract consistency: `{'pass' if not invariant_errors else 'fail'}`",
        f"Eval definition schema: `{'pass' if not definition_errors else 'fail'}`",
        "",
        "## Recorded Host Behavior",
        "",
        f"Overall behavior status: `{behavior_status}`",
        "",
    ]
    for grade in grades:
        lines.append(f"### {grade['eval_name']}")
        lines.append("")
        lines.append(f"- Host: `{grade['host']}`")
        lines.append(f"- Status: `{grade['status']}`")
        if grade["evidence_path"] is not None:
            lines.append(f"- Evidence: `{grade['evidence_path']}`")
        else:
            lines.append("- Evidence: recorded response not supplied")
        for expectation in grade["expectations"]:
            status = "pass" if expectation["passed"] else "fail"
            lines.append(f"- `{status}` {expectation['text']}: {expectation['evidence']}")
        lines.append("")

    lines.extend(["## Imported External Benchmark", "", *benchmark_lines, ""])
    if errors:
        lines.extend(["## Validation Errors", ""])
        lines.extend(f"- {error}" for error in errors)
        lines.append("")
    return "\n".join(lines), errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("bundle_root", type=Path)
    parser.add_argument("--responses", type=Path)
    parser.add_argument("--benchmark", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report, errors = build_review(
        args.bundle_root,
        response_manifest=args.responses,
        benchmark_path=args.benchmark,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report + "\n", encoding="utf-8")
    print(f"Wrote {args.output}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
