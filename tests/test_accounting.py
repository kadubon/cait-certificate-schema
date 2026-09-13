from __future__ import annotations

import json
from copy import deepcopy
from fractions import Fraction as F

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from cait_schema.accounting.checker import check_report
from cait_schema.accounting.examples import CHILD, NAMES, A, B, event, example, fixture_parts, seal
from cait_schema.accounting.numeric import AnalysisError, canonical, parse, rational
from cait_schema.accounting.report import analyze, window
from cait_schema.accounting.schema import SCHEMAS, validate
from cait_schema.accounting.source import envelope


@pytest.mark.parametrize("name", NAMES)
def test_examples(name):
    bundle = example(name)
    report = analyze(bundle)
    if name == "inconsistent":
        assert report["status"] == "inconsistent"
        return
    validate(report, "report")
    assert check_report(bundle, report)["status"] == "checked"
    assert report["layers"]["causal_attribution"] is None
    assert report["layers"]["execution_authority"] is None


@pytest.mark.parametrize(
    "value", [True, False, 1, 0.1, "1.0", "01", "1/0", "2/2", "-0", "NaN", "1/01", "9" * 90]
)
def test_bad_numbers(value):
    with pytest.raises(AnalysisError):
        rational(value)


@pytest.mark.parametrize(
    "text",
    ['{"a":1,"a":2}', '{"a":NaN}', '{"a":0.1}', "[]", "{", '{"x":' + "[" * 1000 + "0" + "]" * 1000 + "}"],
)
def test_bad_json(text):
    with pytest.raises(AnalysisError):
        parse(text)


def test_parser_limits_and_canonicalization():
    assert parse('{"a":"1/2","b":true}') == {"a": "1/2", "b": True}
    assert rational("-2/3") == F(-2, 3)
    for text in (
        " " * 2_000_001,
        '{"x":[' + ",".join("0" for _ in range(50001)) + "]}",
        '{"x":' + "[" * 25 + "0" + "]" * 25 + "}",
    ):
        with pytest.raises(AnalysisError):
            parse(text)
    assert canonical({"b": 1, "a": 2}) == canonical({"a": 2, "b": 1})


@pytest.mark.parametrize(
    "field,value",
    [
        ("scope", "other"),
        ("arm", "other"),
        ("contract", "0" * 64),
        ("episode", "other"),
        ("recorded", 0),
        ("stream", "other"),
    ],
)
def test_source_binding(field, value):
    b = example()
    row = json.loads(b["events"][1]["content"])
    row[field] = value
    b["events"][1] = envelope(row)
    assert analyze(b)["status"] in {"invalid", "inconsistent"}


def test_digest_and_duplicate_deliveries():
    b = example()
    r = window(b)
    b["events"].append(deepcopy(b["events"][0]))
    assert window(b)["balances"] == r["balances"]
    row = json.loads(b["events"][-1]["content"])
    row["data"]["quantity"]["joint-a"] = "7"
    b["events"][-1] = envelope(row)
    assert analyze(b)["code"] == "conflicting_event"
    b = example()
    b["events"][0]["sha256"] = "0" * 64
    assert analyze(b)["code"] == "source_digest"


