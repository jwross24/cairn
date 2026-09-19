import copy
import dataclasses
import json
import os
import sys
from decimal import Decimal
from pathlib import Path

import pytest

from cairn import allowlist, bundle, claims, instances, ladder, ladderplan, laddertable, ledger, runner
from cairn.skills import bsgs, instance_maker, rho_dp

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _substrate_helpers as helpers

ROOT = Path(__file__).resolve().parents[2]
COMMITTED = json.loads((ROOT / "bundle" / "ladder_plan.json").read_text())
BACKEND = os.path.realpath(sys.executable)
RUN_ID = "run-ladder-e2e"
PATIENCE = 60
MAKER_CEILING = 60
FIT_BITS = 28
HOLD_OUT_BITS = 30


@pytest.fixture
def shipped(pinned_bundle):
    return bundle.GateBundle.open(*pinned_bundle())


@pytest.fixture
def writer(tmp_path):
    sub = helpers.open_writer(tmp_path)
    yield sub
    sub.close()


@pytest.fixture
def plan():
    obj = copy.deepcopy(COMMITTED)
    obj["baseline"]["implementation_revision"] = rho_dp.implementation_revision()
    full = ladderplan.LadderPlan.load(obj)
    fit = dataclasses.replace(full.rung(30), bits=FIT_BITS, trials=2)
    hold_out = dataclasses.replace(full.rung(40), bits=HOLD_OUT_BITS, role=ladderplan.ROLE_HOLD_OUT, trials=2)
    return dataclasses.replace(full, rungs=(fit, hold_out), hold_out_m=2, patience_multiplier=PATIENCE)


@pytest.fixture
def hypothesis_object():
    return claims.HypothesisObject(
        target_family="dlp",
        claimed={"model": "c_sqrt_n_ops"},
        method_identity={"interface_version": bsgs.INTERFACE_VERSION, "params": {}},
        declared_parameter_ranges={"bits": [FIT_BITS, HOLD_OUT_BITS]},
        sampling_distribution=None,
    )


def _dispatch_run(writer, shipped, tmp_path, plan, hypothesis_object, run_id, *, claimant=bsgs):
    if claims.get_hypothesis_object(writer, hypothesis_object.hash) is None:
        claims.write_hypothesis_object(writer, hypothesis_object)
    _, nonce = ladder.commit_entropy(writer, hypothesis_hash=hypothesis_object.hash, run_id=run_id)
    for module in (claimant, rho_dp, instance_maker):
        identity = module.identity_bundle()
        digest = writer.put_identity_bundle(identity)
        if not writer.certified(digest):
            writer.put_certificate(digest, helpers.TRANSCRIPT_HASH, helpers.ENV_MANIFEST_HASH, helpers.SELFTEST_SUMMARY)
    scratch = tmp_path / f"allow-{run_id}"
    scratch.mkdir()
    hypothesis = {
        "target_family": hypothesis_object.target_family,
        "claimed": hypothesis_object.claimed,
        "method_identity": hypothesis_object.method_identity,
        "declared_parameter_ranges": hypothesis_object.declared_parameter_ranges,
        "sampling_distribution": hypothesis_object.sampling_distribution,
    }
    allow = allowlist.instantiate(shipped, hypothesis=hypothesis, counted_object=BACKEND, scratch_dir=scratch)
    for arm, module in (
        (ladder.CLAIMANT, claimant),
        (ladder.BASELINE, rho_dp),
        (ladder.BASELINE_AA, rho_dp),
    ):
        ladder.dispatch(
            writer,
            shipped,
            plan=plan,
            plan_hash=ladderplan.plan_digest(shipped) or "dd" * 32,
            hypothesis_hash=hypothesis_object.hash,
            nonce=nonce.nonce,
            run_id=run_id,
            arm=arm,
            skill=module.__name__,
            allow_list=allow,
        )
    return nonce.nonce


@pytest.fixture
def dispatched(writer, shipped, tmp_path, plan, hypothesis_object):
    return _dispatch_run(writer, shipped, tmp_path, plan, hypothesis_object, RUN_ID)


@pytest.fixture
def attest_path(tmp_path):
    path = tmp_path / "attestations.log"
    path.touch()
    return path


