from __future__ import annotations

import json
from pathlib import Path


def _load_catalog(catalog_path: Path, errors: list[str]) -> object | None:
    if not catalog_path.exists():
        errors.append(f"missing catalog: {catalog_path}")
        return None

    try:
        return json.loads(catalog_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError) as exc:
        errors.append(f"unable to read catalog {catalog_path}: {exc}")
        return None
    except json.JSONDecodeError as exc:
        errors.append(f"invalid catalog json in {catalog_path}: {exc}")
        return None


def _validate_required_any(
    invariant_id: str,
    document_path: str,
    required_any: object,
    errors: list[str],
) -> list[list[str]]:
    if not isinstance(required_any, list) or not required_any:
        errors.append(
            f"invariant {invariant_id} document {document_path} must define non-empty required_any"
        )
        return []

    groups: list[list[str]] = []
    for group_index, group in enumerate(required_any):
        if not isinstance(group, list) or not group:
            errors.append(
                f"invariant {invariant_id} document {document_path} required_any[{group_index}] "
                "must be a non-empty list"
            )
            continue
        tokens = [token for token in group if isinstance(token, str) and token.strip()]
        if len(tokens) != len(group):
            errors.append(
                f"invariant {invariant_id} document {document_path} required_any[{group_index}] "
                "must only contain non-empty strings"
            )
            continue
        groups.append(tokens)
    return groups


def _parse_invariants(catalog: object, errors: list[str]) -> list[dict[str, object]]:
    if not isinstance(catalog, dict):
        errors.append("catalog top-level value must be an object")
        return []

    if catalog.get("version") != 1:
        errors.append("catalog version must be 1")

    invariants = catalog.get("invariants")
    if not isinstance(invariants, list) or not invariants:
        errors.append("catalog invariants must be a non-empty list")
        return []

    parsed: list[dict[str, object]] = []
    seen_ids: set[str] = set()

    for index, invariant in enumerate(invariants):
        if not isinstance(invariant, dict):
            errors.append(f"invariant[{index}] must be an object")
            continue

        invariant_id = invariant.get("id")
        if not isinstance(invariant_id, str) or not invariant_id.strip():
            errors.append(f"invariant[{index}] must define a non-empty string id")
            continue
        if invariant_id in seen_ids:
            errors.append(f"duplicate invariant id: {invariant_id}")
            continue
        seen_ids.add(invariant_id)

        documents = invariant.get("documents")
        if not isinstance(documents, list) or not documents:
            errors.append(f"invariant {invariant_id} must define a non-empty documents list")
            continue

        parsed_documents: list[dict[str, object]] = []
        for doc_index, document in enumerate(documents):
            if not isinstance(document, dict):
                errors.append(f"invariant {invariant_id} document[{doc_index}] must be an object")
                continue

            relative_path = document.get("path")
            if not isinstance(relative_path, str) or not relative_path.strip():
                errors.append(
                    f"invariant {invariant_id} document[{doc_index}] must define a non-empty string path"
                )
                continue

            groups = _validate_required_any(
                invariant_id,
                relative_path,
                document.get("required_any"),
                errors,
            )
            if not groups:
                continue

            parsed_documents.append({"path": relative_path, "required_any": groups})

        if not parsed_documents:
            continue

        parsed.append({"id": invariant_id, "documents": parsed_documents})

    return parsed


def validate_contract_consistency(
    root: Path,
    catalog_path: Path | None = None,
) -> list[str]:
    root = root.resolve()
    if catalog_path is None:
        resolved_catalog_path = root / "evals" / "contract-invariants.json"
    elif catalog_path.is_absolute():
        resolved_catalog_path = catalog_path
    else:
        resolved_catalog_path = root / catalog_path
    catalog_path = resolved_catalog_path.resolve()
    errors: list[str] = []

    catalog = _load_catalog(catalog_path, errors)
    if catalog is None:
        return errors

    invariants = _parse_invariants(catalog, errors)
    if not invariants:
        return errors

    for invariant in invariants:
        invariant_id = invariant["id"]
        for document in invariant["documents"]:
            relative_path = document["path"]
            document_path = root / relative_path
            if not document_path.exists():
                errors.append(f"invariant {invariant_id} missing document: {relative_path}")
                continue

            try:
                content = document_path.read_text(encoding="utf-8").casefold()
            except (OSError, UnicodeDecodeError) as exc:
                errors.append(f"invariant {invariant_id} unable to read {relative_path}: {exc}")
                continue

            for group in document["required_any"]:
                if any(token.casefold() in content for token in group):
                    continue
                errors.append(
                    f"invariant {invariant_id} missing required terms in {relative_path}: "
                    + " | ".join(group)
                )

    return errors