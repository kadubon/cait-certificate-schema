"""Independent source-to-report audit. Does not import replay or window computation.

Shares the closed input/admission vocabulary, not the reducer or matrix inequalities.
The second ledger is rebuilt from source events with separate lifecycle state.
"""

from __future__ import annotations

from copy import deepcopy
from fractions import Fraction as F
from typing import Any

from .numeric import AnalysisError, canonical, digest, require
from .schema import validate
from .source import Prepared, prepare, qualified, registration

Json = dict[str, Any]


def reference_trace(p: Prepared, scenario: str) -> Json:
    c = p.contract
    events = deepcopy([e for e in p.events if e["recorded"] <= c["cutoff"]])
    overrides: dict[str, Json] = {}
    source = {e["id"]: e for e in events}
    for e in events:
        if e["kind"] == "correct":
            target = source.get(e["data"]["target"])
            require(target is not None, "correction_target", e["id"], "unknown")
            assert target is not None
            require(
                target["kind"] in {"create", "use", "cost"}
                and target["arm"] == e["arm"]
                and target["time"] <= e["time"]
                and target["id"] in e["dependencies"],
                "correction",
                e["id"],
            )
            require(target["id"] not in overrides, "conflicting_correction", e["id"], "inconsistent")
            overrides[target["id"]] = e["data"]["quantity"]
    if c["interpretation"] == "corrected":
        for e in events:
            if e["id"] in overrides:
                e["data"]["quantity"] = overrides[e["id"]]
    resolutions: dict[str, str] = {}
    for resolution in events:
        if resolution["kind"] == "resolve_use" and resolution["time"] < c["end"]:
            data = resolution["data"]
            target = source.get(data["target"])
            require(target is not None, "resolution_target", resolution["id"], "unknown")
            assert target is not None
            require(
                target["kind"] == "use"
                and target["data"]["outcome"] in {"pending", "censored"}
                and target["arm"] == resolution["arm"]
                and target["time"] <= resolution["time"]
                and target["id"] in resolution["dependencies"],
                "resolution",
                resolution["id"],
            )
            require(target["id"] not in resolutions, "duplicate_resolution", resolution["id"], "inconsistent")
            require(
                all(F(data["quantity"][s]) <= F(target["data"]["quantity"][s]) for s in c["scenarios"]),
                "resolution_quantity",
                resolution["id"],
            )
            resolutions[target["id"]] = resolution["id"]
            resolution["kind"] = "use"
            resolution["data"] = {**target["data"], "quantity": data["quantity"], "outcome": data["outcome"]}
    records: dict[tuple[str, str], Json] = {}
    seen: set[tuple[str, str]] = set()
    live: set[tuple[str, str]] = set()
    revoked: set[tuple[str, str]] = set()
    outcomes: set[tuple[str, ...]] = set()
    journal: list[Json] = []
    costs: list[Json] = []
    uses: list[Json] = []
    residuals = list(p.missing)

    def add(t: int, arm: str, coord: str, term: str, q: F, eid: str) -> None:
        journal.append(dict(time=t, arm=arm, coordinate=coord, term=term, quantity=str(q), source=eid))

    def invalidate(keys: list[tuple[str, str]], t: int, eid: str) -> None:
        for k in keys:
            if k in live:
                r = records[k]
                add(t, k[0], r["coordinate"], "losses", F(r["quantity"][scenario]), eid)
                live.remove(k)

    def deadlines(t: int) -> None:
        for k, r in records.items():
            if r["expires"] <= t:
                invalidate([k], r["expires"], "expiry:" + k[1])

    for a in c["opening"]:
        k = (a["arm"], a["artifact"])
        records[k] = {**a, "parents": []}
        seen.add(k)
        live.add(k)
        add(c["checkpoint_time"], k[0], a["coordinate"], "initial", F(a["quantity"][scenario]), "checkpoint")
    for e in events:
        t, arm, d, kind = e["time"], e["arm"], e["data"], e["kind"]
        if t >= c["end"] or e["id"] in resolutions:
            continue
        deadlines(t)
        if not set(e["dependencies"]) <= set(source):
            residuals.append("missing_event_dependency:" + e["id"])
        k = (arm, d.get("artifact", ""))
        if kind == "create":
            if k in seen:
                residuals.append("copied_asset:" + e["id"])
            else:
                seen.add(k)
                if not qualified(p, e):
                    residuals.append("unqualified_creation:" + e["id"])
                elif k in revoked or any((arm, a) not in live or (arm, a) in revoked for a in d["parents"]):
                    residuals.append("invalid_parent:" + e["id"])
                else:
                    records[k] = deepcopy(d)
                    live.add(k)
                    for term in ("endogenous", "external", "unresolved"):
                        add(
                            t,
                            arm,
                            d["coordinate"],
                            term,
                            F(d["quantity"][scenario]) * F(d["shares"][term]),
                            e["id"],
                        )
        elif kind == "use":
            identity = tuple([arm] + [d[x] for x in ("task", "input", "receiver", "protocol", "evaluator")])
            require(identity not in outcomes, "duplicate_outcome", e["id"], "inconsistent")
            outcomes.add(identity)
            admitted = k in live and k not in revoked and qualified(p, e)
            success = d["outcome"] == "success" and admitted
            uses.append(
                dict(
                    event=e["id"],
                    arm=arm,
                    receiver=d["receiver"],
                    outcome=d["outcome"],
                    qualified=success,
                    time=t,
                )
            )
            if success:
                add(t, arm, d["coordinate"], "service", F(d["quantity"][scenario]), e["id"])
            else:
                residuals.append("reuse:" + d["outcome"] + ":" + e["id"])
        elif kind == "cost":
            for owner, share in c["allocations"].get(d["cost_id"], {arm: "1"}).items():
                costs.append(
                    dict(
                        time=t,
                        arm=owner,
                        unit=d["unit"],
                        stage=d["stage"],
                        cost_id=d["cost_id"],
                        quantity=str(F(d["quantity"][scenario]) * F(share)),
                    )
                )
        elif kind in {"withdraw", "expire"}:
            require(k in records, "lifecycle_target", e["id"], "unknown")
            reach = {k}
            for _ in range(len(records)):
                reach |= {
                    other
                    for other, r in records.items()
                    if any((other[0], parent) in reach for parent in r["parents"])
                }
            invalidate(sorted(reach), t, e["id"])
            if kind == "withdraw":
                revoked |= reach
        elif kind == "revalidate":
            require(k in records and k not in revoked, "renewal", e["id"], "unknown")
            require(d["expires"] > t, "expiry", e["id"])
            if qualified(p, e):
                r = records[k]
                if k not in live:
                    add(t, arm, r["coordinate"], "unresolved", F(r["quantity"][scenario]), e["id"])
                live.add(k)
                r["expires"] = d["expires"]
            else:
                residuals.append("unqualified_renewal:" + e["id"])
        elif kind == "repair":
            require(k in records, "repair_target", e["id"], "unknown")
            residuals.append("repair_pending:" + e["id"])
        elif kind == "external_input":
            residuals.append("external_input_causal_influence_unresolved:" + e["id"])
    deadlines(c["end"] - 1)
    checks = []
    for unit in c["cost_units"]:
        used = F(0)
        for row in costs:
            if row["unit"] == unit and c["start"] <= row["time"] < c["end"]:
                used += F(row["quantity"])
        bound = c["resource_limits"].get(unit, {}).get(scenario)
        status = "unknown" if bound is None else "exceeded" if used > F(bound) else "within_declared_limit"
        checks.append(dict(unit=unit, consumed=str(used), limit=bound, status=status))
        if status != "within_declared_limit":
            residuals.append("resource:" + status + ":" + unit)
    return dict(
        scenario=scenario,
        journal=journal,
        costs=costs,
        uses=uses,
        residuals=sorted(set(residuals)),
        resource_checks=checks,
    )


