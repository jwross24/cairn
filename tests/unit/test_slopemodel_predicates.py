from math import isqrt

import pytest

from cairn.slopemodel import slope_hunt_verifier, slope_predicates

PRIME_GRID = (1, 2, 3, 4, 5, 7, 10, 11, 65537, 971153)


@pytest.mark.parametrize("ell", PRIME_GRID)
@pytest.mark.parametrize(("num", "den"), [(0, 1), (1, 1), (11, 10), (5, 4), (7, 3)])
def test_weight_le_forms_agree_across_integer_boundary(ell, num, den):
    predicate = {"kind": "weight_le", "num": num, "den": den}
    boundary = isqrt(num * num * ell**3) // den
    for weight in {0, max(0, boundary - 1), boundary, boundary + 1, ell * ell}:
        expected = (den * weight) ** 2 <= num * num * ell**3
        assert slope_predicates.holds(predicate, ell, weight) is expected
        assert slope_hunt_verifier.statement_fails(predicate, ell, weight) is not expected


def test_weight_le_exact_equality_holds():
    predicate = {"kind": "weight_le", "num": 1, "den": 1}
    assert slope_predicates.holds(predicate, 4, 8)
    assert not slope_hunt_verifier.statement_fails(predicate, 4, 8)
    assert not slope_predicates.holds(predicate, 4, 9)
    assert slope_hunt_verifier.statement_fails(predicate, 4, 9)


@pytest.mark.parametrize("ell", [*range(1, 40), *PRIME_GRID])
def test_counting_bound_forms_and_predicates_agree(ell):
    bound = slope_predicates.counting_bound(ell)
    assert bound == slope_hunt_verifier.counting_bound_closed_form(ell)
    predicate = {"kind": "weight_ge_counting_bound"}
    for weight in (bound - 1, bound, bound + 1):
        expected = weight >= bound
        assert slope_predicates.holds(predicate, ell, weight) is expected
        assert slope_hunt_verifier.statement_fails(predicate, ell, weight) is not expected


@pytest.mark.parametrize("module", [slope_predicates, slope_hunt_verifier])
@pytest.mark.parametrize(
    "predicate",
    [
        {"kind": "weight_le", "num": -1, "den": 1},
        {"kind": "weight_le", "num": 1, "den": 0},
        {"kind": "weight_le", "num": True, "den": 1},
        {"kind": "unknown"},
    ],
)
def test_predicates_refuse_undefined_statements(module, predicate):
    function = module.holds if module is slope_predicates else module.statement_fails
    with pytest.raises(ValueError, match=r"must be|unknown predicate"):
        function(predicate, 4, 8)


@pytest.mark.parametrize("module", [slope_predicates, slope_hunt_verifier])
@pytest.mark.parametrize(("ell", "weight"), [(0, 8), (True, 8), (4, -1), (4, True)])
def test_predicates_refuse_nonphysical_inputs(module, ell, weight):
    function = module.holds if module is slope_predicates else module.statement_fails
    with pytest.raises(ValueError, match="must be"):
        function({"kind": "weight_le", "num": 1, "den": 1}, ell, weight)
