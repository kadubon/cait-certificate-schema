from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema.validators import validator_for

from cait_schema.schema_loader import SCHEMA_DIR, load_registry


def test_all_schema_files_are_valid_json_and_have_metadata() -> None:
    schema_paths = sorted(SCHEMA_DIR.glob("*.schema.json"))
    assert schema_paths, "No schema files found."
    for path in schema_paths:
        schema = json.loads(path.read_text(encoding="utf-8"))
        assert schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema"
        assert schema.get("$id")
        assert schema.get("title")
        assert schema.get("type") == "object"
        validator_cls = validator_for(schema)
        validator_cls.check_schema(schema)


def test_local_ref_resolution_works_for_examples() -> None:
    registry = load_registry()
    schema = json.loads((SCHEMA_DIR / "arrival_record.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, registry=registry)
    example_path = Path("examples/valid/arrival_record.json")
    instance = json.loads(example_path.read_text(encoding="utf-8"))
    assert list(validator.iter_errors(instance)) == []
