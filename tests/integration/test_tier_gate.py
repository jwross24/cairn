import json
import sys
from pathlib import Path

import pytest

from cairn import bundle, claims, keys
from cairn.profile import CostProfile, Production, SizeCost, Verification
from cairn.tiergate import (
    BOUNDARY_TABLE,
    BUDGET,
    PROFILE_UNDECLARED,
    TICKET_ABSENT,
    TICKET_BUNDLE_MISMATCH,
    TIER_TWO_ABOVE,
    UNCERTIFIED,
    YANKED,
    Admitted,
    Launch,
    TierGate,
    TierRefused,
)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _substrate_helpers as helpers  # noqa: E402
import factories  # noqa: E402

BUDGET_PLENTY = 10_000_000.0
METHOD_IDENTITY = {"interface_version": "toy_curve/1", "params": {"r": "20"}}


def synthetic_profile(core_s, *, bits=40, tier=0):
    """A CostProfile the tier gate can evaluate; never the toy-curve one, so the gate's tests do not move with a measurement.

    `same_as_production` makes verification cost the same, so a launch charges 2 * core_s against the budget.
    """
    return CostProfile(
        tier=tier,
        production=Production(model="synthetic", per_size={bits: SizeCost(mean_tries=1.0, sd_tries=0.0, per_try_s=core_s, mean_wall_s=core_s)}),
        verification=Verification(grade="Verifiable", cost_model="same_as_production"),
        source="tests/integration/test_tier_gate.py",
    )


@pytest.fixture
def gate(tmp_path, pinned_bundle):
    bundle_path, pin_path = pinned_bundle()
    sub = helpers.open_writer(tmp_path)
    gate_bundle = bundle.GateBundle.open(bundle_path, pin_path)
    yield TierGate(sub, gate_bundle), sub, gate_bundle
    sub.close()


def certify(sub, identity=None):
    identity = identity or helpers.IDENTITY_A
    identity_hash = sub.put_identity_bundle(identity)
    sub.put_certificate(identity_hash, helpers.TRANSCRIPT_HASH, helpers.ENV_MANIFEST_HASH, helpers.SELFTEST_SUMMARY)
    return identity_hash


def record_hypothesis(sub, seed=0):
    obj = factories.hypothesis_object(seed=seed, method_identity=METHOD_IDENTITY)
    claims.write_hypothesis_object(sub, obj)
    return obj


def launch(sub, *, declared_tier=0, core_s=0.1, budget=BUDGET_PLENTY, hypothesis_key=None, skill_identity_hash=None, bits=40):
    return Launch(
        cost_profile=synthetic_profile(core_s, bits=bits),
        inputs=bits,
        budget_remaining=budget,
        hypothesis_key=hypothesis_key or ("f" * 64),
        method_identity=METHOD_IDENTITY,
        skill_identity_hash=skill_identity_hash,
        declared_tier=declared_tier,
    )


def gate_runs(sub):
    return [dict(r) for r in sub.conn.execute("SELECT * FROM gate_runs WHERE gate = 'tier_gate' ORDER BY rowid")]


def tickets(sub):
    return [dict(r) for r in sub.conn.execute("SELECT * FROM tickets ORDER BY rowid")]


def test_a_tier_zero_launch_on_a_certified_skill_is_admitted_and_recorded(gate, db_snapshot):
    tier_gate, sub, gate_bundle = gate
    identity = certify(sub)
    decision = tier_gate.admit(launch(sub, declared_tier=0, core_s=0.1, skill_identity_hash=identity))
    assert isinstance(decision, Admitted)
    assert decision.reasons == ()
    runs = gate_runs(sub)
    assert len(runs) == 1
    assert runs[0]["result"] == "admitted"
    assert json.loads(runs[0]["reasons"]) == []
    assert runs[0]["bundle_hash"] == gate_bundle.hash and runs[0]["pin_hash"] == gate_bundle.pin_hash
    assert tickets(sub) == []
    db_snapshot(sub.conn, "after-tier0-admission")


def test_a_tier_one_launch_with_a_recorded_hypothesis_object_is_admitted_and_mints_its_ticket(gate, db_snapshot):
    tier_gate, sub, gate_bundle = gate
    identity = certify(sub)
    obj = record_hypothesis(sub)
    decision = tier_gate.admit(launch(sub, declared_tier=1, core_s=10, hypothesis_key=obj.hash, skill_identity_hash=identity))
    assert isinstance(decision, Admitted)
    rows = tickets(sub)
    assert len(rows) == 1
    assert rows[0]["tier"] == 0 and rows[0]["kind"] == "hypothesis_object"
    assert rows[0]["node_hash"] == obj.hash
    assert rows[0]["bundle_hash"] == gate_bundle.hash
    assert decision.ticket_hash == rows[0]["ticket_hash"]
    db_snapshot(sub.conn, "after-tier1-admission")


