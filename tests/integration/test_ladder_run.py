import copy
import dataclasses
import json
import os
import sys
from decimal import Decimal
from pathlib import Path

import pytest

from cairn import allowlist, bundle, claims, instances, ladder, ladderplan, laddertable, runner
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


def _dispatch_run(writer, shipped, tmp_path, plan, hypothesis_object, run_id):
    if claims.get_hypothesis_object(writer, hypothesis_object.hash) is None:
        claims.write_hypothesis_object(writer, hypothesis_object)
    _, nonce = ladder.commit_entropy(writer, hypothesis_hash=hypothesis_object.hash, run_id=run_id)
    for module in (bsgs, rho_dp, instance_maker):
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
        (ladder.CLAIMANT, bsgs),
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


def test_a_full_small_run_writes_a_table_with_every_arm_on_one_instance_stream(
    writer, shipped, tmp_path, plan, hypothesis_object, dispatched
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
    )

    assert {r.bits for r in table.rungs} == {FIT_BITS, HOLD_OUT_BITS}
    assert len(table.trials) == 4
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
            assert t.completed and t.recovered

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


def test_a_run_missing_an_arm_refuses_before_any_instance_is_drawn(
    writer, shipped, tmp_path, plan, hypothesis_object, popen_spy
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
        )
    assert raised.value.reason == ladder.ARMS_MISSING
    assert popen_spy == []
    assert instances.trials_for(writer, nonce.nonce) == []


def test_a_trial_driven_into_the_patience_ceiling_lands_as_a_success_rate_failure(
    writer, shipped, tmp_path, plan, hypothesis_object
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
    )
    claimant = [t for t in arm_trials if t.arm == ladder.CLAIMANT]
    assert claimant and all(t.status == runner.STATUS_BUDGET_EXCEEDED for t in claimant)
    assert all(not t.completed and not t.recovered for t in claimant)
    for t in claimant:
        assert t.ops == ladder._ceiling_ops(bsgs, t.bits, impatient.patience_multiplier)
    for row in table.rungs:
        assert Decimal(row.success_rate) == 0
    found = laddertable.verdict(table, impatient)
    assert found.kind != laddertable.KEEP
    assert laddertable.recorded_verdict(writer, table.hash).kind == found.kind
