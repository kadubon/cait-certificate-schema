"""Closed language-neutral v1 profile; generators serialize these definitions."""

from __future__ import annotations

from typing import Any

from jsonschema import Draft202012Validator

from .numeric import bounded, require

Json = dict[str, Any]
ID = {"type": "string", "pattern": "^[A-Za-z0-9_.:-]{1,80}$"}
HASH = {"type": "string", "pattern": "^[a-f0-9]{64}$"}
Q = {"type": "string", "maxLength": 81, "pattern": "^-?(0|[1-9][0-9]*)(/[1-9][0-9]*)?$"}
TIME = {"type": "integer", "minimum": 0, "maximum": 1000000}


def enum(*values: str) -> Json:
    return {"enum": list(values)}


def obj(**fields: Any) -> Json:
    return {"type": "object", "properties": fields, "required": list(fields), "additionalProperties": False}


def arr(item: Json, maximum: int = 256, minimum: int = 0) -> Json:
    return {"type": "array", "items": item, "maxItems": maximum, "minItems": minimum}


def mapping(item: Json, maximum: int = 16) -> Json:
    return {"type": "object", "propertyNames": ID, "additionalProperties": item, "maxProperties": maximum}


AMOUNT = mapping(Q, 8)
PARTITION = obj(endogenous=Q, external=Q, unresolved=Q)
COORD = obj(id=ID, unit=ID, meaning=enum("asset_stock", "service_outcome", "coverage"))
RECEIVER = obj(id=ID, context=ID, task=ID, evaluator=ID, protocol=ID, checks=arr(ID, 16, 1))
OPENING = obj(artifact=HASH, coordinate=ID, arm=ID, quantity=AMOUNT, expires=TIME)
STREAM = obj(id=ID, arm=ID, checkpoint=HASH, first=TIME, last=TIME, terminal=HASH)
CONTRACT = obj(
    record_type={"const": "cait_computation_contract_v1"},
    scope=ID,
    episode=ID,
    study=ID,
    start=TIME,
    end=TIME,
    cutoff=TIME,
    checkpoint_time=TIME,
    basis=enum("synthetic", "declared-record"),
    interpretation=enum("as_of", "corrected"),
    coordinates=arr(COORD, 8, 1),
    receivers=arr(RECEIVER, 16, 1),
    arms=arr(ID, 8, 1),
    scenarios=arr(ID, 8, 1),
    opening=arr(OPENING, 64),
    streams=arr(STREAM, 8, 1),
    mandatory_events=arr(ID),
    mandatory_costs=arr(ID),
    negative_terms_complete={"type": "boolean"},
    allocations=mapping(mapping(Q, 8), 256),
    cost_units=arr(ID, 8),
    resource_limits=mapping(AMOUNT, 8),
    valuation=obj(version=ID, target=ID, rates=mapping(AMOUNT, 8)),
    operation_budget={"type": "integer", "minimum": 1, "maximum": 100000},
    policy={"const": "disjoint-origin-v1:content-dedup:propagate-revocation:half-open"},
)
EVIDENCE = obj(
    id=ID,
    scope=ID,
    arm=ID,
    artifact=HASH,
    receiver=ID,
    context=ID,
    evaluator=ID,
    protocol=ID,
    check=ID,
    outcome=enum("pass", "fail", "unknown"),
    valid_from=TIME,
    valid_until=TIME,
    dependencies=arr(ID, 16),
    blocking_defeaters=arr(ID, 16),
    cost_ids=arr(ID, 16),
)
DATA = {
    "create": obj(
        artifact=HASH,
        coordinate=ID,
        quantity=AMOUNT,
        shares=PARTITION,
        parents=arr(HASH, 16),
        parent_shares=mapping(Q),
        expires=TIME,
    ),
    "use": obj(
        artifact=HASH,
        coordinate=ID,
        quantity=AMOUNT,
        receiver=ID,
        context=ID,
        task=ID,
        input=HASH,
        evaluator=ID,
        protocol=ID,
        outcome=enum("success", "failure", "rejection", "timeout", "pending", "censored"),
    ),
    "cost": obj(
        cost_id=ID,
        unit=ID,
        quantity=AMOUNT,
        stage=enum("formation", "execution", "transfer", "validation", "refresh", "maintenance", "repair"),
    ),
    "withdraw": obj(artifact=HASH, reason=ID),
    "expire": obj(artifact=HASH, reason=ID),
    "repair": obj(artifact=HASH, reason=ID),
    "revalidate": obj(artifact=HASH, expires=TIME, reason=ID),
    "correct": obj(target=ID, quantity=AMOUNT, reason=ID),
    "resolve_use": obj(
        target=ID, quantity=AMOUNT, outcome=enum("success", "failure", "rejection", "timeout"), reason=ID
    ),
    "external_input": obj(artifact=HASH, kind=enum("model", "data", "tool", "human"), cost_ids=arr(ID, 16)),
}
EVENT = {
    "oneOf": [
        obj(
            id=ID,
            scope=ID,
            episode=ID,
            contract=HASH,
            stream=ID,
            sequence=TIME,
            previous=HASH,
            time=TIME,
            recorded=TIME,
            arm=ID,
            study=ID,
            kind={"const": kind},
            dependencies=arr(ID, 16),
            evidence=arr(ID, 16),
            costs=arr(ID, 16),
            data=data,
        )
        for kind, data in DATA.items()
    ]
}
ENVELOPE = obj(sha256=HASH, content={"type": "string", "maxLength": 100000})
BUNDLE = obj(
    record_type={"const": "cait_source_bundle_v1"},
    contract=CONTRACT,
    events=arr(ENVELOPE),
    evidence=arr(ENVELOPE),
    models=arr(ENVELOPE, 8),
)
MATRIX = arr(arr(Q, 8, 1), 8, 1)
WITNESS = obj(vector=arr(Q, 8, 1), bound=Q, block=arr(TIME, 8))
MODEL = obj(
    record_type={"const": "cait_reproduction_model_v1"},
    scope=ID,
    episode=ID,
    contract=HASH,
    types=arr(ID, 8, 1),
    orientation={"const": "rows-child-columns-parent"},
    kind=enum("expected_offspring", "uniform_pathwise", "time_varying", "local_jacobian"),
    interpretation=enum("births_only", "total_next_state"),
    exposure=ID,
    time_basis=enum("generation", "elapsed_time"),
    retention=ID,
    external_boundary=ID,
    valid_from=TIME,
    valid_until=TIME,
    evidence_basis=enum("declared-model", "synthetic"),
    sources=arr(ID, 16),
    family=arr(obj(lower=MATRIX, upper={"anyOf": [MATRIX, {"type": "null"}]}), 8, 1),
    complete={"type": "boolean"},
    lower_witness={"anyOf": [WITNESS, {"type": "null"}]},
    upper_witness={"anyOf": [WITNESS, {"type": "null"}]},
    iterations=TIME,
)
SCHEMAS = {"contract": CONTRACT, "event": EVENT, "evidence": EVIDENCE, "bundle": BUNDLE, "model": MODEL}

