import copy
import dataclasses
import json
from decimal import Decimal
from pathlib import Path

import pytest

from cairn import human_queue, ladderplan, laddertable, runner, substrate

ROOT = Path(__file__).resolve().parents[2]
COMMITTED = json.loads((ROOT / "bundle" / "ladder_plan.json").read_text())
BITS = (30, 40, 50, 60)
RUN_ID = "run-clock"

_TRIAL_BASE = laddertable.Trial(
    arm=ladderplan.ARMS[0],
    bits=0,
    trial=0,
    seed=1,
    instance_hash="aa" * 32,
    status=runner.STATUS_OK,
    output_complete=True,
    recovered=True,
    gate_ops=laddertable.OpsObservation(laddertable.OPS_EXACT, 1000),
    reported_ops=1000,
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
    ops_kind=laddertable.OPS_EXACT,
    mean_ops="1000000",
    sd_ops="0",
    cpu_seconds="1",
    reference_rate="1000",
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
    return ladderplan.LadderPlan.load(copy.deepcopy(COMMITTED))


@pytest.fixture
def writer(tmp_path):
    sub = substrate.Substrate.open(tmp_path / "sub.db", role="writer")
    try:
        yield sub
    finally:
        sub.close()


def _table(**planted):
    rungs = tuple(
        dataclasses.replace(_RUNG_BASE, bits=bits, role=ladderplan.ROLE_HOLD_OUT if bits == 60 else ladderplan.ROLE_FIT)
        for bits in BITS
    )
    trials = tuple(
        dataclasses.replace(_TRIAL_BASE, bits=bits, trial=trial, **(planted if (bits, trial) == (30, 0) else {}))
        for bits in BITS
        for trial in (0, 1)
    )
    return laddertable.ResultTable(
        run_id=RUN_ID,
        nonce="nonce-clock",
        hypothesis_hash="aa" * 32,
        method_identity={"interface_version": "toy/1", "params": {}},
        implementation_revision="bb" * 32,
        gate_bundle_hash="cc" * 32,
        plan_hash="dd" * 32,
        uncounted_backend=None,
        rungs=rungs,
        trials=trials,
        created_at="2026-09-30T17:00:00Z",
    )


def _queue_rows(sub):
    rows = sub.conn.execute(
        f"SELECT class, target_kind, target FROM {human_queue.ITEMS} WHERE class = ?",
        (human_queue.CLOCK_INCONCLUSIVE,),
    ).fetchall()
    return [tuple(row) for row in rows]


@pytest.mark.parametrize(
    ("planted", "predicate"),
    [({"wall_seconds": "1.3"}, laddertable.WALL), ({"cpu_seconds": "1.2"}, laddertable.CLOCK)],
)
def test_a_planted_clock_or_wall_overrun_lands_inconclusive_with_a_queue_item(writer, plan, planted, predicate):
    table = _table(**planted)
    verdict = laddertable.verdict(table, plan)
    assert (verdict.kind, verdict.predicate, verdict.rung_bits) == (laddertable.INCONCLUSIVE, predicate, 30)
    laddertable.write(writer, table, plan)
    assert laddertable.recorded_verdict(writer, table.hash).predicate == predicate
    assert _queue_rows(writer) == [(human_queue.CLOCK_INCONCLUSIVE, human_queue.RUNG, f"{RUN_ID}:30")]


def test_a_clean_table_enqueues_no_clock_item(writer, plan):
    table = _table()
    assert laddertable.verdict(table, plan).predicate not in laddertable.CLOCK_QUEUE_PREDICATES
    laddertable.write(writer, table, plan)
    assert _queue_rows(writer) == []


@pytest.mark.parametrize(
    ("first", "second", "predicate", "rung_bits"),
    [
        ({"wall_seconds": "1.3"}, {"wall_seconds": "1.3"}, laddertable.WALL, 30),
        ({"cpu_seconds": "1.2"}, {"cpu_seconds": "1.2"}, laddertable.CLOCK, 30),
        ({"cpu_seconds": "1.2"}, {"wall_seconds": "1.3"}, laddertable.CLOCK, 30),
        ({"wall_seconds": "1.3"}, {"cpu_seconds": "1.2"}, laddertable.CLOCK, 40),
        (
            {"cpu_seconds": "1.2", "wall_seconds": "1.5"},
            {"cpu_seconds": "1.2", "wall_seconds": "1.5"},
            laddertable.CLOCK,
            30,
        ),
    ],
)
def test_two_overrunning_rungs_enqueue_one_clock_item_per_rung(writer, plan, first, second, predicate, rung_bits):
    base = _table()
    overruns = {30: first, 40: second}
    table = dataclasses.replace(
        base,
        trials=tuple(dataclasses.replace(trial, **overruns.get(trial.bits, {})) for trial in base.trials),
    )
    expected_verdict = laddertable.verdict(table, plan)
    assert (expected_verdict.kind, expected_verdict.predicate, expected_verdict.rung_bits) == (
        laddertable.INCONCLUSIVE,
        predicate,
        rung_bits,
    )
    laddertable.write(writer, table, plan)
    recorded = laddertable.recorded_verdict(writer, table.hash)
    assert (recorded.kind, recorded.predicate, recorded.rung_bits) == (
        expected_verdict.kind,
        expected_verdict.predicate,
        expected_verdict.rung_bits,
    )
    assert _queue_rows(writer) == [
        (human_queue.CLOCK_INCONCLUSIVE, human_queue.RUNG, f"{RUN_ID}:30"),
        (human_queue.CLOCK_INCONCLUSIVE, human_queue.RUNG, f"{RUN_ID}:40"),
    ]


@pytest.mark.parametrize("rungs", [(30,), (30, 40)])
def test_writing_the_same_overrun_table_twice_enqueues_one_item_per_rung(writer, plan, rungs):
    base = _table()
    table = dataclasses.replace(
        base,
        trials=tuple(
            dataclasses.replace(trial, wall_seconds="1.3") if trial.bits in rungs else trial for trial in base.trials
        ),
    )
    laddertable.write(writer, table, plan)
    laddertable.write(writer, table, plan)
    assert _queue_rows(writer) == [
        (human_queue.CLOCK_INCONCLUSIVE, human_queue.RUNG, f"{RUN_ID}:{bits}") for bits in rungs
    ]


def test_rewriting_an_undated_table_at_a_later_time_enqueues_one_item(writer, plan):
    table = dataclasses.replace(_table(wall_seconds="1.3"), created_at=None)
    laddertable.write(writer, table, plan, at="2026-09-30T17:00:00Z")
    laddertable.write(writer, table, plan, at="2026-09-30T17:01:00Z")
    rows = writer.conn.execute(
        f"SELECT enqueued_at FROM {human_queue.ITEMS} WHERE class = ?", (human_queue.CLOCK_INCONCLUSIVE,)
    ).fetchall()
    assert [row[0] for row in rows] == ["2026-09-30T17:00:00Z"]


@pytest.mark.parametrize(
    ("kind", "predicate"),
    [(laddertable.INCONCLUSIVE, laddertable.FAILED_TRIAL), (laddertable.REJECT, laddertable.CLOCK)],
)
def test_a_verdict_outside_the_clock_predicates_is_not_enqueued(writer, plan, kind, predicate):
    table = _table(wall_seconds="1.3")
    verdict = laddertable.Verdict(kind, predicate, rung_bits=30)
    assert laddertable.enqueue_clock_inconclusive(writer, table, plan, verdict) is None
    assert _queue_rows(writer) == []


@pytest.mark.parametrize("claimant_overrun", [False, True])
def test_baseline_overruns_do_not_enqueue_clock_items(writer, plan, claimant_overrun):
    base = _table(**({"wall_seconds": "1.3"} if claimant_overrun else {}))
    table = dataclasses.replace(
        base,
        trials=base.trials
        + tuple(
            dataclasses.replace(trial, arm=ladderplan.ARMS[1], cpu_seconds="1.2", wall_seconds="1.5")
            for trial in base.trials
            if trial.bits == 40
        ),
    )
    laddertable.write(writer, table, plan)
    expected = [(human_queue.CLOCK_INCONCLUSIVE, human_queue.RUNG, f"{RUN_ID}:30")] if claimant_overrun else []
    assert _queue_rows(writer) == expected


def test_effective_clock_tolerance_takes_the_smaller_of_plan_and_band(plan):
    assert laddertable.effective_clock_tolerance(plan) == plan.tolerances.clock
    tight = dataclasses.replace(plan, rate_ratio=Decimal(3))
    assert laddertable.effective_clock_tolerance(tight) == 2 * plan.design_radius / Decimal(3)
    assert laddertable.effective_clock_tolerance(tight) < plan.tolerances.clock
    loose = dataclasses.replace(plan, rate_ratio=Decimal(2))
    assert laddertable.effective_clock_tolerance(loose) == plan.tolerances.clock