def reference_balances(p: Prepared, traces: list[Json]) -> list[Json]:
    c = p.contract
    result = []
    for trace in traces:
        for arm in c["arms"]:
            spent = dict.fromkeys(c["cost_units"], F(0))
            for row in trace["costs"]:
                if row["arm"] == arm and c["start"] <= row["time"] < c["end"]:
                    spent[row["unit"]] += F(row["quantity"])
            for coordinate in c["coordinates"]:
                opening = F(0)
                totals = dict.fromkeys(("endogenous", "external", "unresolved", "losses", "service"), F(0))
                for row in trace["journal"]:
                    if row["arm"] != arm or row["coordinate"] != coordinate["id"]:
                        continue
                    term, amount = row["term"], F(row["quantity"])
                    if term == "initial":
                        opening += amount
                    elif row["time"] < c["start"]:
                        if term != "service":
                            opening += -amount if term == "losses" else amount
                    elif row["time"] < c["end"]:
                        totals[term] += amount
                gross = totals["endogenous"] + totals["external"] + totals["unresolved"]
                valued = None
                if coordinate["id"] == c["valuation"]["target"] and set(spent) == set(
                    c["valuation"]["rates"]
                ):
                    valued = F(0)
                    for unit, amount in spent.items():
                        valued += amount * F(c["valuation"]["rates"][unit][trace["scenario"]])
                result.append(
                    dict(
                        scenario=trace["scenario"],
                        arm=arm,
                        coordinate=coordinate["id"],
                        unit=coordinate["unit"],
                        meaning=coordinate["meaning"],
                        opening=str(opening),
                        closing=str(opening + gross - totals["losses"]),
                        **{k: str(v) for k, v in totals.items()},
                        gross=str(gross),
                        costs={k: str(v) for k, v in spent.items()},
                        valued_cost=None if valued is None else str(valued),
                        declared_net=None
                        if valued is None
                        else str(totals["endogenous"] - totals["losses"] - valued),
                        external_share=None if not gross else str(totals["external"] / gross),
                        unresolved_share=None if not gross else str(totals["unresolved"] / gross),
                    )
                )
    return result


