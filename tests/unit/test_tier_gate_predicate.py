import itertools

import pytest

from cairn import tiergate
from cairn.tiergate import (
    BOUNDARY_TABLE,
    BUDGET,
    PROFILE_UNDECLARED,
    REASON_ORDER,
    TICKET_ABSENT,
    TICKET_BUNDLE_MISMATCH,
    TIER_TWO_ABOVE,
    UNCERTIFIED,
    YANKED,
)

M0_BOUNDARY_TABLE = [
    {"tier": 0, "max_core_s": 1},
    {"tier": 1, "max_core_s": 3600},
    {"tier": 2, "max_core_s": 3600000},
    {"tier": 3, "max_core_s": None},
]
CLEAN = {
    "declared_tier": 0,
    "ticket_tier": None,
    "cost_tier": 0,
    "certified": True,
    "yanked": False,
    "budget_ok": True,
    "ticket_bundle_matches": True,
    "profile_declared": True,
}


def reasons(**overrides):
    return tiergate.predicate_reasons(**{**CLEAN, **overrides})


def test_a_clean_launch_names_no_reason():
    assert reasons() == ()


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"profile_declared": False}, (PROFILE_UNDECLARED,)),
        ({"declared_tier": 1}, (TICKET_ABSENT,)),
        ({"declared_tier": 2, "ticket_tier": 0}, (TIER_TWO_ABOVE,)),
        ({"declared_tier": 0, "cost_tier": 1}, (BOUNDARY_TABLE,)),
        ({"certified": False}, (UNCERTIFIED,)),
        ({"yanked": True}, (YANKED,)),
        ({"budget_ok": False}, (BUDGET,)),
        ({"ticket_bundle_matches": False}, (TICKET_BUNDLE_MISMATCH,)),
    ],
    ids=list(REASON_ORDER),
)
def test_each_reason_is_reached_by_exactly_its_own_fact(overrides, expected):
    assert reasons(**overrides) == expected


def test_a_declared_profile_leaves_no_cost_reason_unevaluated_and_an_undeclared_one_suppresses_both():
    assert reasons(declared_tier=0, cost_tier=3, budget_ok=False) == (BOUNDARY_TABLE, BUDGET)
    assert reasons(declared_tier=0, cost_tier=3, budget_ok=False, profile_declared=False) == (PROFILE_UNDECLARED,)


def test_a_tier_one_launch_with_a_tier_zero_ticket_is_not_two_above():
    assert reasons(declared_tier=1, ticket_tier=0, cost_tier=1) == ()


def test_an_absent_ticket_is_not_also_two_above():
    assert reasons(declared_tier=1, ticket_tier=None) == (TICKET_ABSENT,)


def test_reasons_accumulate_without_short_circuiting():
    assert reasons(declared_tier=2, ticket_tier=0, certified=False) == (TIER_TWO_ABOVE, UNCERTIFIED)
    everything_else = tuple(r for r in REASON_ORDER if r not in (PROFILE_UNDECLARED, TICKET_ABSENT))
    assert reasons(declared_tier=2, ticket_tier=0, certified=False, yanked=True, budget_ok=False, ticket_bundle_matches=False, cost_tier=3) == everything_else


TRUTH_TABLE_AXES = {
    "declared_tier": (0, 1, 2),
    "ticket_tier": (None, 0),
    "cost_tier": (0, 1),
    "certified": (True, False),
    "yanked": (False, True),
    "budget_ok": (True, False),
    "ticket_bundle_matches": (True, False),
    "profile_declared": (True, False),
}


COUPLING = {
    "declared_tier": {TICKET_ABSENT, TIER_TWO_ABOVE, BOUNDARY_TABLE},
    "ticket_tier": {TICKET_ABSENT, TIER_TWO_ABOVE},
    "cost_tier": {BOUNDARY_TABLE},
    "certified": {UNCERTIFIED},
    "yanked": {YANKED},
    "budget_ok": {BUDGET},
    "ticket_bundle_matches": {TICKET_BUNDLE_MISMATCH},
    "profile_declared": {PROFILE_UNDECLARED, BOUNDARY_TABLE, BUDGET},
}


def _rows():
    names = tuple(TRUTH_TABLE_AXES)
    for values in itertools.product(*(TRUTH_TABLE_AXES[n] for n in names)):
        yield dict(zip(names, values, strict=True))


@pytest.mark.parametrize("axis", list(TRUTH_TABLE_AXES), ids=list(TRUTH_TABLE_AXES))
def test_an_axis_moves_only_the_reasons_it_is_declared_to_couple_to(axis):
    for row in _rows():
        for value in TRUTH_TABLE_AXES[axis]:
            if value == row[axis]:
                continue
            moved = set(tiergate.predicate_reasons(**row)) ^ set(tiergate.predicate_reasons(**{**row, axis: value}))
            assert moved <= COUPLING[axis], f"{axis} {row[axis]!r}->{value!r} moved {sorted(moved - COUPLING[axis])} on {row}"


def test_every_axis_actually_moves_each_reason_it_couples_to():
    moved_by = {axis: set() for axis in TRUTH_TABLE_AXES}
    for row in _rows():
        for axis, values in TRUTH_TABLE_AXES.items():
            for value in values:
                if value != row[axis]:
                    moved_by[axis] |= set(tiergate.predicate_reasons(**row)) ^ set(tiergate.predicate_reasons(**{**row, axis: value}))
    assert moved_by == COUPLING


def test_admitted_is_exactly_the_empty_reason_tuple():
    clean = [row for row in _rows() if tiergate.predicate_reasons(**row) == ()]
    assert clean
    for row in clean:
        assert row["certified"] and not row["yanked"] and row["budget_ok"] and row["ticket_bundle_matches"] and row["profile_declared"]
        assert row["declared_tier"] >= row["cost_tier"]


def test_every_reason_is_reachable_and_every_reachable_reason_is_named():
    reached = {r for row in _rows() for r in tiergate.predicate_reasons(**row)}
    assert reached == set(REASON_ORDER)


@pytest.mark.parametrize(
    ("core_s", "tier"),
    [
        (0, 0),
        (1, 0),
        (1.000001, 1),
        (3600, 1),
        (3600.000001, 2),
        (3_600_000, 2),
        (3_600_000.000001, 3),
        (10**12, 3),
    ],
    ids=["zero", "edge-1-stays-0", "just-above-1", "edge-3600-stays-1", "just-above-3600", "edge-3.6e6-stays-2", "just-above-3.6e6", "far-above"],
)
def test_the_boundary_table_lookup_at_its_edges(core_s, tier):
    assert tiergate.tier_for_cost(M0_BOUNDARY_TABLE, core_s) == tier
