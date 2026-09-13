"""Source-byte integrity, registered boundaries, and finite dependency closure."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Any

from .numeric import bytes_digest, canonical, digest, parse, rational, require
from .schema import validate

Json = dict[str, Any]


def registration(contract: Json) -> str:
    # Terminal chain hashes are commitments to records that bind this registration.
    # Excluding ONLY terminals avoids a circular hash; bundle digest binds them too.
    copy = parse(canonical(contract))
    for stream in copy["streams"]:
        stream["terminal"] = "0" * 64
    return digest(copy)


def envelope(record: Json) -> Json:
    content = canonical(record)
    return {"sha256": bytes_digest(content), "content": content}


def unpack(item: Json, schema: str) -> Json:
    require(bytes_digest(item["content"]) == item["sha256"], "source_digest", "Source bytes changed")
    result = parse(item["content"])
    validate(result, schema)
    return result


def unique(items: list[Any], label: str) -> None:
    require(len(items) == len(set(items)), "duplicate", label, "inconsistent")


def quantities(values: Json, scenarios: list[str]) -> dict[str, Fraction]:
    require(set(values) == set(scenarios), "scenarios", "Quantity does not cover registered joint scenarios")
    result = {k: rational(v) for k, v in values.items()}
    require(all(x >= 0 for x in result.values()), "negative", "Negative magnitude")
    return result


@dataclass(frozen=True)
class Prepared:
    bundle: Json
    contract: Json
    events: list[Json]
    evidence: dict[str, Json]
    models: list[Json]
    missing: tuple[str, ...]


def prepare(bundle: Json) -> Prepared:
    validate(bundle, "bundle")
    require(len(canonical(bundle).encode("utf-8")) <= 2_000_000, "size", "Two MB source limit")
    c = bundle["contract"]
    for field in ("arms", "scenarios", "mandatory_events", "mandatory_costs", "cost_units"):
        unique(c[field], field)
    for field in ("coordinates", "receivers", "streams"):
        unique([x["id"] for x in c[field]], field)
    require(
        c["checkpoint_time"] <= c["start"] < c["end"] <= c["cutoff"],
        "window",
        "Invalid half-open window/cutoff",
    )
    coords = {x["id"]: x for x in c["coordinates"]}
    require(c["valuation"]["target"] in coords, "valuation", "Unknown target coordinate")
    require(set(c["valuation"]["rates"]) <= set(c["cost_units"]), "units", "Unregistered valuation unit")
    for values in c["valuation"]["rates"].values():
        quantities(values, c["scenarios"])
    require(set(c["resource_limits"]) <= set(c["cost_units"]), "units", "Unknown resource budget")
    for values in c["resource_limits"].values():
        quantities(values, c["scenarios"])
    for shares in c["allocations"].values():
        require(set(shares) <= set(c["arms"]), "arm", "Unknown cost allocation arm")
        amounts = [rational(x) for x in shares.values()]
        require(
            all(x >= 0 for x in amounts) and sum(amounts) == 1,
            "allocation",
            "Physical cost allocations must sum to one",
        )
    seen_open: set[tuple[str, str]] = set()
    for a in c["opening"]:
        key = (a["arm"], a["artifact"])
        require(key not in seen_open, "duplicate_asset", "Copied opening stock", "inconsistent")
        seen_open.add(key)
        require(
            a["coordinate"] in coords
            and coords[a["coordinate"]]["meaning"] == "asset_stock"
            and a["arm"] in c["arms"]
            and a["expires"] > c["checkpoint_time"],
            "opening",
            "Invalid initial endowment",
        )
        quantities(a["quantity"], c["scenarios"])
    events: dict[str, Json] = {}
    hashes: dict[str, str] = {}
    for item in bundle["events"]:
        event = unpack(item, "event")
        eid = event["id"]
        if eid in events:
            require(events[eid] == event, "conflicting_event", eid, "inconsistent")
            continue
        require(
            event["scope"] == c["scope"]
            and event["episode"] == c["episode"]
            and event["contract"] == registration(c),
            "binding",
            eid,
        )
        require(c["checkpoint_time"] <= event["time"] <= event["recorded"], "time", eid)
        require(event["arm"] in c["arms"], "arm", eid)
        require(event["study"] == c["study"], "study", "Training/holdout identity mismatch")
        data = event["data"]
        if "quantity" in data:
            quantities(data["quantity"], c["scenarios"])
        if "coordinate" in data:
            require(data["coordinate"] in coords, "units", eid)
            meaning = coords[data["coordinate"]]["meaning"]
            require((event["kind"] == "create") == (meaning == "asset_stock"), "coordinate_kind", eid)
        if event["kind"] == "create":
            shares = [rational(x) for x in data["shares"].values()]
            require(all(x >= 0 for x in shares) and sum(shares) == 1, "partition", eid, "inconsistent")
            unique(data["parents"], "parents")
            require(set(data["parent_shares"]) <= set(data["parents"]), "parents", eid)
            allocated = [rational(x) for x in data["parent_shares"].values()]
            require(
                all(x >= 0 for x in allocated) and (not allocated or sum(allocated) == 1),
                "parent_credit",
                eid,
            )
            require(data["expires"] > event["time"], "expiry", eid)
        if event["kind"] == "cost":
            require(data["unit"] in c["cost_units"], "units", eid)
        for field in ("dependencies", "evidence", "costs"):
            unique(event[field], field)
        events[eid], hashes[eid] = event, item["sha256"]
    missing: list[str] = []
    streams = {x["id"]: x for x in c["streams"]}
    require(all(e["stream"] in streams for e in events.values()), "stream", "Unknown stream")
    for sid, stream in streams.items():
        rows = sorted((e for e in events.values() if e["stream"] == sid), key=lambda e: e["sequence"])
        require(stream["first"] <= stream["last"] + 1, "range", sid)
        expected = list(range(stream["first"], stream["last"] + 1))
        require(len(expected) <= 256, "size", "Stream limit")
        actual = [e["sequence"] for e in rows]
        unique(actual, "sequence")
        require(set(actual) <= set(expected), "range", sid)
        if actual != expected:
            missing.append("incomplete_stream:" + sid)
        prior, t = stream["checkpoint"], c["checkpoint_time"]
        for e in rows:
            require(e["arm"] == stream["arm"] and e["time"] >= t, "stream_order", e["id"])
            if actual == expected:
                require(e["previous"] == prior, "chain", e["id"], "inconsistent")
            prior, t = hashes[e["id"]], e["time"]
        if actual == expected:
            require(prior == stream["terminal"], "terminal", sid, "inconsistent")
    evidence: dict[str, Json] = {}
    for item in bundle["evidence"]:
        ev = unpack(item, "evidence")
        require(ev["id"] not in evidence, "duplicate_evidence", ev["id"])
        require(
            ev["scope"] == c["scope"] and ev["arm"] in c["arms"] and ev["valid_from"] < ev["valid_until"],
            "evidence_scope",
            ev["id"],
        )
        evidence[ev["id"]] = ev
    cost_ids: dict[str, Json] = {}
    for e in events.values():
        if e["kind"] == "cost":
            cid = e["data"]["cost_id"]
            require(cid not in cost_ids, "duplicate_cost", cid, "inconsistent")
            cost_ids[cid] = e
    for cid in c["mandatory_costs"]:
        if cid not in cost_ids:
            missing.append("omitted_cost:" + cid)
        elif cost_ids[cid]["recorded"] > c["cutoff"]:
            missing.append("unavailable_cost_at_cutoff:" + cid)
    for eid in c["mandatory_events"]:
        if eid not in events:
            missing.append("omitted_event:" + eid)
        elif events[eid]["recorded"] > c["cutoff"]:
            missing.append("unavailable_event_at_cutoff:" + eid)
    for e in events.values():
        if e["time"] < c["end"] and e["recorded"] > c["cutoff"]:
            missing.append("unavailable_source_at_cutoff:" + e["id"])
    if not c["negative_terms_complete"]:
        missing.append("negative_terms_incomplete")
    operations = 0
    active: set[str] = set()
    done: set[str] = set()

    def visit(key: str, graph: dict[str, Json], depth: int = 0) -> None:
        nonlocal operations
        operations += 1
        require(operations <= c["operation_budget"] and depth <= 24, "budget", key, "exhausted")
        require(key not in active, "cycle", key, "inconsistent")
        if key in done:
            return
        if key not in graph:
            missing.append("missing_dependency:" + key)
            return
        active.add(key)
        row = graph[key]
        for dep in row["dependencies"]:
            if dep in graph:
                require(graph[dep]["arm"] == row["arm"], "cross_arm", key)
                if "time" in row:
                    require(graph[dep]["time"] <= row["time"], "dependency_time", key)
            visit(dep, graph, depth + 1)
        active.remove(key)
        done.add(key)

    for graph in (events, evidence):
        done.clear()
        for graph_key in graph:
            visit(graph_key, graph)
    for e in events.values():
        for cid in e["costs"] + (e["data"].get("cost_ids", [])):
            if cid not in cost_ids:
                missing.append("omitted_cost:" + cid)
        for ref in e["evidence"]:
            if ref not in evidence:
                missing.append("missing_evidence:" + ref)
    for ev in evidence.values():
        for cid in ev["cost_ids"]:
            if cid not in cost_ids:
                missing.append("omitted_cost:" + cid)
    models = [unpack(x, "model") for x in bundle["models"]]
    for model in models:
        for member in model["family"]:
            for mat in [member["lower"]] + ([] if member["upper"] is None else [member["upper"]]):
                for row in mat:
                    for number in row:
                        rational(number)
        for witness in (model["lower_witness"], model["upper_witness"]):
            if witness is not None:
                for number in witness["vector"] + [witness["bound"]]:
                    rational(number)
    ordered: list[Json] = []
    pending = dict(events)
    predecessors: dict[str, set[str]] = {
        eid: set(e["dependencies"]) & set(events) for eid, e in events.items()
    }
    for sid in streams:
        rows = sorted((e for e in events.values() if e["stream"] == sid), key=lambda e: e["sequence"])
        for before, after in zip(rows, rows[1:], strict=False):
            predecessors[after["id"]].add(before["id"])
    while pending:
        ready = [e for eid, e in pending.items() if not predecessors[eid] & pending.keys()]
        require(
            bool(ready), "stream_dependency_cycle", "Contradictory stream/dependency order", "inconsistent"
        )
        next_event = min(ready, key=lambda e: (e["time"], e["stream"], e["sequence"]))
        ordered.append(next_event)
        del pending[next_event["id"]]
    return Prepared(
        bundle,
        c,
        ordered,
        evidence,
        models,
        tuple(sorted(set(missing))),
    )


def qualified(p: Prepared, event: Json) -> bool:
    """Recompute receiver/check closure; flags in legacy records are not consulted."""
    d, c = event["data"], p.contract
    receivers = {x["id"]: x for x in c["receivers"]}
    receiver = receivers.get(d.get("receiver", c["receivers"][0]["id"]))
    require(receiver is not None, "receiver", event["id"])
    assert receiver is not None
    for field in ("context", "evaluator", "protocol", "task"):
        require(d.get(field, receiver[field]) == receiver[field], "receiver_binding", event["id"])
    checked: set[str] = set()
    okay = True
    todo = list(event["evidence"])
    seen: set[str] = set()
    while todo:
        key = todo.pop()
        if key in seen:
            continue
        seen.add(key)
        ev = p.evidence.get(key)
        if ev is None:
            okay = False
            continue
        matches = (
            ev["arm"] == event["arm"]
            and ev["artifact"] == d["artifact"]
            and ev["receiver"] == receiver["id"]
            and ev["context"] == receiver["context"]
            and ev["evaluator"] == receiver["evaluator"]
            and ev["protocol"] == receiver["protocol"]
        )
        okay = okay and matches and ev["outcome"] == "pass" and not ev["blocking_defeaters"]
        okay = okay and ev["valid_from"] <= event["time"] < ev["valid_until"]
        checked.add(ev["check"])
        todo.extend(ev["dependencies"])
    return okay and set(receiver["checks"]) <= checked
