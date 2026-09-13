from __future__ import annotations

from fractions import Fraction as F

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from cait_schema.accounting.checker import check_report, reference_model
from cait_schema.accounting.examples import fixture_parts, seal
from cait_schema.accounting.numeric import AnalysisError
from cait_schema.accounting.report import window
from cait_schema.accounting.reproduction import inequality, propose_lower, reproduction
from cait_schema.accounting.source import prepare


def model_case(lower, upper, low=None, high=None, **changes):
    c, e, v, models = fixture_parts()
    m = models[0]
    m.update(
        types=[f"type-{i}" for i in range(len(lower))],
        family=[dict(lower=lower, upper=upper)],
        lower_witness=low,
        upper_witness=high,
        **changes,
    )
    return seal(c, e, v, [m])


@pytest.mark.parametrize(
    "lower,upper,low,high,expected",
    [
        ([["2"]], [["3"]], dict(vector=["1"], bound="2", block=[]), None, "supercritical"),
        ([["0"]], [["0"]], None, dict(vector=["1"], bound="0", block=[]), "subcritical"),
        ([["1"]], [["1"]], None, None, "unknown"),
        ([["2", "0"], ["0", "0"]], None, dict(vector=["1"], bound="2", block=[0]), None, "supercritical"),
        (
            [["0", "2"], ["1", "0"]],
            None,
            dict(vector=["4", "3"], bound="4/3", block=[]),
            None,
            "supercritical",
        ),
        ([["0", "1/1000"], ["1000", "0"]], [["0", "1/1000"], ["1000", "0"]], None, None, "unknown"),
    ],
)
def test_exact_matrix_cases(lower, upper, low, high, expected):
    b = model_case(lower, upper, low, high)
    p = prepare(b)
    r = window(b)
    assert r["models"][0]["classification"] == expected
    assert reference_model(p.models[0], p) == r["models"][0]
    assert check_report(b, r)["status"] == "checked"


@pytest.mark.parametrize(
    "change,code",
    [
        (lambda m: m.update(types=["a", "a"]), "duplicate"),
        (lambda m: m.update(valid_until=0), "model_horizon"),
        (lambda m: m["family"][0].update(lower=[["-1"]]), "negative_matrix"),
        (lambda m: m["family"][0].update(lower=[["4"]]), "empty_model"),
        (lambda m: m["family"][0].update(lower=[["2", "0"]]), "matrix_shape"),
        (lambda m: m["lower_witness"].update(vector=["0"]), "vector"),
        (lambda m: m["lower_witness"].update(bound="1"), "bound"),
        (lambda m: m["lower_witness"].update(bound="3"), "lower_inequality"),
        (lambda m: m["lower_witness"].update(block=[1]), "block"),
        (lambda m: m["lower_witness"].update(block=[0, 0]), "duplicate"),
    ],
)
def test_bad_model_witnesses(change, code):
    m = fixture_parts()[3][0]
    change(m)
    with pytest.raises(AnalysisError) as exc:
        reproduction(m)
    assert exc.value.code == code


@pytest.mark.parametrize("kind", ["time_varying", "local_jacobian"])
def test_no_product_or_nonlinear_growth(kind):
    b = model_case([["2"]], [["3"]], dict(vector=["1"], bound="2", block=[]), kind=kind)
    r = window(b)
    assert r["models"][0]["classification"] == "unknown"
    assert check_report(b, r)["status"] == "checked"


def test_uniform_pathwise_and_expected():
    for kind, steps, expected in [
        ("expected_offspring", 3, None),
        ("uniform_pathwise", 3, "8"),
        ("uniform_pathwise", 20, None),
        ("uniform_pathwise", 65, None),
    ]:
        b = model_case([["2"]], None, dict(vector=["1"], bound="2", block=[]), kind=kind, iterations=steps)
        r = window(b)
        assert r["models"][0]["uniform_pathwise_factor"] == expected
        assert check_report(b, r)["status"] == "checked"


def test_family_enumeration_and_missing_upper():
    c, e, v, m = fixture_parts()
    m[0]["family"].append(dict(lower=[["3"]], upper=[["4"]]))
    b = seal(c, e, v, m)
    assert window(b)["models"][0]["lower"] == "2"
    m[0]["complete"] = False
    b = seal(c, e, v, m)
    r = window(b)
    assert r["models"][0]["classification"] == "unknown"
    assert check_report(b, r)["status"] == "checked"
    m[0].update(
        complete=True,
        lower_witness=None,
        upper_witness=dict(vector=["1"], bound="1/2", block=[]),
        family=[dict(lower=[["0"]], upper=None)],
    )
    b = seal(c, e, v, m)
    r = window(b)
    assert "missing_upper" in r["models"][0]["residuals"]
    assert check_report(b, r)["status"] == "checked"


def test_stale_missing_and_budget_models():
    for change in [
        lambda c, m: m.update(valid_from=1),
        lambda c, m: m.update(sources=["absent"]),
        lambda c, m: c.update(operation_budget=5),
    ]:
        c, e, v, m = fixture_parts()
        if change.__code__.co_firstlineno:
            pass
        change(c, m[0])
        # Exhaust model inequality work while graph replay remains within its budget.
        if c["operation_budget"] == 5:
            m[0].update(
                types=["a", "b"],
                family=[dict(lower=[["2", "0"], ["0", "2"]], upper=None)],
                lower_witness=dict(vector=["1", "1"], bound="2", block=[]),
            )
        b = seal(c, e, v, m)
        r = window(b)
        assert r["models"][0]["classification"] == "unknown"
        assert check_report(b, r)["status"] == "checked"


def test_upper_scope_and_failure():
    with pytest.raises(AnalysisError):
        inequality([[F(0), F(0)], [F(0), F(0)]], dict(vector=["1"], bound="0", block=[0]), False)
    b = model_case([["1"]], [["2"]], None, dict(vector=["1"], bound="1/2", block=[]))
    with pytest.raises(AnalysisError) as exc:
        window(b)
    assert exc.value.code == "upper_inequality"


def test_bounded_search():
    m = fixture_parts()[3][0]
    assert propose_lower(m, "2", 0)["status"] == "exhausted"
    assert propose_lower(m, "2")["status"] == "candidate"
    assert propose_lower(m, "4")["status"] == "unknown"
    assert propose_lower(m, "4", 1)["status"] == "exhausted"


def test_empty_compatible_family_is_inconsistent():
    c, e, v, m = fixture_parts()
    m[0]["family"] = []
    with pytest.raises(AnalysisError) as error:
        reproduction(m[0])
    assert error.value.status == "inconsistent"
    with pytest.raises(AnalysisError) as error:
        prepare(seal(c, e, v, m))
    assert error.value.status == "inconsistent"


@settings(max_examples=30, deadline=None)
@given(a=st.integers(2, 7), b=st.integers(0, 3))
def test_matrix_power_oracle_and_weakening(a, b):
    # Independent matrix power oracle: positive diagonal model and all-ones vector.
    mat = [[F(a), F(b)], [F(b), F(a)]]
    vector = [F(1), F(1)]
    for _ in range(4):
        vector = [sum(row[j] * vector[j] for j in range(2)) for row in mat]
    assert vector == [F((a + b) ** 4)] * 2
    witness = dict(vector=["1", "1"], bound=str(a), block=[])
    model = model_case([[str(a), str(b)], [str(b), str(a)]], None, witness)
    assert window(model)["models"][0]["lower"] == str(a)
    weakened = model_case([["0", "0"], ["0", "0"]], None, None)
    assert window(weakened)["models"][0]["lower"] is None
