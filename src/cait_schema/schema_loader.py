from __future__ import annotations

import json
from contextlib import ExitStack
from importlib import resources
from functools import lru_cache
from pathlib import Path
from typing import Any

from referencing import Registry, Resource


REPO_ROOT = Path(__file__).resolve().parents[2]
_REPO_SCHEMA_DIR = REPO_ROOT / "schemas" / "cait"
_RESOURCE_STACK = ExitStack()


def _resolve_schema_dir() -> Path:
    if (_REPO_SCHEMA_DIR / "schema_index.json").exists():
        return _REPO_SCHEMA_DIR

    package_schema_dir = resources.files("cait_schema").joinpath("schemas", "cait")
    if package_schema_dir.joinpath("schema_index.json").is_file():
        return Path(_RESOURCE_STACK.enter_context(resources.as_file(package_schema_dir)))

    raise FileNotFoundError("Could not locate CAIT schemas in the repository or installed package resources.")


SCHEMA_DIR = _resolve_schema_dir()
SCHEMA_INDEX_PATH = SCHEMA_DIR / "schema_index.json"
SEMANTIC_RULES_PATH = SCHEMA_DIR / "semantic_rules.json"


@lru_cache(maxsize=1)
def load_schema_index() -> dict[str, Any]:
    return json.loads(SCHEMA_INDEX_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def record_type_to_schema_file() -> dict[str, str]:
    return dict(load_schema_index()["record_types"])


def schema_name_to_file(schema_name: str) -> str:
    if schema_name.endswith(".schema.json"):
        return schema_name
    if schema_name in record_type_to_schema_file():
        return record_type_to_schema_file()[schema_name]
    return f"{schema_name}.schema.json"


def schema_path(schema_name: str) -> Path:
    return SCHEMA_DIR / schema_name_to_file(schema_name)


def known_schema_names() -> list[str]:
    return sorted(record_type_to_schema_file())


def load_schema(schema_name: str) -> dict[str, Any]:
    path = schema_path(schema_name)
    if not path.exists():
        known = ", ".join(known_schema_names())
        raise ValueError(f"Unknown schema '{schema_name}'. Known schemas: {known}")
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_registry() -> Registry:
    pairs = []
    for path in SCHEMA_DIR.glob("*.schema.json"):
        schema = json.loads(path.read_text(encoding="utf-8"))
        pairs.append((schema["$id"], Resource.from_contents(schema)))
    return Registry().with_resources(pairs)


@lru_cache(maxsize=1)
def load_semantic_rules() -> dict[str, Any]:
    return json.loads(SEMANTIC_RULES_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def semantic_rule_by_id() -> dict[str, dict[str, Any]]:
    return {rule["rule_id"]: rule for rule in load_semantic_rules()["rules"]}


def infer_schema_name(instance: dict[str, Any]) -> str:
    record_type = instance.get("record_type")
    if not isinstance(record_type, str):
        raise ValueError("Cannot infer schema: top-level 'record_type' is missing or not a string.")
    mapping = record_type_to_schema_file()
    if record_type not in mapping:
        known = ", ".join(sorted(mapping))
        raise ValueError(f"Unknown record_type '{record_type}'. Known record types: {known}")
    return record_type
