"""Pinned released JSON interfaces; imported fields never acquire new authority."""

from __future__ import annotations

import json
from importlib.resources import files
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from .checker import check_report
from .numeric import digest, rational, require

Json = dict[str, Any]


def companion(name: str) -> Json:
    allowed = {
        "vek-capacity-report.schema.json",
        "vek-report-positive.json",
        "vek-report-negative.json",
        "ccr-task.schema.json",
        "ccr-task.json",
        "ccr-phase-observation.schema.json",
        "manifest.json",
    }
    require(name in allowed, "companion", "Unknown pinned resource")
    return dict(
        json.loads(
            files("cait_schema.accounting")
            .joinpath("fixtures", "companions", name)
            .read_text(encoding="utf-8")
        )
    )


def validate_companion(record: Json, schema: str) -> None:
    validator = Draft202012Validator(companion(schema), format_checker=FormatChecker())
    error = next(validator.iter_errors(record), None)
    require(error is None, "companion_schema", error.message if error else "")


def import_vek(record: Json, *, scope: str, source_digest: str) -> Json:
    validate_companion(record, "vek-capacity-report.schema.json")
    require(
        record["producer_version"] == "1.3.0"
        and record["scope"] == scope
        and record["source_digest"] == source_digest,
        "vek_binding",
        "Unsupported version or source scope",
    )
    require(
        record["observed_service"] is None and record["service_guaranteed_lower_envelope"] is None,
        "vek_promotion",
        "Pinned profile supplies no observed or guaranteed service adapter",
        "unknown",
    )
    require(
        record["evidence_basis"] in {"synthetic", "declared-model"},
        "vek_basis",
        "Unsupported basis",
        "unknown",
    )
    seconds = rational(record["slot_seconds"])
    require(seconds > 0 and 0 < record["horizon"] <= 16, "vek_horizon", "Invalid finite horizon")
    ids = [w["work_id"] for w in record["work"]]
    require(len(ids) == len(set(ids)), "vek_work", "Duplicated work IDs")
    local = record["local_accounting"]
    require(
        local["completed"] + local["unfinished"] == len(ids), "vek_conservation", "Work accounting mismatch"
    )
    require(
        len(local["consumed"]) == len(record["resources"]), "vek_resources", "Resource dimension mismatch"
    )
    return dict(
        record_type="cait_vek_capacity_import_v1",
        source_digest=source_digest,
        report_digest=digest(record),
        producer_version="1.3.0",
        scope=scope,
        checkpoint_revision=record["snapshot_revision"],
        contract_digest=record["contract_digest"],
        horizon_seconds=str(seconds * record["horizon"]),
        time_origin=record["time_origin"],
        work_unit=record["work_unit"],
        offered=len(ids),
        completed=local["completed"],
        due=sum(w["required"] and w["deadline"] <= record["horizon"] for w in record["work"]),
        unfinished=local["unfinished"],
        repair=local["repair"],
        pending_followups=record["pending_followup_work"],
        resources=record["resources"],
        consumed=local["consumed"],
        evidence_basis=record["evidence_basis"],
        forecast=record["forecast"],
        measured_rate=None,
        guaranteed_service=None,
        independent_errors=None,
        authentication=None,
        authority=None,
        missing=[
            "source journal not included: counters remain VEK supplied",
            "cross-scope valuation not inferred",
        ],
    )


def import_ccr_task(record: Json) -> Json:
    validate_companion(record, "ccr-task.schema.json")
    return dict(
        record_type="cait_ccr_task_import_v1",
        source_version="CCR-1.8.0/ccr.task.v0.1",
        source_digest=digest(record),
        task_id=record["task_id"],
        status=record["status"],
        input_refs=record["inputs"],
        dependencies=record.get("dependencies", []),
        accounting=None,
        authority=None,
        missing=[
            "run/arm/holdout identity",
            "physical cost-event IDs",
            "source journal completeness",
            "qualified receiver outcomes",
        ],
    )


def export_ccr(bundle: Json, report: Json, *, created_at: str) -> Json:
    require(
        check_report(bundle, report)["status"] == "checked",
        "unchecked_report",
        "Report must pass independent reconstruction",
    )
    task = companion("ccr-task.json")
    task.update(
        task_id="task.cait." + digest(report)[:24],
        created_at=created_at,
        role="verifier",
        priority=50,
        title="Review scoped CAIT accounting obligations",
        objective="Resolve the declared evidence obligations; preserve unresolved costs and attribution.",
        inputs=[],
        dependencies=[],
        completion={},
        blackboard_refs=[],
    )
    task["verifier_plan"] = dict(
        required_verifiers=[], optional_verifiers=[], promotion_gate="custom", failure_route="residual"
    )
    task["pic_interop"].update(enabled=False, recommended_pic_commands=[])
    task["expected_outputs"] = [
        dict(
            kind="json",
            schema_ref="cait_report_check_v1",
            destination="derived",
            acceptance_criteria=[
                "Independent source replay",
                "Receiver and physical cost binding",
                "No authority promotion",
            ],
        )
    ]
    task["extensions"] = {
        "x_cait_growth_window_report_v1": report,
        "x_source_bundle_digest": digest(bundle),
        "x_missing_registry_binding": True,
        "x_task_hint_only": True,
    }
    validate_companion(task, "ccr-task.schema.json")
    return dict(
        record_type="cait_ccr_accounting_sidecar_v1",
        report=report,
        proposal=task,
        verifier_work_obligations=report["residuals"],
        source_digest=digest(bundle),
        settlement=None,
        reward=None,
        authority=None,
    )


def legacy_partition(record: Json) -> Json:
    """No automatic sum of overlapping legacy injection/input/output categories."""
    from cait_schema.validator import validate_instance

    require(validate_instance(record).valid, "legacy_invalid", "Legacy input does not validate")
    return dict(
        status="unsupported",
        source_digest=digest(record),
        accounting=None,
        reason="Legacy supplied totals/flags lack a disjoint source-event partition",
        authority=None,
    )


def integration(bundle: Json, report: Json, vek_report: Json, ccr_task: Json, *, created_at: str) -> Json:
    """Bind the independently checked native report to specifically imported sidecars.

    No implicit cross-scope merge, costs, rates, or attribution are invented.
    """
    exported = export_ccr(bundle, report, created_at=created_at)
    capacity = import_vek(vek_report, scope=vek_report["scope"], source_digest=vek_report["source_digest"])
    task = import_ccr_task(ccr_task)
    return dict(
        record_type="cait_interchange_evidence_v1",
        native=exported,
        verification_capacity=capacity,
        ccr_source=task,
        bindings=dict(bundle=digest(bundle), vek=digest(vek_report), ccr=digest(ccr_task)),
        cross_scope_mapping="unestablished",
        joint_capacity=None,
        arrival_verdict=None,
        authority=None,
    )