@pytest.mark.parametrize(
    "change,code",
    [
        (lambda c, e, v, m: c["arms"].append("candidate"), "duplicate"),
        (lambda c, e, v, m: c.update(end=0), "window"),
        (lambda c, e, v, m: c["valuation"].update(target="unknown"), "valuation"),
        (lambda c, e, v, m: c["valuation"]["rates"].update(unknown={"joint-a": "1"}), "units"),
        (lambda c, e, v, m: c["opening"].append(deepcopy(c["opening"][0])), "duplicate_asset"),
        (lambda c, e, v, m: c["opening"][0].update(coordinate="service"), "opening"),
        (
            lambda c, e, v, m: e[1]["data"].update(
                shares={"endogenous": "1", "external": "1", "unresolved": "0"}
            ),
            "partition",
        ),
        (lambda c, e, v, m: e[1]["data"].update(parent_shares={A: "1", B: "1"}), "parent_credit"),
        (lambda c, e, v, m: e[1]["data"].update(expires=1), "expiry"),
        (lambda c, e, v, m: e[1]["data"].update(coordinate="service"), "coordinate_kind"),
        (lambda c, e, v, m: e[1]["data"].update(coordinate="missing"), "units"),
        (lambda c, e, v, m: e[0]["data"].update(unit="missing"), "units"),
        (lambda c, e, v, m: e[0]["data"].update(quantity={"joint-a": "-1"}), "negative"),
        (lambda c, e, v, m: e[0]["data"].update(quantity={"other": "1"}), "scenarios"),
        (lambda c, e, v, m: c["allocations"].update({"physical-1": {"candidate": "1/2"}}), "allocation"),
        (lambda c, e, v, m: c["allocations"].update({"physical-1": {"unknown": "1"}}), "arm"),
        (lambda c, e, v, m: v.append(deepcopy(v[0])), "duplicate_evidence"),
        (lambda c, e, v, m: v[0].update(scope="other"), "evidence_scope"),
        (lambda c, e, v, m: v[0].update(dependencies=["check-creation"]), "cycle"),
        (lambda c, e, v, m: e[1].update(dependencies=["reuse-child"]), "dependency_time"),
        (lambda c, e, v, m: c.update(operation_budget=1), "budget"),
    ],
)
def test_contract_guards(change, code):
    c, e, v, m = fixture_parts()
    change(c, e, v, m)
    assert analyze(seal(c, e, v, m))["code"] == code


@pytest.mark.parametrize("missing", ["event", "cost", "evidence", "dependency", "negative", "evidence-cost"])
def test_missing_obligations_never_strengthen(missing):
    c, e, v, m = fixture_parts()
    if missing == "event":
        c["mandatory_events"].append("absent")
    elif missing == "cost":
        c["mandatory_costs"].append("absent")
    elif missing == "evidence":
        e[1]["evidence"] = ["absent"]
    elif missing == "dependency":
        v[0]["dependencies"] = ["absent"]
    elif missing == "evidence-cost":
        v[0]["cost_ids"].append("absent")
    else:
        c["negative_terms_complete"] = False
    b = seal(c, e, v, m)
    r = window(b)
    assert r["bounds"][0]["lower"] is None
    assert check_report(b, r)["status"] == "checked"


def test_truncation_and_conflicting_cost():
    b = example()
    b["events"].pop(0)
    assert window(b)["completeness"] == "incomplete"
    c, e, v, m = fixture_parts()
    duplicate = deepcopy(e[0])
    duplicate["id"] = "cost-copy"
    e.append(duplicate)
    assert analyze(seal(c, e, v, m))["code"] == "duplicate_cost"


@pytest.mark.parametrize(
    "field,value",
    [
        ("outcome", "fail"),
        ("outcome", "unknown"),
        ("blocking_defeaters", ["blocker"]),
        ("valid_until", 1),
        ("artifact", A),
        ("receiver", "receiver-2"),
        ("protocol", "other"),
        ("check", "other"),
    ],
)
def test_qualification_is_replayed(field, value):
    c, e, v, m = fixture_parts()
    v[0][field] = value
    b = seal(c, e, v, m)
    r = window(b)
    assert r["balances"][0]["endogenous"] == "0"
    assert check_report(b, r)["status"] == "checked"


@pytest.mark.parametrize("outcome", ["failure", "rejection", "timeout", "pending", "censored"])
def test_reuse_states_not_success(outcome):
    c, e, v, m = fixture_parts()
    e[2]["data"]["outcome"] = outcome
    b = seal(c, e, v, m)
    r = window(b)
    assert r["balances"][1]["service"] == "0"
    assert r["traces"][0]["uses"][0]["outcome"] == outcome
    assert check_report(b, r)["status"] == "checked"


