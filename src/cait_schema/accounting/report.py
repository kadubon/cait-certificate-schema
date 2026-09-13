"""Derived coordinate reports. No cross-unit aggregation without registered rates."""

from __future__ import annotations

from fractions import Fraction
from typing import Any

from .numeric import AnalysisError, digest, rational
from .replay import replay
from .reproduction import reproduction
from .source import Prepared, prepare, registration

Json = dict[str, Any]


def summarize(p: Prepared, traces: list[Json]) -> list[Json]:
    c = p.contract
    result: list[Json] = []
    for trace in traces:
        for arm in c["arms"]:
            costs = {
                unit: sum(
                    (
                        rational(x["quantity"])
                        for x in trace["costs"]
                        if x["arm"] == arm and x["unit"] == unit and c["start"] <= x["time"] < c["end"]
                    ),
                    Fraction(),
                )
                for unit in c["cost_units"]
            }
            for coord in c["coordinates"]:
                rows = [x for x in trace["journal"] if x["arm"] == arm and x["coordinate"] == coord["id"]]
                initial = sum((rational(x["quantity"]) for x in rows if x["term"] == "initial"), Fraction())
                before = [
                    x for x in rows if x["time"] < c["start"] and x["term"] not in {"initial", "service"}
                ]
                opening = initial + sum(
                    (
                        -rational(x["quantity"]) if x["term"] == "losses" else rational(x["quantity"])
                        for x in before
                    ),
                    Fraction(),
                )
                totals = {
                    term: sum(
                        (
                            rational(x["quantity"])
                            for x in rows
                            if x["term"] == term and c["start"] <= x["time"] < c["end"]
                        ),
                        Fraction(),
                    )
                    for term in ("endogenous", "external", "unresolved", "losses", "service")
                }
                gross = sum((totals[k] for k in ("endogenous", "external", "unresolved")), Fraction())
                closing = opening + gross - totals["losses"]
                valuation = c["valuation"]
                valued = None
                if coord["id"] == valuation["target"] and set(valuation["rates"]) == set(costs):
                    valued = sum(
                        (costs[u] * rational(valuation["rates"][u][trace["scenario"]]) for u in costs),
                        Fraction(),
                    )
                net = None if valued is None else totals["endogenous"] - totals["losses"] - valued
                result.append(
                    {
                        "scenario": trace["scenario"],
                        "arm": arm,
                        "coordinate": coord["id"],
                        "unit": coord["unit"],
                        "meaning": coord["meaning"],
                        "opening": str(opening),
                        "closing": str(closing),
                        **{k: str(v) for k, v in totals.items()},
                        "gross": str(gross),
                        "costs": {u: str(v) for u, v in costs.items()},
                        "valued_cost": None if valued is None else str(valued),
                        "declared_net": None if net is None else str(net),
                        "external_share": None if gross == 0 else str(totals["external"] / gross),
                        "unresolved_share": None if gross == 0 else str(totals["unresolved"] / gross),
                    }
                )
    return result


def assemble(p: Prepared, traces: list[Json], balances: list[Json], models: list[Json]) -> Json:
    c = p.contract
    residuals = sorted(set(p.missing) | {x for trace in traces for x in trace["residuals"]})
    bounds = []
    for arm in c["arms"]:
        for coord in c["coordinates"]:
            rows = [r for r in balances if r["arm"] == arm and r["coordinate"] == coord["id"]]
            nets = [rational(r["declared_net"]) for r in rows if r["declared_net"] is not None]
            supported = not residuals and len(nets) == len(c["scenarios"])
            bounds.append(
                {
                    "arm": arm,
                    "coordinate": coord["id"],
                    "lower": str(min(nets)) if supported else None,
                    "upper": str(max(nets)) if supported else None,
                    "status": "declared_finite_bound" if supported else "unknown",
                }
            )
    return {
        "record_type": "cait_growth_window_report_v1",
        "schema_version": "1",
        "producer_version": "0.2.0",
        "algorithm_version": "finite-accounting-1",
        "input_digest": digest(p.bundle),
        "registration_digest": registration(c),
        "scope": c["scope"],
        "episode": c["episode"],
        "study": c["study"],
        "window": {
            "start": c["start"],
            "end": c["end"],
            "cutoff": c["cutoff"],
            "unit": c["time_unit"],
            "endpoints": "[start,end)",
        },
        "evidence_basis": c["basis"],
        "completeness": "declared_complete" if not p.missing else "incomplete",
        "layers": {
            "structural_integrity": "checked",
            "authentication": "unestablished",
            "accounting": "consistent" if not p.missing else "incomplete",
            "mathematics": "conditional",
            "statistical_coverage": None,
            "causal_attribution": None,
            "execution_authority": None,
        },
        "uncertainty": "exact per joint scenario; extrema are a conservative outer projection",
        "balances": balances,
        "bounds": bounds,
        "traces": traces,
        "models": models,
        "residuals": residuals,
        "arrival_verdict": None,
        "non_claims": [
            "No empirical acceleration experiment",
            "No causal endogenous reproduction",
            "No AGI/ASI or infinite growth",
            "No execution authority",
            "Hashes do not authenticate sources",
        ],
    }


def window(bundle: Json) -> Json:
    p = prepare(bundle)
    traces = [replay(p, scenario) for scenario in p.contract["scenarios"]]
    models = [reproduction(m, p, budget=p.contract["operation_budget"]) for m in p.models]
    return assemble(p, traces, summarize(p, traces), models)


def analyze(bundle: Json) -> Json:
    try:
        return window(bundle)
    except AnalysisError as exc:
        return {
            "record_type": "cait_analysis_failure_v1",
            "status": exc.status,
            "code": exc.code,
            "detail": str(exc),
            "authority": None,
        }
