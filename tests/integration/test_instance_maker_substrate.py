import dataclasses
import hashlib
import json
import sys
from pathlib import Path

import pytest

from cairn import (
    bundle,
    canon,
    claims,
    instances,
    ladderplan,
    laddertable,
    repro,
    runner,
    selftest_skills,
    substrate,
    ticketlattice,
    tiergate,
)
from cairn.skills import instance_maker

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import factories

pytestmark = pytest.mark.skipif(
    sys.platform != "darwin",
    reason="pinned_bundle pins through uappnd, a macOS/BSD chflags bit; the Linux arm is cairn-hcl",
)

NONCE = "ab" * 32
HYPOTHESIS = "cd" * 32
METHOD_IDENTITY = {"interface_version": "instance_maker/1", "params": {}}
BUDGET = 10_000_000.0
CEILING = 60


@pytest.fixture
def harness(tmp_path, pinned_bundle):
    bundle_path, pin_path = pinned_bundle()
    gate = bundle.GateBundle.open(bundle_path, pin_path)
    with substrate.Substrate.open(tmp_path / "substrate.sqlite") as sub:
        yield sub, gate, tmp_path / "runs"


def _launch(sub, gate, scratch, *, bits=28, trial=0, nonce=NONCE, declared_tier=instances.DECLARED_TIER):
    return instances.launch_trial(
        sub,
        gate,
        nonce=nonce,
        bits=bits,
        trial=trial,
        scratch_root=scratch,
        method_identity=METHOD_IDENTITY,
        budget_remaining=BUDGET,
        ceiling_multiplier=CEILING,
        declared_tier=declared_tier,
    )


def test_an_uncertified_maker_revision_is_refused_by_the_tier_gate_and_nothing_launches(harness):
    sub, gate, scratch = harness
    instances.commit_nonce(sub, HYPOTHESIS, "run-1", NONCE)
    assert not sub.certified(instance_maker.skill_identity_hash())
    with pytest.raises(instances.TrialRefused) as info:
        _launch(sub, gate, scratch)
    assert info.value.reasons == (tiergate.UNCERTIFIED,)
    assert sub.conn.execute("SELECT count(*) FROM attempts").fetchone()[0] == 0
    assert sub.conn.execute("SELECT count(*) FROM recipes").fetchone()[0] == 0
    assert instances.trials_for(sub, NONCE) == []
    runs = sub.conn.execute("SELECT result, reasons FROM gate_runs WHERE gate = 'tier_gate'").fetchall()
    assert [tuple(r) for r in runs] == [("refused", '["uncertified"]')]


def test_a_certified_maker_launches_with_do_not_cache_and_the_serve_path_refuses_it(harness, json_test_log):
    sub, gate, scratch = harness
    selftest_skills.certify(sub, gate.verifier_config(), selftest_skills.INSTANCE_MAKER)
    instances.commit_nonce(sub, HYPOTHESIS, "run-1", NONCE)
    attempt, out = _launch(sub, gate, scratch)
    assert attempt.status == runner.STATUS_OK and not attempt.served_from_cache and out is not None
    row = sub.conn.execute("SELECT do_not_cache FROM recipes WHERE recipe_key = ?", (attempt.recipe_key,)).fetchone()
    assert row[0] == 1
    assert sub.serve(attempt.recipe_key) is None
    assert sub._why_not_served(attempt.recipe_key) == "do_not_cache"
    served = [
        line for line in json_test_log.read_text().splitlines() if '"event": "serve"' in line and "do_not_cache" in line
    ]
    assert served, "the serve path logged no do_not_cache refusal"
    seed = instances.trial_seed(NONCE, HYPOTHESIS, 28, 0)
    assert out.seed == seed and out.bits == 28
    assert instances.trials_for(sub, NONCE) == [
        {
            "nonce": NONCE,
            "bits": 28,
            "trial": 0,
            "seed": seed,
            "instance_hash": out.instance_hash,
            "x": str(out.x),
            "attempt_id": attempt.attempt_id,
        }
    ]


def test_the_launched_document_is_the_in_process_document_byte_for_byte(harness):
    sub, gate, scratch = harness
    selftest_skills.certify(sub, gate.verifier_config(), selftest_skills.INSTANCE_MAKER)
    instances.commit_nonce(sub, HYPOTHESIS, "run-1", NONCE)
    attempt, out = _launch(sub, gate, scratch)
    stdout = (Path(scratch) / attempt.attempt_id / "stdout").read_bytes()
    replayed = instance_maker.run(28, instances.trial_seed(NONCE, HYPOTHESIS, 28, 0)).to_json().encode()
    assert (len(stdout), hashlib.sha256(stdout).hexdigest()) == (len(replayed), hashlib.sha256(replayed).hexdigest())
    assert out.to_json().encode() == stdout


