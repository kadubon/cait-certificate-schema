"""Stateful replay of immutable source events over joint finite scenarios."""

from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
from typing import Any

from .numeric import rational, require
from .source import Prepared, qualified

Json = dict[str, Any]


def effective(p: Prepared) -> list[Json]:
    c = p.contract
    events = deepcopy([e for e in p.events if e["recorded"] <= c["cutoff"]])
    by_id = {e["id"]: e for e in events}
    corrected: set[str] = set()
    for e in events:
        if e["kind"] != "correct":
            continue
        d = e["data"]
        require(d["target"] in by_id, "correction_target", e["id"], "unknown")
        target = by_id[d["target"]]
        require(
            target["kind"] in {"create", "use", "cost"}
            and target["arm"] == e["arm"]
            and target["time"] <= e["time"]
            and d["target"] in e["dependencies"],
            "correction",
            e["id"],
        )
        require(d["target"] not in corrected, "conflicting_correction", e["id"], "inconsistent")
        corrected.add(d["target"])
        if c["interpretation"] == "corrected":
            target["data"]["quantity"] = d["quantity"]
    resolved: set[str] = set()
    for e in events:
        if e["kind"] != "resolve_use" or e["time"] >= c["end"]:
            continue
        d = e["data"]
        require(d["target"] in by_id, "resolution_target", e["id"], "unknown")
        target = by_id[d["target"]]
        require(
            target["kind"] == "use"
            and target["data"]["outcome"] in {"pending", "censored"}
            and target["arm"] == e["arm"]
            and target["time"] <= e["time"]
            and target["id"] in e["dependencies"],
            "resolution",
            e["id"],
        )
        require(target["id"] not in resolved, "duplicate_resolution", e["id"], "inconsistent")
        require(
            all(
                rational(d["quantity"][s]) <= rational(target["data"]["quantity"][s]) for s in c["scenarios"]
            ),
            "resolution_quantity",
            e["id"],
        )
        resolved.add(target["id"])
        target["resolved"] = True
        e["kind"] = "use"
        e["data"] = {**target["data"], "outcome": d["outcome"], "quantity": d["quantity"]}
    return events


