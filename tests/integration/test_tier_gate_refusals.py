import dataclasses
import json
import sys
from pathlib import Path

import pytest

from cairn import bundle, claims, ladderplan, laddertable, tiergate
from cairn.profile import CostProfile, Production, SizeCost, Verification
from cairn.tiergate import (
    BOUNDARY_TABLE,
    TICKET_ABSENT,
    UNCERTIFIED,
    YANKED,
    Admitted,
    Launch,
    TierGate,
    TierRefused,
)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _substrate_helpers as helpers
import factories

BUDGET_PLENTY = 10_000_000.0
METHOD_IDENTITY = {"interface_version": "toy_curve/1", "params": {"r": "20"}}

FIT_BITS = 50
HOLD_OUT_BITS = 60
OFF_PLAN_BITS = 45
TIER_TWO_CORE_S = 4000.0
TIER_ONE_CORE_S = 60.0
TIER_THREE_CORE_S = 4_000_000.0
REVISION = "aa" * 32

TRIAL_BASE = laddertable.Trial(
    bits=0,
    trial=0,
    seed=1,
    instance_hash="aa" * 32,
    recovered=True,
    completed=True,
    gate_ops=1000000,
    reported_ops=1000000,
    cpu_seconds="1",
    wall_seconds="1",
    peak_rss_bytes=1000,
    scratch_bytes=1000,
    reported_memory_bytes=1000,
    replay_grade="Replayable",
)
RUNG_BASE = laddertable.RungRow(
    bits=0,
    role=ladderplan.ROLE_FIT,
    trials=2,
    mean_ops="1000000",
    sd_ops="0",
    cpu_seconds="1",
    reference_rate="1000000",
    memory_bytes=100000,
    success_rate="1",
    radius="0.1216",
    claim_ci_low="1.5",
    claim_ci_high="1.8",
    model_prediction="1000000",
    model_band="0.05",
    shape_statistic="1",
    declared_shape="stable",
)
TABLE_BASE = laddertable.ResultTable(
    run_id="run-keep",
    nonce="nonce-1",
    hypothesis_hash="aa" * 32,
    method_identity=METHOD_IDENTITY,
    implementation_revision=REVISION,
    gate_bundle_hash="cc" * 32,
    plan_hash="dd" * 32,
    uncounted_backend=None,
    rungs=(),
    trials=(),
)


@pytest.fixture
def plan():
    return ladderplan.LadderPlan.load(
        json.loads((Path(__file__).resolve().parents[2] / "bundle" / "ladder_plan.json").read_text())
    )


def keep_table(hypothesis_hash):
    sizes = [30, 40, FIT_BITS, HOLD_OUT_BITS]
    return dataclasses.replace(
        TABLE_BASE,
        hypothesis_hash=hypothesis_hash,
        rungs=tuple(
            dataclasses.replace(
                RUNG_BASE, bits=b, role=ladderplan.ROLE_HOLD_OUT if b == HOLD_OUT_BITS else ladderplan.ROLE_FIT
            )
            for b in sizes
        ),
        trials=tuple(dataclasses.replace(TRIAL_BASE, bits=b, trial=t) for b in sizes for t in (0, 1)),
    )