def check_report(bundle: Json, report: Json) -> Json:
    try:
        p = prepare(bundle)
        validate(report, "report")
        require(
            report.get("input_digest") == digest(bundle)
            and report.get("registration_digest") == registration(p.contract),
            "report_source",
            "Report source binding",
        )
        traces = [reference_trace(p, s) for s in p.contract["scenarios"]]
        balances = reference_balances(p, traces)
        require(
            canonical(traces) == canonical(report.get("traces")),
            "replay_mismatch",
            "Source replay differs",
            "inconsistent",
        )
        require(
            balances == report.get("balances"),
            "balance_mismatch",
            "Coordinate/cost total differs",
            "inconsistent",
        )
        # Full presentation/schema and independent bound checks are checked below.
        residuals = sorted(set(p.missing) | {r for trace in traces for r in trace["residuals"]})
        require(report.get("residuals") == residuals, "omitted_evidence", "Residuals removed", "inconsistent")
        require(
            report["completeness"] == ("incomplete" if p.missing else "declared_complete"),
            "completeness",
            "Source boundary mismatch",
        )
        expected_bounds = []
        for arm in p.contract["arms"]:
            for coord in p.contract["coordinates"]:
                values = [
                    F(r["declared_net"])
                    for r in balances
                    if r["arm"] == arm and r["coordinate"] == coord["id"] and r["declared_net"] is not None
                ]
                okay = not residuals and len(values) == len(p.contract["scenarios"])
                expected_bounds.append(
                    dict(
                        arm=arm,
                        coordinate=coord["id"],
                        lower=str(min(values)) if okay else None,
                        upper=str(max(values)) if okay else None,
                        status="declared_finite_bound" if okay else "unknown",
                    )
                )
        require(
            report.get("bounds") == expected_bounds, "bound_mismatch", "Unwarranted bound", "inconsistent"
        )
        require(
            report.get("models") == [reference_model(m, p) for m in p.models],
            "model_mismatch",
            "Matrix witness differs",
            "inconsistent",
        )
        expected_layers = dict(
            structural_integrity="checked",
            authentication="unestablished",
            accounting="incomplete" if p.missing else "consistent",
            mathematics="conditional",
            statistical_coverage=None,
            causal_attribution=None,
            execution_authority=None,
        )
        require(
            report.get("layers") == expected_layers and report.get("arrival_verdict") is None,
            "authority_promotion",
            "Unsupported evidence/authority claim",
            "inconsistent",
        )
        require(
            report.get("scope") == p.contract["scope"]
            and report.get("study") == p.contract["study"]
            and report.get("episode") == p.contract["episode"]
            and report.get("evidence_basis") == p.contract["basis"],
            "report_scope",
            "Report scope/basis changed",
        )
        require(
            report.get("window")
            == dict(
                start=p.contract["start"],
                end=p.contract["end"],
                cutoff=p.contract["cutoff"],
                unit=p.contract["time_unit"],
                endpoints="[start,end)",
            ),
            "report_window",
            "Window changed",
        )
        return dict(
            record_type="cait_report_check_v1", status="checked", report_digest=digest(report), authority=None
        )
    except AnalysisError as exc:
        return dict(
            record_type="cait_report_check_v1",
            status=exc.status,
            code=exc.code,
            detail=str(exc),
            authority=None,
        )


