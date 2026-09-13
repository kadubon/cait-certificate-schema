"""Deterministic synthetic histories constructed by the real admission/replay path."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from .numeric import digest
from .source import envelope, registration

Json = dict[str, Any]
NAMES = (
    "positive",
    "external",
    "unresolved",
    "multi-parent",
    "costly",
    "censored-expiry",
    "correction",
    "model-resource",
    "matrix-boundary",
    "inconsistent",
    "interchange",
)
A, B, CHILD = (digest(x) for x in ("parent-a", "parent-b", "child"))


def seal(c: Json, events: list[Json], evidence: list[Json], models: list[Json] | None = None) -> Json:
    """Create fixture source envelopes; never used to repair user inputs on admission."""
    c, events, evidence, models = deepcopy((c, events, evidence, models or []))
    for stream in c["streams"]:
        rows = [e for e in events if e["stream"] == stream["id"]]
        stream["first"], stream["last"] = 1, len(rows)
    reg = registration(c)
    wrapped = []
    for stream in c["streams"]:
        previous = stream["checkpoint"]
        rows = sorted((e for e in events if e["stream"] == stream["id"]), key=lambda e: (e["time"], e["id"]))
        for sequence, row in enumerate(rows, 1):
            row.update(
                contract=reg, previous=previous, sequence=sequence, scope=c["scope"], episode=c["episode"]
            )
            item = envelope(row)
            wrapped.append(item)
            previous = item["sha256"]
        stream["terminal"] = previous
    for model in models:
        model["contract"] = reg
    return dict(
        record_type="cait_source_bundle_v1",
        contract=c,
        events=wrapped,
        evidence=[envelope(e) for e in evidence],
        models=[envelope(m) for m in models],
    )


def event(eid: str, kind: str, time: int, data: Json, **extra: Any) -> Json:
    return dict(
        id=eid,
        kind=kind,
        time=time,
        recorded=time,
        arm="candidate",
        stream="journal",
        study="holdout",
        dependencies=[],
        evidence=[],
        costs=[],
        data=data,
        **extra,
    )


def fixture_parts() -> tuple[Json, list[Json], list[Json], list[Json]]:
    receiver = dict(
        id="receiver-1",
        context="finite-task",
        task="task-1",
        evaluator="evaluator-v1",
        protocol="holdout-v1",
        checks=["exact-check"],
    )
    c = dict(
        record_type="cait_computation_contract_v1",
        scope="synthetic",
        episode="episode-1",
        study="holdout",
        time_unit="registered-tick",
        start=0,
        end=10,
        cutoff=12,
        checkpoint_time=0,
        basis="synthetic",
        interpretation="as_of",
        coordinates=[
            dict(id="assets", unit="qualified-artifact", meaning="asset_stock"),
            dict(id="service", unit="qualified-task", meaning="service_outcome"),
        ],
        receivers=[receiver, {**receiver, "id": "receiver-2"}],
        arms=["candidate"],
        scenarios=["joint-a"],
        opening=[
            dict(artifact=a, coordinate="assets", arm="candidate", quantity={"joint-a": "1"}, expires=100)
            for a in (A, B)
        ],
        streams=[
            dict(
                id="journal",
                arm="candidate",
                checkpoint=digest("genesis"),
                first=1,
                last=0,
                terminal=digest("genesis"),
            )
        ],
        mandatory_events=["cost-formation", "create-child", "reuse-child"],
        mandatory_costs=["physical-1"],
        negative_terms_complete=True,
        allocations={},
        cost_units=["work-hour"],
        resource_limits={"work-hour": {"joint-a": "100"}},
        valuation=dict(version="valuation-v1", target="assets", rates={"work-hour": {"joint-a": "1"}}),
        operation_budget=100000,
        policy="disjoint-origin-v1:content-dedup:propagate-revocation:half-open",
    )
    cost = event(
        "cost-formation",
        "cost",
        0,
        dict(cost_id="physical-1", unit="work-hour", quantity={"joint-a": "1"}, stage="formation"),
    )
    creation = event(
        "create-child",
        "create",
        1,
        dict(
            artifact=CHILD,
            coordinate="assets",
            quantity={"joint-a": "5"},
            shares=dict(endogenous="1", external="0", unresolved="0"),
            parents=[A, B],
            parent_shares={A: "1/2", B: "1/2"},
            expires=100,
        ),
    )
    creation.update(evidence=["check-creation"], costs=["physical-1"])
    reuse = event(
        "reuse-child",
        "use",
        2,
        dict(
            artifact=CHILD,
            coordinate="service",
            quantity={"joint-a": "1"},
            receiver="receiver-1",
            context="finite-task",
            task="task-1",
            input=digest("input"),
            evaluator="evaluator-v1",
            protocol="holdout-v1",
            outcome="success",
        ),
    )
    reuse.update(evidence=["check-creation"], dependencies=["create-child"], costs=["physical-1"])
    ev = dict(
        id="check-creation",
        scope="synthetic",
        arm="candidate",
        artifact=CHILD,
        receiver="receiver-1",
        context="finite-task",
        evaluator="evaluator-v1",
        protocol="holdout-v1",
        check="exact-check",
        outcome="pass",
        valid_from=0,
        valid_until=100,
        dependencies=[],
        blocking_defeaters=[],
        cost_ids=["physical-1"],
    )
    model = dict(
        record_type="cait_reproduction_model_v1",
        scope="synthetic",
        episode="episode-1",
        contract="0" * 64,
        types=["qualified-artifact"],
        orientation="rows-child-columns-parent",
        kind="expected_offspring",
        interpretation="births_only",
        exposure="registered-parent-cohort",
        time_basis="generation",
        retention="parents-excluded",
        external_boundary="external-offspring-excluded",
        valid_from=0,
        valid_until=10,
        evidence_basis="synthetic",
        sources=["create-child"],
        family=[dict(lower=[["2"]], upper=[["3"]])],
        complete=True,
        lower_witness=dict(vector=["1"], bound="2", block=[]),
        upper_witness=None,
        iterations=3,
    )
    return c, [cost, creation, reuse], [ev], [model]


def example(name: str = "positive") -> Json:
    if name not in NAMES:
        raise ValueError("Unknown example: " + name)
    c, events, evidence, models = fixture_parts()
    if name == "external":
        events[1]["data"]["shares"] = dict(endogenous="0", external="1", unresolved="0")
    elif name == "unresolved":
        events[1]["data"]["shares"] = dict(endogenous="1/4", external="1/4", unresolved="1/2")
    elif name in {"multi-parent", "interchange"}:
        use = deepcopy(events[2])
        use.update(id="reuse-receiver-2", time=3, recorded=3, evidence=["check-receiver-2"])
        use["data"]["receiver"] = "receiver-2"
        events.append(use)
        evidence.append({**evidence[0], "id": "check-receiver-2", "receiver": "receiver-2"})
    elif name in {"costly", "model-resource"}:
        if name == "model-resource":
            c["resource_limits"]["work-hour"]["joint-a"] = "4"
        events.extend(
            [
                event(
                    "cost-transfer",
                    "cost",
                    3,
                    dict(cost_id="physical-2", unit="work-hour", quantity={"joint-a": "3"}, stage="transfer"),
                ),
                event(
                    "cost-maintenance",
                    "cost",
                    4,
                    dict(
                        cost_id="physical-3", unit="work-hour", quantity={"joint-a": "3"}, stage="maintenance"
                    ),
                ),
            ]
        )
        c["mandatory_costs"].extend(["physical-2", "physical-3"])
    elif name == "censored-expiry":
        events[1]["data"]["expires"] = 3
        events[2]["data"]["outcome"] = "censored"
    elif name == "correction":
        c["interpretation"] = "corrected"
        correction = event(
            "correct-child",
            "correct",
            5,
            dict(target="create-child", quantity={"joint-a": "2"}, reason="measurement-correction"),
        )
        correction["dependencies"] = ["create-child"]
        events.append(correction)
    elif name == "matrix-boundary":
        models[0]["family"] = [dict(lower=[["1"]], upper=[["1"]])]
        models[0]["lower_witness"] = None
    elif name == "inconsistent":
        evidence[0]["dependencies"] = ["check-creation"]
    return seal(c, events, evidence, models)
