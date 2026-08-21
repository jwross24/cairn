import sys
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from cairn import pari
from cairn.skills import toy_curve

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "tests"))
from _checks import matches_vector  # noqa: E402
from mutants import toy_curve_mutants  # noqa: E402


def build_output(bits, seed):
    toy_curve.validate(bits, seed)
    pari.pari.setrand(seed)
    p = int(pari.pari.randomprime([2 ** (bits - 1), 2**bits]))
    a, b, n, tries, E, call = toy_curve._search(bits, p)
    confirm, point = toy_curve._settle(bits, E, (a, b, p))
    return toy_curve.ToyCurveOutput(bits, seed, p, a, b, n, point, tries, toy_curve._cross_check("untested"), toy_curve.STATUS_OK)


def check_postcondition_arm(out):
    toy_curve.check_postcondition(out)
    assert out.status == toy_curve.STATUS_OK
    return out


def check_replayable(bits, seed):
    first = toy_curve.run(bits, seed)
    check_postcondition_arm(first)
    second = toy_curve.run(bits, seed)
    assert second.manifest() == first.manifest() and second.to_json() == first.to_json()
    return first


def check_curve60_vector(vector):
    assert matches_vector(toy_curve.run(60, 1), vector)


@pytest.mark.parametrize("bits", [30, 35])
@settings(max_examples=30, deadline=None)
@given(seed=st.integers(1, 2**31 - 1))
def test_postcondition_arm_holds_for_30_random_seeds_per_size(bits, seed):
    check_replayable(bits, seed)


def test_mutant_composite_n_skill_is_killed_by_the_postcondition_arm():
    check_postcondition_arm(build_output(30, 1))
    with toy_curve_mutants.composite_n_skill():
        accepted = build_output(30, 1)
    assert not bool(pari.pari.isprime(accepted.n))
    with pytest.raises(toy_curve.PostconditionFailed, match="isprime"):
        check_postcondition_arm(accepted)


def test_mutant_unpinned_sequence_skill_is_killed_by_curve60_vector(load_vector):
    vector = load_vector("curve60_seed1.json")
    check_curve60_vector(vector)
    with toy_curve_mutants.unpinned_sequence_skill(), pytest.raises(AssertionError):
        check_curve60_vector(vector)