NULL_Q = {"anyOf": [Q, {"type": "null"}]}
MODEL_RESULT = obj(
    record_type={"const": "cait_reproduction_check_v1"},
    model_digest=HASH,
    classification=enum("supercritical", "subcritical", "unknown"),
    kind=MODEL["properties"]["kind"],
    interpretation=MODEL["properties"]["interpretation"],
    lower=NULL_Q,
    upper=NULL_Q,
    uniform_pathwise_factor=NULL_Q,
    residuals=arr({"type": "string"}),
    basis={"const": "declared mathematical premise"},
    empirical_growth={"type": "null"},
    authority={"type": "null"},
)
BALANCE = obj(
    scenario=ID,
    arm=ID,
    coordinate=ID,
    unit=ID,
    meaning=COORD["properties"]["meaning"],
    opening=Q,
    closing=Q,
    endogenous=Q,
    external=Q,
    unresolved=Q,
    losses=Q,
    service=Q,
    gross=Q,
    costs=mapping(Q, 8),
    valued_cost=NULL_Q,
    declared_net=NULL_Q,
    external_share=NULL_Q,
    unresolved_share=NULL_Q,
)
TRACE = obj(
    scenario=ID,
    journal=arr(
        obj(
            time=TIME,
            arm=ID,
            coordinate=ID,
            term=enum("initial", "endogenous", "external", "unresolved", "losses", "service"),
            quantity=Q,
            source={"type": "string"},
        ),
        4096,
    ),
    costs=arr(
        obj(time=TIME, arm=ID, unit=ID, stage=DATA["cost"]["properties"]["stage"], cost_id=ID, quantity=Q),
        4096,
    ),
    uses=arr(
        obj(
            event=ID,
            arm=ID,
            receiver=ID,
            outcome=DATA["use"]["properties"]["outcome"],
            qualified={"type": "boolean"},
            time=TIME,
        )
    ),
    residuals=arr({"type": "string"}, 4096),
    resource_checks=arr(
        obj(unit=ID, consumed=Q, limit=NULL_Q, status=enum("within_declared_limit", "exceeded", "unknown")), 8
    ),
)
SCHEMAS["report"] = obj(
    record_type={"const": "cait_growth_window_report_v1"},
    schema_version={"const": "1"},
    producer_version={"const": "0.2.0"},
    algorithm_version={"const": "finite-accounting-1"},
    input_digest=HASH,
    registration_digest=HASH,
    scope=ID,
    episode=ID,
    study=ID,
    window=obj(start=TIME, end=TIME, cutoff=TIME, endpoints={"const": "[start,end)"}),
    evidence_basis=CONTRACT["properties"]["basis"],
    completeness=enum("declared_complete", "incomplete"),
    layers=obj(
        structural_integrity={"const": "checked"},
        authentication={"const": "unestablished"},
        accounting=enum("consistent", "incomplete"),
        mathematics={"const": "conditional"},
        statistical_coverage={"type": "null"},
        causal_attribution={"type": "null"},
        execution_authority={"type": "null"},
    ),
    uncertainty={"const": "exact per joint scenario; extrema are a conservative outer projection"},
    balances=arr(BALANCE, 512),
    bounds=arr(
        obj(
            arm=ID, coordinate=ID, lower=NULL_Q, upper=NULL_Q, status=enum("declared_finite_bound", "unknown")
        ),
        64,
    ),
    traces=arr(TRACE, 8),
    models=arr(MODEL_RESULT, 8),
    residuals=arr({"type": "string"}, 4096),
    arrival_verdict={"type": "null"},
    non_claims={
        "const": [
            "No empirical acceleration experiment",
            "No causal endogenous reproduction",
            "No AGI/ASI or infinite growth",
            "No execution authority",
            "Hashes do not authenticate sources",
        ]
    },
)


def validate(value: Json, name: str) -> None:
    require(bounded(value) <= 50000, "size", "Node limit")
    error = next(Draft202012Validator(SCHEMAS[name]).iter_errors(value), None)
    require(error is None, "schema", str(error.message) if error else "")
