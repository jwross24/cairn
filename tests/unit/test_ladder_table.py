import copy
import dataclasses
import inspect
import json
from decimal import Decimal
from pathlib import Path

import pytest

from cairn import ladderplan, laddertable

ROOT = Path(__file__).resolve().parents[2]
COMMITTED = json.loads((ROOT / "bundle" / "ladder_plan.json").read_text())

_TRIAL_BASE = laddertable.Trial(
    bits=0,
    trial=0,
    seed=1,
    instance_hash="aa" * 32,
    recovered=True,
    completed=True,
    gate_ops=1000,
    reported_ops=1000,
    cpu_seconds="1",
    wall_seconds="1",
    peak_rss_bytes=1000,
    scratch_bytes=1000,
    reported_memory_bytes=1000,
    replay_grade="Replayable",
)
_RUNG_BASE = laddertable.RungRow(
    bits=0,
    role=ladderplan.ROLE_FIT,
    trials=2,
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


def _trial(bits, trial, **overrides):
    return dataclasses.replace(_TRIAL_BASE, bits=bits, trial=trial, **overrides)


def _rung(bits, role, **overrides):
    return dataclasses.replace(_RUNG_BASE, bits=bits, role=role, **overrides)


def _table(rungs, trials, **overrides):
    return dataclasses.replace(_TABLE_BASE, rungs=rungs, trials=trials, **overrides)


def _clean_table(include_hold_out=True):
    bits_list = [30, 40, 50] + ([60] if include_hold_out else [])
    rungs = tuple(_rung(bits, ladderplan.ROLE_HOLD_OUT if bits == 60 else ladderplan.ROLE_FIT) for bits in bits_list)
    trials = tuple(_trial(bits, trial) for bits in bits_list for trial in (0, 1))
    return _table(rungs, trials)


def _with_rung(table, bits, **overrides):
    rungs = tuple(dataclasses.replace(r, **overrides) if r.bits == bits else r for r in table.rungs)
    return dataclasses.replace(table, rungs=rungs)


def _without_rung(table, bits):
    return dataclasses.replace(table, rungs=tuple(r for r in table.rungs if r.bits != bits))


def _with_trial(table, bits, trial_no, **overrides):
    trials = tuple(
        dataclasses.replace(t, **overrides) if (t.bits, t.trial) == (bits, trial_no) else t for t in table.trials
    )
    return dataclasses.replace(table, trials=trials)


def _recovery_case():
    return _with_trial(_clean_table(), 30, 0, recovered=False)


def _count_divergence_case():
    return _with_trial(_clean_table(), 30, 0, reported_ops=2000)


def _memory_cap_case():
    return _with_rung(_clean_table(), 50, memory_bytes=477370809)


def _refutation_floor_case():
    return _with_rung(_clean_table(), 50, mean_ops="44769554", model_prediction="44769554")


def _in_sample_miss_case():
    return _with_rung(_clean_table(), 30, mean_ops="2000000")


def _out_of_sample_miss_case():
    return _with_rung(_clean_table(), 60, mean_ops="1500000")


def _uncounted_backend_case():
    return dataclasses.replace(_clean_table(), uncounted_backend="gmp")


def _clock_case():
    return _with_trial(_clean_table(), 30, 0, cpu_seconds="1.2")


def _wall_case():
    return _with_trial(_clean_table(), 30, 0, wall_seconds="1.3")


def _failed_trial_case():
    return _with_rung(_clean_table(), 30, success_rate="0.99")


def _inside_band_case():
    return _with_rung(_clean_table(), 30, claim_ci_low="1.0")


PREDICATE_CASES = [
    (laddertable.RECOVERY, _recovery_case, laddertable.REJECT, 30),
    (laddertable.COUNT_DIVERGENCE, _count_divergence_case, laddertable.REJECT, 30),
    (laddertable.MEMORY_CAP, _memory_cap_case, laddertable.REJECT, 50),
    (laddertable.REFUTATION_FLOOR, _refutation_floor_case, laddertable.REJECT, 50),
    (laddertable.IN_SAMPLE_MISS, _in_sample_miss_case, laddertable.REJECT, 30),
    (laddertable.OUT_OF_SAMPLE_MISS, _out_of_sample_miss_case, laddertable.REJECT, 60),
    (laddertable.UNCOUNTED_BACKEND, _uncounted_backend_case, laddertable.INCONCLUSIVE, None),
    (laddertable.CLOCK, _clock_case, laddertable.INCONCLUSIVE, 30),
    (laddertable.WALL, _wall_case, laddertable.INCONCLUSIVE, 30),
    (laddertable.FAILED_TRIAL, _failed_trial_case, laddertable.INCONCLUSIVE, 30),
    (laddertable.INSIDE_BAND, _inside_band_case, laddertable.INCONCLUSIVE, 30),
]


@pytest.mark.parametrize(("predicate", "build", "kind", "rung_bits"), PREDICATE_CASES)
def test_each_predicate_fires_the_expected_verdict(plan, predicate, build, kind, rung_bits):
    v = laddertable.verdict(build(), plan)
    assert (v.kind, v.predicate, v.refutation_kind, v.rung_bits) == (
        kind,
        predicate,
        laddertable.REFUTATION_KIND.get(predicate),
        rung_bits,
    )


def test_struct_field_names_are_exact():
    assert laddertable.TRIAL.names == (
        "bits",
        "trial",
        "seed",
        "instance_hash",
        "recovered",
        "completed",
        "gate_ops",
        "reported_ops",
        "cpu_seconds",
        "wall_seconds",
        "peak_rss_bytes",
        "scratch_bytes",
        "reported_memory_bytes",
        "replay_grade",
        "witness_hash",
    )
    assert laddertable.RUNG.names == (
        "bits",
        "role",
        "trials",
        "mean_ops",
        "sd_ops",
        "cpu_seconds",
        "reference_rate",
        "memory_bytes",
        "success_rate",
        "radius",
        "claim_ci_low",
        "claim_ci_high",
        "model_prediction",
        "model_band",
        "shape_statistic",
        "declared_shape",
    )
    assert laddertable.TABLE_STRUCT.names == (
        "run_id",
        "nonce",
        "hypothesis_hash",
        "method_identity",
        "implementation_revision",
        "gate_bundle_hash",
        "plan_hash",
        "uncounted_backend",
        "rungs",
        "trials",
    )


def test_module_defined_public_api_is_closed():
    public = set()
    for name, value in vars(laddertable).items():
        if name.startswith("_") or inspect.ismodule(value):
            continue
        if getattr(value, "__module__", laddertable.__name__) != laddertable.__name__:
            continue
        public.add(name)
    assert public == {
        "LadderTableError",
        "Trial",
        "RungRow",
        "ResultTable",
        "Verdict",
        "Recomputation",
        "verdict",
        "in_sample_sizes",
        "replay_grade",
        "shape_departures",
        "enqueue_shape_departures",
        "write",
        "read",
        "recorded_verdict",
        "recompute",
        "policy",
        "record",
        "evidence_node",
        "KEEP",
        "KEEP_IN_SAMPLE",
        "REJECT",
        "INCONCLUSIVE",
        "VERDICTS",
        "NODE_KIND",
        "TABLES",
        "RUNGS",
        "TRIALS",
        "RECOVERY",
        "COUNT_DIVERGENCE",
        "MEMORY_CAP",
        "REFUTATION_FLOOR",
        "IN_SAMPLE_MISS",
        "OUT_OF_SAMPLE_MISS",
        "UNCOUNTED_BACKEND",
        "CLOCK",
        "WALL",
        "FAILED_TRIAL",
        "INSIDE_BAND",
        "ALL_RUNGS_PASS",
        "REJECT_PREDICATES",
        "INCONCLUSIVE_PREDICATES",
        "PREDICATES",
        "REFUTATION_KIND",
    }


def test_refutation_floor_beats_inside_band(plan):
    table = _with_rung(_clean_table(), 50, mean_ops="44769554", model_prediction="44769554", claim_ci_low="1.0")
    v = laddertable.verdict(table, plan)
    assert (v.kind, v.predicate) == (laddertable.REJECT, laddertable.REFUTATION_FLOOR)


def test_recovery_beats_inside_band(plan):
    table = _with_rung(_with_trial(_clean_table(), 30, 0, recovered=False), 40, claim_ci_low="1.0")
    v = laddertable.verdict(table, plan)
    assert (v.kind, v.predicate) == (laddertable.REJECT, laddertable.RECOVERY)


@pytest.mark.parametrize("include_hold_out", [True, False])
def test_recovery_failure_never_yields_keep(plan, include_hold_out):
    table = _with_trial(_clean_table(include_hold_out), 30, 0, recovered=False)
    v = laddertable.verdict(table, plan)
    assert v.kind not in (laddertable.KEEP, laddertable.KEEP_IN_SAMPLE)


def test_uncounted_backend_fires_however_clean_the_numbers(plan):
    table = dataclasses.replace(_clean_table(), uncounted_backend="gmp")
    v = laddertable.verdict(table, plan)
    assert (v.kind, v.predicate) == (laddertable.INCONCLUSIVE, laddertable.UNCOUNTED_BACKEND)


def test_keep_in_sample_iff_hold_out_absent(plan):
    with_hold_out = laddertable.verdict(_clean_table(include_hold_out=True), plan)
    without_hold_out = laddertable.verdict(_clean_table(include_hold_out=False), plan)
    assert with_hold_out.kind == laddertable.KEEP
    assert without_hold_out.kind == laddertable.KEEP_IN_SAMPLE


def test_replay_grade_is_the_weakest_grade():
    table = _clean_table()
    assert laddertable.replay_grade(table) == "Replayable"
    table = _with_trial(table, 30, 0, replay_grade="AuditOnly")
    assert laddertable.replay_grade(table) == "AuditOnly"


def test_replay_grade_raises_with_no_trials():
    table = dataclasses.replace(_clean_table(), trials=())
    with pytest.raises(laddertable.LadderTableError):
        laddertable.replay_grade(table)


def test_shape_departure_does_not_move_the_verdict(plan):
    table = _clean_table()
    before = laddertable.verdict(table, plan)
    departed = _with_rung(table, 30, shape_statistic="2.0")
    assert laddertable.shape_departures(departed, plan) == (30,)
    after = laddertable.verdict(departed, plan)
    assert before == after


def test_the_shape_tolerance_is_exclusive_at_its_own_boundary(plan):
    tolerance = plan.shape_departure_tolerance
    at = _with_rung(_clean_table(), 30, shape_statistic=str(1 + tolerance))
    beyond = _with_rung(_clean_table(), 30, shape_statistic=str(1 + tolerance + Decimal("0.000001")))
    under = _with_rung(_clean_table(), 30, shape_statistic=str(1 - tolerance))
    assert laddertable.shape_departures(at, plan) == ()
    assert laddertable.shape_departures(under, plan) == ()
    assert laddertable.shape_departures(beyond, plan) == (30,)


def test_in_sample_sizes_returns_only_fit_rungs_ascending():
    assert laddertable.in_sample_sizes(_clean_table()) == (30, 40, 50)


def test_rung_row_naming_unknown_bits_raises(plan):
    table = _clean_table()
    bad = dataclasses.replace(table, rungs=(*table.rungs, _rung(99, ladderplan.ROLE_FIT)))
    with pytest.raises(laddertable.LadderTableError):
        laddertable.verdict(bad, plan)


def test_plan_fit_rung_with_no_row_raises(plan):
    table = _without_rung(_clean_table(), 40)
    with pytest.raises(laddertable.LadderTableError):
        laddertable.verdict(table, plan)


def _render(table, v):
    lines = [f"verdict {v.kind} {v.predicate} {v.refutation_kind} {v.rung_bits}"]
    lines.extend(
        f"rung {row.bits} {row.role} mean_ops={row.mean_ops} success_rate={row.success_rate} "
        f"claim_ci_low={row.claim_ci_low} claim_ci_high={row.claim_ci_high}"
        for row in sorted(table.rungs, key=lambda r: r.bits)
    )
    return "\n".join(lines) + "\n"


def test_golden_verdict_summary(plan, assert_golden):
    table = _clean_table()
    v = laddertable.verdict(table, plan)
    assert_golden("ladder_table_verdict", _render(table, v))
