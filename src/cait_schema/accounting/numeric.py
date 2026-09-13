"""Bounded JSON and canonical rational profile, independent of legacy numbers."""

from __future__ import annotations

import hashlib
import json
import re
from fractions import Fraction
from typing import Any


class AnalysisError(ValueError):
    def __init__(self, code: str, detail: str, status: str = "invalid") -> None:
        super().__init__(detail)
        self.code, self.status = code, status


def require(condition: bool, code: str, detail: str, status: str = "invalid") -> None:
    if not condition:
        raise AnalysisError(code, detail, status)


def rational(value: Any) -> Fraction:
    require(isinstance(value, str) and len(value) <= 81, "numeric", "Expected bounded rational string")
    require(
        re.fullmatch(r"-?(0|[1-9][0-9]*)(/[1-9][0-9]*)?", value) is not None,
        "numeric",
        "Use reduced p/q or integer strings",
    )
    q = Fraction(value)
    require(
        str(q) == value and max(abs(q.numerator).bit_length(), q.denominator.bit_length()) <= 128,
        "numeric",
        "Noncanonical or oversized rational",
    )
    return q


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def bytes_digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for k, v in items:
        require(k not in result, "duplicate_key", k)
        result[k] = v
    return result


def _constant(value: str) -> None:
    raise AnalysisError("numeric", value)


def bounded(value: Any, depth: int = 0) -> int:
    require(depth <= 24, "size", "Nesting limit")
    if isinstance(value, dict):
        return 1 + sum(bounded(x, depth + 1) for x in value.values())
    if isinstance(value, list):
        return 1 + sum(bounded(x, depth + 1) for x in value)
    require(not isinstance(value, float), "numeric", "Floating point is not in the computation profile")
    return 1


def parse(text: str) -> dict[str, Any]:
    require(len(text.encode("utf-8")) <= 2_000_000, "size", "Two MB input limit")
    try:
        value = json.loads(text, object_pairs_hook=_pairs, parse_constant=_constant)
    except (RecursionError, json.JSONDecodeError) as exc:
        raise AnalysisError("json", str(exc)) from exc
    require(isinstance(value, dict), "shape", "Expected an object")
    require(bounded(value) <= 50000, "size", "Node limit")
    return dict(value)