def test_a_full_small_run_writes_a_table_with_every_arm_on_one_instance_stream(
    writer, shipped, tmp_path, plan, hypothesis_object, dispatched, attest_path
):
    scratch = tmp_path / "runs"
    scratch.mkdir()
    table, arm_trials = ladder.run(
        writer,
        shipped,
        plan=plan,
        plan_hash=ladderplan.plan_digest(shipped) or "dd" * 32,
        run_id=RUN_ID,
        hypothesis_hash=hypothesis_object.hash,
        nonce=dispatched,
        scratch_root=scratch,
        budget_remaining=10_000.0,
        ceiling_multiplier=MAKER_CEILING,
        attest_path=attest_path,
    )

    assert {r.bits for r in table.rungs} == {FIT_BITS, HOLD_OUT_BITS}
    assert len(table.trials) == len(arm_trials)
    assert {trial.gate_ops.kind for trial in table.trials} == {laddertable.OPS_UNKNOWN}
    assert all(trial.gate_ops.value is None for trial in table.trials)
    assert table.method_identity == hypothesis_object.method_identity
    assert table.implementation_revision == bsgs.implementation_revision()
    assert table.uncounted_backend == BACKEND

    fit_arms = {t.arm for t in arm_trials if t.bits == FIT_BITS}
    assert fit_arms == set(ladderplan.ARMS)
    assert {t.arm for t in arm_trials if t.bits == HOLD_OUT_BITS} == {ladder.CLAIMANT}

    by_key = {}
    for t in arm_trials:
        by_key.setdefault((t.bits, t.trial), {})[t.arm] = t
    for arms in by_key.values():
        assert len({t.instance_hash for t in arms.values()}) == 1
        assert len({t.seed for t in arms.values()}) == len(arms)
        for t in arms.values():
            assert t.output_complete and t.recovered

    stored = laddertable.read(writer, table.hash)
    assert stored.hash == table.hash
    assert {t.measurement_scope for t in stored.trials} == {t.measurement_scope for t in table.trials}
    assert all(scope in runner.MEASUREMENT_SCOPES for scope in {t.measurement_scope for t in table.trials})
    assert laddertable.verdict(table, plan).predicate != laddertable.MEASUREMENT_SCOPE
    recorded = laddertable.recorded_verdict(writer, table.hash)
    assert (recorded.kind, recorded.predicate) == (
        laddertable.verdict(table, plan).kind,
        laddertable.verdict(table, plan).predicate,
    )
    assert recorded.kind != laddertable.KEEP
    published = instances.trials_for(writer, dispatched)
    assert len(published) == 4


def test_an_injected_gate_counter_aggregates_all_arms_before_persistence(
    writer, shipped, tmp_path, plan, hypothesis_object, dispatched, attest_path
):
    scratch = tmp_path / "counted-runs"
    scratch.mkdir()

    def count(trial):
        arm_offset = {ladder.CLAIMANT: 0, ladder.BASELINE: 1_000_000, ladder.BASELINE_AA: 2_000_000}[trial.arm]
        return laddertable.OpsObservation(laddertable.OPS_EXACT, 10_000_000 + arm_offset + trial.trial)

    table, arm_trials = ladder.run(
        writer,
        shipped,
        plan=plan,
        plan_hash=ladderplan.plan_digest(shipped) or "dd" * 32,
        run_id=RUN_ID,
        hypothesis_hash=hypothesis_object.hash,
        nonce=dispatched,
        scratch_root=scratch,
        budget_remaining=10_000.0,
        ceiling_multiplier=MAKER_CEILING,
        ops_counter=count,
        attest_path=attest_path,
    )

    assert all(trial.gate_ops.kind == laddertable.OPS_EXACT for trial in table.trials)
    assert {trial.gate_ops.value for trial in table.trials if trial.arm == ladder.CLAIMANT} == {10_000_000, 10_000_001}
    assert all(trial.reported_ops != trial.gate_ops.value for trial in table.trials)
    assert all(row.ops_kind == laddertable.OPS_EXACT for row in table.rungs)
    assert all(row.claim_ci_low is not None for row in table.rungs if row.role == ladderplan.ROLE_FIT)
    assert all(row.claim_ci_low is None for row in table.rungs if row.role == ladderplan.ROLE_HOLD_OUT)
    verified = {(trial.arm, trial.bits, trial.trial) for trial in table.trials}
    assert laddertable.recompute(table, plan, verified).agrees
    assert laddertable.read(writer, table.hash).hash == table.hash
    assert len(arm_trials) == len(table.trials)
    claimant = ladder.dispatches_for(writer, RUN_ID)[ladder.CLAIMANT]
    assert writer.yanked(claimant.identity_bundle_hash)
    assert laddertable.recorded_verdict(writer, table.hash).predicate == laddertable.COUNT_DIVERGENCE
    entries = ledger.entries_for(writer, hypothesis_object.hash)
    assert [(entry["refutation_kind"], entry["faulting_revision"], entry["caught_by"]) for entry in entries] == [
        (ledger.IMPLEMENTATION, claimant.identity_bundle_hash, "ladder:count_divergence")
    ]


