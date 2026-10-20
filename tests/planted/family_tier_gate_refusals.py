import dataclasses
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import _substrate_helpers as helpers
import factories
import tier_gate_arena as t
from _corpus import MUST_FAIL, MUST_PASS, Entry

from cairn import attest, claims, gateplan, keys, scrutiny, tiergate
from cairn import yank as yank_ops

OWNER = t.OWNER
YANKED_ID = "tier_gate/yanked-revision-refused-whatever-ticket"
UNCERTIFIED_ID = "tier_gate/uncertified-revision-refused-whatever-ticket"
BOUNDARY_ID = "tier_gate/tier-one-declared-for-a-tier-two-cost-refused"
BOUNDARY_FIT_ID = "tier_gate/fit-rung-tier-one-for-a-tier-two-cost-admits"
ROUTER_ID = "tier_gate/target-family-sub-generic-claim-holds-no-tier-three-without-signoff"
WAIVER_TICKET_PRESENT_ID = "tier_gate/waiver-step-with-a-ticket-row-beside-ticket-absent"
WAIVER_NO_TICKET_ID = "tier_gate/waiver-step-without-a-ticket-row-lands-no-ticket"
TICKET_PRESENT = "ticket-present"
BELOW_BOUND = {"exponent": "1/3", "constant": "1", "crossover": 40}
SOURCE_REFUSAL = "test-yank-source"


def _yank(env, identity_hash):
    verdict = claims.GateRun(
        gate="tier_gate",
        bundle_hash=env.bundle.hash,
        pin_hash=env.bundle.pin_hash,
        result="refused",
        reasons=(SOURCE_REFUSAL,),
        at=datetime.now(UTC).isoformat(),
    )
    yank_ops.record(
        env.sub,
        yank_id="yank-1",
        skill_identity_hash=identity_hash,
        kind=yank_ops.GATE_VERDICT,
        attest_path=env.attest_path,
        verdict_ref=claims.write_gate_run(env.sub, verdict),
    )


def _revision_refused(cold, reason, *, certified, yanked):
    env = t.arena(cold)
    skill = t.certify(env) if certified else env.sub.put_identity_bundle(helpers.IDENTITY_A)
    if yanked:
        _yank(env, skill)
    key = t.hypothesis(env)
    t.keep_table(env, key)
    tier_one = env.gate.admit(t.launch(key, skill, tier=1))
    tier_two = env.gate.admit(t.launch(key, skill, tier=2))
    refused = (
        t.refused_with(tier_one, reason, ticket_tier=tiergate.HYPOTHESIS_TICKET_TIER)
        and t.refused_with(tier_two, reason, ticket_tier=tiergate.TIER_TWO_TICKET_TIER)
        and tiergate.TICKET_ABSENT not in tier_one.reasons + tier_two.reasons
    )
    return t.verdict(refused)


def yanked_refused(cold):
    return _revision_refused(cold, tiergate.YANKED, certified=True, yanked=True)


def uncertified_refused(cold):
    return _revision_refused(cold, tiergate.UNCERTIFIED, certified=False, yanked=False)


def boundary_refused(cold):
    env = t.arena(cold)
    skill = t.certify(env)
    key = t.hypothesis(env)
    decision = env.gate.admit(t.launch(key, skill, tier=1, bits=t.HOLD_OUT_BITS, core_s=t.TIER_TWO_CORE_S))
    refused = t.refused_with(decision, tiergate.BOUNDARY_TABLE, ticket_tier=tiergate.HYPOTHESIS_TICKET_TIER)
    recorded = [r["reason"] for r in env.sub.conn.execute("SELECT reason FROM tier_refusals")]
    return t.verdict(refused and tiergate.BOUNDARY_TABLE in recorded)


def boundary_fit_admit(cold):
    env = t.arena(cold)
    skill = t.certify(env)
    key = t.hypothesis(env)
    decision = env.gate.admit(t.launch(key, skill, tier=1, bits=t.FIT_BITS, core_s=t.TIER_TWO_CORE_S))
    return t.ADMIT if t.admitted_at(decision, tiergate.HYPOTHESIS_TICKET_TIER) else t.ACCEPT


