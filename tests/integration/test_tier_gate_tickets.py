import dataclasses
import json
import shutil
import sys
from pathlib import Path

import pytest

from cairn import bundle, claims, hunt, ladderplan, laddertable, prefilter, substrate, ticketlattice

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _substrate_helpers as helpers
import factories

STATEMENT = "b" * 64
OTHER_STATEMENT = "c" * 64
AT = "2026-09-08T00:00:00.000000+00:00"
LATER = "2026-09-08T00:00:01.000000+00:00"

ALL_QUIET = dict.fromkeys(prefilter.REQUIRED_FILTERS, prefilter.QUIET)


def with_verdict(name, verdict):
    return {**ALL_QUIET, name: verdict}


@pytest.fixture
def gate(tmp_path, pinned_bundle):
    bundle_path, pin_path = pinned_bundle()
    sub = helpers.open_writer(tmp_path)
    yield sub, bundle.GateBundle.open(bundle_path, pin_path)
    sub.close()


def nodes_of_kind(sub, kind):
    return sub.conn.execute("SELECT COUNT(*) FROM nodes WHERE kind = ?", (kind,)).fetchone()[0]


def variant_source(tmp_path):
    """A gate-bundle source that differs from the repository's in one pinned value, so it hashes apart."""
    src = tmp_path / "bundle-variant"
    shutil.copytree(Path(__file__).resolve().parents[2] / "bundle", src)
    auditor = json.loads((src / "auditor.json").read_text())
    auditor["f"] = "0.02"
    (src / "auditor.json").write_text(json.dumps(auditor))
    return src


def test_a_complete_quiet_battery_admits_tier_one_and_round_trips_through_the_substrate(gate):
    sub, gate_bundle = gate
    digest, result = prefilter.record(sub, gate_bundle, statement_hash=STATEMENT, verdicts=ALL_QUIET, at=AT)
    assert result.passed and result.missing == () and result.rejected == ()
    assert nodes_of_kind(sub, prefilter.KIND) == 1
    assert prefilter.result_for(sub, digest) == result
    assert prefilter.read(sub, gate_bundle, STATEMENT) == result
    assert prefilter.admits_tier_one(sub, gate_bundle, STATEMENT)


def test_a_flagged_but_complete_battery_still_admits_tier_one_and_keeps_the_flag(gate):
    sub, gate_bundle = gate
    _, result = prefilter.record(
        sub,
        gate_bundle,
        statement_hash=STATEMENT,
        verdicts=with_verdict(prefilter.BOUNDED_PROVER, prefilter.FLAG),
        flags=(prefilter.BOUNDED_PROVER,),
        at=AT,
    )
    assert result.flagged == (prefilter.BOUNDED_PROVER,)
    assert result.passed
    assert prefilter.admits_tier_one(sub, gate_bundle, STATEMENT)


def test_a_rejecting_filter_denies_tier_one(gate):
    sub, gate_bundle = gate
    _, result = prefilter.record(
        sub, gate_bundle, statement_hash=STATEMENT, verdicts=with_verdict(prefilter.VACUITY, prefilter.REJECT), at=AT
    )
    assert result.rejected == (prefilter.VACUITY,)
    assert not result.passed
    assert not prefilter.admits_tier_one(sub, gate_bundle, STATEMENT)


def test_an_unrun_filter_denies_tier_one_and_is_not_read_as_a_quiet_one(gate):
    sub, gate_bundle = gate
    partial = {name: prefilter.QUIET for name in prefilter.REQUIRED_FILTERS if name != prefilter.VACUITY}
    _, result = prefilter.record(sub, gate_bundle, statement_hash=STATEMENT, verdicts=partial, at=AT)
    assert result.missing == (prefilter.VACUITY,)
    assert result.rejected == ()
    assert not result.passed
    assert not prefilter.admits_tier_one(sub, gate_bundle, STATEMENT)


def test_an_absent_record_denies_tier_one(gate):
    sub, gate_bundle = gate
    prefilter.record(sub, gate_bundle, statement_hash=OTHER_STATEMENT, verdicts=ALL_QUIET, at=AT)
    assert prefilter.read(sub, gate_bundle, STATEMENT) is None
    assert not prefilter.admits_tier_one(sub, gate_bundle, STATEMENT)


