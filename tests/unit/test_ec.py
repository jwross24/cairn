import json
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from cairn import ec, pari

VECTORS = Path(__file__).resolve().parent.parent / "vectors"
GF101 = {"p": 101, "a": 90, "b": 44, "n": 89, "P": (2, 38)}
BITS28 = json.loads((VECTORS / "dlp_instances.json").read_text())["instances"]["bits28_seed1"]
CURVES = [GF101, {**BITS28, "P": tuple(BITS28["P"])}]


def _E(c):
    return pari.pari.ellinit([c["a"], c["b"]], c["p"])


def _lift(point):
    return None if len(point) == 1 else tuple(int(v.lift()) for v in point)


def _pari_mul(c, point, k):
    return _lift(pari.pari.ellmul(_E(c), list(point), k))


@pytest.mark.parametrize("c", CURVES, ids=["GF101", "bits28"])
@given(k=st.integers(min_value=-300, max_value=300))
def test_mul_agrees_with_libpari_over_a_window_of_scalars(c, k):
    assert ec.mul(c["p"], c["a"], c["P"], k) == _pari_mul(c, c["P"], k)


@pytest.mark.parametrize("c", CURVES, ids=["GF101", "bits28"])
@given(i=st.integers(min_value=1, max_value=200), j=st.integers(min_value=1, max_value=200))
def test_add_agrees_with_libpari_on_multiples(c, i, j):
    left, right = ec.mul(c["p"], c["a"], c["P"], i), ec.mul(c["p"], c["a"], c["P"], j)
    expected = _pari_mul(c, c["P"], i + j)
    assert ec.add(c["p"], c["a"], left, right) == expected
    assert ec.sub(c["p"], c["a"], left, ec.neg(c["p"], right)) == expected


@pytest.mark.parametrize("c", CURVES, ids=["GF101", "bits28"])
def test_the_group_order_kills_the_generator_and_inverses_cancel(c):
    p, a, P = c["p"], c["a"], c["P"]
    assert ec.mul(p, a, P, c["n"]) is None
    assert ec.add(p, a, P, ec.neg(p, P)) is None
    assert ec.add(p, a, None, P) == P and ec.add(p, a, P, None) == P
    assert ec.mul(p, a, P, 0) is None and ec.neg(p, None) is None
    assert ec.mul(p, a, P, c["n"] + 1) == P


def test_doubling_a_point_of_order_two_is_the_identity():
    assert ec.double(7, 1, (0, 0)) is None
    assert ec.double(7, 1, None) is None


@given(k=st.integers(min_value=0, max_value=1 << 60))
def test_mul_ops_counts_one_double_per_bit_and_one_add_per_set_bit(k):
    doubles = max(0, k.bit_length() - 1)
    adds = max(0, k.bit_count() - 1)
    assert ec.mul_ops(k) == doubles + adds == ec.mul_ops(-k)


@pytest.mark.parametrize("c", CURVES, ids=["GF101", "bits28"])
@given(k=st.integers(min_value=1, max_value=300))
def test_canonical_picks_the_smaller_y_and_reports_the_flip(c, k):
    p = c["p"]
    point = ec.mul(p, c["a"], c["P"], k % (c["n"] - 1) + 1)
    rep, flipped = ec.canonical(p, point)
    assert rep[1] <= p - rep[1]
    assert flipped == (point[1] > p - point[1])
    assert rep == (point if not flipped else ec.neg(p, point))
    assert ec.canonical(p, None) == (None, False)


def test_is_on_curve_and_require_on_curve():
    c = GF101
    assert ec.is_on_curve(c["p"], c["a"], c["b"], c["P"]) and ec.is_on_curve(c["p"], c["a"], c["b"], None)
    assert not ec.is_on_curve(c["p"], c["a"], c["b"], (2, 39))
    assert not ec.is_on_curve(c["p"], c["a"], c["b"], (2, 139))
    assert ec.require_on_curve(c["p"], c["a"], c["b"], c["P"], "P") == c["P"]
    with pytest.raises(ec.NotOnCurve, match=r"Q = \(2, 39\) is not an affine point"):
        ec.require_on_curve(c["p"], c["a"], c["b"], (2, 39), "Q")
    with pytest.raises(ec.NotOnCurve, match="Q = None"):
        ec.require_on_curve(c["p"], c["a"], c["b"], None, "Q")
