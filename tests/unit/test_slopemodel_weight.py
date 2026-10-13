import json
from pathlib import Path

import pytest

from cairn.slopemodel import slope_hunt_verifier, slope_predicates, slopemodel_a, slopemodel_b

VECTORS = json.loads((Path(__file__).resolve().parents[1] / "vectors" / "slope_weights.json").read_text())
ENGINES = (slopemodel_a, slopemodel_b)
AGREEMENT_PRIMES = (65537, 131101, 300007, 1048583, 2097169, 4194301)


@pytest.mark.parametrize("engine", ENGINES, ids=("incremental", "all-pairs"))
@pytest.mark.parametrize("row", VECTORS["printed"], ids=lambda row: str(row["l"]))
def test_printed_weights(engine, row):
    weight, last = engine.weight(row["l"], row["n"])
    assert weight == row["weight"]
    assert 0 < last < weight


@pytest.mark.parametrize("engine", ENGINES, ids=("incremental", "all-pairs"))
@pytest.mark.parametrize("row", VECTORS["neighbors"], ids=lambda row: str(row["n"]))
def test_neighbor_weights_depend_on_step_size(engine, row):
    weight, _ = engine.weight(row["l"], row["n"])
    assert weight == row["weight"]
    assert weight != VECTORS["printed"][0]["weight"]


@pytest.mark.parametrize("ell", AGREEMENT_PRIMES)
def test_independent_weights_and_last_indices_agree(ell):
    n = slope_predicates.step_size(ell)
    assert slopemodel_a.weight(ell, n) == slopemodel_b.weight(ell, n)


@pytest.mark.parametrize("ell", [3, 5, 7, 11])
def test_small_primes_and_edge_steps_agree(ell):
    for n in range(1, ell - 1):
        assert slopemodel_a.weight(ell, n) == slopemodel_b.weight(ell, n)


@pytest.mark.parametrize(("ell", "expected"), [(65537, 144), (971153, 556), (1048583, 578), (4194301, 1155)])
def test_campaign_step_rule(ell, expected):
    assert slope_predicates.step_size(ell) == expected
    assert slope_hunt_verifier.step_size(ell) == expected


@pytest.mark.parametrize("engine", ENGINES, ids=("incremental", "all-pairs"))
@pytest.mark.parametrize(("ell", "n"), [(2, 1), (9, 1), (True, 1), (4194305, 100), (7, 0), (7, 6), (7, True)])
def test_engines_refuse_invalid_parameters(engine, ell, n):
    with pytest.raises(ValueError, match="must be"):
        engine.weight(ell, n)


@pytest.mark.parametrize(("t", "expected"), [(3, 3), (4, 5), (65536, 65537), (971152, 971153)])
def test_independent_next_prime(t, expected):
    assert slopemodel_b.next_prime(t) == expected


@pytest.mark.parametrize("t", [2, True, 4194304, 4194305])
def test_independent_next_prime_refuses_outside_bound(t):
    with pytest.raises(ValueError, match=r"must be|exceeds l bound"):
        slopemodel_b.next_prime(t)