def test_a_second_admitted_launch_reads_the_existing_ticket_and_mints_no_duplicate(gate):
    tier_gate, sub, _ = gate
    identity = certify(sub)
    obj = record_hypothesis(sub)
    first = tier_gate.admit(launch(sub, declared_tier=1, core_s=10, hypothesis_key=obj.hash, skill_identity_hash=identity))
    second = tier_gate.admit(launch(sub, declared_tier=1, core_s=10, hypothesis_key=obj.hash, skill_identity_hash=identity))
    assert isinstance(second, Admitted)
    assert second.ticket_hash == first.ticket_hash
    assert len(tickets(sub)) == 1


REFUSAL_CASES = [
    ("ticket-absent", {"declared_tier": 1, "core_s": 10}, (TICKET_ABSENT,), False),
    ("tier-two-above", {"declared_tier": 2, "core_s": 10}, (TIER_TWO_ABOVE,), True),
    ("boundary-table", {"declared_tier": 0, "core_s": 100}, (BOUNDARY_TABLE,), False),
    ("budget", {"declared_tier": 0, "core_s": 0.4, "budget": 0.5}, (BUDGET,), False),
    ("boundary-and-budget", {"declared_tier": 0, "core_s": 100, "budget": 1.0}, (BOUNDARY_TABLE, BUDGET), False),
]


@pytest.mark.parametrize(("name", "delta", "expected", "needs_hypothesis"), REFUSAL_CASES, ids=[c[0] for c in REFUSAL_CASES])
def test_a_refused_launch_names_every_failed_predicate(gate, name, delta, expected, needs_hypothesis):
    tier_gate, sub, _ = gate
    identity = certify(sub)
    key = record_hypothesis(sub).hash if needs_hypothesis else "f" * 64
    decision = tier_gate.admit(launch(sub, hypothesis_key=key, skill_identity_hash=identity, **delta))
    assert isinstance(decision, TierRefused)
    assert decision.reasons == expected
    runs = gate_runs(sub)
    assert runs[-1]["result"] == "refused"
    assert json.loads(runs[-1]["reasons"]) == list(expected)
    refusals = claims.tier_refusals_for(sub, key)
    assert [row["reason"] for row in refusals] == list(expected)


def test_an_uncertified_skill_is_refused(gate):
    tier_gate, sub, _ = gate
    decision = tier_gate.admit(launch(sub, declared_tier=0, core_s=0.1, skill_identity_hash="9" * 64))
    assert isinstance(decision, TierRefused)
    assert decision.reasons == (UNCERTIFIED,)


def test_a_yanked_skill_is_refused(gate):
    tier_gate, sub, _ = gate
    identity = certify(sub)
    sub.add_yank_record("yank-1", identity, "all", record_digest="a" * 64, file_offset=0)
    decision = tier_gate.admit(launch(sub, declared_tier=0, core_s=0.1, skill_identity_hash=identity))
    assert isinstance(decision, TierRefused)
    assert decision.reasons == (YANKED,)


def test_an_uncertified_tier_two_launch_names_both_reasons(gate):
    tier_gate, sub, _ = gate
    obj = record_hypothesis(sub)
    decision = tier_gate.admit(launch(sub, declared_tier=2, core_s=10, hypothesis_key=obj.hash, skill_identity_hash="9" * 64))
    assert decision.reasons == (TIER_TWO_ABOVE, UNCERTIFIED)


def test_a_profile_that_declares_no_such_size_refuses_and_leaves_the_cost_predicates_unevaluated(gate):
    tier_gate, sub, _ = gate
    identity = certify(sub)
    undeclared = launch(sub, declared_tier=0, core_s=10_000_000, budget=0.0, skill_identity_hash=identity, bits=40)
    undeclared = Launch(**{**undeclared.__dict__, "inputs": 41})
    decision = tier_gate.admit(undeclared)
    assert isinstance(decision, TierRefused)
    assert decision.reasons == (PROFILE_UNDECLARED,)
    assert BOUNDARY_TABLE not in decision.reasons and BUDGET not in decision.reasons


