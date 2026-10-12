import copy
import dataclasses
import json
import os
import sys
from decimal import Decimal
from pathlib import Path

import pytest

from cairn import (
    allowlist,
    bundle,
    claims,
    escrow,
    instances,
    ladder,
    ladderplan,
    laddertable,
    ledger,
    runner,
    verifier,
)
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


def _dispatch_run(
    writer, shipped, tmp_path, plan, hypothesis_object, run_id, *, claimant=bsgs, backend_paths=None, withheld_roots=()
):
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
    allow = allowlist.instantiate(
        shipped,
        hypothesis=hypothesis,
        counted_object=BACKEND,
        scratch_dir=scratch,
        backend_paths=backend_paths,
        withheld_roots=withheld_roots,
    )
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


@pytest.mark.parametrize("cpu_core_s", [0.3, 0.0], ids=["measured-overage", "standing-verification"])
def test_a_run_debits_the_maker_before_the_first_arm_spawn(
    writer, shipped, tmp_path, plan, hypothesis_object, dispatched, attest_path, popen_spy, monkeypatch, cpu_core_s
):
    real_spawn = runner.spawn_and_wait

    def measured_spawn(*args, **kwargs):
        result = real_spawn(*args, **kwargs)
        return dataclasses.replace(result, cpu_user_s=cpu_core_s, cpu_sys_s=0.0)

    monkeypatch.setattr(runner, "spawn_and_wait", measured_spawn)
    evaluation = bsgs.COST_PROFILE.evaluate(FIT_BITS)
    grant = (
        runner.ceiling_for(evaluation.expected_core_s, plan.patience_multiplier)
        + evaluation.expected_verification_core_s
    )
    with pytest.raises(runner.BudgetRefused):
        ladder.run(
            writer,
            shipped,
            plan=plan,
            plan_hash=ladderplan.plan_digest(shipped),
            run_id=RUN_ID,
            hypothesis_hash=hypothesis_object.hash,
            nonce=dispatched,
            scratch_root=tmp_path / "runs",
            budget_remaining=grant,
            ceiling_multiplier=40,
            attest_path=attest_path,
        )
    launches = [args for args in popen_spy if "-m" in args]
    assert len(launches) == 1 and instance_maker.__name__ in launches[0]
    attempts = writer.conn.execute("SELECT status FROM attempts").fetchall()
    assert [row["status"] for row in attempts] == [runner.STATUS_OK]


def test_a_run_debits_an_arm_before_the_next_arm_spawn(
    writer, shipped, tmp_path, plan, hypothesis_object, dispatched, attest_path, popen_spy, monkeypatch
):
    real_spawn = runner.spawn_and_wait

    def measured_spawn(*args, **kwargs):
        result = real_spawn(*args, **kwargs)
        return dataclasses.replace(result, cpu_user_s=0.3, cpu_sys_s=0.0)

    monkeypatch.setattr(runner, "spawn_and_wait", measured_spawn)
    maker = instance_maker.COST_PROFILE.evaluate(FIT_BITS)
    claimant = bsgs.COST_PROFILE.evaluate(FIT_BITS)
    baseline = rho_dp.COST_PROFILE.evaluate(FIT_BITS)
    grant = (
        runner.ceiling_for(baseline.expected_core_s, plan.patience_multiplier)
        + baseline.expected_verification_core_s
        + maker.expected_core_s
        + maker.expected_verification_core_s
        + claimant.expected_core_s
        + claimant.expected_verification_core_s
    )
    with pytest.raises(runner.BudgetRefused):
        ladder.run(
            writer,
            shipped,
            plan=plan,
            plan_hash=ladderplan.plan_digest(shipped),
            run_id=RUN_ID,
            hypothesis_hash=hypothesis_object.hash,
            nonce=dispatched,
            scratch_root=tmp_path / "runs",
            budget_remaining=grant,
            ceiling_multiplier=40,
            attest_path=attest_path,
        )
    launches = [args for args in popen_spy if "-m" in args]
    assert len(launches) == 2
    assert instance_maker.__name__ in launches[0] and bsgs.__name__ in launches[1]


