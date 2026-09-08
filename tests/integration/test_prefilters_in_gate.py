import json
import os
import shutil
import sys
from pathlib import Path

import pytest

from cairn import bundle, claims, prefilter, tiergate
from cairn import statement_prefilters as battery
from cairn.profile import CostProfile, Production, SizeCost, Verification

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _substrate_helpers as helpers
import factories

AT = "2026-09-08T00:00:00.000000+00:00"
METHOD = {"interface_version": "toy/1", "params": {}}
BITS = 60
BUDGET_PLENTY = 10_000_000.0

CLEAN = battery.Statement(name="clean", binders="(n : Nat)", hypotheses=("n > 0",), conclusion="∃ m : Nat, m > n")
VACUOUS = battery.Statement(name="vacuous", binders="(n : Nat)", hypotheses=("n > 0", "n < 0"), conclusion="n = n")
PLAIN_TRAP = battery.Statement(name="trap", conclusion="∃ n : Nat, n ≠ 0 → False")
BINDER_TRAP = battery.Statement(name="silent", conclusion="∃ n : Nat, n > 0 ∧ (n ≠ 1 → False)")
NESTED_TRAP = battery.Statement(name="nested", conclusion="∃ n : Nat, (n ≠ 0 → False) ∧ True")
AXIOMATIZED = battery.Statement(name="axiomatized", conclusion="1 = 1", kind=battery.AXIOM)
STUBBED = battery.Statement(name="stubbed", conclusion="Nat", kind=battery.OPAQUE)

QUIET_ON_ALL_FOUR = dict.fromkeys(battery.PRODUCED_FILTERS, prefilter.QUIET)


@pytest.fixture
def gate(tmp_path, pinned_bundle):
    bundle_path, pin_path = pinned_bundle()
    sub = helpers.open_writer(tmp_path)
    yield sub, bundle.GateBundle.open(bundle_path, pin_path)
    sub.close()


@pytest.fixture(scope="module")
def battery_project(tmp_path_factory):
    """One scratch project for the module: the four vendored linters compile once, not once per statement."""
    root = tmp_path_factory.mktemp("battery")
    bundle_path, pin_path = root / "gate-bundle.sqlite", root / "gate-bundle.pin"
    bundle.build(Path(__file__).resolve().parents[2] / "bundle", bundle_path)
    bundle.write_pin(bundle_path, pin_path)
    gate_bundle = bundle.GateBundle.open(bundle_path, pin_path)
    yield gate_bundle, battery.scratch_project(gate_bundle, root / "proj")
    for path in (pin_path, bundle_path):
        if path.exists():
            os.chflags(path, 0)
            path.chmod(0o644)


def variant_source(tmp_path):
    src = tmp_path / "bundle-variant"
    shutil.copytree(Path(__file__).resolve().parents[2] / "bundle", src)
    auditor = json.loads((src / "auditor.json").read_text())
    auditor["f"] = "0.02"
    (src / "auditor.json").write_text(json.dumps(auditor))
    return src


def tiny_profile():
    return CostProfile(
        tier=0,
        production=Production(
            model="synthetic",
            per_size={BITS: SizeCost(mean_tries=1.0, sd_tries=0.0, per_try_s=0.01, mean_wall_s=0.01)},
        ),
        verification=Verification(grade="Verifiable", cost_model="same_as_production"),
        source="tests/integration/test_prefilters_in_gate.py",
    )


def theorem_statement(sub):
    stmt = factories.claim_statement(formal_source="theorem toy : True := trivial")
    claims.write_claim_statement(sub, stmt)
    return stmt


def theorem_launch(sub, statement_hash):
    claimed = {"kind": "cost_model", "exponent": "0.5", "constant": "1", "crossover": "30"}
    obj = factories.hypothesis_object(
        family="toy_curve", claimed=claimed, method_identity=METHOD, claim_statement_hash=statement_hash
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
        statement_hash=statement_hash,
    )


def produced(battery_project, statement, statement_hash):
    gate_bundle, project = battery_project
    return gate_bundle, battery.run(gate_bundle, statement, statement_hash=statement_hash, project_dir=project)


@pytest.mark.slow
def test_a_clean_statement_is_quiet_on_every_filter_the_battery_runs(battery_project):
    _, result = produced(battery_project, CLEAN, "01" * 32)
    assert result.verdicts == QUIET_ON_ALL_FOUR
    assert result.flags == ()
    assert result.detail["stub_or_axiom"] == []
    assert result.detail["bounded_prover"] == []


@pytest.mark.slow
def test_hypotheses_that_derive_False_are_rejected(battery_project):
    _, result = produced(battery_project, VACUOUS, "02" * 32)
    assert result.verdicts[prefilter.VACUITY] == prefilter.REJECT
    assert prefilter.VACUITY not in result.flags


