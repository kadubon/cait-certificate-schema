from __future__ import annotations

from copy import deepcopy
from fractions import Fraction as F

import pytest

from cait_schema.accounting.checker import check_report
from cait_schema.accounting.examples import CHILD, A, event, example, fixture_parts, seal
from cait_schema.accounting.report import analyze, window


@pytest.mark.parametrize("time,outcome", [(5, "success"), (5, "failure"), (10, "success")])
def test_pending_resolution_fixed_window(time, outcome):
    c, e, v, m = fixture_parts()
    e[2]["data"]["outcome"] = "pending"
    old = window(seal(c, e, v, m))
    row = event(
        "observed-use",
        "resolve_use",
        time,
        dict(target="reuse-child", quantity={"joint-a": "1"}, outcome=outcome, reason="new-evidence"),
    )
    row.update(dependencies=["reuse-child"], evidence=["check-creation"], costs=["physical-1"])
    e.append(row)
    b = seal(c, e, v, m)
    r = window(b)
    assert old["balances"][1]["service"] == "0"
    assert r["balances"][1]["service"] == ("1" if time < 10 and outcome == "success" else "0")
    assert check_report(b, r)["status"] == "checked"


def test_resource_unknown_and_declared_infeasibility():
    r = window(example("model-resource"))
    assert r["models"][0]["classification"] == "supercritical"
    assert r["traces"][0]["resource_checks"][0]["status"] == "exceeded"
    assert r["bounds"][0]["lower"] is None
    c, e, v, m = fixture_parts()
    c["resource_limits"] = {}
    b = seal(c, e, v, m)
    r = window(b)
    assert r["traces"][0]["resource_checks"][0]["status"] == "unknown"
    assert check_report(b, r)["status"] == "checked"


def test_unavailable_cost_cutoff():
    c, e, v, m = fixture_parts()
    e[0]["recorded"] = 20
    b = seal(c, e, v, m)
    r = window(b)
    assert r["bounds"][0]["lower"] is None
    assert r["completeness"] == "incomplete"
    assert check_report(b, r)["status"] == "checked"


def test_disjoint_arms_and_shared_cost_allocation():
    c, e, v, m = fixture_parts()
    c["arms"].append("baseline")
    c["streams"].append({**c["streams"][0], "id": "baseline-stream", "arm": "baseline"})
    c["opening"] += [{**x, "arm": "baseline"} for x in deepcopy(c["opening"])]
    second = deepcopy(e)
    for row in second:
        row.update(
            id=row["id"] + "-b",
            arm="baseline",
            stream="baseline-stream",
            dependencies=[x + "-b" for x in row["dependencies"]],
            evidence=[x + "-b" for x in row["evidence"]],
            costs=[x + "-b" for x in row["costs"]],
        )
        if row["kind"] == "cost":
            row["data"]["cost_id"] += "-b"
    v.append({**v[0], "id": "check-creation-b", "arm": "baseline", "cost_ids": ["physical-1-b"]})
    e += second
    b = seal(c, e, v, [])
    r = window(b)
    stocks = [x for x in r["balances"] if x["coordinate"] == "assets"]
    assert sum(F(x["closing"]) for x in stocks) == 14
    assert r["traces"][0]["resource_checks"][0]["consumed"] == "2"
    assert check_report(b, r)["status"] == "checked"
    c["allocations"] = {"physical-1": {"candidate": "1/2", "baseline": "1/2"}}
    b = seal(c, e, v, [])
    r = window(b)
    assert r["traces"][0]["resource_checks"][0]["consumed"] == "2"
    assert check_report(b, r)["status"] == "checked"


def test_joint_scenario_valuation_no_mixed_extrema():
    c, e, v, m = fixture_parts()
    c["scenarios"].append("joint-b")
    for a in c["opening"]:
        a["quantity"]["joint-b"] = "1"
    for row in e:
        row["data"]["quantity"]["joint-b"] = row["data"]["quantity"]["joint-a"]
    c["resource_limits"]["work-hour"]["joint-b"] = "100"
    c["valuation"]["rates"]["work-hour"] = {"joint-a": "1", "joint-b": "1/2"}
    e[0]["data"]["quantity"]["joint-b"] = "2"
    b = seal(c, e, v, [])
    r = window(b)
    assert r["bounds"][0]["lower"] == r["bounds"][0]["upper"] == "4"
    assert check_report(b, r)["status"] == "checked"


def test_external_influence_and_invalid_parent():
    c, e, v, m = fixture_parts()
    e.append(event("input-model", "external_input", 0, dict(artifact=A, kind="model", cost_ids=["absent"])))
    e[1]["data"]["parents"] = ["f" * 64]
    e[1]["data"]["parent_shares"] = {}
    b = seal(c, e, v, m)
    r = window(b)
    assert r["bounds"][0]["lower"] is None
    assert check_report(b, r)["status"] == "checked"


def test_missing_event_dependency_and_unqualified_renewal():
    c, e, v, m = fixture_parts()
    e[1]["dependencies"] = ["missing"]
    e.append(event("renew", "revalidate", 4, dict(artifact=CHILD, expires=20, reason="fixture")))
    b = seal(c, e, v, m)
    r = window(b)
    assert check_report(b, r)["status"] == "checked"
    assert any("unqualified_renewal" in x for x in r["residuals"])


def test_new_study_does_not_relabel_old_evidence():
    c, e, v, m = fixture_parts()
    e[1]["study"] = "training"
    assert analyze(seal(c, e, v, m))["code"] == "study"
