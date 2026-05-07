from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from cait_schema.schema_loader import infer_schema_name, load_registry, load_schema
from cait_schema.semantics import ValidationIssue, make_issue, semantic_issues_for


@dataclass(frozen=True)
class ValidationResult:
    file_path: str | None
    schema_name: str
    structural_valid: bool
    semantic_valid: bool
    issues: list[ValidationIssue]

    @property
    def valid(self) -> bool:
        return self.structural_valid and self.semantic_valid

    @property
    def errors(self) -> list[str]:
        return [issue.format() for issue in self.issues]


def validate_instance(
    instance: dict[str, Any],
    schema_name: str | None = None,
    file_path: str | None = None,
) -> ValidationResult:
    resolved_schema_name = schema_name or infer_schema_name(instance)
    schema = load_schema(resolved_schema_name)
    registry = load_registry()
    validator = Draft202012Validator(schema, registry=registry)

    structural_issues = [
        _schema_issue(error)
        for error in sorted(validator.iter_errors(instance), key=lambda e: list(e.path))
    ]
    semantic_issues = semantic_issues_for(instance)
    return ValidationResult(
        file_path=file_path,
        schema_name=resolved_schema_name,
        structural_valid=not structural_issues,
        semantic_valid=not semantic_issues,
        issues=structural_issues + semantic_issues,
    )


def validate_file(path: str | Path, schema_name: str | None = None) -> ValidationResult:
    json_path = Path(path)
    instance = json.loads(json_path.read_text(encoding="utf-8"))
    if not isinstance(instance, dict):
        return ValidationResult(
            file_path=str(json_path),
            schema_name=schema_name or "<unknown>",
            structural_valid=False,
            semantic_valid=False,
            issues=[
                make_issue(
                    "json_schema_structural_validation",
                    "Top-level JSON value must be an object.",
                    path="$",
                    kind="structural",
                )
            ],
        )
    return validate_instance(instance, schema_name=schema_name, file_path=str(json_path))


def _schema_issue(error: Any) -> ValidationIssue:
    path = "$"
    if error.path:
        path += "." + ".".join(str(part) for part in error.path)
    return make_issue(
        "json_schema_structural_validation",
        error.message,
        path=path,
        kind="structural",
    )
