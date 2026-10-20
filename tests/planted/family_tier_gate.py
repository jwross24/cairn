import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import _substrate_helpers as helpers
import tier_gate_arena as t
from _corpus import MUST_FAIL, MUST_PASS, Entry

from cairn import laddertable, ticketlattice, tiergate

OWNER = t.OWNER
KEEP_IN_SAMPLE_REFUSED_ID = "tier_gate/keep-in-sample-refused-off-the-hold-out-rung"
KEEP_IN_SAMPLE_ADMIT_ID = "tier_gate/keep-in-sample-admits-the-hold-out-rung"
KEEP_UNBOUND_ID = "tier_gate/keep-refused-for-a-differing-launch"
BOTH_KINDS_REFUSED_ID = "tier_gate/cost-and-conjecture-refused-while-either-ticket-absent"
BOTH_KINDS_ADMIT_ID = "tier_gate/cost-and-conjecture-admits-with-both-tickets"
TIER_THREE_REFUSED_ID = "tier_gate/tier-three-holding-keep-and-no-tier-two-node-refused"
TIER_THREE_ADMIT_ID = "tier_gate/tier-three-with-a-bound-tier-two-node-admits"
OFF_HOLD_OUT_BITS = (30, 40, t.FIT_BITS, 45)
STATEMENT_B = "b" * 64
STATEMENT_D = "d" * 64


def _in_sample_state(cold):
    env = t.arena(cold)
    skill = t.certify(env)
    key = t.hypothesis(env)
    t.keep_table(env, key, hold_out=False)
    candidate = ticketlattice.ladder_candidate(env.sub, env.bundle, key, t.METHOD)
    if candidate.verdict != laddertable.KEEP_IN_SAMPLE or candidate.scoped_rung_bits != t.HOLD_OUT_BITS:
        raise AssertionError(candidate)
    return env, skill, key


def keep_in_sample_refused(cold):
    env, skill, key = _in_sample_state(cold)
    decisions = [env.gate.admit(t.launch(key, skill, tier=2, bits=bits)) for bits in OFF_HOLD_OUT_BITS]
    refused = all(
        t.refused_with(d, tiergate.TIER_TWO_ABOVE, ticket_tier=tiergate.HYPOTHESIS_TICKET_TIER) for d in decisions
    )
    return t.verdict(refused)


def keep_in_sample_admit(cold):
    env, skill, key = _in_sample_state(cold)
    decision = env.gate.admit(t.launch(key, skill, tier=2, bits=t.HOLD_OUT_BITS))
    return t.ADMIT if t.admitted_at(decision, tiergate.TIER_TWO_TICKET_TIER) else t.ACCEPT


def keep_unbound(cold):
    env = t.arena(cold)
    skill = t.certify(env)
    key = t.hypothesis(env)
    t.keep_table(env, key)
    bound = env.gate.admit(t.launch(key, skill, tier=2))
    if not t.admitted_at(bound, tiergate.TIER_TWO_TICKET_TIER):
        raise AssertionError(bound)
    other_key = t.hypothesis(env, family="other_family")
    other_revision = t.certify(env, helpers.IDENTITY_B)
    decisions = (
        env.gate.admit(t.launch(other_key, skill, tier=2)),
        env.gate.admit(t.launch(key, skill, tier=2, method=t.OTHER_METHOD)),
        env.gate.admit(t.launch(key, other_revision, tier=2)),
    )
    refused = all(
        t.refused_with(d, tiergate.TIER_TWO_ABOVE, ticket_tier=tiergate.HYPOTHESIS_TICKET_TIER) for d in decisions
    )
    return t.verdict(refused)


def _incomplete_keys(env):
    neither = t.hypothesis(env, marker="true", family="neither")
    keep_only = t.hypothesis(env, marker="true", family="keep_only")
    t.keep_table(env, keep_only, run_id="run-keep-only")
    survived_only = t.hypothesis(env, marker="true", family="survived_only")
    t.survived_hunt(env, survived_only, STATEMENT_B)
    return neither, keep_only, survived_only


def _both_key(env):
    both = t.hypothesis(env, marker="true", family="both")
    t.keep_table(env, both, run_id="run-keep-both")
    t.survived_hunt(env, both, STATEMENT_D, seed_base=10)
    return both


def both_kinds_refused(cold):
    env = t.arena(cold)
    skill = t.certify(env)
    both = _both_key(env)
    admitted = env.gate.admit(t.launch(both, skill, tier=2))
    if not t.admitted_at(admitted, tiergate.TIER_TWO_TICKET_TIER):
        raise AssertionError(admitted)
    keys = _incomplete_keys(env)
    refused = all(
        t.refused_with(
            env.gate.admit(t.launch(key, skill, tier=2)),
            tiergate.TIER_TWO_ABOVE,
            ticket_tier=tiergate.HYPOTHESIS_TICKET_TIER,
        )
        for key in keys
    )
    return t.verdict(refused)


def both_kinds_admit(cold):
    env = t.arena(cold)
    skill = t.certify(env)
    decision = env.gate.admit(t.launch(_both_key(env), skill, tier=2))
    return t.ADMIT if t.admitted_at(decision, tiergate.TIER_TWO_TICKET_TIER) else t.ACCEPT


def tier_three_refused(cold):
    env = t.arena(cold)
    skill = t.certify(env)
    key = t.hypothesis(env)
    t.keep_table(env, key)
    tier_two = env.gate.admit(t.launch(key, skill, tier=2))
    if not t.admitted_at(tier_two, tiergate.TIER_TWO_TICKET_TIER):
        raise AssertionError(tier_two)
    decision = env.gate.admit(t.launch(key, skill, tier=3))
    refused = t.refused_with(decision, tiergate.TIER_TWO_ABOVE, ticket_tier=tiergate.TIER_TWO_TICKET_TIER)
    return t.verdict(refused)


def tier_three_admit(cold):
    env = t.arena(cold)
    skill = t.certify(env)
    key = t.hypothesis(env)
    table = t.keep_table(env, key)
    t.bind_tier_two(env, key, table.hash)
    decision = env.gate.admit(t.launch(key, skill, tier=3))
    return t.ADMIT if t.admitted_at(decision, tiergate.TIER_THREE_TICKET_TIER) else t.ACCEPT


def _entry(test_id, expected_class, expected_verdict, run):
    return Entry(test_id, t.FAMILY, expected_class, expected_verdict, OWNER, run, launches=False)


ENTRIES = (
    _entry(KEEP_IN_SAMPLE_REFUSED_ID, MUST_FAIL, t.REJECT, keep_in_sample_refused),
    _entry(KEEP_IN_SAMPLE_ADMIT_ID, MUST_PASS, t.ADMIT, keep_in_sample_admit),
    _entry(KEEP_UNBOUND_ID, MUST_FAIL, t.REJECT, keep_unbound),
    _entry(BOTH_KINDS_REFUSED_ID, MUST_FAIL, t.REJECT, both_kinds_refused),
    _entry(BOTH_KINDS_ADMIT_ID, MUST_PASS, t.ADMIT, both_kinds_admit),
    _entry(TIER_THREE_REFUSED_ID, MUST_FAIL, t.REJECT, tier_three_refused),
    _entry(TIER_THREE_ADMIT_ID, MUST_PASS, t.ADMIT, tier_three_admit),
)
