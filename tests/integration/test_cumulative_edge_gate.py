import sys
from pathlib import Path

import pytest

from cairn import keycharge, runner, substrate
from cairn.tiergate import CUMULATIVE_EDGE, HYPOTHESIS_TICKET_TIER, Admitted, Launch, TierGate, TierRefused

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _substrate_helpers as helpers
from test_tier_gate import synthetic_profile
from test_tier_gate_tickets import METHOD, certify, gate, plan, record_hypothesis, seed_table  # noqa: F401

EDGE = 100.0
OFF_PLAN_BITS = 45
RUNG_BITS = 40
HOLD_OUT_BITS = 60
RECEIPT_BASE = {name: ("aa" * 32 if name.endswith(("hash", "digest")) else 1) for name in substrate.RECEIPT_FIELDS}


@pytest.fixture
def world(gate, monkeypatch):  # noqa: F811
    sub, gate_bundle = gate
    monkeypatch.setitem(gate_bundle.tiers, keycharge.EDGE_KEY, EDGE)
    tier_gate = TierGate(sub, gate_bundle, attest_path=sub._test_attest_path)
    return sub, gate_bundle, tier_gate, certify(sub), record_hypothesis(sub).hash


@pytest.fixture
def null_edge_world(gate):  # noqa: F811
    sub, gate_bundle = gate
    assert gate_bundle.tiers[keycharge.EDGE_KEY] is None
    tier_gate = TierGate(sub, gate_bundle, attest_path=sub._test_attest_path)
    return sub, gate_bundle, tier_gate, certify(sub), record_hypothesis(sub).hash


def launch(key, skill, core_s, *, declared_tier=1, bits=OFF_PLAN_BITS, **extra):
    return Launch(
        cost_profile=synthetic_profile(core_s, bits=bits),
        inputs={"bits": bits},
        budget_remaining=10_000_000.0,
        hypothesis_key=key,
        method_identity=METHOD,
        skill_identity_hash=skill,
        declared_tier=declared_tier,
        **extra,
    )


def worker_total(sub, key):
    return keycharge.metered(sub, key, HYPOTHESIS_TICKET_TIER)


def close_with_receipt(sub, *, cpu_user_s, cpu_sys_s, seed):
    receipt = sub.put_receipt(
        {**RECEIPT_BASE, "cpu_user_s": cpu_user_s, "cpu_sys_s": cpu_sys_s, "measurement_scope": "tree"}
    )
    attempt_id = sub.start_attempt(sub.put_recipe(helpers.recipe(seed=seed)))
    sub.close_attempt(attempt_id, "OK", receipt_hash=receipt)
    return runner.Attempt(attempt_id, "recipe", "OK", receipt_hash=receipt)


def test_worker_launches_below_the_edge_are_admitted_and_each_accrues_its_declared_charge(world):
    sub, _, tier_gate, skill, key = world
    decisions = [tier_gate.admit(launch(key, skill, 30)) for _ in range(3)]
    assert all(isinstance(d, Admitted) for d in decisions), [getattr(d, "reasons", ()) for d in decisions]
    rows = keycharge.rows(sub, key)
    assert [(r["declared_core_s"], r["origin"], r["ticket_tier"]) for r in rows] == [(30, "worker", 0)] * 3
    assert [r["charge_id"] for r in rows] == [d.charge_id for d in decisions]
    assert worker_total(sub, key) == 90


def test_the_launch_that_would_carry_the_charge_past_the_edge_is_refused_at_the_crossing(world):
    sub, gate_bundle, tier_gate, skill, key = world
    for _ in range(3):
        assert isinstance(tier_gate.admit(launch(key, skill, 30)), Admitted)
    refused = tier_gate.admit(launch(key, skill, 11))
    assert isinstance(refused, TierRefused)
    assert refused.reasons == (CUMULATIVE_EDGE,)
    assert [r["reason"] for r in sub.conn.execute("SELECT reason FROM tier_refusals ORDER BY id").fetchall()] == [
        CUMULATIVE_EDGE
    ]
    run = sub.conn.execute(
        "SELECT result, reasons FROM gate_runs WHERE gate = 'tier_gate' ORDER BY rowid DESC"
    ).fetchone()
    assert (run["result"], run["reasons"]) == ("refused", f'["{CUMULATIVE_EDGE}"]')
    assert len(keycharge.rows(sub, key)) == 3
    assert worker_total(sub, key) == 90


