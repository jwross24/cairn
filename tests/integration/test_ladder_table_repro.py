import copy
import dataclasses
import json
import sqlite3
from pathlib import Path

import pytest
from _substrate_helpers import open_writer

from cairn import human_queue, ladderplan, laddertable, repro, runner

ROOT = Path(__file__).resolve().parents[2]
COMMITTED = json.loads((ROOT / "bundle" / "ladder_plan.json").read_text())

_TRIAL_BASE = laddertable.Trial(
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
_RUNG_BASE = laddertable.RungRow(
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
_TABLE_BASE = laddertable.ResultTable(
    run_id="run-1",
    nonce="nonce-1",
    hypothesis_hash="aa" * 32,
    method_identity={"interface_version": "toy/1", "params": {}},
    implementation_revision="bb" * 32,
    gate_bundle_hash="cc" * 32,
    plan_hash="dd" * 32,
    uncounted_backend=None,
    rungs=(),
    trials=(),
)


@pytest.fixture
def plan():
    return ladderplan.LadderPlan.load(copy.deepcopy(COMMITTED))


@pytest.fixture
def writer(tmp_path):
    sub = open_writer(tmp_path)
    yield sub
    sub.close()


def _trial(bits, trial, **overrides):
    return dataclasses.replace(_TRIAL_BASE, bits=bits, trial=trial, **overrides)


def _rung(bits, role, **overrides):
    return dataclasses.replace(_RUNG_BASE, bits=bits, role=role, **overrides)


def _table(rungs, trials, **overrides):
    return dataclasses.replace(_TABLE_BASE, rungs=rungs, trials=trials, **overrides)


def _clean_table(include_hold_out=True, run_id="run-1"):
    bits_list = [30, 40, 50] + ([60] if include_hold_out else [])
    rungs = tuple(_rung(bits, ladderplan.ROLE_HOLD_OUT if bits == 60 else ladderplan.ROLE_FIT) for bits in bits_list)
    trials = tuple(_trial(bits, trial) for bits in bits_list for trial in (0, 1))
    return _table(rungs, trials, run_id=run_id)


def _with_trial(table, bits, trial_no, **overrides):
    trials = tuple(
        dataclasses.replace(t, **overrides) if (t.bits, t.trial) == (bits, trial_no) else t for t in table.trials
    )
    return dataclasses.replace(table, trials=trials)


def _with_rung(table, bits, **overrides):
    rungs = tuple(dataclasses.replace(r, **overrides) if r.bits == bits else r for r in table.rungs)
    return dataclasses.replace(table, rungs=rungs)


def test_write_then_read_round_trips_byte_equal(writer, plan):
    table = _clean_table()
    table_hash = laddertable.write(writer, table, plan)
    fetched = laddertable.read(writer, table_hash)
    assert fetched.hash == table.hash
    assert laddertable._table_canonical(fetched) == laddertable._table_canonical(table)

    row = writer.conn.execute("SELECT * FROM ladder_tables WHERE hash = ?", (table_hash,)).fetchone()
    v = laddertable.verdict(table, plan)
    assert row["verdict"] == v.kind
    assert row["verdict_predicate"] == v.predicate
    assert row["refutation_kind"] == v.refutation_kind
    assert row["verdict_rung"] == v.rung_bits
    assert row["replay_grade"] == laddertable.replay_grade(table)


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE ladder_tables SET verdict = 'REJECT'",
        "DELETE FROM ladder_tables",
        "UPDATE ladder_rungs SET mean_ops = '0'",
        "DELETE FROM ladder_rungs",
        "UPDATE ladder_trials SET gate_ops = 0",
        "DELETE FROM ladder_trials",
    ],
)
def test_ladder_tables_are_append_only(writer, plan, sql):
    laddertable.write(writer, _clean_table(), plan)
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        writer.conn.execute(sql)


def test_writing_the_same_table_twice_inserts_one_row_set(writer, plan, db_snapshot):
    table = _clean_table()
    laddertable.write(writer, table, plan)
    before = db_snapshot(writer.conn, "first-write")
    laddertable.write(writer, table, plan)
    after = db_snapshot(writer.conn, "second-write")
    assert before == after


def test_recompute_over_all_trials_reproduces_the_recorded_verdict(writer, plan):
    table = _clean_table()
    laddertable.write(writer, table, plan)
    verified = {(t.bits, t.trial) for t in table.trials}
    recomputation = laddertable.recompute(table, plan, verified)
    assert recomputation.agrees is True
    assert recomputation.divergences == ()
    recorded = laddertable.recorded_verdict(writer, table.hash)
    assert (recomputation.verdict.kind, recomputation.verdict.predicate) == (recorded.kind, recorded.predicate)


def test_altered_mean_ops_makes_recompute_diverge(writer, plan):
    table = _clean_table()
    tampered = _with_rung(table, 30, mean_ops="999999999")
    laddertable.write(writer, tampered, plan)
    verified = {(t.bits, t.trial) for t in tampered.trials}
    recomputation = laddertable.recompute(tampered, plan, verified)
    assert recomputation.agrees is False
    assert any("30" in d and "mean_ops" in d for d in recomputation.divergences)


def test_withholding_the_failed_trial_flips_the_verdict(writer, plan):
    table = _with_trial(_clean_table(), 30, 0, recovered=False)
    laddertable.write(writer, table, plan)
    original = laddertable.verdict(table, plan)
    assert original.kind == laddertable.REJECT

    verified = {(t.bits, t.trial) for t in table.trials if not (t.bits == 30 and t.trial == 0)}
    recomputation = laddertable.recompute(table, plan, verified)
    assert recomputation.agrees is False
    assert any(d.startswith("verdict recorded") for d in recomputation.divergences)
    assert recomputation.verdict.kind != laddertable.REJECT


def test_enqueue_shape_departure_writes_a_human_queue_item_and_leaves_the_verdict(writer, plan):
    table = _with_rung(_clean_table(), 30, shape_statistic="2.0")
    table_hash = laddertable.write(writer, table, plan)
    before = laddertable.recorded_verdict(writer, table_hash)

    ids = laddertable.enqueue_shape_departures(writer, table, plan)
    assert ids == (human_queue.get_item(writer, ids[0])["item_id"],)
    item = human_queue.get_item(writer, ids[0])
    assert item["class"] == human_queue.SHAPE_DEPARTURE
    assert item["target"] == f"{table.run_id}:30"

    after = laddertable.recorded_verdict(writer, table_hash)
    assert before == after


def test_record_writes_a_repro_record_whose_passed_matches_agrees(writer, plan):
    table = _clean_table()
    laddertable.write(writer, table, plan)
    verified = {(t.bits, t.trial) for t in table.trials}
    repro_record, recomputation = laddertable.record(writer, table, plan, verified, attempt_id="attempt-1")
    row = writer.conn.execute("SELECT * FROM repro_records WHERE hash = ?", (repro_record.hash,)).fetchone()
    assert bool(row["passed"]) == recomputation.agrees


def test_policy_maps_trials_by_replay_grade_and_tier(writer, plan):
    table = _with_trial(_clean_table(), 30, 0, replay_grade="Verifiable")
    policy = laddertable.policy(table, 1)
    assert policy[(30, 0)] == repro.CHECK_WITNESS
    assert policy[(30, 1)] == repro.RERUN_NOW
