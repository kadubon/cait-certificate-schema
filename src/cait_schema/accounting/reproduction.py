"""Exact sufficient Perron bounds, not an estimator of reproduction laws."""

from __future__ import annotations

from fractions import Fraction
from itertools import product
from typing import Any

from .numeric import digest, rational, require
from .schema import validate
from .source import Prepared, registration, unique

Json = dict[str, Any]


def matrix(value: list[list[str]], n: int) -> list[list[Fraction]]:
    require(
        len(value) == n and all(len(row) == n for row in value), "matrix_shape", "Basis dimension mismatch"
    )
    result = [[rational(x) for x in row] for row in value]
    require(all(x >= 0 for row in result for x in row), "negative_matrix", "Nonnegative model required")
    return result


def inequality(a: list[list[Fraction]], witness: Json, lower: bool) -> bool:
    n = len(a)
    block = witness["block"] or list(range(n))
    unique(block, "matrix block")
    require(all(i < n for i in block), "block", "Index outside declared basis")
    require(lower or set(block) == set(range(n)), "upper_block", "Upper witness must cover whole matrix")
    v, bound = [rational(x) for x in witness["vector"]], rational(witness["bound"])
    require(len(v) == len(block) and all(x > 0 for x in v), "vector", "Positive vector required")
    require(bound > 1 if lower else 0 <= bound < 1, "bound", "Strict reproduction threshold required")
    av = [sum((a[i][j] * v[k] for k, j in enumerate(block)), Fraction()) for i in block]
    return all(x >= bound * y if lower else x <= bound * y for x, y in zip(av, v, strict=True))


def reproduction(model: Json, prepared: Prepared | None = None, *, budget: int = 100000) -> Json:
    require(model.get("family") != [], "empty_model", "Empty compatible model family", "inconsistent")
    validate(model, "model")
    unique(model["types"], "matrix types")
    n = len(model["types"])
    require(model["valid_from"] < model["valid_until"], "model_horizon", "Empty model horizon")
    families = []
    for member in model["family"]:
        lo = matrix(member["lower"], n)
        hi = None if member["upper"] is None else matrix(member["upper"], n)
        if hi is not None:
            require(
                all(lo[i][j] <= hi[i][j] for i in range(n) for j in range(n)),
                "empty_model",
                "Lower exceeds upper: inconsistent set",
                "inconsistent",
            )
        families.append((lo, hi))
    missing: list[str] = []
    if prepared is not None:
        c = prepared.contract
        require(
            (model["scope"], model["episode"], model["contract"])
            == (c["scope"], c["episode"], registration(c)),
            "model_binding",
            "Model scope/registration changed",
        )
        if not (model["valid_from"] <= c["start"] and model["valid_until"] >= c["end"]):
            missing.append("stale_model")
        ids = {e["id"] for e in prepared.events if e["recorded"] <= c["cutoff"]}
        if not set(model["sources"]) <= ids:
            missing.append("missing_model_source")
    if model["kind"] in {"time_varying", "local_jacobian"}:
        missing.append("unsupported_model_kind")
    if not model["complete"]:
        missing.append("incomplete_family")
    if n * n * len(families) * 2 > budget:
        missing.append("exhausted")
    lower, upper = model["lower_witness"], model["upper_witness"]
    low_ok, high_ok = lower is not None, upper is not None
    if not missing:
        for lo, hi in families:
            if lower is not None:
                require(
                    inequality(lo, lower, True),
                    "lower_inequality",
                    "Supplied lower witness fails",
                    "inconsistent",
                )
            if upper is not None:
                if hi is None:
                    high_ok = False
                    missing.append("missing_upper")
                else:
                    require(
                        inequality(hi, upper, False),
                        "upper_inequality",
                        "Supplied upper witness fails",
                        "inconsistent",
                    )
    if missing:
        low_ok = high_ok = False
    require(not (low_ok and high_ok), "contradictory_bounds", "Both spectral classifications", "inconsistent")
    classification = "supercritical" if low_ok else "subcritical" if high_ok else "unknown"
    realized = None
    if low_ok and model["kind"] == "uniform_pathwise" and model["iterations"] <= 64:
        # Caller supplies a uniform finite-horizon premise; never inferred from expectation.
        if model["iterations"] <= model["valid_until"] - model["valid_from"]:
            realized = str(rational(lower["bound"]) ** model["iterations"])
    return {
        "record_type": "cait_reproduction_check_v1",
        "model_digest": digest(model),
        "classification": classification,
        "kind": model["kind"],
        "interpretation": model["interpretation"],
        "lower": lower["bound"] if low_ok else None,
        "upper": upper["bound"] if high_ok else None,
        "uniform_pathwise_factor": realized,
        "residuals": sorted(set(missing)),
        "basis": "declared mathematical premise",
        "empirical_growth": None,
        "authority": None,
    }


def propose_lower(model: Json, bound: str, budget: int = 1000) -> Json:
    """Optional finite integer-vector proposals, always rechecked exactly."""
    validate(model, "model")
    require(0 <= budget <= 100000, "budget", "Search bound")
    n = len(model["types"])
    lows = [matrix(x["lower"], n) for x in model["family"]]
    attempts = 0
    for v in product(range(1, 5), repeat=n):
        if attempts >= budget:
            return {"status": "exhausted", "attempts": attempts, "witness": None}
        attempts += 1
        w = {"vector": [str(x) for x in v], "bound": bound, "block": []}
        if all(inequality(a, w, True) for a in lows):
            return {"status": "candidate", "attempts": attempts, "witness": w}
    return {"status": "unknown", "attempts": attempts, "witness": None}
