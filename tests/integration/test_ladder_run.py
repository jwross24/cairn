import copy
import dataclasses
import json
from decimal import Decimal
from pathlib import Path

import pytest
from _ladder_run_helpers import (
    BACKEND,
    COMMITTED,
    FIT_BITS,
    HOLD_OUT_BITS,
    MAKER_CEILING,
    ROOT,
    RUN_ID,
    _dispatch_run,
)
from _ladder_run_helpers import attest_path as attest_path
from _ladder_run_helpers import dispatched as dispatched
from _ladder_run_helpers import hypothesis_object as hypothesis_object
from _ladder_run_helpers import plan as plan
from _ladder_run_helpers import shipped as shipped
from _ladder_run_helpers import writer as writer

from cairn import (
    allowlist,
    claims,
    escrow,
    instances,
    ladder,
    ladderplan,
    laddertable,
    runner,
    verifier,
)
from cairn.skills import bsgs, rho_dp


def test_a_full_small_run_writes_a_table_with_every_arm_on_one_instance_stream(
    writer, shipped, tmp_path, plan, hypothesis_object, dispatched, attest_path, json_test_log, monkeypatch
):
    foreign_nonce = instances.draw_nonce(writer, hypothesis_object.hash, "unrelated-run")
    foreign_attempt, foreign_instance = instances.launch_trial(
        writer,
        shipped,
        nonce=foreign_nonce.nonce,
        bits=FIT_BITS,
        trial=0,
        scratch_root=tmp_path / "foreign",
        method_identity=hypothesis_object.method_identity,
        budget_remaining=10_000.0,
        ceiling_multiplier=MAKER_CEILING,
        attest_path=attest_path,
    )
    assert foreign_instance is not None and escrow.standing(writer, foreign_attempt.attempt_id)
    real_arm = ladder.run_arm

    def checked_arm(*args, **kwargs):
        result = real_arm(*args, **kwargs)
        if escrow.standing(writer, result.attempt_id):
            escrow.first_check(writer, result.attempt_id, check_event="test:verification")
        return result

    monkeypatch.setattr(ladder, "run_arm", checked_arm)
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
    assert all(trial.reported_ops is not None for trial in table.trials)
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
            policy = allowlist.read(writer, t.allow_list_hash)
            dispatch = ladder.dispatches_for(writer, RUN_ID)[t.arm]
            assert policy.writable_root == t.writable_root
            assert policy.writable_root == str(Path(dispatch.allow_list["writable_root"]) / t.attempt_id / "scratch")
            assert policy.counted_object == dispatch.allow_list["counted_object"]
            assert policy.profile_hash == dispatch.allow_list["profile_hash"]

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
    assert (recorded.kind, recorded.predicate) == (laddertable.INCONCLUSIVE, laddertable.UNCOUNTED_BACKEND)

    claimant_attempt = next(
        attempt_id
        for arm, _, _, attempt_id in laddertable.membership_for_table(writer, table.hash)
        if arm == ladder.CLAIMANT
    )
    claimant_trials = {(trial.arm, trial.bits, trial.trial) for trial in table.trials if trial.arm == ladder.CLAIMANT}
    with pytest.raises(laddertable.LadderTableError, match="must verify every trial"):
        laddertable.record(writer, table, plan, claimant_trials, attempt_id=claimant_attempt)

    published = instances.trials_for(writer, dispatched)
    assert len(published) == 4
    attempt_ids = {trial.attempt_id for trial in arm_trials} | {trial["attempt_id"] for trial in published}
    assert foreign_attempt.attempt_id not in attempt_ids
    assert any(escrow.reservation(writer, attempt_id)["spent_at"] is not None for attempt_id in attempt_ids)
    assert any(escrow.standing(writer, attempt_id) for attempt_id in attempt_ids)
    production = sum(
        writer.get_receipt(writer.get_attempt(attempt_id)["receipt_hash"])["cpu_user_s"]
        + writer.get_receipt(writer.get_attempt(attempt_id)["receipt_hash"])["cpu_sys_s"]
        for attempt_id in attempt_ids
    )
    verification = sum(
        row["reserved"]
        for attempt_id in attempt_ids
        if (row := escrow.reservation(writer, attempt_id))["released_at"] is None
    )
    report = next(
        row
        for line in json_test_log.read_text().splitlines()
        if (row := json.loads(line))["step"] == "ladder" and row["event"] == "run"
    )
    assert report["production_core_s"] == pytest.approx(production)
    assert report["verification_core_s"] == pytest.approx(verification)
    assert report["budget_remaining_core_s"] == pytest.approx(10_000.0 - production - verification)