def test_the_nonce_is_withheld_until_the_run_completes_then_present_in_the_table(harness):
    sub, gate, scratch = harness
    selftest_skills.certify(sub, gate.verifier_config(), selftest_skills.INSTANCE_MAKER)
    instances.commit_nonce(sub, HYPOTHESIS, "run-1", NONCE)
    _launch(sub, gate, scratch, trial=0)
    _launch(sub, gate, scratch, trial=1)
    assert instances.withheld(sub, NONCE)
    published = instances.publish_nonce(sub, NONCE)
    assert not published.withheld
    rows = sub.conn.execute(
        "SELECT n.nonce, n.published_at, t.trial, t.seed FROM instance_nonces n JOIN instance_trials t ON t.nonce = n.nonce ORDER BY t.trial"
    ).fetchall()
    assert [tuple(r) for r in rows] == [
        (NONCE, published.published_at, 0, instances.trial_seed(NONCE, HYPOTHESIS, 28, 0)),
        (NONCE, published.published_at, 1, instances.trial_seed(NONCE, HYPOTHESIS, 28, 1)),
    ]


def test_a_trial_already_recorded_under_the_nonce_is_not_launched_twice(harness):
    sub, gate, scratch = harness
    selftest_skills.certify(sub, gate.verifier_config(), selftest_skills.INSTANCE_MAKER)
    instances.commit_nonce(sub, HYPOTHESIS, "run-1", NONCE)
    _launch(sub, gate, scratch)
    with pytest.raises(instances.TrialRecorded, match="trial-recorded"):
        _launch(sub, gate, scratch)


def test_a_rerun_of_the_same_hypothesis_must_draw_a_fresh_nonce(harness):
    sub, gate, scratch = harness
    instances.commit_nonce(sub, HYPOTHESIS, "run-1", NONCE)
    with pytest.raises(instances.NonceReused, match="nonce-reused"):
        instances.commit_nonce(sub, HYPOTHESIS, "run-2", NONCE)
    fresh = instances.draw_nonce(sub, HYPOTHESIS, "run-2")
    assert fresh.nonce != NONCE and fresh.withheld
    assert instances.trial_seed(fresh.nonce, HYPOTHESIS, 28, 0) != instances.trial_seed(NONCE, HYPOTHESIS, 28, 0)


def test_a_launch_under_an_unknown_nonce_is_refused(harness):
    sub, gate, scratch = harness
    with pytest.raises(instances.UnknownNonce, match="unknown-nonce"):
        _launch(sub, gate, scratch, nonce="ef" * 32)


def test_a_launch_that_does_not_end_ok_records_no_trial_and_returns_no_instance(harness, monkeypatch):
    sub, gate, scratch = harness
    selftest_skills.certify(sub, gate.verifier_config(), selftest_skills.INSTANCE_MAKER)
    instances.commit_nonce(sub, HYPOTHESIS, "run-1", NONCE)
    document = instance_maker.run(28, instances.trial_seed(NONCE, HYPOTHESIS, 28, 0)).to_wire()
    failed = runner.Attempt(
        "attempt-planted",
        "recipe-planted",
        runner.STATUS_BUDGET_EXCEEDED,
        None,
        parsed=runner.ParsedOutput.of(document, runner.STATUS_OK),
    )
    monkeypatch.setattr(runner, "launch", lambda *a, **k: failed)
    attempt, out = _launch(sub, gate, scratch)
    assert attempt is failed and out is None
    assert instances.trials_for(sub, NONCE) == []


def test_the_ceiling_multiplier_defaults_to_the_bundles_tiers_object(harness, monkeypatch):
    sub, gate, scratch = harness
    selftest_skills.certify(sub, gate.verifier_config(), selftest_skills.INSTANCE_MAKER)
    instances.commit_nonce(sub, HYPOTHESIS, "run-1", NONCE)
    seen = {}

    def spy(*args, **kwargs):
        seen.update(kwargs)
        return runner.Attempt("attempt-planted", "recipe-planted", runner.STATUS_FAIL, None)

    monkeypatch.setattr(runner, "launch", spy)
    instances.launch_trial(
        sub,
        gate,
        nonce=NONCE,
        bits=28,
        trial=0,
        scratch_root=scratch,
        method_identity=METHOD_IDENTITY,
        budget_remaining=BUDGET,
    )
    assert seen["ceiling_multiplier"] == gate.tiers["ceiling_multiplier"] == 4
    assert seen["do_not_cache"] is True and seen["skip_cache_lookup"] is True and seen["stdin_document"]["bits"] == 28


HOLD_OUT_BITS = 60
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
    measurement_scope=runner.SCOPE_TREE,
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