def test_a_launch_that_lands_exactly_on_the_edge_is_admitted_and_the_next_is_refused(world):
    sub, _, tier_gate, skill, key = world
    for core_s in (60, 40):
        assert isinstance(tier_gate.admit(launch(key, skill, core_s)), Admitted)
    assert worker_total(sub, key) == EDGE
    refused = tier_gate.admit(launch(key, skill, 0.5))
    assert isinstance(refused, TierRefused) and refused.reasons == (CUMULATIVE_EDGE,)


def test_a_shard_of_small_launches_is_refused_at_the_one_that_crosses(world):
    sub, _, tier_gate, skill, key = world
    outcomes = [type(tier_gate.admit(launch(key, skill, 15))).__name__ for _ in range(8)]
    assert outcomes == ["Admitted"] * 6 + ["TierRefused"] * 2
    assert worker_total(sub, key) == 90


def test_a_refused_crossing_charges_nothing_so_a_smaller_launch_still_fits(world):
    sub, _, tier_gate, skill, key = world
    assert isinstance(tier_gate.admit(launch(key, skill, 95)), Admitted)
    assert isinstance(tier_gate.admit(launch(key, skill, 6)), TierRefused)
    assert isinstance(tier_gate.admit(launch(key, skill, 5)), Admitted)
    assert worker_total(sub, key) == 100


def test_a_second_ladder_run_on_a_key_past_the_edge_is_admitted_charged_and_unmetered(world):
    sub, _, tier_gate, skill, key = world
    assert isinstance(tier_gate.admit(launch(key, skill, 90)), Admitted)
    runs = [tier_gate.admit(launch(key, skill, 40, bits=RUNG_BITS)) for _ in range(2)]
    assert all(isinstance(d, Admitted) for d in runs), [getattr(d, "reasons", ()) for d in runs]
    rungs = [r for r in keycharge.rows(sub, key) if r["origin"] == keycharge.ORIGIN_GATE_OWNED]
    assert [(r["declared_core_s"], r["ticket_tier"]) for r in rungs] == [(40, 0), (40, 0)]
    assert worker_total(sub, key) == 90
    assert isinstance(tier_gate.admit(launch(key, skill, 11)), TierRefused)
    assert isinstance(tier_gate.admit(launch(key, skill, 10)), Admitted)


@pytest.mark.parametrize("origin", [keycharge.ORIGIN_GATE_OWNED, keycharge.ORIGIN_RECORDED_RERUN])
def test_a_launch_the_caller_marks_gate_owned_or_a_recorded_rerun_is_charged_and_never_metered(world, origin):
    sub, _, tier_gate, skill, key = world
    assert isinstance(tier_gate.admit(launch(key, skill, 90)), Admitted)
    exempt = tier_gate.admit(launch(key, skill, 500, origin=origin))
    assert isinstance(exempt, Admitted), getattr(exempt, "reasons", ())
    assert keycharge.charge(sub, exempt.charge_id)["origin"] == origin
    assert worker_total(sub, key) == 90


def test_reconciling_to_a_lower_measured_cost_reopens_room_under_the_edge(world):
    sub, _, tier_gate, skill, key = world
    first = tier_gate.admit(launch(key, skill, 45))
    second = tier_gate.admit(launch(key, skill, 45))
    assert isinstance(tier_gate.admit(launch(key, skill, 20)), TierRefused)
    keycharge.settle_launch(sub, first.charge_id, close_with_receipt(sub, cpu_user_s=3.0, cpu_sys_s=2.0, seed=1))
    assert worker_total(sub, key) == 50
    assert isinstance(tier_gate.admit(launch(key, skill, 20)), Admitted)
    assert second.charge_id != first.charge_id