def test_a_run_debits_completed_trials_before_the_next_instance_spawn(
    writer, shipped, tmp_path, plan, hypothesis_object, dispatched, attest_path, popen_spy, monkeypatch
):
    plan = dataclasses.replace(
        plan,
        rungs=(dataclasses.replace(plan.rungs[0], role=ladderplan.ROLE_HOLD_OUT),),
        patience_multiplier=40,
    )
    real_spawn = runner.spawn_and_wait

    def measured_spawn(*args, **kwargs):
        result = real_spawn(*args, **kwargs)
        return dataclasses.replace(result, cpu_user_s=0.3, cpu_sys_s=0.0)

    monkeypatch.setattr(runner, "spawn_and_wait", measured_spawn)
    maker = instance_maker.COST_PROFILE.evaluate(FIT_BITS)
    claimant = bsgs.COST_PROFILE.evaluate(FIT_BITS)
    grant = (
        runner.ceiling_for(maker.expected_core_s, 40)
        + maker.expected_verification_core_s
        + maker.expected_core_s
        + maker.expected_verification_core_s
        + claimant.expected_core_s
        + claimant.expected_verification_core_s
    )
    with pytest.raises(runner.BudgetRefused):
        ladder.run(
            writer,
            shipped,
            plan=plan,
            plan_hash=ladderplan.plan_digest(shipped),
            run_id=RUN_ID,
            hypothesis_hash=hypothesis_object.hash,
            nonce=dispatched,
            scratch_root=tmp_path / "runs",
            budget_remaining=grant,
            ceiling_multiplier=40,
            attest_path=attest_path,
        )
    launches = [args for args in popen_spy if "-m" in args]
    assert len(launches) == 2
    assert instance_maker.__name__ in launches[0] and bsgs.__name__ in launches[1]


def _draw_instance(writer, shipped, tmp_path, hypothesis_object, nonce, attest_path):
    attempt, out = instances.launch_trial(
        writer,
        shipped,
        nonce=nonce,
        bits=FIT_BITS,
        trial=0,
        scratch_root=tmp_path / "runs",
        method_identity=hypothesis_object.method_identity,
        budget_remaining=10_000.0,
        ceiling_multiplier=MAKER_CEILING,
        attest_path=attest_path,
    )
    assert out is not None
    return attempt, out


def _run_claimant_arm(writer, shipped, tmp_path, plan, out, *, budget_remaining, attest_path):
    return ladder.run_arm(
        writer,
        shipped,
        ladder.dispatches_for(writer, RUN_ID)[ladder.CLAIMANT],
        plan=plan,
        instance=verifier.Instance(**out.instance()),
        instance_hash=out.instance_hash,
        bits=FIT_BITS,
        trial=0,
        scratch_root=tmp_path / "runs",
        budget_remaining=budget_remaining,
        attest_path=attest_path,
    )


def test_an_arm_is_refused_when_the_budget_covers_its_ceiling_but_not_its_ceiling_plus_verification(
    writer, shipped, tmp_path, plan, hypothesis_object, dispatched, attest_path, popen_spy
):
    _, out = _draw_instance(writer, shipped, tmp_path, hypothesis_object, dispatched, attest_path)
    evaluation = bsgs.COST_PROFILE.evaluate(FIT_BITS)
    ceiling = runner.ceiling_for(
        evaluation.expected_core_s,
        plan.patience_multiplier,
        subprocess_startup_ms=shipped.tiers["subprocess_startup_ms"],
    )
    budget_remaining = ceiling + evaluation.expected_verification_core_s / 2
    assert evaluation.expected_core_s + evaluation.expected_verification_core_s <= budget_remaining
    spawned = len(popen_spy)
    attempts = writer.conn.execute("SELECT count(*) AS n FROM attempts").fetchone()["n"]

    with pytest.raises(runner.BudgetRefused) as raised:
        _run_claimant_arm(
            writer, shipped, tmp_path, plan, out, budget_remaining=budget_remaining, attest_path=attest_path
        )

    assert raised.value.ceiling_core_s == pytest.approx(ceiling)
    assert raised.value.remaining == pytest.approx(budget_remaining - evaluation.expected_verification_core_s)
    assert len(popen_spy) == spawned
    assert writer.conn.execute("SELECT count(*) AS n FROM attempts").fetchone()["n"] == attempts