@pytest.fixture
def plan():
    return ladderplan.LadderPlan.load(
        json.loads((Path(__file__).resolve().parents[2] / "bundle" / "ladder_plan.json").read_text())
    )


def keep_table(hypothesis_hash, gate_bundle):
    sizes = [30, 40, 50, HOLD_OUT_BITS]
    return laddertable.ResultTable(
        run_id="run-keep",
        nonce="nonce-keep",
        hypothesis_hash=hypothesis_hash,
        method_identity=METHOD_IDENTITY,
        implementation_revision=instance_maker.identity_bundle()["implementation_revision"],
        gate_bundle_hash=gate_bundle.hash,
        plan_hash="dd" * 32,
        uncounted_backend=None,
        rungs=tuple(
            dataclasses.replace(
                RUNG_BASE, bits=b, role=ladderplan.ROLE_HOLD_OUT if b == HOLD_OUT_BITS else ladderplan.ROLE_FIT
            )
            for b in sizes
        ),
        trials=tuple(dataclasses.replace(TRIAL_BASE, bits=b, trial=t) for b in sizes for t in (0, 1)),
    )


def bindings(sub):
    rows = sub.conn.execute(
        "SELECT canonical FROM nodes WHERE kind = ? ORDER BY rowid", (ticketlattice.BINDING_KIND,)
    ).fetchall()
    return [canon.decode(ticketlattice.BINDING, row["canonical"]) for row in rows]


def seeded_keep(sub, gate):
    obj = factories.hypothesis_object(seed=0, method_identity=METHOD_IDENTITY)
    claims.write_hypothesis_object(sub, obj)
    instances.commit_nonce(sub, obj.hash, "run-1", NONCE)
    return obj


def test_a_tier_two_launch_binds_its_attempt_to_the_ticket_the_gate_selected(harness, plan):
    sub, gate, scratch = harness
    selftest_skills.certify(sub, gate.verifier_config(), selftest_skills.INSTANCE_MAKER)
    obj = seeded_keep(sub, gate)
    table = keep_table(obj.hash, gate)
    laddertable.write(sub, table, plan)
    attempt, out = _launch(sub, gate, scratch, declared_tier=2)
    assert attempt.status == runner.STATUS_OK and out is not None
    bound = bindings(sub)
    assert [(b["attempt_id"], b["hypothesis_key"], b["tier"], b["bundle_hash"]) for b in bound] == [
        (attempt.attempt_id, obj.hash, 2, gate.hash)
    ]
    ticket = claims.get_ticket(sub, bound[0]["ticket_hash"])
    assert (ticket["node_hash"], ticket["tier"]) == (table.hash, tiergate.TIER_TWO_TICKET_TIER)


def test_a_tier_zero_launch_selects_no_ticket_and_records_no_binding(harness):
    sub, gate, scratch = harness
    selftest_skills.certify(sub, gate.verifier_config(), selftest_skills.INSTANCE_MAKER)
    seeded_keep(sub, gate)
    attempt, out = _launch(sub, gate, scratch)
    assert attempt.status == runner.STATUS_OK and out is not None
    assert bindings(sub) == []


def test_the_binding_carries_a_refused_launch_no_further_than_the_refusal(harness):
    sub, gate, scratch = harness
    selftest_skills.certify(sub, gate.verifier_config(), selftest_skills.INSTANCE_MAKER)
    seeded_keep(sub, gate)
    with pytest.raises(instances.TrialRefused) as info:
        _launch(sub, gate, scratch, declared_tier=2)
    assert tiergate.TIER_TWO_ABOVE in info.value.reasons
    assert bindings(sub) == []


def test_a_bound_tier_two_attempt_is_the_record_a_tier_three_launch_reads(harness, plan):
    sub, gate, scratch = harness
    selftest_skills.certify(sub, gate.verifier_config(), selftest_skills.INSTANCE_MAKER)
    obj = seeded_keep(sub, gate)
    laddertable.write(sub, keep_table(obj.hash, gate), plan)
    attempt, _ = _launch(sub, gate, scratch, declared_tier=2)
    candidate = ticketlattice.tier_three_candidate(sub, gate, obj.hash, METHOD_IDENTITY)
    assert candidate is None, "an unverified witness is not a Tier-3 candidate"
    claims.write_repro_record(
        sub,
        claims.ReproRecord(
            attempt_id=attempt.attempt_id, kind=repro.WITNESS_CHECK, passed=True, at="2026-09-08T00:00:00.000000+00:00"
        ),
    )
    verified = ticketlattice.tier_three_candidate(sub, gate, obj.hash, METHOD_IDENTITY)
    assert verified is not None and verified["attempt_id"] == attempt.attempt_id
