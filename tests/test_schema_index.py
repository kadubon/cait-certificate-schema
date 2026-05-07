from __future__ import annotations

import json
import tomllib
from pathlib import Path

from cait_schema.schema_loader import SCHEMA_DIR, infer_schema_name, load_schema_index, record_type_to_schema_file


def test_schema_index_matches_schema_files() -> None:
    index = load_schema_index()
    mapping = record_type_to_schema_file()
    assert index["json_schema_draft"] == "2020-12"
    assert index["record_type_key"] == "record_type"
    assert index["semantic_profile_id"]
    assert index["top_level_bundle"] == "cait.schema.json"
    assert index["semantic_rules_file"] == "semantic_rules.json"
    assert index["examples_directory"] == "examples"
    for record_type, file_name in mapping.items():
        assert record_type
        assert (SCHEMA_DIR / file_name).exists(), f"Missing schema file for {record_type}: {file_name}"


def test_schema_index_matches_top_level_bundle_refs() -> None:
    mapping = record_type_to_schema_file()
    bundle = json.loads((SCHEMA_DIR / "cait.schema.json").read_text(encoding="utf-8"))
    refs = {entry["$ref"] for entry in bundle["oneOf"]}
    assert set(mapping.values()) == refs


def test_schema_inference_uses_schema_index() -> None:
    assert infer_schema_name({"record_type": "arrival_record"}) == "arrival_record"


def test_wheel_configuration_includes_schema_resources() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    force_include = pyproject["tool"]["hatch"]["build"]["targets"]["wheel"]["force-include"]
    assert force_include["schemas/cait"] == "cait_schema/schemas/cait"