def test_reconciling_to_a_higher_measured_cost_closes_room_the_declaration_claimed(world):
    sub, _, tier_gate, skill, key = world
    understated = tier_gate.admit(launch(key, skill, 2))
    keycharge.settle_launch(sub, understated.charge_id, close_with_receipt(sub, cpu_user_s=90.0, cpu_sys_s=9.5, seed=2))
    assert worker_total(sub, key) == 99.5
    assert isinstance(tier_gate.admit(launch(key, skill, 1)), TierRefused)
    assert isinstance(tier_gate.admit(launch(key, skill, 0.5)), Admitted)


def test_a_reconciled_row_reads_the_receipt_cpu_sum_beside_the_declaration(world):
    sub, _, tier_gate, skill, key = world
    admitted = tier_gate.admit(launch(key, skill, 30))
    attempt = close_with_receipt(sub, cpu_user_s=7.25, cpu_sys_s=0.5, seed=3)
    keycharge.settle_launch(sub, admitted.charge_id, attempt)
    row = keycharge.charge(sub, admitted.charge_id)
    assert (row["declared_core_s"], row["measured_core_s"], row["attempt_id"]) == (30, 7.75, attempt.attempt_id)


def test_a_launch_served_from_the_cache_settles_at_zero(world):
    sub, _, tier_gate, skill, key = world
    admitted = tier_gate.admit(launch(key, skill, 80))
    keycharge.settle_launch(sub, admitted.charge_id, runner.Attempt("old", "recipe", "OK", served_from_cache=True))
    assert worker_total(sub, key) == 0.0


def test_a_fresh_tier_two_ticket_lifts_the_edge_and_the_same_launch_before_it_is_refused(world, plan):  # noqa: F811
    sub, gate_bundle, tier_gate, skill, key = world
    assert isinstance(tier_gate.admit(launch(key, skill, 90)), Admitted)
    before = tier_gate.admit(launch(key, skill, 20))
    assert isinstance(before, TierRefused) and CUMULATIVE_EDGE in before.reasons

    seed_table(sub, plan, "run-keep", hypothesis_hash=key)
    after = tier_gate.admit(launch(key, skill, 20, bits=HOLD_OUT_BITS, declared_tier=2))
    assert isinstance(after, Admitted), after.reasons
    assert after.ticket_tier == 1
    assert (keycharge.charge(sub, after.charge_id)["ticket_tier"], worker_total(sub, key)) == (1, 90)
    still_tier_one = tier_gate.admit(launch(key, skill, 20))
    assert isinstance(still_tier_one, Admitted), still_tier_one.reasons


def test_a_tier_zero_launch_holds_no_ticket_and_is_never_metered(world):
    sub, _, tier_gate, skill, key = world
    assert isinstance(tier_gate.admit(launch(key, skill, 90)), Admitted)
    free = tier_gate.admit(launch(key, skill, 0.5, declared_tier=0, bits=OFF_PLAN_BITS))
    assert isinstance(free, Admitted)
    assert keycharge.charge(sub, free.charge_id)["ticket_tier"] is None
    assert worker_total(sub, key) == 90


def test_with_the_edge_null_no_launch_is_refused_however_much_the_key_has_been_charged(null_edge_world):
    sub, _, tier_gate, skill, key = null_edge_world
    decisions = [tier_gate.admit(launch(key, skill, 3000)) for _ in range(5)]
    assert all(isinstance(d, Admitted) for d in decisions)
    assert worker_total(sub, key) == 15000
    assert sub.conn.execute("SELECT COUNT(*) FROM tier_refusals").fetchone()[0] == 0


def test_a_malformed_edge_stops_the_gate_instead_of_reading_as_no_metering(world):
    sub, gate_bundle, tier_gate, skill, key = world
    gate_bundle.tiers[keycharge.EDGE_KEY] = -5
    with pytest.raises(keycharge.ChargeError, match=keycharge.EDGE_KEY):
        tier_gate.admit(launch(key, skill, 1))
    assert keycharge.rows(sub, key) == []
