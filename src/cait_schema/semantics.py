from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cait_schema.schema_loader import semantic_rule_by_id


@dataclass(frozen=True)
class ValidationIssue:
    rule_id: str
    severity: str
    description: str
    record_types: list[str]
    message: str
    path: str = "$"
    kind: str = "semantic"

    def format(self) -> str:
        return f"{self.kind} error [{self.rule_id}] at {self.path}: {self.message}"


def make_issue(rule_id: str, message: str, path: str = "$", kind: str = "semantic") -> ValidationIssue:
    rule = semantic_rule_by_id().get(rule_id)
    if rule is None:
        return ValidationIssue(
            rule_id=rule_id,
            severity="error",
            description="Unregistered validation rule.",
            record_types=["*"],
            message=message,
            path=path,
            kind=kind,
        )
    return ValidationIssue(
        rule_id=rule_id,
        severity=rule["severity"],
        description=rule["description"],
        record_types=list(rule["record_types"]),
        message=message,
        path=path,
        kind=kind,
    )


def semantic_issues_for(instance: dict[str, Any]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    _check_intervals(instance, path="$", issues=issues)

    record_type = instance.get("record_type")
    if record_type == "arrival_record":
        issues.extend(_arrival_issues(instance))
        issues.extend(_arrival_consistency_issues(instance))
    if record_type == "certificate_record":
        issues.extend(_certificate_issues(instance))
    if record_type == "token_record":
        issues.extend(_token_issues(instance))
    issues.extend(_target_boundary_issues(instance))
    return issues


def _check_intervals(value: Any, path: str, issues: list[ValidationIssue]) -> None:
    if isinstance(value, dict):
        if {"lower", "upper"}.issubset(value) and isinstance(value["lower"], (int, float)) and isinstance(value["upper"], (int, float)):
            if value["lower"] > value["upper"]:
                issues.append(
                    make_issue(
                        "interval_lower_leq_upper",
                        "interval.lower must be <= interval.upper.",
                        path=path,
                    )
                )
        for key, child in value.items():
            _check_intervals(child, f"{path}.{key}", issues)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _check_intervals(child, f"{path}[{index}]", issues)


def _arrival_issues(instance: dict[str, Any]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if instance.get("final_decision") != "pass":
        return issues

    growth = instance.get("endogenous_net_growth_interval", {})
    if growth.get("lower", 0) <= 0:
        issues.append(
            make_issue(
                "passing_arrival_requires_positive_endogenous_net_growth",
                "passing arrival_record requires endogenous_net_growth_interval.lower > 0.",
                path="$.endogenous_net_growth_interval.lower",
            )
        )

    queue_margin = instance.get("queue_margin", {})
    if queue_margin.get("lower", 0) <= 0:
        issues.append(
            make_issue(
                "passing_arrival_requires_positive_queue_margin",
                "passing arrival_record requires queue_margin.lower > 0.",
                path="$.queue_margin.lower",
            )
        )

    if instance.get("mandatory_subcertificates_status") != "accepted":
        issues.append(
            make_issue(
                "passing_arrival_requires_accepted_mandatory_subcertificates",
                "passing arrival_record requires mandatory_subcertificates_status = accepted.",
                path="$.mandatory_subcertificates_status",
            )
        )

    if not instance.get("mandatory_subcertificate_ids"):
        issues.append(
            make_issue(
                "passing_arrival_requires_mandatory_subcertificate_links",
                "passing arrival_record requires at least one mandatory_subcertificate_id.",
                path="$.mandatory_subcertificate_ids",
            )
        )

    for index, defeater in enumerate(instance.get("target_defeaters", [])):
        if defeater.get("severity") in {"high", "blocking"} and defeater.get("resolution_status") == "unresolved":
            defeater_id = defeater.get("defeater_id", "<unknown>")
            issues.append(
                make_issue(
                    "passing_arrival_blocks_unresolved_high_defeaters",
                    f"passing arrival_record has unresolved high/blocking target defeater '{defeater_id}'.",
                    path=f"$.target_defeaters[{index}]",
                )
            )

    thresholds = instance.get("acceptance_thresholds", {})
    external_share = instance.get("external_injection_share")
    max_external_share = thresholds.get("max_external_injection_share")
    if _numbers_present(external_share, max_external_share) and external_share > max_external_share:
        issues.append(
            make_issue(
                "passing_arrival_respects_external_injection_threshold",
                "passing arrival_record requires external_injection_share <= acceptance_thresholds.max_external_injection_share.",
                path="$.external_injection_share",
            )
        )

    unresolved_share = instance.get("unresolved_attribution_share")
    max_unresolved_share = thresholds.get("max_unresolved_attribution_share")
    if _numbers_present(unresolved_share, max_unresolved_share) and unresolved_share > max_unresolved_share:
        issues.append(
            make_issue(
                "passing_arrival_respects_unresolved_attribution_threshold",
                "passing arrival_record requires unresolved_attribution_share <= acceptance_thresholds.max_unresolved_attribution_share.",
                path="$.unresolved_attribution_share",
            )
        )

    transfer_coverage = instance.get("transfer_coverage")
    min_transfer_coverage = thresholds.get("min_transfer_coverage")
    if _numbers_present(transfer_coverage, min_transfer_coverage) and transfer_coverage < min_transfer_coverage:
        issues.append(
            make_issue(
                "passing_arrival_respects_transfer_coverage_threshold",
                "passing arrival_record requires transfer_coverage >= acceptance_thresholds.min_transfer_coverage.",
                path="$.transfer_coverage",
            )
        )

    audit_freshness = instance.get("operational_metrics", {}).get("audit_freshness")
    if audit_freshness != "pass":
        issues.append(
            make_issue(
                "passing_arrival_requires_fresh_audit",
                "passing arrival_record requires operational_metrics.audit_freshness = pass.",
                path="$.operational_metrics.audit_freshness",
            )
        )

    residual_upper = instance.get("operational_metrics", {}).get("residual_risk", {}).get("upper")
    max_residual_upper = thresholds.get("max_residual_risk_upper")
    if _numbers_present(residual_upper, max_residual_upper) and residual_upper > max_residual_upper:
        issues.append(
            make_issue(
                "passing_arrival_respects_residual_risk_threshold",
                "passing arrival_record requires operational_metrics.residual_risk.upper <= acceptance_thresholds.max_residual_risk_upper.",
                path="$.operational_metrics.residual_risk.upper",
            )
        )

    for field in ["safety_control_status", "transfer_status", "evaluation_status", "window_balance_status"]:
        if instance.get(field) != "pass":
            issues.append(
                make_issue(
                    "passing_arrival_requires_passed_boundary_statuses",
                    f"passing arrival_record requires {field} = pass.",
                    path=f"$.{field}",
                )
            )

    return issues


def _arrival_consistency_issues(instance: dict[str, Any]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    metrics = instance.get("operational_metrics", {})
    for field in ["external_injection_share", "unresolved_attribution_share", "transfer_coverage"]:
        top_level = instance.get(field)
        metric_value = metrics.get(field)
        if _numbers_present(top_level, metric_value) and top_level != metric_value:
            issues.append(
                make_issue(
                    "arrival_operational_metrics_match_top_level_shares",
                    f"top-level {field} must match operational_metrics.{field}.",
                    path=f"$.operational_metrics.{field}",
                )
            )
    return issues


def _certificate_issues(instance: dict[str, Any]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    status = instance.get("lifecycle_status")
    effect = instance.get("positive_capital_effect")
    if status != "accepted" and effect == "full":
        issues.append(
            make_issue(
                "nonaccepted_lifecycle_cannot_claim_full_capital",
                "only accepted certificate_record lifecycle status can claim full positive capital effect.",
                path="$.positive_capital_effect",
            )
        )
    if instance.get("claimed_strengthening") and not instance.get("strengthening_witness"):
        issues.append(
            make_issue(
                "evidence_strengthening_requires_witness",
                "evidence mode strengthening requires an explicit strengthening_witness.",
                path="$.strengthening_witness",
            )
        )
    if instance.get("domain_witness_required") and effect in {"full", "discounted_and_scoped"}:
        witness = instance.get("domain_witness")
        if not _domain_witness_flags_pass(witness):
            issues.append(
                make_issue(
                    "positive_claim_requires_domain_witness",
                    "positive certificate claim requires a valid domain_witness.",
                    path="$.domain_witness",
                )
            )
    return issues


def _token_issues(instance: dict[str, Any]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    status = instance.get("lifecycle_status")
    effect = instance.get("positive_capital_effect")
    if status != "accepted" and effect == "full":
        issues.append(
            make_issue(
                "nonaccepted_lifecycle_cannot_claim_full_capital",
                "only accepted token_record lifecycle status can claim full positive capital effect.",
                path="$.positive_capital_effect",
            )
        )
    return issues


def _target_boundary_issues(instance: dict[str, Any]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for index, item in enumerate(instance.get("target_coordinate_statuses", [])):
        if isinstance(item, dict) and item.get("within_boundary") is False:
            if item.get("status") != "abstained_or_uncertified":
                issues.append(
                    make_issue(
                        "outside_boundary_coordinates_must_abstain",
                        "outside-boundary coordinates must be abstained_or_uncertified.",
                        path=f"$.target_coordinate_statuses[{index}]",
                    )
                )
    return issues


def _domain_witness_flags_pass(witness: Any) -> bool:
    if not isinstance(witness, dict):
        return False
    required = [
        "compatible_scope",
        "accepted_dependencies",
        "valid_budget",
        "fresh_evidence",
        "no_open_blocking_defeater",
        "disjoint_support",
    ]
    return all(witness.get(key) is True for key in required)


def _numbers_present(*values: Any) -> bool:
    return all(isinstance(value, (int, float)) for value in values)