def _signoff(env, statement_hash, *, offset=None):
    unplaced = scrutiny.SignOff(
        statement_hash=statement_hash, expert="expert-1", gate_bundle_hash=env.bundle.hash, at=t.AT
    )
    if offset is None:
        offset = attest.append_record(env.attest_path, scrutiny.signoff_canonical(unplaced))
    scrutiny.write_signoff(env.sub, dataclasses.replace(unplaced, file_offset=offset))


def router_top_class(cold):
    env = t.arena(cold)
    skill = t.certify(env)
    obj = factories.hypothesis_object(family="toy_curve", cost_model=BELOW_BOUND, seed=9, method_identity=t.METHOD)
    claims.write_hypothesis_object(env.sub, obj)
    statement = factories.claim_statement(seed=21, family="toy_curve")
    claims.write_claim_statement(env.sub, statement)

    def tier_three():
        return env.gate.admit(t.launch(obj.hash, skill, tier=3, statement_hash=statement.hash))

    read = scrutiny.gate_read(
        env.sub,
        env.bundle,
        hypothesis_key=obj.hash,
        statement_hash=statement.hash,
        declared_tier=3,
        nogo_flagged=False,
        attest_path=env.attest_path,
    )
    if read.scrutiny_class != scrutiny.TOP:
        raise AssertionError(read)
    unsigned = tier_three()
    _signoff(env, statement.hash, offset=4096)
    ghost = tier_three()
    _signoff(env, statement.hash)
    signed = tier_three()
    refused = (
        t.refused_with(unsigned, scrutiny.EXPERT_SIGNOFF_ABSENT)
        and t.refused_with(ghost, scrutiny.EXPERT_SIGNOFF_ABSENT)
        and isinstance(signed, tiergate.TierRefused)
        and scrutiny.EXPERT_SIGNOFF_ABSENT not in signed.reasons
    )
    return t.verdict(refused)


def _waiver_state(cold, *, seed_ticket):
    env = t.arena(cold, session=False)
    fixtures = env.bundle.gate_plan["fixtures"]
    hypothesis = fixtures["waiver_hypothesis"]
    target = keys.hypothesis_key(hypothesis)
    if claims.get_hypothesis_object(env.sub, target) is not None:
        raise AssertionError("the waiver hypothesis is already recorded")
    if seed_ticket:
        claims.write_ticket(
            env.sub,
            factories.ticket(
                hypothesis_key=target,
                tier=tiergate.HYPOTHESIS_TICKET_TIER,
                method_identity=hypothesis["method_identity"],
                bundle_hash=env.bundle.hash,
            ),
        )
    observed, reasons, _ = gateplan._run_waiver(env.bundle, env.sub, env.attest_path, fixtures)
    if observed in (gateplan.EXPECT_NO_TICKET, TICKET_PRESENT) and tiergate.TICKET_ABSENT not in reasons:
        raise AssertionError(reasons)
    return observed


def waiver_ticket_present(cold):
    return _waiver_state(cold, seed_ticket=True)


def waiver_no_ticket(cold):
    return _waiver_state(cold, seed_ticket=False)


def _entry(test_id, expected_class, expected_verdict, run):
    return Entry(test_id, t.FAMILY, expected_class, expected_verdict, OWNER, run, launches=False)


ENTRIES = (
    _entry(YANKED_ID, MUST_FAIL, t.REJECT, yanked_refused),
    _entry(UNCERTIFIED_ID, MUST_FAIL, t.REJECT, uncertified_refused),
    _entry(BOUNDARY_ID, MUST_FAIL, t.REJECT, boundary_refused),
    _entry(BOUNDARY_FIT_ID, MUST_PASS, t.ADMIT, boundary_fit_admit),
    _entry(ROUTER_ID, MUST_FAIL, t.REJECT, router_top_class),
    _entry(WAIVER_TICKET_PRESENT_ID, MUST_FAIL, TICKET_PRESENT, waiver_ticket_present),
    _entry(WAIVER_NO_TICKET_ID, MUST_PASS, gateplan.EXPECT_NO_TICKET, waiver_no_ticket),
)
