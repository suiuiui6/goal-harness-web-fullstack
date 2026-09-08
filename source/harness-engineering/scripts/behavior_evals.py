import json
import re
from pathlib import Path


EVAL_FILES = (
    "codex-behavior-evals.json",
    "claude-behavior-evals.json",
)
ASCII_TOKEN_PATTERN = re.compile(r"[0-9a-z_]+(?:'[0-9a-z_]+)?")
CJK_PATTERN = re.compile(r"[\u3400-\u9fff]")
NEGATION_TOKENS = {
    "not",
    "no",
    "never",
    "without",
    "cannot",
    "can't",
    "don't",
    "doesn't",
    "didn't",
    "isn't",
    "aren't",
    "wasn't",
    "weren't",
    "won't",
    "wouldn't",
    "shouldn't",
    "mustn't",
}
CHINESE_NEGATION_PREFIXES = (
    "不需要",
    "不应",
    "不需",
    "禁止",
    "不能",
    "没有",
    "无需",
    "不要",
    "不是",
    "未",
    "没",
    "不",
    "无",
)
NEGATION_SUFFIX_GAP_PATTERN = re.compile(r"[\s\u3000:：,，、]*$")
CHINESE_NEGATION_PATTERN = re.compile(
    rf"(?:{'|'.join(map(re.escape, CHINESE_NEGATION_PREFIXES))})(?:[\u3400-\u9fff]\s*){{0,8}}$"
)


def _load_json(path: Path, errors: list[str], label: str) -> object | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        errors.append(f"missing {label}: {path}")
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"invalid {label} {path}: {exc}")
    return None


def _is_non_empty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_string_list(value: object) -> bool:
    return isinstance(value, list) and all(_is_non_empty_string(item) for item in value)


def _validate_expectation(expectation: object, label: str, errors: list[str]) -> bool:
    if not isinstance(expectation, dict):
        errors.append(f"{label} expectation must be an object")
        return False
    if not _is_non_empty_string(expectation.get("text")):
        errors.append(f"{label} expectation must contain text")
        return False
    for field in ("all", "any", "none"):
        if not _is_string_list(expectation.get(field)):
            errors.append(f"{label} expectation {field} must be a string list")
            return False
    return True


def _is_negated(tokens: list[str], start_index: int) -> bool:
    window_start = max(0, start_index - 3)
    return any(token in NEGATION_TOKENS for token in tokens[window_start:start_index])


def _is_text_negated(response_text: str, start_index: int) -> bool:
    context = response_text[:start_index]
    prefix_context = NEGATION_SUFFIX_GAP_PATTERN.sub("", context)
    if CHINESE_NEGATION_PATTERN.search(prefix_context):
        return True

    context_tokens = ASCII_TOKEN_PATTERN.findall(context)
    return bool(context_tokens) and context_tokens[-1] in NEGATION_TOKENS


def _matches_ascii_term(response_text: str, response_tokens: list[str], term: str) -> bool:
    term_tokens = ASCII_TOKEN_PATTERN.findall(term.casefold())
    if not term_tokens:
        return False

    token_spans = [match.span() for match in ASCII_TOKEN_PATTERN.finditer(response_text)]
    limit = len(response_tokens) - len(term_tokens) + 1
    for start_index in range(max(0, limit)):
        if response_tokens[start_index : start_index + len(term_tokens)] != term_tokens:
            continue
        if not _is_negated(response_tokens, start_index) and not _is_text_negated(
            response_text, token_spans[start_index][0]
        ):
            return True
    return False


def _matches_term(folded_response: str, response_tokens: list[str], term: str) -> bool:
    folded_term = term.casefold().strip()
    if not folded_term:
        return False
    if CJK_PATTERN.search(folded_term):
        start_index = folded_response.find(folded_term)
        while start_index != -1:
            if not _is_text_negated(folded_response, start_index):
                return True
            start_index = folded_response.find(folded_term, start_index + 1)
        return False
    if ASCII_TOKEN_PATTERN.search(folded_term):
        return _matches_ascii_term(folded_response, response_tokens, folded_term)
    return folded_term in folded_response


