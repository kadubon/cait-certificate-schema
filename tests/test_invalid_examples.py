from __future__ import annotations

from pathlib import Path

from cait_schema.validator import validate_file


EXPECTED_RULE_IDS = {
    "arrival_external_share_above_threshold.json": {"passing_arrival_respects_external_injection_threshold"},
    "arrival_missing_audit_freshness.json": {"passing_arrival_requires_fresh_audit"},
    "arrival_missing_subcertificate_links.json": {"passing_arrival_requires_mandatory_subcertificate_links"},
    "arrival_operational_metrics_mismatch.json": {"arrival_operational_metrics_match_top_level_shares"},
    "arrival_residual_risk_above_threshold.json": {"passing_arrival_respects_residual_risk_threshold"},
    "arrival_transfer_coverage_below_threshold.json": {"passing_arrival_respects_transfer_coverage_threshold"},
    "arrival_unresolved_share_above_threshold.json": {"passing_arrival_respects_unresolved_attribution_threshold"},
    "arrival_with_nonpositive_queue_margin.json": {"passing_arrival_requires_positive_queue_margin"},
    "arrival_with_unresolved_high_defeater.json": {"passing_arrival_blocks_unresolved_high_defeaters"},
    "conditional_certificate_claims_full_capital.json": {"nonaccepted_lifecycle_cannot_claim_full_capital"},
    "interval_lower_greater_than_upper.json": {"interval_lower_leq_upper"},
    "invalid_lifecycle_status.json": {"json_schema_structural_validation"},
    "missing_required_status.json": {"json_schema_structural_validation"},
    "nonaccepted_certificate_claims_full_capital.json": {"nonaccepted_lifecycle_cannot_claim_full_capital"},
    "outside_boundary_coordinate_not_abstained.json": {"outside_boundary_coordinates_must_abstain"},
    "positive_claim_without_witness.json": {
        "evidence_strengthening_requires_witness",
        "positive_claim_requires_domain_witness",
    },
}


def test_invalid_examples_fail_with_expected_rule_ids() -> None:
    for file_name, expected_rule_ids in EXPECTED_RULE_IDS.items():
        path = f"examples/invalid/{file_name}"
        result = validate_file(path)
        assert not result.valid, f"{path} should be invalid."
        assert result.errors, f"{path} should report at least one error."
        actual_rule_ids = {issue.rule_id for issue in result.issues}
        assert expected_rule_ids <= actual_rule_ids


def test_every_invalid_example_has_expected_rule_ids() -> None:
    file_names = {path.name for path in Path("examples/invalid").glob("*.json")}
    assert file_names == set(EXPECTED_RULE_IDS)
