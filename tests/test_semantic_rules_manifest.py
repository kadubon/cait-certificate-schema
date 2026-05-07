from __future__ import annotations

from cait_schema.schema_loader import load_semantic_rules, semantic_rule_by_id
from cait_schema.validator import validate_file


def test_semantic_rules_manifest_has_unique_rule_ids() -> None:
    manifest = load_semantic_rules()
    rules = manifest["rules"]
    rule_ids = [rule["rule_id"] for rule in rules]
    assert len(rule_ids) == len(set(rule_ids))
    for rule in rules:
        assert rule["severity"] in {"error", "warning"}
        assert rule["description"]
        assert rule["record_types"]
        assert rule["primary_paths"]
        assert rule["portable_logic"]


def test_validator_returns_registered_rule_ids() -> None:
    result = validate_file("examples/invalid/arrival_with_nonpositive_queue_margin.json")
    rule_ids = {issue.rule_id for issue in result.issues}
    assert "passing_arrival_requires_positive_queue_margin" in rule_ids
    known_rule_ids = set(semantic_rule_by_id())
    assert rule_ids <= known_rule_ids
