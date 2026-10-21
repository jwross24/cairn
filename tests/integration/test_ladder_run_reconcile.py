import json

import pytest
from _ladder_run_helpers import MAKER_CEILING, RUN_ID
from _ladder_run_helpers import attest_path as attest_path
from _ladder_run_helpers import dispatched as dispatched
from _ladder_run_helpers import hypothesis_object as hypothesis_object
from _ladder_run_helpers import plan as plan
from _ladder_run_helpers import shipped as shipped
from _ladder_run_helpers import writer as writer

from cairn import escrow, instances, ladder, ladderplan, laddertable, ledger, runner


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