def replay(p: Prepared, scenario: str) -> Json:
    c = p.contract
    require(scenario in c["scenarios"], "scenario", scenario)
    assets: dict[tuple[str, str], Json] = {}
    ever: set[tuple[str, str]] = set()
    blocked: set[tuple[str, str]] = set()
    use_keys: set[tuple[str, ...]] = set()
    journal: list[Json] = []
    residuals = list(p.missing)
    uses: list[Json] = []
    cost_rows: list[Json] = []

    def entry(time: int, arm: str, coord: str, term: str, quantity: Fraction, source: str) -> None:
        journal.append(
            {
                "time": time,
                "arm": arm,
                "coordinate": coord,
                "term": term,
                "quantity": str(quantity),
                "source": source,
            }
        )

    def lose(key: tuple[str, str], time: int, source: str) -> None:
        a = assets[key]
        if a["live"]:
            entry(time, key[0], a["coordinate"], "losses", a["quantity"], source)
            a["live"] = False

    def expire(time: int) -> None:
        for key, a in assets.items():
            if a["expires"] <= time:
                lose(key, a["expires"], "expiry:" + key[1])

    for a in c["opening"]:
        key = (a["arm"], a["artifact"])
        assets[key] = {**a, "quantity": rational(a["quantity"][scenario]), "live": True, "parents": []}
        ever.add(key)
        entry(
            c["checkpoint_time"], a["arm"], a["coordinate"], "initial", assets[key]["quantity"], "checkpoint"
        )
    events = effective(p)
    eligible_ids = {e["id"] for e in events}
    for event in events:
        t, arm, kind, d = event["time"], event["arm"], event["kind"], event["data"]
        if t >= c["end"] or event.get("resolved", False):
            continue
        expire(t)
        if not set(event["dependencies"]) <= eligible_ids:
            residuals.append("missing_event_dependency:" + event["id"])
        key = (arm, d.get("artifact", ""))
        if kind == "create":
            if key in ever:
                residuals.append("copied_asset:" + event["id"])
                continue
            ever.add(key)
            if not qualified(p, event):
                residuals.append("unqualified_creation:" + event["id"])
                continue
            parents = [(arm, parent) for parent in d["parents"]]
            if key in blocked or any(
                parent in blocked or parent not in assets or not assets[parent]["live"] for parent in parents
            ):
                residuals.append("invalid_parent:" + event["id"])
                continue
            amount = rational(d["quantity"][scenario])
            assets[key] = {**d, "quantity": amount, "live": True, "parents": parents}
            for origin, share in d["shares"].items():
                entry(t, arm, d["coordinate"], origin, amount * rational(share), event["id"])
        elif kind == "use":
            ukey = (arm, d["task"], d["input"], d["receiver"], d["protocol"], d["evaluator"])
            require(ukey not in use_keys, "duplicate_outcome", event["id"], "inconsistent")
            use_keys.add(ukey)
            supported = key in assets and assets[key]["live"] and key not in blocked and qualified(p, event)
            accepted = d["outcome"] == "success" and supported
            uses.append(
                {
                    "event": event["id"],
                    "arm": arm,
                    "receiver": d["receiver"],
                    "outcome": d["outcome"],
                    "qualified": accepted,
                    "time": t,
                }
            )
            if accepted:
                entry(t, arm, d["coordinate"], "service", rational(d["quantity"][scenario]), event["id"])
            else:
                residuals.append("reuse:" + d["outcome"] + ":" + event["id"])
        elif kind == "cost":
            cid = d["cost_id"]
            allocation = c["allocations"].get(cid, {arm: "1"})
            amount = rational(d["quantity"][scenario])
            for charged_arm, share in allocation.items():
                cost_rows.append(
                    {
                        "time": t,
                        "arm": charged_arm,
                        "unit": d["unit"],
                        "stage": d["stage"],
                        "cost_id": cid,
                        "quantity": str(amount * rational(share)),
                    }
                )
        elif kind in {"withdraw", "expire"}:
            require(key in assets, "lifecycle_target", event["id"], "unknown")
            targets = {key}
            while True:
                found = {k for k, a in assets.items() if any(parent in targets for parent in a["parents"])}
                if found <= targets:
                    break
                targets |= found
            for target in sorted(targets):
                lose(target, t, event["id"])
                if kind == "withdraw":
                    blocked.add(target)
        elif kind == "revalidate":
            require(key in assets and key not in blocked, "renewal", event["id"], "unknown")
            require(d["expires"] > t, "expiry", event["id"])
            if qualified(p, event):
                a = assets[key]
                if not a["live"]:
                    entry(t, arm, a["coordinate"], "unresolved", a["quantity"], event["id"])
                a["live"], a["expires"] = True, d["expires"]
            else:
                residuals.append("unqualified_renewal:" + event["id"])
        elif kind == "repair":
            require(key in assets, "repair_target", event["id"], "unknown")
            residuals.append("repair_pending:" + event["id"])
        elif kind == "external_input":
            residuals.append("external_input_causal_influence_unresolved:" + event["id"])
    expire(c["end"] - 1)  # integer clock; [start,end), including exact expiry at start
    checks = []
    for unit in c["cost_units"]:
        total = sum(
            (
                rational(row["quantity"])
                for row in cost_rows
                if row["unit"] == unit and c["start"] <= row["time"] < c["end"]
            ),
            Fraction(),
        )
        limit = c["resource_limits"].get(unit, {}).get(scenario)
        status = (
            "unknown"
            if limit is None
            else "within_declared_limit"
            if total <= rational(limit)
            else "exceeded"
        )
        checks.append(dict(unit=unit, consumed=str(total), limit=limit, status=status))
        if status != "within_declared_limit":
            residuals.append("resource:" + status + ":" + unit)
    return {
        "scenario": scenario,
        "journal": journal,
        "costs": cost_rows,
        "uses": uses,
        "residuals": sorted(set(residuals)),
        "resource_checks": checks,
    }