def test_a_run_missing_an_arm_refuses_before_any_instance_is_drawn(
    writer, shipped, tmp_path, plan, hypothesis_object, popen_spy, attest_path
):
    claims.write_hypothesis_object(writer, hypothesis_object)
    _, nonce = ladder.commit_entropy(writer, hypothesis_hash=hypothesis_object.hash, run_id=RUN_ID)
    scratch = tmp_path / "runs"
    scratch.mkdir()
    with pytest.raises(ladder.RunRefused) as raised:
        ladder.run(
            writer,
            shipped,
            plan=plan,
            plan_hash="dd" * 32,
            run_id=RUN_ID,
            hypothesis_hash=hypothesis_object.hash,
            nonce=nonce.nonce,
            scratch_root=scratch,
            budget_remaining=10_000.0,
            attest_path=attest_path,
        )
    assert raised.value.reason == ladder.ARMS_MISSING
    assert popen_spy == []
    assert instances.trials_for(writer, nonce.nonce) == []


def test_a_patience_limited_run_records_the_observed_claimant_success_rate(
    writer, shipped, tmp_path, plan, hypothesis_object, attest_path
):
    impatient = dataclasses.replace(plan, patience_multiplier=1)
    nonce = _dispatch_run(writer, shipped, tmp_path, impatient, hypothesis_object, "run-ladder-impatient")
    scratch = tmp_path / "impatient"
    scratch.mkdir()
    table, arm_trials = ladder.run(
        writer,
        shipped,
        plan=impatient,
        plan_hash=ladderplan.plan_digest(shipped) or "dd" * 32,
        run_id="run-ladder-impatient",
        hypothesis_hash=hypothesis_object.hash,
        nonce=nonce,
        scratch_root=scratch,
        budget_remaining=10_000.0,
        ceiling_multiplier=MAKER_CEILING,
        attest_path=attest_path,
    )
    claimant = [t for t in arm_trials if t.arm == ladder.CLAIMANT]
    diagnostics = [
        {
            "bits": t.bits,
            "seed": t.seed,
            "status": t.status,
            "cpu_seconds": t.cpu_seconds,
            "ceiling_seconds": runner.ceiling_for(
                bsgs.COST_PROFILE.evaluate(t.bits).expected_wall_s,
                impatient.patience_multiplier,
                subprocess_startup_ms=shipped.tiers["subprocess_startup_ms"],
            ),
        }
        for t in claimant
    ]
    assert claimant, diagnostics
    for t in claimant:
        if t.status == runner.STATUS_BUDGET_EXCEEDED:
            assert t.output_complete and t.reported_ops is not None, diagnostics
    for row in table.rungs:
        trials = [t for t in claimant if t.bits == row.bits]
        successes = sum(t.status == runner.STATUS_OK and t.output_complete and t.recovered for t in trials)
        expected = (Decimal(successes) / len(trials)).quantize(Decimal("0.0001"))
        assert Decimal(row.success_rate) == expected, diagnostics
    found = laddertable.verdict(table, impatient)
    if any(not t.output_complete or not t.recovered or t.status != runner.STATUS_OK for t in claimant):
        assert found.kind not in (laddertable.KEEP, laddertable.KEEP_IN_SAMPLE), diagnostics
    assert laddertable.recorded_verdict(writer, table.hash).kind == found.kind
