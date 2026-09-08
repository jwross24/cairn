import json
from pathlib import Path

import pytest

from cairn import ladderplan
from cairn.tiergate import (
    BOUNDARY_TABLE,
    LADDER_EXEMPT_CEILING_TIER,
    UNCERTIFIED,
    YANKED,
    predicate_reasons,
    tier_for_cost,
)

TIERS = json.loads((Path(__file__).resolve().parents[2] / "bundle" / "tiers.json").read_text())
TABLE = TIERS["boundary_table"]


def reasons(**kw):
    fields = {
        "declared_tier": 1,
        "ticket_tier": 1,
        "cost_tier": 1,
        "certified": True,
        "yanked": False,
        "budget_ok": True,
        "ticket_bundle_matches": True,
        "profile_declared": True,
    }
    return predicate_reasons(**{**fields, **kw})


def test_the_pinned_table_is_the_four_rows_the_tiers_are_defined_over():
    assert [(row["tier"], row["max_core_s"]) for row in TABLE] == [
        (0, 1),
        (1, 3600),
        (2, 3600000),
        (3, None),
    ]


@pytest.mark.parametrize(
    ("core_s", "tier"),
    [
        (0.0, 0),
        (1, 0),
        (1.0001, 1),
        (3600, 1),
        (3600.0001, 2),
        (3600000, 2),
        (3600000.0001, 3),
        (1e12, 3),
    ],
)
def test_every_boundary_value_lands_on_the_tier_its_ceiling_names(core_s, tier):
    assert tier_for_cost(TABLE, core_s) == tier


def test_a_cost_above_every_ceiling_falls_to_the_last_row_rather_than_off_the_table():
    assert tier_for_cost([{"tier": 0, "max_core_s": 1}, {"tier": 1, "max_core_s": 2}], 1e9) == 1


def test_a_declared_tier_below_the_table_s_assignment_is_refused():
    assert BOUNDARY_TABLE in reasons(declared_tier=1, cost_tier=2)


def test_a_declared_tier_at_or_above_the_table_s_assignment_is_not_a_boundary_refusal():
    assert BOUNDARY_TABLE not in reasons(declared_tier=2, cost_tier=2, ticket_tier=2)
    assert BOUNDARY_TABLE not in reasons(declared_tier=3, cost_tier=2, ticket_tier=2)


def test_a_fit_rung_is_admitted_on_the_tier_one_ticket_whatever_the_table_assigns_its_cost():
    assert BOUNDARY_TABLE not in reasons(declared_tier=1, cost_tier=2, boundary_exempt=True)


def test_the_exemption_reaches_the_boundary_reason_alone():
    unmet = reasons(declared_tier=1, cost_tier=2, boundary_exempt=True, certified=False, yanked=True)
    assert set(unmet) == {UNCERTIFIED, YANKED}


def test_an_unexempt_rung_of_the_same_declared_tier_is_still_refused():
    assert BOUNDARY_TABLE in reasons(declared_tier=1, cost_tier=2, boundary_exempt=False)


def test_the_pinned_plan_exempts_its_fit_rungs_and_not_its_hold_out_rung():
    plan = ladderplan.LadderPlan.load(
        json.loads((Path(__file__).resolve().parents[2] / "bundle" / "ladder_plan.json").read_text())
    )
    roles = {rung.bits: rung.role for rung in plan.rungs}
    assert roles == {
        30: ladderplan.ROLE_FIT,
        40: ladderplan.ROLE_FIT,
        50: ladderplan.ROLE_FIT,
        60: ladderplan.ROLE_HOLD_OUT,
    }
    for bits, role in roles.items():
        is_fit = role == ladderplan.ROLE_FIT
        unmet = reasons(declared_tier=1, cost_tier=2, boundary_exempt=is_fit)
        assert (BOUNDARY_TABLE in unmet) is not is_fit, bits


def test_the_exemption_stops_at_the_tier_two_ceiling_and_a_tier_three_cost_is_refused():
    assert BOUNDARY_TABLE in reasons(declared_tier=1, cost_tier=3, boundary_exempt=True)


def test_the_ceiling_is_the_last_tier_the_pinned_table_bounds():
    bounded = [row["tier"] for row in TABLE if row["max_core_s"] is not None]
    assert bounded[-1] == LADDER_EXEMPT_CEILING_TIER


def test_the_exemption_is_the_tier_one_ticket_s_and_does_not_reach_a_tier_zero_declaration():
    assert BOUNDARY_TABLE in reasons(declared_tier=0, cost_tier=1, ticket_tier=None, boundary_exempt=True)