def test_a_result_recorded_under_another_bundle_is_not_read_for_this_one(gate, tmp_path, pinned_bundle):
    sub, gate_bundle = gate
    other = bundle.GateBundle.open(*pinned_bundle(name="other", src=variant_source(tmp_path)))
    prefilter.record(sub, other, statement_hash=STATEMENT, verdicts=ALL_QUIET, at=AT)
    assert nodes_of_kind(sub, prefilter.KIND) == 1
    assert prefilter.read(sub, gate_bundle, STATEMENT) is None
    assert not prefilter.admits_tier_one(sub, gate_bundle, STATEMENT)
    assert prefilter.admits_tier_one(sub, other, STATEMENT)


def test_the_most_recent_result_for_the_statement_is_the_one_read(gate):
    sub, gate_bundle = gate
    prefilter.record(sub, gate_bundle, statement_hash=STATEMENT, verdicts=ALL_QUIET, at=AT)
    assert prefilter.admits_tier_one(sub, gate_bundle, STATEMENT)
    _, later = prefilter.record(
        sub,
        gate_bundle,
        statement_hash=STATEMENT,
        verdicts=with_verdict(prefilter.EXISTS_IMPLICATION, prefilter.REJECT),
        at=LATER,
    )
    assert prefilter.read(sub, gate_bundle, STATEMENT) == later
    assert not prefilter.admits_tier_one(sub, gate_bundle, STATEMENT)


def test_a_malformed_record_is_refused_and_writes_no_node(gate):
    sub, gate_bundle = gate
    with pytest.raises(prefilter.PrefilterError, match="not one of"):
        prefilter.record(sub, gate_bundle, statement_hash=STATEMENT, verdicts=with_verdict(prefilter.VACUITY, "PASS"))
    with pytest.raises(prefilter.PrefilterError, match="not in the battery"):
        prefilter.record(sub, gate_bundle, statement_hash=STATEMENT, verdicts={**ALL_QUIET, "invented": "QUIET"})
    with pytest.raises(prefilter.PrefilterError, match="carry no flag"):
        prefilter.record(
            sub, gate_bundle, statement_hash=STATEMENT, verdicts=with_verdict(prefilter.VACUITY, prefilter.FLAG)
        )
    assert nodes_of_kind(sub, prefilter.KIND) == 0


HYPOTHESIS = "aa" * 32
OTHER_HYPOTHESIS = "ab" * 32
REVISION = "bb" * 32
OTHER_REVISION = "bc" * 32
METHOD = {"interface_version": "toy/1", "params": {}}
OTHER_METHOD = {"interface_version": "toy/2", "params": {}}
HOLD_OUT_BITS = 60
FIT_BITS = 50

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
    run_id="run-1",
    nonce="nonce-1",
    hypothesis_hash=HYPOTHESIS,
    method_identity=METHOD,
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


def table(run_id, *, include_hold_out=True, **overrides):
    sizes = [30, 40, 50] + ([HOLD_OUT_BITS] if include_hold_out else [])
    rungs = tuple(
        dataclasses.replace(
            RUNG_BASE, bits=b, role=ladderplan.ROLE_HOLD_OUT if b == HOLD_OUT_BITS else ladderplan.ROLE_FIT
        )
        for b in sizes
    )
    trials = tuple(dataclasses.replace(TRIAL_BASE, bits=b, trial=t) for b in sizes for t in (0, 1))
    return dataclasses.replace(TABLE_BASE, run_id=run_id, rungs=rungs, trials=trials, **overrides)


def seed_table(sub, plan, run_id, **kw):
    written = table(run_id, **kw)
    laddertable.write(sub, written, plan)
    return written


def select(sub, gate_bundle, *, bits=HOLD_OUT_BITS, hypothesis_key=HYPOTHESIS, method=None, revision=REVISION):
    return ticketlattice.select_kind(
        sub,
        gate_bundle,
        ticketlattice.ALGORITHMIC,
        hypothesis_key=hypothesis_key,
        method_identity=METHOD if method is None else method,
        inputs={"bits": bits},
        implementation_revision=revision,
    )


def test_a_keep_table_is_the_tier_two_algorithmic_ticket_for_its_own_launch(gate, plan):
    sub, gate_bundle = gate
    written = seed_table(sub, plan, "run-keep")
    selection = select(sub, gate_bundle)
    assert selection.candidate.node_hash == written.hash
    assert selection.candidate.verdict == laddertable.KEEP
    assert selection.mismatches == ()
    assert selection.admits