def test_captured_post_exit_overage_keeps_reported_operations_diagnostic(writer, shipped, tmp_path, monkeypatch):
    plan_data = copy.deepcopy(COMMITTED)
    plan_data["baseline"]["implementation_revision"] = rho_dp.implementation_revision()
    full_plan = dataclasses.replace(ladderplan.LadderPlan.load(plan_data), patience_multiplier=1)
    hypothesis = claims.HypothesisObject(
        target_family="dlp",
        claimed={"model": "c_sqrt_n_ops"},
        method_identity={"interface_version": bsgs.INTERFACE_VERSION, "params": {}},
        declared_parameter_ranges={"bits": [40, 40]},
        sampling_distribution=None,
    )
    run_id = "run-ladder-post-exit-capture"
    _dispatch_run(writer, shipped, tmp_path, full_plan, hypothesis, run_id)
    claimant = ladder.dispatches_for(writer, run_id)[ladder.CLAIMANT]
    output = (ROOT / "tests" / "fixtures" / "cairn-kjgf-post-exit.stdout.json").read_bytes()
    captured = json.loads(output)
    parsed = runner.parse_skill_output(output)
    instance = verifier.Instance(
        p=int(captured["p"]),
        a=int(captured["a"]),
        b=int(captured["b"]),
        n=int(captured["n"]),
        P=tuple(int(value) for value in captured["P"]),
        Q=tuple(int(value) for value in captured["Q"]),
    )
    launch = runner.Launch(
        exit_status=0,
        start_mono=112593.354008708,
        end_mono=112595.388844333,
        wall_s=2.03483562500332,
        cpu_user_s=2.014101,
        cpu_sys_s=0.011,
        peak_rss_bytes=67_010_560,
        timed_out=False,
        skill_yanked=False,
        argv=(),
        measurement_scope=runner.SCOPE_TREE,
    )
    cpu_seconds = launch.cpu_user_s + launch.cpu_sys_s
    ceiling = runner.ceiling_for(
        bsgs.COST_PROFILE.evaluate(captured["bits"]).expected_wall_s,
        full_plan.patience_multiplier,
        subprocess_startup_ms=shipped.tiers["subprocess_startup_ms"],
    )
    status = runner.status_for(parsed, launch.exit_status, cpu_seconds, ceiling)
    launched = []

    def replay(*args, **kwargs):
        launched.append(kwargs["stdin_document"])
        return runner.Attempt(
            attempt_id="captured-overage",
            recipe_key="captured-recipe",
            status=status,
            launch=launch,
            parsed=parsed,
        )

    monkeypatch.setattr(runner, "launch", replay)
    trial = ladder.run_arm(
        writer,
        shipped,
        claimant,
        plan=full_plan,
        instance=instance,
        instance_hash=instance.instance_hash,
        bits=captured["bits"],
        trial=4,
        scratch_root=tmp_path / "captured-overage",
        budget_remaining=10_000.0,
    )

    assert parsed.well_formed
    assert cpu_seconds > ceiling
    assert status == runner.STATUS_BUDGET_EXCEEDED
    assert launched[0]["bits"] == captured["bits"]
    assert launched[0]["p"] == captured["p"]
    assert trial.trial == 4
    assert trial.status == status
    assert trial.output_complete and trial.recovered
    assert trial.reported_ops == 1_654_804
    assert trial.gate_ops == laddertable.OpsObservation(laddertable.OPS_UNKNOWN, None)


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