def test_a_stale_bundle_ticket_is_refused_once_reminted_and_admitted_on_the_next_launch(gate, db_snapshot):
    tier_gate, sub, gate_bundle = gate
    identity = certify(sub)
    obj = record_hypothesis(sub)
    stale = claims.Ticket(
        hypothesis_key=obj.hash,
        method_identity=METHOD_IDENTITY,
        statement_hash=None,
        tier=0,
        kind="hypothesis_object",
        node_hash=obj.hash,
        bundle_hash="0" * 64,
    )
    claims.write_ticket(sub, stale)
    args = dict(declared_tier=1, core_s=10, hypothesis_key=obj.hash, skill_identity_hash=identity)

    refused = tier_gate.admit(launch(sub, **args))
    assert isinstance(refused, TierRefused)
    assert refused.reasons == (TICKET_BUNDLE_MISMATCH,)
    rows = tickets(sub)
    assert len(rows) == 2
    assert rows[0]["bundle_hash"] == "0" * 64
    assert rows[1]["bundle_hash"] == gate_bundle.hash
    assert refused.reminted_ticket_hash == rows[1]["ticket_hash"]

    readmitted = tier_gate.admit(launch(sub, **args))
    assert isinstance(readmitted, Admitted)
    assert readmitted.ticket_hash == rows[1]["ticket_hash"]
    assert len(tickets(sub)) == 2
    db_snapshot(sub.conn, "after-remint")


def test_a_waiver_produces_no_ticket_and_admits_no_tier(gate, tmp_path, clear_flags):
    from cairn import attest

    tier_gate, sub, gate_bundle = gate
    log_path = tmp_path / "attestations.log"
    clear_flags(log_path)
    attest.init(log_path, gate_bundle.waiver_target())
    waiver = attest.fixture_waiver(gate_bundle.waiver_target())
    assert attest.attestation_record_matches(log_path, 0, claims.blob_hash(attest.waiver_canonical(waiver)))
    assert gate_bundle.waivable_checks == []

    identity = certify(sub)
    obj = record_hypothesis(sub)
    assert keys.hypothesis_key(gate_bundle.waiver_hypothesis()) == waiver["target"]
    decision = tier_gate.admit(launch(sub, declared_tier=2, core_s=10, hypothesis_key=obj.hash, skill_identity_hash=identity))
    assert isinstance(decision, TierRefused)
    assert TIER_TWO_ABOVE in decision.reasons
    assert tickets(sub) == []


def test_every_decision_records_the_bundle_and_pin_hash_it_judged_under(gate):
    tier_gate, sub, gate_bundle = gate
    identity = certify(sub)
    tier_gate.admit(launch(sub, declared_tier=0, core_s=0.1, skill_identity_hash=identity))
    tier_gate.admit(launch(sub, declared_tier=0, core_s=100, skill_identity_hash=identity))
    runs = gate_runs(sub)
    assert len(runs) == 2
    assert {r["bundle_hash"] for r in runs} == {gate_bundle.hash}
    assert {r["pin_hash"] for r in runs} == {gate_bundle.pin_hash}
    assert [r["result"] for r in runs] == ["admitted", "refused"]


def test_admitted_is_exactly_the_decision_whose_reasons_are_empty(gate):
    tier_gate, sub, _ = gate
    identity = certify(sub)
    obj = record_hypothesis(sub)
    cases = [
        launch(sub, declared_tier=0, core_s=0.1, skill_identity_hash=identity),
        launch(sub, declared_tier=1, core_s=10, hypothesis_key=obj.hash, skill_identity_hash=identity),
        launch(sub, declared_tier=0, core_s=100, skill_identity_hash=identity),
        launch(sub, declared_tier=0, core_s=0.1, skill_identity_hash="9" * 64),
        launch(sub, declared_tier=2, core_s=10, hypothesis_key=obj.hash, skill_identity_hash=identity),
    ]
    decisions = []
    for case in cases:
        decision = tier_gate.admit(case)
        decisions.append(decision)
        assert isinstance(decision, Admitted) == (decision.reasons == ())
        assert isinstance(decision, TierRefused) == (decision.reasons != ())
    assert [d.reasons for d in decisions] == [(), (), (BOUNDARY_TABLE,), (UNCERTIFIED,), (TIER_TWO_ABOVE,)]
    recorded = {(r["result"], r["reasons"]) for r in gate_runs(sub)}
    assert recorded == {("admitted", "[]"), ("refused", json.dumps([BOUNDARY_TABLE])), ("refused", json.dumps([UNCERTIFIED])), ("refused", json.dumps([TIER_TWO_ABOVE]))}


def test_two_indistinguishable_decisions_in_one_second_are_one_content_addressed_row(gate, monkeypatch):
    """gate_runs is keyed by the hash of the decision's content, and that content names no launch: an auditor
    reading the table sees which verdicts were reached under which bundle, not how many launches reached them.
    The launch identity survives in tier_refusals (refusals only) and in the JSON log."""
    tier_gate, sub, _ = gate
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "0")
    identity = certify(sub)
    first = tier_gate.admit(launch(sub, declared_tier=0, core_s=0.1, skill_identity_hash=identity))
    second = tier_gate.admit(launch(sub, declared_tier=0, core_s=0.2, skill_identity_hash=identity))
    assert first.gate_run_hash == second.gate_run_hash
    assert len(gate_runs(sub)) == 1
