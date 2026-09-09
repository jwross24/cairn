import sys
from pathlib import Path

import pytest

from cairn import bundle, claims, prefilter, tiergate
from cairn.profile import CostProfile, Production, SizeCost, Verification

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _substrate_helpers as helpers
import factories

AT = "2026-09-09T00:00:00.000000+00:00"
METHOD = {"interface_version": "toy/1", "params": {}}
BITS = 60
BUDGET_PLENTY = 10_000_000.0


@pytest.fixture
def gate(tmp_path, pinned_bundle):
    bundle_path, pin_path = pinned_bundle()
    sub = helpers.open_writer(tmp_path)
    yield sub, bundle.GateBundle.open(bundle_path, pin_path)
    sub.close()


def tiny_profile():
    return CostProfile(
        tier=0,
        production=Production(
            model="synthetic",
            per_size={BITS: SizeCost(mean_tries=1.0, sd_tries=0.0, per_try_s=0.01, mean_wall_s=0.01)},
        ),
        verification=Verification(grade="Verifiable", cost_model="same_as_production"),
        source="tests/integration/test_tier_gate_unbound_statement.py",
    )


def passing_theorem_statement(sub, gate_bundle):
    stmt = factories.claim_statement(formal_source="theorem toy : True := trivial")
    claims.write_claim_statement(sub, stmt)
    complete = dict.fromkeys(prefilter.REQUIRED_FILTERS, prefilter.QUIET)
    prefilter.record(sub, gate_bundle, statement_hash=stmt.hash, verdicts=complete, at=AT)
    assert prefilter.admits_tier_one(sub, gate_bundle, stmt.hash)
    return stmt


def launch_against(sub, hypothesis_claim_statement_hash, launch_statement_hash):
    obj = factories.hypothesis_object(
        family="toy_curve", method_identity=METHOD, claim_statement_hash=hypothesis_claim_statement_hash
    )
    claims.write_hypothesis_object(sub, obj)
    identity_hash = sub.put_identity_bundle(helpers.IDENTITY_B)
    sub.put_certificate(identity_hash, helpers.TRANSCRIPT_HASH, helpers.ENV_MANIFEST_HASH, helpers.SELFTEST_SUMMARY)
    return tiergate.Launch(
        cost_profile=tiny_profile(),
        inputs={"bits": BITS},
        budget_remaining=BUDGET_PLENTY,
        hypothesis_key=obj.hash,
        method_identity=METHOD,
        skill_identity_hash=identity_hash,
        declared_tier=1,
        statement_hash=launch_statement_hash,
    )


def test_an_unbound_hypothesis_naming_a_passing_statement_is_refused_the_hypothesis_ticket(gate):
    sub, gate_bundle = gate
    stmt = passing_theorem_statement(sub, gate_bundle)
    launch = launch_against(sub, None, stmt.hash)
    decision = tiergate.TierGate(sub, gate_bundle).admit(launch)
    assert isinstance(decision, tiergate.TierRefused)
    assert tiergate.TICKET_ABSENT in decision.reasons


def test_the_same_statement_bound_by_the_hypothesis_is_admitted(gate):
    sub, gate_bundle = gate
    stmt = passing_theorem_statement(sub, gate_bundle)
    launch = launch_against(sub, stmt.hash, stmt.hash)
    decision = tiergate.TierGate(sub, gate_bundle).admit(launch)
    assert isinstance(decision, tiergate.Admitted), decision.reasons
    assert decision.ticket_tier == tiergate.HYPOTHESIS_TICKET_TIER


def test_a_launch_naming_no_statement_against_an_unbound_hypothesis_reads_no_statement(gate):
    sub, gate_bundle = gate
    launch = launch_against(sub, None, None)
    assert tiergate.TierGate(sub, gate_bundle)._statement_hash(launch) is None


def test_the_refusal_is_raised_where_the_resolution_happens_not_inferred_downstream(gate):
    sub, gate_bundle = gate
    stmt = passing_theorem_statement(sub, gate_bundle)
    launch = launch_against(sub, None, stmt.hash)
    with pytest.raises(tiergate.StatementUnrecorded, match=stmt.hash):
        tiergate.TierGate(sub, gate_bundle)._statement_hash(launch)


def test_a_hypothesis_binding_a_different_statement_still_refuses_as_a_disagreement(gate):
    sub, gate_bundle = gate
    stmt = passing_theorem_statement(sub, gate_bundle)
    other = factories.claim_statement(formal_source="theorem other : True := trivial", claim_id="other")
    claims.write_claim_statement(sub, other)
    launch = launch_against(sub, other.hash, stmt.hash)
    with pytest.raises(tiergate.StatementDisagreement):
        tiergate.TierGate(sub, gate_bundle)._statement_hash(launch)