def test_a_run_budget_counts_standing_verification_and_not_a_released_reservation(
    writer, shipped, tmp_path, plan, hypothesis_object, dispatched, attest_path, monkeypatch
):
    maker, out = _draw_instance(writer, shipped, tmp_path, hypothesis_object, dispatched, attest_path)
    real_spawn = runner.spawn_and_wait

    def overage_spawn(*args, **kwargs):
        result = real_spawn(*args, **kwargs)
        return dataclasses.replace(result, cpu_user_s=5.0, cpu_sys_s=0.0)

    monkeypatch.setattr(runner, "spawn_and_wait", overage_spawn)
    trial = _run_claimant_arm(writer, shipped, tmp_path, plan, out, budget_remaining=10_000.0, attest_path=attest_path)

    assert trial.status == runner.STATUS_BUDGET_EXCEEDED
    assert escrow.reservation(writer, trial.attempt_id)["released_at"] is not None
    assert escrow.standing(writer, maker.attempt_id)
    maker_receipt = writer.get_receipt(writer.get_attempt(maker.attempt_id)["receipt_hash"])
    maker_core_s = maker_receipt["cpu_user_s"] + maker_receipt["cpu_sys_s"]
    standing_core_s = instance_maker.COST_PROFILE.evaluate(FIT_BITS).expected_verification_core_s
    released_core_s = bsgs.COST_PROFILE.evaluate(FIT_BITS).expected_verification_core_s
    assert released_core_s > 0

    budget = ladder.RunBudget(10_000.0, [maker.attempt_id, trial.attempt_id])

    assert budget.snapshot(writer) == {
        "granted_core_s": 10_000.0,
        "production_core_s": pytest.approx(maker_core_s + 5.0),
        "verification_core_s": pytest.approx(standing_core_s),
        "budget_remaining_core_s": pytest.approx(10_000.0 - maker_core_s - 5.0 - standing_core_s),
    }


def _run_ladder(writer, shipped, tmp_path, plan, hypothesis_object, nonce, attest_path):
    return ladder.run(
        writer,
        shipped,
        plan=plan,
        plan_hash=ladderplan.plan_digest(shipped) or "dd" * 32,
        run_id=RUN_ID,
        hypothesis_hash=hypothesis_object.hash,
        nonce=nonce,
        scratch_root=tmp_path / "runs",
        budget_remaining=10_000.0,
        ceiling_multiplier=MAKER_CEILING,
        attest_path=attest_path,
    )


def _fail_on_spawn(monkeypatch, number, error):
    real_spawn = runner.spawn_and_wait
    calls = []

    def spawn(*args, **kwargs):
        calls.append(args)
        if len(calls) == number:
            raise error
        return real_spawn(*args, **kwargs)

    monkeypatch.setattr(runner, "spawn_and_wait", spawn)


def _record_snapshots(monkeypatch):
    seen = []
    real_snapshot = ladder.RunBudget.snapshot

    def snapshot(self, sub):
        seen.append(list(self.attempt_ids))
        return real_snapshot(self, sub)

    monkeypatch.setattr(ladder.RunBudget, "snapshot", snapshot)
    return seen


def test_a_run_reconciles_when_an_earlier_run_died_mid_attempt(
    writer, shipped, tmp_path, plan, hypothesis_object, dispatched, attest_path, json_test_log, monkeypatch
):
    _fail_on_spawn(monkeypatch, 1, KeyboardInterrupt())
    with pytest.raises(KeyboardInterrupt):
        _run_ladder(writer, shipped, tmp_path, plan, hypothesis_object, dispatched, attest_path)
    (killed,) = runner.running_attempts(writer)
    assert writer.get_attempt(killed)["receipt_hash"] is None
    assert escrow.standing(writer, killed)

    snapshots = _record_snapshots(monkeypatch)
    table, arm_trials = _run_ladder(writer, shipped, tmp_path, plan, hypothesis_object, dispatched, attest_path)

    interrupted = writer.get_attempt(killed)
    assert interrupted["status"] == runner.STATUS_INTERRUPTED and interrupted["receipt_hash"] is None
    assert escrow.reservation(writer, killed)["released_at"] is not None
    assert len(table.trials) == len(arm_trials) and snapshots
    assert all(killed not in attempt_ids for attempt_ids in snapshots)
    attempt_ids = {trial.attempt_id for trial in arm_trials} | {
        trial["attempt_id"] for trial in instances.trials_for(writer, dispatched)
    }
    assert killed not in attempt_ids
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
    assert report["budget_remaining_core_s"] == pytest.approx(10_000.0 - production - verification)


def test_a_run_aborted_by_an_attempt_error_never_reconciles_the_receiptless_attempt(
    writer, shipped, tmp_path, plan, hypothesis_object, dispatched, attest_path, monkeypatch
):
    snapshots = _record_snapshots(monkeypatch)
    _fail_on_spawn(monkeypatch, 2, RuntimeError("planted spawn failure"))
    with pytest.raises(RuntimeError, match="planted spawn failure"):
        _run_ladder(writer, shipped, tmp_path, plan, hypothesis_object, dispatched, attest_path)
    failed = writer.conn.execute("SELECT attempt_id, receipt_hash FROM attempts WHERE status = 'FAIL'").fetchall()
    assert len(failed) == 1 and failed[0]["receipt_hash"] is None
    assert escrow.reservation(writer, failed[0]["attempt_id"])["released_at"] is not None
    assert snapshots and all(failed[0]["attempt_id"] not in attempt_ids for attempt_ids in snapshots)


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
