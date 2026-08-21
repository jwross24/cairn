import sys
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from cairn import pari
from cairn.skills import toy_curve

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from mutants import toy_curve_mutants  # noqa: E402

CURVE60_FIELDS = ("p", "a", "b", "n", "tries")


def check_postcondition_arm(bits, seed):
    out = toy_curve.run(bits, seed)
    toy_curve.check_postcondition(out)
    E = pari.pari.ellinit([out.a, out.b], out.p)
    assert bool(pari.pari.isprime(out.n)), "isprime"
    assert len(pari.pari.ellmul(E, list(out.P), out.n)) == 1, "ellmul"
    assert (out.n - (out.p + 1)) ** 2 <= 4 * out.p, "hasse"
    assert bool(pari.pari.ellisoncurve(E, list(out.P))), "ellisoncurve"
    assert out.status == "OK"
    again = toy_curve.run(bits, seed)
    assert again.manifest() == out.manifest() and again.to_json() == out.to_json()
    return out


def check_curve60_golden(vector):
    out = toy_curve.run(60, 1)
    assert (str(out.p), str(out.a), str(out.b), str(out.n), out.tries) == tuple(vector[f] for f in CURVE60_FIELDS)
    assert [str(c) for c in out.P] == vector["P"]


@pytest.mark.parametrize("bits", [30, 35])
@settings(max_examples=30, deadline=None)
@given(seed=st.integers(1, 2**31 - 1))
def test_postcondition_arm_holds_for_30_random_seeds_per_size(bits, seed):
    check_postcondition_arm(bits, seed)


def test_mutant_composite_n_skill_is_killed_by_isprime_clause():
    check_postcondition_arm(30, 1)
    with toy_curve_mutants.composite_n_skill(), pytest.raises(AssertionError, match="isprime"):
        check_postcondition_arm(30, 1)


def test_mutant_unpinned_sequence_skill_is_killed_by_curve60_golden(load_vector):
    vector = load_vector("curve60_seed1.json")
    check_curve60_golden(vector)
    with toy_curve_mutants.unpinned_sequence_skill(), pytest.raises(AssertionError):
        check_curve60_golden(vector)
