import sys
from pathlib import Path

import pytest
from hypothesis import example, given
from hypothesis import strategies as st

from cairn import tiergate
from cairn.tiergate import BUDGET, REASON_ORDER, TICKET_BUNDLE_MISMATCH, UNCERTIFIED, YANKED

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from mutants import tiergate_mutants  # noqa: E402

BOUNDARY_EDGES = (1, 3600, 3_600_000)

facts = st.fixed_dictionaries(
    {
        "declared_tier": st.integers(min_value=0, max_value=3),
        "ticket_tier": st.one_of(st.none(), st.integers(min_value=0, max_value=3)),
        "cost_tier": st.integers(min_value=0, max_value=3),
        "certified": st.booleans(),
        "yanked": st.booleans(),
        "budget_ok": st.booleans(),
        "ticket_bundle_matches": st.booleans(),
        "profile_declared": st.booleans(),
    }
)


def _is_subsequence(reasons, order=REASON_ORDER):
    it = iter(order)
    return all(r in it for r in reasons)


@given(facts)
@example({**dict.fromkeys(("certified", "budget_ok", "ticket_bundle_matches", "profile_declared"), True), "declared_tier": 0, "ticket_tier": None, "cost_tier": 0, "yanked": False})
def test_reasons_are_a_subsequence_of_the_fixed_order(row):
    reasons = tiergate.predicate_reasons(**row)
    assert _is_subsequence(reasons)
    assert len(set(reasons)) == len(reasons)


STANDING = {UNCERTIFIED, YANKED, BUDGET, TICKET_BUNDLE_MISMATCH}
STANDING_REPAIR = {"certified": True, "yanked": False, "budget_ok": True, "ticket_bundle_matches": True}


@given(facts)
def test_repairing_the_standing_facts_removes_exactly_their_reasons_and_admits_iff_nothing_else_was_wrong(row):
    before = set(tiergate.predicate_reasons(**row))
    after = set(tiergate.predicate_reasons(**{**row, **STANDING_REPAIR}))
    assert before - after == before & STANDING
    assert after - before == set()
    assert (after == set()) == (before <= STANDING)


@pytest.mark.parametrize(("weakened", "value"), [("certified", False), ("yanked", True), ("budget_ok", False)], ids=["uncertified", "yanked", "no-budget"])
@given(row=facts)
def test_adding_a_failing_standing_yank_or_budget_predicate_never_removes_a_reason(row, weakened, value):
    before = set(tiergate.predicate_reasons(**row))
    after = set(tiergate.predicate_reasons(**{**row, weakened: value}))
    assert after >= before


@given(facts)
def test_a_launch_with_every_standing_predicate_failing_is_never_admitted(row):
    worst = {**row, "certified": False, "yanked": True, "budget_ok": False}
    assert tiergate.predicate_reasons(**worst) != ()


@pytest.mark.parametrize("edge", BOUNDARY_EDGES, ids=[f"edge-{e}" for e in BOUNDARY_EDGES])
def test_a_cost_exactly_at_an_edge_stays_in_the_lower_tier(edge):
    table = [{"tier": 0, "max_core_s": 1}, {"tier": 1, "max_core_s": 3600}, {"tier": 2, "max_core_s": 3_600_000}, {"tier": 3, "max_core_s": None}]
    at_edge = tiergate.tier_for_cost(table, edge)
    assert tiergate.tier_for_cost(table, edge - 1) == at_edge
    assert tiergate.tier_for_cost(table, edge + 1) == at_edge + 1


REFUSING = {"declared_tier": 2, "ticket_tier": 0, "cost_tier": 3, "certified": False, "yanked": True, "budget_ok": False, "ticket_bundle_matches": False, "profile_declared": True}


def test_short_circuit_gate_mutant_is_killed():
    honest = tiergate.predicate_reasons(**REFUSING)
    assert len(honest) > 1
    with tiergate_mutants.short_circuit_gate():
        mutated = tiergate.predicate_reasons(**REFUSING)
    assert mutated != honest and len(mutated) == 1


def test_reasons_unordered_mutant_is_killed():
    honest = tiergate.predicate_reasons(**REFUSING)
    with tiergate_mutants.reasons_unordered():
        mutated = tiergate.predicate_reasons(**REFUSING)
    assert not _is_subsequence(mutated)
    assert sorted(mutated) == sorted(honest)