def test_a_later_inconclusive_table_displaces_an_older_keep(gate, plan):
    sub, gate_bundle = gate
    seed_table(sub, plan, "run-keep")
    assert select(sub, gate_bundle).admits
    later = seed_table(sub, plan, "run-inconclusive", uncounted_backend="gp")
    selection = select(sub, gate_bundle)
    assert selection.candidate.node_hash == later.hash
    assert selection.candidate.verdict == "INCONCLUSIVE"
    assert not selection.admits


def test_a_keep_in_sample_table_admits_the_hold_out_rung_and_no_other_launch(gate, plan):
    sub, gate_bundle = gate
    written = seed_table(sub, plan, "run-in-sample", include_hold_out=False)
    scoped = select(sub, gate_bundle, bits=HOLD_OUT_BITS)
    assert scoped.candidate.node_hash == written.hash
    assert scoped.candidate.verdict == laddertable.KEEP_IN_SAMPLE
    assert scoped.candidate.scoped_rung_bits == HOLD_OUT_BITS
    assert scoped.admits

    elsewhere = select(sub, gate_bundle, bits=FIT_BITS)
    assert elsewhere.mismatches == (ticketlattice.SCOPE_MISMATCH,)
    assert not elsewhere.admits


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"hypothesis_key": OTHER_HYPOTHESIS}, None),
        ({"method": OTHER_METHOD}, None),
        ({"revision": OTHER_REVISION}, ticketlattice.REVISION_MISMATCH),
    ],
    ids=["key", "method_identity", "implementation_revision"],
)
def test_a_keep_table_offered_for_a_differing_launch_is_refused(gate, plan, kwargs, expected):
    sub, gate_bundle = gate
    seed_table(sub, plan, "run-keep")
    selection = select(sub, gate_bundle, **kwargs)
    assert not selection.admits
    if expected is None:
        assert selection.candidate is None
    else:
        assert selection.mismatches == (expected,)


def test_no_table_at_all_is_an_absent_ticket_rather_than_an_admitting_one(gate, plan):
    sub, gate_bundle = gate
    selection = select(sub, gate_bundle)
    assert selection.candidate is None and not selection.admits


def test_the_rung_role_comes_from_the_pinned_plan_and_an_off_plan_size_has_none(gate):
    _, gate_bundle = gate
    assert ticketlattice.rung_role(gate_bundle, {"bits": HOLD_OUT_BITS}) == ladderplan.ROLE_HOLD_OUT
    for bits in (30, 40, 50):
        assert ticketlattice.rung_role(gate_bundle, bits) == ladderplan.ROLE_FIT
    assert ticketlattice.rung_role(gate_bundle, 55) is None
    assert ticketlattice.rung_role(gate_bundle, {"seed": 7}) is None


def survived_hunt(sub, hypothesis_key, trials=2, verdict="SURVIVED"):
    """A hunt record seeded through the real writers; the run's own execution is bead R4's."""
    survived = tuple(
        hunt.TrialRecord(
            trial=index,
            point={"n": index},
            seed=index + 1,
            attempt_id=f"attempt-{index}",
            execution_status="OK",
            execution_evidence=f"{index:02d}" * 32,
            outcome="SURVIVED_TRIAL",
            verifier_status="NOT_REQUIRED",
            verifier_evidence=None,
        )
        for index in range(trials)
    )
    standing = verdict == "SURVIVED"
    record = hunt.HuntRecord(
        "ee" * 32,
        "ef" * 32,
        STATEMENT,
        hypothesis_key,
        "hunt-nonce",
        trials,
        len(survived) if standing else 0,
        "FULL_DECLARED_BUDGET" if standing else "PARTIAL",
        verdict,
        None,
        standing,
        survived if standing else (),
    )
    run_hash = sub.put_node("hunt_run", hunt.run_canonical(record), producer_identity="gate:hunt")
    evidence_hash = claims.write_evidence_node(
        sub,
        claims.EvidenceNode(
            kind=hunt.KIND,
            target_statement_hash=STATEMENT,
            population=factories.scope(),
            assumptions=frozenset({factories.assumption_id("A1")}),
            producer_identity="gate:hunt",
            producer_tag="gate",
            verdict=verdict,
        ),
    )
    sub.add_lineage(evidence_hash, run_hash, substrate.EDGE_INPUT)
    return evidence_hash