@pytest.mark.parametrize("kind", ["withdraw", "expire", "repair", "revalidate"])
def test_lifecycle(kind):
    c, e, v, m = fixture_parts()
    if kind == "revalidate":
        e[1]["data"]["expires"] = 3
    d = dict(artifact=CHILD, reason="fixture")
    if kind == "revalidate":
        d["expires"] = 20
    row = event("lifecycle", kind, 4, d)
    row["evidence"] = ["check-creation"]
    e.append(row)
    b = seal(c, e, v, m)
    r = window(b)
    assert check_report(b, r)["status"] == "checked"
    assert r["balances"][0]["closing"] == ("2" if kind in {"withdraw", "expire"} else "7")


def test_revocation_alias_and_descendants():
    c, e, v, m = fixture_parts()
    e.append(event("revoke-parent", "withdraw", 3, dict(artifact=A, reason="revoked")))
    copy = deepcopy(e[1])
    copy.update(id="wrapped-copy", time=4, recorded=4)
    e.append(copy)
    b = seal(c, e, v, m)
    r = window(b)
    assert r["balances"][0]["closing"] == "1"
    assert check_report(b, r)["status"] == "checked"


def test_correction_asof_and_historical():
    b = example("correction")
    assert window(b)["balances"][0]["gross"] == "2"
    c, e, v, m = fixture_parts()
    correction = event(
        "fix", "correct", 5, dict(target="create-child", quantity={"joint-a": "2"}, reason="fixture")
    )
    correction["dependencies"] = ["create-child"]
    e.append(correction)
    assert window(seal(c, e, v, m))["balances"][0]["gross"] == "5"
    c["interpretation"] = "corrected"
    correction["recorded"] = 20
    assert window(seal(c, e, v, m))["balances"][0]["gross"] == "5"


@pytest.mark.parametrize(
    "field",
    [
        "balances",
        "traces",
        "bounds",
        "models",
        "residuals",
        "scope",
        "window",
        "layers",
        "completeness",
        "producer_version",
        "non_claims",
    ],
)
def test_forged_report(field):
    b = example()
    r = window(b)
    if isinstance(r[field], list):
        r[field] = []
    elif isinstance(r[field], dict):
        r[field] = {}
    else:
        r[field] = "forged"
    if field == "residuals":
        r[field] = ["forged"]
    assert check_report(b, r)["status"] != "checked"


@settings(max_examples=30, deadline=None)
@given(produced=st.integers(0, 20), cost=st.integers(0, 20), numerator=st.integers(0, 4))
def test_independent_rational_oracle(produced, cost, numerator):
    c, e, v, m = fixture_parts()
    e[1]["data"]["quantity"]["joint-a"] = str(produced)
    e[0]["data"]["quantity"]["joint-a"] = str(cost)
    e[1]["data"]["shares"] = {
        "endogenous": str(F(numerator, 4)),
        "external": str(1 - F(numerator, 4)),
        "unresolved": "0",
    }
    b = seal(c, e, v, m)
    r = window(b)
    assert F(r["balances"][0]["declared_net"]) == produced * F(numerator, 4) - cost
    assert F(r["balances"][0]["closing"]) == 2 + produced
    assert check_report(b, r)["status"] == "checked"


@settings(max_examples=15, deadline=None)
@given(cut=st.integers(1, 8))
def test_adjacent_windows(cut):
    c, e, v, m = fixture_parts()
    full = window(seal(c, e, v, []))["balances"][0]
    c["end"] = cut
    first = window(seal(c, e, v, []))["balances"][0]
    c["start"], c["end"] = cut, 10
    second = window(seal(c, e, v, []))["balances"][0]
    assert F(first["gross"]) + F(second["gross"]) == F(full["gross"])
    assert first["closing"] == second["opening"]


def test_event_transport_permutation():
    b = example()
    r = window(b)
    b["events"].reverse()
    assert window(b)["balances"] == r["balances"]
    assert window(b)["traces"] == r["traces"]


def test_all_schema_metaschemas():
    from jsonschema import Draft202012Validator

    for schema in SCHEMAS.values():
        Draft202012Validator.check_schema(schema)