def load_eval_definitions(root: Path) -> tuple[list[dict], list[str]]:
    definitions: list[dict] = []
    errors: list[str] = []
    seen_ids: set[int] = set()
    seen_names: set[str] = set()

    for filename in EVAL_FILES:
        data = _load_json(root / "evals" / filename, errors, "behavior eval file")
        if not isinstance(data, dict):
            continue

        if data.get("skill_name") != "harness-engineering":
            errors.append(f"{filename} must name the harness-engineering skill")
            continue

        host = data.get("host")
        if not _is_non_empty_string(host):
            errors.append(f"{filename} must have non-empty host")
            continue

        evals = data.get("evals")
        if not isinstance(evals, list):
            errors.append(f"{filename} must contain an evals list")
            continue

        for index, item in enumerate(evals):
            label = f"{filename} eval[{index}]"
            if not isinstance(item, dict):
                errors.append(f"{label} must be an object")
                continue

            eval_id = item.get("id")
            name = item.get("name")
            prompt = item.get("prompt")
            expected_output = item.get("expected_output")
            files = item.get("files")
            expectations = item.get("expectations")

            if type(eval_id) is not int:
                errors.append(f"{label} must have integer id")
                continue
            if not _is_non_empty_string(name):
                errors.append(f"{label} must have non-empty name")
                continue
            if eval_id in seen_ids:
                errors.append(f"duplicate behavior eval id: {eval_id}")
                continue
            if name in seen_names:
                errors.append(f"duplicate behavior eval name: {name}")
                continue
            if not _is_non_empty_string(prompt) or not _is_non_empty_string(expected_output):
                errors.append(f"{label} must have prompt and expected_output")
                continue
            if not isinstance(files, list) or not all(isinstance(path, str) for path in files):
                errors.append(f"{label} files must be a string list")
                continue
            if not isinstance(expectations, list) or not expectations:
                errors.append(f"{label} must have non-empty expectations")
                continue

            if not all(_validate_expectation(expectation, label, errors) for expectation in expectations):
                continue

            seen_ids.add(eval_id)
            seen_names.add(name)
            definitions.append({**item, "host": host})

    return definitions, errors


def grade_response(eval_definition: dict, response_text: str | None) -> dict:
    if response_text is None:
        return {
            "eval_id": eval_definition["id"],
            "eval_name": eval_definition["name"],
            "host": eval_definition["host"],
            "status": "not-run",
            "expectations": [],
            "summary": {"passed": 0, "failed": 0, "total": 0, "pass_rate": None},
        }

    folded = response_text.casefold()
    response_tokens = ASCII_TOKEN_PATTERN.findall(folded)
    graded_expectations: list[dict] = []
    for expectation in eval_definition["expectations"]:
        missing_all = [
            term
            for term in expectation["all"]
            if not _matches_term(folded, response_tokens, term)
        ]
        matched_any = [
            term
            for term in expectation["any"]
            if _matches_term(folded, response_tokens, term)
        ]
        forbidden = [
            term
            for term in expectation["none"]
            if _matches_term(folded, response_tokens, term)
        ]
        any_ok = not expectation["any"] or bool(matched_any)
        passed = not missing_all and any_ok and not forbidden

        evidence_parts: list[str] = []
        if not missing_all and any_ok:
            evidence_parts.append("matched required terms")
        if missing_all:
            evidence_parts.append(f"missing required terms: {missing_all}")
        if not any_ok:
            evidence_parts.append(f"matched none of: {expectation['any']}")
        if forbidden:
            evidence_parts.append(f"forbidden terms present: {forbidden}")

        graded_expectations.append(
            {
                "text": expectation["text"],
                "passed": passed,
                "evidence": "; ".join(evidence_parts),
            }
        )

    passed_count = sum(1 for expectation in graded_expectations if expectation["passed"])
    total = len(graded_expectations)
    failed_count = total - passed_count
    return {
        "eval_id": eval_definition["id"],
        "eval_name": eval_definition["name"],
        "host": eval_definition["host"],
        "status": "pass" if failed_count == 0 else "fail",
        "expectations": graded_expectations,
        "summary": {
            "passed": passed_count,
            "failed": failed_count,
            "total": total,
            "pass_rate": passed_count / total if total else None,
        },
    }


def load_recorded_responses(manifest_path: Path | None) -> tuple[dict[int, dict], list[str]]:
    if manifest_path is None:
        return {}, []

    errors: list[str] = []
    data = _load_json(manifest_path, errors, "recorded response manifest")
    if not isinstance(data, dict) or not isinstance(data.get("responses"), list):
        errors.append("recorded response manifest must contain a responses list")
        return {}, errors

    responses: dict[int, dict] = {}
    for index, item in enumerate(data["responses"]):
        label = f"recorded response[{index}]"
        if not isinstance(item, dict) or type(item.get("eval_id")) is not int:
            errors.append(f"{label} must have integer eval_id")
            continue

        eval_id = item["eval_id"]
        if eval_id in responses:
            errors.append(f"duplicate recorded response eval_id: {eval_id}")
            continue

        response_path = item.get("response_path")
        if not _is_non_empty_string(response_path):
            errors.append(f"recorded response {eval_id} must have response_path")
            continue

        resolved_path = (manifest_path.parent / response_path).resolve()
        if not resolved_path.is_file():
            errors.append(f"recorded response {eval_id} missing file: {resolved_path}")
            continue

        responses[eval_id] = {**item, "resolved_path": resolved_path}

    return responses, errors