@pytest.mark.slow
def test_the_plain_existential_implication_trap_is_flagged(battery_project):
    _, result = produced(battery_project, PLAIN_TRAP, "03" * 32)
    assert result.verdicts[prefilter.EXISTS_IMPLICATION] == prefilter.FLAG
    assert prefilter.EXISTS_IMPLICATION in result.flags


@pytest.mark.slow
@pytest.mark.parametrize(
    ("statement", "statement_hash"), [(BINDER_TRAP, "04" * 32), (NESTED_TRAP, "05" * 32)], ids=["binder", "nested"]
)
def test_the_binder_predicate_and_conjunction_nested_traps_pass_the_linter(battery_project, statement, statement_hash):
    """The measured limitation the Skeptic's checklist carries: linter-green is not trap-free."""
    _, result = produced(battery_project, statement, statement_hash)
    assert result.verdicts[prefilter.EXISTS_IMPLICATION] == prefilter.QUIET
    assert prefilter.EXISTS_IMPLICATION not in result.flags


@pytest.mark.slow
@pytest.mark.parametrize(
    ("statement", "statement_hash", "expected"),
    [(AXIOMATIZED, "06" * 32, battery.NEW_AXIOM), (STUBBED, "07" * 32, battery.STUB)],
    ids=["axiom", "stub"],
)
def test_a_new_axiom_and_a_stub_share_one_verdict_and_are_separated_in_the_detail(
    battery_project, statement, statement_hash, expected
):
    _, result = produced(battery_project, statement, statement_hash)
    assert result.verdicts[prefilter.STUB_OR_AXIOM] == prefilter.FLAG
    assert prefilter.STUB_OR_AXIOM in result.flags
    assert result.detail["stub_or_axiom"] == [expected]


@pytest.mark.slow
def test_a_trivially_provable_statement_is_flagged_and_the_side_that_closed_is_named(battery_project):
    _, result = produced(battery_project, battery.Statement(name="triv", conclusion="1 = 1"), "08" * 32)
    assert result.verdicts[prefilter.BOUNDED_PROVER] == prefilter.FLAG
    assert result.detail["bounded_prover"] == [battery.PROVABLE]


@pytest.mark.slow
def test_a_produced_record_is_refused_by_the_tier_one_predicate_and_the_round_trip_filter_is_what_holds_it_shut(
    battery_project, gate
):
    sub, _ = gate
    stmt = theorem_statement(sub)
    gate_bundle, produced_battery = produced(battery_project, CLEAN, stmt.hash)
    digest, result = battery.record(sub, gate_bundle, produced_battery, at=AT)

    assert result.missing == (prefilter.ROUNDTRIP_DIVERGENCE,)
    assert result.rejected == ()
    assert result.passed is False
    assert prefilter.result_for(sub, digest) == result
    assert not prefilter.admits_tier_one(sub, gate_bundle, produced_battery.statement_hash)

    launch = theorem_launch(sub, produced_battery.statement_hash)
    decision = tiergate.TierGate(sub, gate_bundle).admit(launch)
    assert isinstance(decision, tiergate.TierRefused)
    assert tiergate.TICKET_ABSENT in decision.reasons

    supplied = {**produced_battery.verdicts, prefilter.ROUNDTRIP_DIVERGENCE: prefilter.QUIET}
    prefilter.record(sub, gate_bundle, statement_hash=produced_battery.statement_hash, verdicts=supplied, at=AT)
    admitted = tiergate.TierGate(sub, gate_bundle).admit(launch)
    assert isinstance(admitted, tiergate.Admitted), admitted.reasons
    assert admitted.ticket_tier == tiergate.HYPOTHESIS_TICKET_TIER


def test_a_result_read_by_digest_alone_does_not_admit_under_another_bundle(gate, tmp_path, pinned_bundle):
    """`result_for` reads by digest with no bundle check; admission is what has to refuse the stale bundle."""
    sub, gate_bundle = gate
    other = bundle.GateBundle.open(*pinned_bundle(name="other", src=variant_source(tmp_path)))
    assert other.hash != gate_bundle.hash
    statement_hash = "0a" * 32
    complete = dict.fromkeys(prefilter.REQUIRED_FILTERS, prefilter.QUIET)
    digest, result = prefilter.record(sub, other, statement_hash=statement_hash, verdicts=complete, at=AT)

    assert result.passed is True
    assert prefilter.result_for(sub, digest) == result
    assert prefilter.admits_tier_one(sub, other, statement_hash)
    assert not prefilter.admits_tier_one(sub, gate_bundle, statement_hash)
