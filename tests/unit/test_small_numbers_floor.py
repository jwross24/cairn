from fractions import Fraction
from pathlib import Path

import pytest

from cairn import hunt, hunt_attempt, hunt_record
from cairn import small_numbers_floor as floor
from cairn.substrate import blob_hash

HUNT_MODULES = (hunt, hunt_record, hunt_attempt)


def _framed(paths):
    framed = bytearray()
    for path in paths:
        name = Path(path).name.encode()
        content = Path(path).read_bytes()
        framed += len(name).to_bytes(8, "big") + name + len(content).to_bytes(8, "big") + content
    return blob_hash(bytes(framed))


def test_the_sampler_identity_covers_every_hunt_module():
    assert tuple(module.__file__ for module in HUNT_MODULES) == floor.SAMPLER_SOURCES
    assert floor.sampler_identity() == _framed(floor.SAMPLER_SOURCES)


@pytest.mark.parametrize("module", HUNT_MODULES, ids=lambda module: module.__name__)
def test_a_one_byte_change_to_any_hunt_module_moves_the_sampler_identity(tmp_path, monkeypatch, module):
    before = floor.sampler_identity()
    changed = tmp_path / Path(module.__file__).name
    changed.write_bytes(Path(module.__file__).read_bytes() + b"\n")
    sources = tuple(str(changed) if path == module.__file__ else path for path in floor.SAMPLER_SOURCES)
    monkeypatch.setattr(floor, "SAMPLER_SOURCES", sources)
    assert floor.sampler_identity() != before


@pytest.mark.parametrize(
    ("outcomes", "stake", "expected"),
    [
        ([0, 0, 1], "1", Fraction(25, 64)),
        ([0, 0], "4/3", Fraction(16, 9)),
        ([0, 1], "4/3", Fraction(0)),
        ([0, 1], "0", Fraction(1)),
    ],
)
def test_hand_checked_wealth(outcomes, stake, expected):
    wealth = Fraction(1)
    for outcome in outcomes:
        wealth = floor.update(wealth, outcome, "1/4", stake)
    assert wealth == expected


def test_threshold_is_exact_and_low_wealth_refuses():
    assert floor.passes("20", "1/20")
    assert not floor.passes(Fraction(20 * 10**30 - 1, 10**30), "1/20")
    assert not floor.passes("1", "1/20")
    assert floor.rational(floor.exact_text(Fraction(1000**6000, 999**6000))) == Fraction(1000**6000, 999**6000)


@pytest.mark.parametrize("value", [True, False, 0.1, float("inf"), float("nan"), "nan", "1/0", None])
def test_invalid_rational_refused(value):
    with pytest.raises(floor.FloorRefused):
        floor.rational(value)


@pytest.mark.parametrize(("epsilon", "alpha"), [("0", "1/20"), ("1", "1/20"), ("1/2", "0"), ("1/2", "1")])
def test_probability_endpoints_refused(epsilon, alpha):
    with pytest.raises(floor.FloorRefused):
        floor.Protocol("p", "h", "d", epsilon, alpha, 1, "study")


@pytest.mark.parametrize(("outcome", "stake"), [(True, "1"), (False, "1"), (2, "1"), (0.0, "1"), (0, "-1"), (0, "3")])
def test_invalid_outcome_and_stake_refused(outcome, stake):
    with pytest.raises(floor.FloorRefused):
        floor.update(1, outcome, "1/2", stake)


def test_distribution_mutation_changes_canonical_hash():
    distribution = hunt.Distribution({"n": (0, 10)})
    plan = hunt.HuntPlan("s", "h", distribution, 1, {"n": (0, 10)})
    protocol = floor.Protocol(plan.hash, plan.hypothesis_key, distribution.hash, "1/2", "1/20", 1, "study")
    object.__setattr__(distribution, "ranges", {"n": (1, 2)})
    with pytest.raises(floor.FloorRefused, match="distribution mutation"):
        floor._validate_plan(protocol, plan)