def reference_model(m: Json, p: Prepared) -> Json:
    """Separate weighted row-ratio verification, no production matrix functions."""
    n = len(m["types"])
    require(len(set(m["types"])) == n and m["valid_from"] < m["valid_until"], "model", "Basis/horizon")
    require(
        (m["scope"], m["episode"], m["contract"])
        == (p.contract["scope"], p.contract["episode"], registration(p.contract)),
        "model_binding",
        "Source mismatch",
    )
    missing = []
    if not (m["valid_from"] <= p.contract["start"] and m["valid_until"] >= p.contract["end"]):
        missing.append("stale_model")
    if not set(m["sources"]) <= {e["id"] for e in p.events if e["recorded"] <= p.contract["cutoff"]}:
        missing.append("missing_model_source")
    if m["kind"] in {"time_varying", "local_jacobian"}:
        missing.append("unsupported_model_kind")
    if not m["complete"]:
        missing.append("incomplete_family")
    if n * n * len(m["family"]) * 2 > p.contract["operation_budget"]:
        missing.append("exhausted")
    for member in m["family"]:
        lo, hi = member["lower"], member["upper"]
        for mat in [lo] + ([] if hi is None else [hi]):
            require(len(mat) == n and all(len(row) == n for row in mat), "matrix_shape", "Invalid dimensions")
            require(all(F(x) >= 0 for row in mat for x in row), "negative_matrix", "Negative entry")
        if hi is not None:
            require(
                all(F(lo[i][j]) <= F(hi[i][j]) for i in range(n) for j in range(n)),
                "empty_model",
                "Empty enclosure",
                "inconsistent",
            )
    approved = [False, False]
    for side, name in enumerate(("lower", "upper")):
        witness = m[name + "_witness"]
        if witness is None or missing:
            continue
        block = witness["block"] or list(range(n))
        v = [F(x) for x in witness["vector"]]
        r = F(witness["bound"])
        require(len(set(block)) == len(block) and all(i < n for i in block), "block", "Invalid block")
        require(side == 0 or set(block) == set(range(n)), "upper_block", "Upper block incomplete")
        require(
            len(v) == len(block) and min(v) > 0 and (r > 1 if side == 0 else 0 <= r < 1),
            "vector",
            "Invalid witness",
        )
        approved[side] = True
        for member in m["family"]:
            mat = member[name]
            if mat is None:
                missing.append("missing_upper")
                approved[side] = False
                continue
            for i, row in enumerate(block):
                ratio = sum((F(mat[row][col]) * v[j] for j, col in enumerate(block)), F()) / v[i]
                require(
                    ratio >= r if side == 0 else ratio <= r,
                    name + "_inequality",
                    "Witness fails",
                    "inconsistent",
                )
    if missing:
        approved = [False, False]
    lo_ok, hi_ok = approved
    factor = None
    if (
        lo_ok
        and m["kind"] == "uniform_pathwise"
        and m["iterations"] <= min(64, m["valid_until"] - m["valid_from"])
    ):
        factor = str(F(m["lower_witness"]["bound"]) ** m["iterations"])
    return dict(
        record_type="cait_reproduction_check_v1",
        model_digest=digest(m),
        classification="supercritical" if lo_ok else "subcritical" if hi_ok else "unknown",
        kind=m["kind"],
        interpretation=m["interpretation"],
        lower=m["lower_witness"]["bound"] if lo_ok else None,
        upper=m["upper_witness"]["bound"] if hi_ok else None,
        uniform_pathwise_factor=factor,
        residuals=sorted(set(missing)),
        basis="declared mathematical premise",
        empirical_growth=None,
        authority=None,
    )