def record_hypothesis(sub, *, conjecture_marker=None, family="toy_curve"):
    claimed = {"kind": "cost_model", "exponent": "0.5", "constant": "1", "crossover": "30"}
    if conjecture_marker is not None:
        claimed["correctness_conjecture"] = conjecture_marker
    obj = factories.hypothesis_object(family=family, claimed=claimed, method_identity=METHOD)
    claims.write_hypothesis_object(sub, obj)
    return obj


def tier_two(sub, gate_bundle, hypothesis_key, bits=HOLD_OUT_BITS):
    return ticketlattice.tier_two_selections(
        sub,
        gate_bundle,
        hypothesis_key=hypothesis_key,
        statement_hash=None,
        method_identity=METHOD,
        inputs={"bits": bits},
        revision=REVISION,
    )


def test_a_cost_model_without_the_marker_carries_the_algorithmic_kind_alone(gate):
    sub, _ = gate
    obj = record_hypothesis(sub)
    assert ticketlattice.claim_kinds(sub, obj.hash) == (ticketlattice.ALGORITHMIC,)


def test_the_marker_adds_the_conjecture_kind_to_the_same_cost_model(gate):
    sub, _ = gate
    obj = record_hypothesis(sub, conjecture_marker="true")
    assert ticketlattice.claim_kinds(sub, obj.hash) == (ticketlattice.ALGORITHMIC, ticketlattice.CONJECTURE)


@pytest.mark.parametrize("marker", ["false", "True", "1", ""], ids=["false", "capitalized", "one", "empty"])
def test_a_malformed_marker_refuses_rather_than_reading_as_absent(gate, marker):
    sub, _ = gate
    obj = record_hypothesis(sub, conjecture_marker=marker)
    with pytest.raises(ticketlattice.ClaimKindMalformed, match="correctness_conjecture"):
        ticketlattice.claim_kinds(sub, obj.hash)


def test_a_multi_kind_claim_needs_both_tickets_and_is_refused_while_either_is_absent(gate, plan):
    sub, gate_bundle = gate
    obj = record_hypothesis(sub, conjecture_marker="true")

    neither = tier_two(sub, gate_bundle, obj.hash)
    assert [s.claim_kind for s in neither] == [ticketlattice.ALGORITHMIC, ticketlattice.CONJECTURE]
    assert not ticketlattice.admits_tier_two(neither)

    seed_table(sub, plan, "run-keep", hypothesis_hash=obj.hash)
    keep_only = tier_two(sub, gate_bundle, obj.hash)
    assert [s.admits for s in keep_only] == [True, False]
    assert not ticketlattice.admits_tier_two(keep_only)

    survived_hunt(sub, obj.hash)
    both = tier_two(sub, gate_bundle, obj.hash)
    assert [s.admits for s in both] == [True, True]
    assert ticketlattice.admits_tier_two(both)


def test_a_survived_record_alone_does_not_admit_the_algorithmic_half(gate):
    sub, gate_bundle = gate
    obj = record_hypothesis(sub, conjecture_marker="true")
    survived_hunt(sub, obj.hash)
    selections = tier_two(sub, gate_bundle, obj.hash)
    assert [s.admits for s in selections] == [False, True]
    assert not ticketlattice.admits_tier_two(selections)


def test_an_incomplete_hunt_does_not_serve_as_the_conjecture_ticket(gate, plan):
    sub, gate_bundle = gate
    obj = record_hypothesis(sub, conjecture_marker="true")
    seed_table(sub, plan, "run-keep", hypothesis_hash=obj.hash)
    survived_hunt(sub, obj.hash, verdict="INCOMPLETE")
    selections = tier_two(sub, gate_bundle, obj.hash)
    assert selections[1].candidate.verdict == "INCOMPLETE"
    assert [s.admits for s in selections] == [True, False]
    assert not ticketlattice.admits_tier_two(selections)


def test_a_survived_hunt_for_another_hypothesis_is_not_this_claims_ticket(gate, plan):
    sub, gate_bundle = gate
    obj = record_hypothesis(sub, conjecture_marker="true")
    other = record_hypothesis(sub, conjecture_marker="true", family="another_family")
    seed_table(sub, plan, "run-keep", hypothesis_hash=obj.hash)
    survived_hunt(sub, other.hash)
    selections = tier_two(sub, gate_bundle, obj.hash)
    assert selections[1].candidate is None
    assert not ticketlattice.admits_tier_two(selections)