def profile_at(core_s, bits):
    return CostProfile(
        tier=0,
        production=Production(
            model="synthetic",
            per_size={bits: SizeCost(mean_tries=1.0, sd_tries=0.0, per_try_s=core_s, mean_wall_s=core_s)},
        ),
        verification=Verification(grade="Verifiable", cost_model="same_as_production"),
        source="tests/integration/test_tier_gate_refusals.py",
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


def uncertified(sub, identity=None):
    return sub.put_identity_bundle(identity or helpers.IDENTITY_A)


def record_hypothesis(sub, seed=0):
    obj = factories.hypothesis_object(seed=seed, method_identity=METHOD_IDENTITY)
    claims.write_hypothesis_object(sub, obj)
    return obj


def launch(*, hypothesis_key, skill_identity_hash, bits, core_s, declared_tier=1):
    return Launch(
        cost_profile=profile_at(core_s, bits),
        inputs=bits,
        budget_remaining=BUDGET_PLENTY,
        hypothesis_key=hypothesis_key,
        method_identity=METHOD_IDENTITY,
        skill_identity_hash=skill_identity_hash,
        declared_tier=declared_tier,
    )


def refusals(sub):
    return [dict(r) for r in sub.conn.execute("SELECT * FROM tier_refusals ORDER BY rowid")]


def reasons_recorded(sub):
    return [row["reason"] for row in refusals(sub)]


def seeded(gate, *, bits, core_s, certified=True, yank=False, declared_tier=1):
    tier_gate, sub, _ = gate
    identity_hash = certify(sub) if certified else uncertified(sub)
    if yank:
        sub.add_yank_record(
            "yank-1",
            identity_hash,
            "all",
            kind="human_path",
            ruling_ref="ruling-1",
            record_digest="a" * 64,
            file_offset=0,
        )
    obj = record_hypothesis(sub)
    return tier_gate.admit(
        launch(
            hypothesis_key=obj.hash,
            skill_identity_hash=identity_hash,
            bits=bits,
            core_s=core_s,
            declared_tier=declared_tier,
        )
    )


def test_a_fit_rung_declaring_tier_one_is_admitted_though_the_table_assigns_its_cost_tier_two(gate):
    _, sub, _ = gate
    decision = seeded(gate, bits=FIT_BITS, core_s=TIER_TWO_CORE_S)
    assert isinstance(decision, Admitted)
    assert decision.reasons == ()
    assert refusals(sub) == []


def test_the_hold_out_rung_is_tiered_by_its_own_declared_cost_and_is_refused(gate):
    _, sub, _ = gate
    decision = seeded(gate, bits=HOLD_OUT_BITS, core_s=TIER_TWO_CORE_S)
    assert isinstance(decision, TierRefused)
    assert BOUNDARY_TABLE in decision.reasons
    assert BOUNDARY_TABLE in reasons_recorded(sub)


def test_a_size_the_pinned_plan_holds_no_rung_for_is_off_plan_rather_than_exempt(gate):
    decision = seeded(gate, bits=OFF_PLAN_BITS, core_s=TIER_TWO_CORE_S)
    assert isinstance(decision, TierRefused)
    assert BOUNDARY_TABLE in decision.reasons


def test_a_fit_rung_within_its_tier_is_admitted_and_records_no_refusal(gate):
    _, sub, _ = gate
    decision = seeded(gate, bits=FIT_BITS, core_s=TIER_ONE_CORE_S)
    assert isinstance(decision, Admitted)
    assert refusals(sub) == []


def test_a_yanked_revision_is_refused_while_holding_its_tier_one_ticket(gate):
    _, sub, _ = gate
    decision = seeded(gate, bits=FIT_BITS, core_s=TIER_ONE_CORE_S, yank=True)
    assert isinstance(decision, TierRefused)
    assert YANKED in decision.reasons
    assert TICKET_ABSENT not in decision.reasons
    assert decision.ticket_tier is not None
    assert YANKED in reasons_recorded(sub)


def test_an_uncertified_revision_is_refused_while_holding_its_tier_one_ticket(gate):
    _, sub, _ = gate
    decision = seeded(gate, bits=FIT_BITS, core_s=TIER_ONE_CORE_S, certified=False)
    assert isinstance(decision, TierRefused)
    assert UNCERTIFIED in decision.reasons
    assert TICKET_ABSENT not in decision.reasons
    assert UNCERTIFIED in reasons_recorded(sub)


def test_a_yanked_and_uncertified_revision_names_both_reasons_rather_than_the_first(gate):
    _, sub, _ = gate
    decision = seeded(gate, bits=FIT_BITS, core_s=TIER_ONE_CORE_S, certified=False, yank=True)
    assert {UNCERTIFIED, YANKED} <= set(decision.reasons)
    assert {UNCERTIFIED, YANKED} <= set(reasons_recorded(sub))
    assert len(decision.refusal_ids) == len(decision.reasons)


def test_the_exemption_does_not_survive_a_yank(gate):
    decision = seeded(gate, bits=FIT_BITS, core_s=TIER_TWO_CORE_S, yank=True)
    assert isinstance(decision, TierRefused)
    assert YANKED in decision.reasons
    assert BOUNDARY_TABLE not in decision.reasons


def test_an_unchanged_resubmission_is_refused_again_and_records_its_own_rows(gate):
    tier_gate, sub, _ = gate
    identity_hash = uncertified(sub)
    obj = record_hypothesis(sub)
    resubmitted = launch(
        hypothesis_key=obj.hash,
        skill_identity_hash=identity_hash,
        bits=FIT_BITS,
        core_s=TIER_ONE_CORE_S,
    )
    first = tier_gate.admit(resubmitted)
    after_first = len(refusals(sub))
    second = tier_gate.admit(resubmitted)
    assert isinstance(first, TierRefused)
    assert isinstance(second, TierRefused)
    assert second.reasons == first.reasons
    assert len(refusals(sub)) == after_first + len(second.reasons)


def test_a_tier_two_declaration_for_a_tier_two_cost_is_admitted_while_its_keep_ticket_stands(gate, plan):
    tier_gate, sub, _ = gate
    identity_hash = certify(sub)
    obj = record_hypothesis(sub)
    laddertable.write(sub, keep_table(obj.hash), plan)
    decision = tier_gate.admit(
        launch(
            hypothesis_key=obj.hash,
            skill_identity_hash=identity_hash,
            bits=HOLD_OUT_BITS,
            core_s=TIER_TWO_CORE_S,
            declared_tier=2,
        )
    )
    assert isinstance(decision, Admitted), decision.reasons
    assert decision.ticket_tier == tiergate.TIER_TWO_TICKET_TIER
    assert refusals(sub) == []


def test_a_fit_rung_whose_declared_cost_clears_the_tier_three_edge_is_refused_rather_than_exempt(gate):
    _, sub, _ = gate
    decision = seeded(gate, bits=FIT_BITS, core_s=TIER_THREE_CORE_S)
    assert isinstance(decision, TierRefused)
    assert BOUNDARY_TABLE in decision.reasons
    assert BOUNDARY_TABLE in reasons_recorded(sub)
