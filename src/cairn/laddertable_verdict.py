from decimal import Decimal

from cairn import human_queue, ladderplan, runner, substrate
from cairn.laddertable_rows import (
    ALL_RUNGS_PASS,
    CLOCK,
    CLOCK_QUEUE_PREDICATES,
    COUNT_DIVERGENCE,
    FAILED_TRIAL,
    IN_SAMPLE_MISS,
    INCONCLUSIVE,
    INSIDE_BAND,
    KEEP,
    KEEP_IN_SAMPLE,
    MEASUREMENT_SCOPE,
    MEMORY_CAP,
    OPS_EXACT,
    OPS_LOWER_BOUND,
    OPS_UNKNOWN,
    OUT_OF_SAMPLE_MISS,
    RECOVERY,
    REFUTATION_FLOOR,
    REFUTATION_KIND,
    REJECT,
    UNCOUNTED_BACKEND,
    WALL,
    LadderTableError,
    Verdict,
)


def _validate_rungs(table, plan):
    for row in table.rungs:
        try:
            plan.rung(row.bits)
        except KeyError:
            raise LadderTableError(f"rung row bits={row.bits} names no rung the plan carries") from None
    present = {row.bits for row in table.rungs}
    for rung in plan.fit_rungs:
        if rung.bits not in present:
            raise LadderTableError(f"plan fit rung bits={rung.bits} has no row in the table")


def _trial_numeric(t):
    value = {"bits": t.bits, "trial": t.trial}
    if t.gate_ops.value is not None:
        value["gate_ops"] = t.gate_ops.value
    return value


def _recovery(trials):
    for t in trials:
        if t.arm == ladderplan.ARMS[0] and t.status == runner.STATUS_OK and t.output_complete and not t.recovered:
            return Verdict(
                REJECT,
                RECOVERY,
                refutation_kind=REFUTATION_KIND[RECOVERY],
                rung_bits=t.bits,
                trial=t.trial,
                measured_points=(
                    {
                        "numeric": _trial_numeric(t),
                        "categorical": {"predicate": RECOVERY, "instance_hash": t.instance_hash},
                    },
                ),
                ci=None,
            )
    return None


def _count_divergence(trials, plan):
    tolerance = plan.tolerances.count_divergence
    for t in trials:
        if t.arm != ladderplan.ARMS[0] or t.reported_ops is None or t.gate_ops.kind == OPS_UNKNOWN:
            continue
        gate = Decimal(t.gate_ops.value)
        reported = Decimal(t.reported_ops)
        if t.gate_ops.kind == OPS_EXACT:
            divergent = t.reported_ops != 0 if t.gate_ops.value == 0 else abs(reported - gate) / gate > tolerance
        else:
            divergent = reported < gate * (1 - tolerance)
        if divergent:
            return Verdict(
                REJECT,
                COUNT_DIVERGENCE,
                refutation_kind=REFUTATION_KIND[COUNT_DIVERGENCE],
                rung_bits=t.bits,
                trial=t.trial,
                measured_points=(
                    {
                        "numeric": {
                            "bits": t.bits,
                            "trial": t.trial,
                            "gate_ops": t.gate_ops.value,
                            "reported_ops": t.reported_ops,
                        },
                        "categorical": {"predicate": COUNT_DIVERGENCE},
                    },
                ),
                ci=None,
            )
    return None


def _memory_cap(rungs, plan):
    for row in rungs:
        prung = plan.rung(row.bits)
        if prung.memory_cap_bytes is not None and row.memory_bytes > prung.memory_cap_bytes:
            return Verdict(
                REJECT,
                MEMORY_CAP,
                refutation_kind=REFUTATION_KIND[MEMORY_CAP],
                rung_bits=row.bits,
                measured_points=(
                    {
                        "numeric": {
                            "bits": row.bits,
                            "memory_bytes": row.memory_bytes,
                            "memory_cap_bytes": prung.memory_cap_bytes,
                        },
                        "categorical": {"predicate": MEMORY_CAP},
                    },
                ),
                ci=("0", str(prung.memory_cap_bytes)),
            )
    return None


def _refutation_floor(rungs, plan):
    for row in rungs:
        prung = plan.rung(row.bits)
        if (
            row.ops_kind in (OPS_EXACT, OPS_LOWER_BOUND)
            and row.mean_ops is not None
            and prung.floor_binds
            and Decimal(row.mean_ops) >= Decimal(prung.refutation_floor.group_ops)
        ):
            return Verdict(
                REJECT,
                REFUTATION_FLOOR,
                refutation_kind=REFUTATION_KIND[REFUTATION_FLOOR],
                rung_bits=row.bits,
                measured_points=(
                    {
                        "numeric": {"bits": row.bits, "floor_group_ops": prung.refutation_floor.group_ops},
                        "categorical": {"predicate": REFUTATION_FLOOR, "mean_ops": row.mean_ops},
                    },
                ),
                ci=("0", str(prung.refutation_floor.group_ops)),
            )
    return None


def _model_miss(rows_by_bits, role, predicate):
    for bits in sorted(rows_by_bits):
        row = rows_by_bits[bits]
        if row.role != role:
            continue
        prediction = Decimal(row.model_prediction)
        band = Decimal(row.model_band)
        if row.ops_kind == OPS_UNKNOWN or row.mean_ops is None:
            continue
        mean = Decimal(row.mean_ops)
        missed = row.ops_kind == OPS_EXACT and abs(mean / prediction - 1) > band
        if missed:
            return Verdict(
                REJECT,
                predicate,
                refutation_kind=REFUTATION_KIND[predicate],
                rung_bits=bits,
                measured_points=(
                    {
                        "numeric": {"bits": bits},
                        "categorical": {
                            "predicate": predicate,
                            "mean_ops": row.mean_ops,
                            "model_prediction": row.model_prediction,
                            "model_band": row.model_band,
                        },
                    },
                ),
                ci=(str(prediction * (1 - band)), str(prediction * (1 + band))),
            )
    return None


def _uncounted_backend(table):
    if table.uncounted_backend is not None:
        return Verdict(INCONCLUSIVE, UNCOUNTED_BACKEND, rung_bits=None, measured_points=(), ci=None)
    return None


def _measurement_scope(trials):
    for t in trials:
        if not runner.scope_is_verified_complete(t.measurement_scope):
            return Verdict(
                INCONCLUSIVE,
                MEASUREMENT_SCOPE,
                rung_bits=t.bits,
                trial=t.trial,
                measured_points=(
                    {
                        "numeric": {"bits": t.bits, "trial": t.trial, "cpu_seconds": t.cpu_seconds},
                        "categorical": {"predicate": MEASUREMENT_SCOPE, "measurement_scope": t.measurement_scope},
                    },
                ),
                ci=None,
            )
    return None


def effective_clock_tolerance(plan):
    tolerance = plan.tolerances.clock
    if plan.rate_ratio == 0:
        return tolerance
    return min(tolerance, 2 * plan.design_radius / plan.rate_ratio)


def _clock(trials, rows_by_bits, plan):
    effective = effective_clock_tolerance(plan)
    for t in trials:
        if t.gate_ops.kind != OPS_EXACT:
            continue
        row = rows_by_bits.get(t.bits)
        if row is None:
            continue
        expected = Decimal(t.gate_ops.value) / Decimal(row.reference_rate)
        if Decimal(t.cpu_seconds) > expected * (1 + effective):
            return Verdict(
                INCONCLUSIVE,
                CLOCK,
                rung_bits=t.bits,
                trial=t.trial,
                measured_points=(
                    {
                        "numeric": {"bits": t.bits, "trial": t.trial, "cpu_seconds": t.cpu_seconds},
                        "categorical": {"predicate": CLOCK, "expected_cpu_seconds": str(expected)},
                    },
                ),
                ci=None,
            )
    return None


def _wall(trials, plan):
    tolerance = plan.tolerances.wall
    for t in trials:
        if Decimal(t.wall_seconds) > Decimal(t.cpu_seconds) * (1 + tolerance):
            return Verdict(
                INCONCLUSIVE,
                WALL,
                rung_bits=t.bits,
                trial=t.trial,
                measured_points=(
                    {
                        "numeric": {"bits": t.bits, "trial": t.trial, "wall_seconds": t.wall_seconds},
                        "categorical": {"predicate": WALL, "cpu_seconds": t.cpu_seconds},
                    },
                ),
                ci=None,
            )
    return None


def _failed_trial(rungs):
    for row in rungs:
        if Decimal(row.success_rate) < 1:
            return Verdict(
                INCONCLUSIVE,
                FAILED_TRIAL,
                rung_bits=row.bits,
                measured_points=(
                    {
                        "numeric": {"bits": row.bits},
                        "categorical": {"predicate": FAILED_TRIAL, "success_rate": row.success_rate},
                    },
                ),
                ci=None,
            )
    return None


def _inside_band(rows_by_bits, plan):
    for bits in sorted(rows_by_bits):
        row = rows_by_bits[bits]
        if row.role != ladderplan.ROLE_FIT:
            continue
        threshold = max(1 + 2 * Decimal(row.radius), plan.keep_band_floor)
        fires = row.claim_ci_low is None or Decimal(row.claim_ci_low) <= threshold
        if fires:
            ci = None
            if row.claim_ci_low is not None and row.claim_ci_high is not None:
                ci = (row.claim_ci_low, row.claim_ci_high)
            return Verdict(
                INCONCLUSIVE,
                INSIDE_BAND,
                rung_bits=bits,
                measured_points=(
                    {
                        "numeric": {"bits": bits},
                        "categorical": {
                            "predicate": INSIDE_BAND,
                            "claim_ci_low": row.claim_ci_low,
                            "threshold": str(threshold),
                        },
                    },
                ),
                ci=ci,
            )
    return None


def verdict(table, plan):
    _validate_rungs(table, plan)
    trials = sorted((t for t in table.trials if t.arm == ladderplan.ARMS[0]), key=lambda t: (t.bits, t.trial))
    rungs = sorted(table.rungs, key=lambda r: r.bits)
    rows_by_bits = {r.bits: r for r in rungs}

    for step in (
        lambda: _recovery(trials),
        lambda: _count_divergence(trials, plan),
        lambda: _memory_cap(rungs, plan),
        lambda: _refutation_floor(rungs, plan),
        lambda: _model_miss(rows_by_bits, ladderplan.ROLE_FIT, IN_SAMPLE_MISS),
        lambda: _model_miss(rows_by_bits, ladderplan.ROLE_HOLD_OUT, OUT_OF_SAMPLE_MISS),
        lambda: _uncounted_backend(table),
        lambda: _measurement_scope(trials),
        lambda: _clock(trials, rows_by_bits, plan),
        lambda: _wall(trials, plan),
        lambda: _failed_trial(rungs),
        lambda: _inside_band(rows_by_bits, plan),
    ):
        found = step()
        if found is not None:
            return found

    hold_out_present = plan.hold_out_rung.bits in rows_by_bits
    return Verdict(KEEP if hold_out_present else KEEP_IN_SAMPLE, ALL_RUNGS_PASS)


def in_sample_sizes(table):
    return tuple(sorted(row.bits for row in table.rungs if row.role == ladderplan.ROLE_FIT))


def replay_grade(table):
    if not table.trials:
        raise LadderTableError("a table with no trials carries no replay grade")
    order = {grade: i for i, grade in enumerate(substrate.GRADES)}
    weakest = None
    for t in table.trials:
        if t.replay_grade not in order:
            raise LadderTableError(f"trial replay_grade {t.replay_grade!r} is not one of {substrate.GRADES}")
        if weakest is None or order[t.replay_grade] > order[weakest]:
            weakest = t.replay_grade
    return weakest


def shape_departures(table, plan):
    """Ascending bits of every rung row whose shape statistic departs beyond the plan's tolerance."""
    tolerance = plan.shape_departure_tolerance
    return tuple(
        sorted(
            row.bits
            for row in table.rungs
            if row.ops_kind == OPS_EXACT
            and row.shape_statistic is not None
            and abs(Decimal(row.shape_statistic) - 1) > tolerance
        )
    )


def enqueue_shape_departures(sub, table, plan, *, at=None):
    return tuple(
        human_queue.enqueue_shape_departure(sub, rung=f"{table.run_id}:{bits}", at=at)
        for bits in shape_departures(table, plan)
    )


def _clock_overrun_rungs(table, plan):
    rows_by_bits = {row.bits: row for row in table.rungs}
    return tuple(
        sorted(
            {
                trial.bits
                for trial in table.trials
                if trial.arm == ladderplan.ARMS[0]
                and (_clock([trial], rows_by_bits, plan) is not None or _wall([trial], plan) is not None)
            }
        )
    )


def enqueue_clock_inconclusive(sub, table, plan, v, *, at=None):
    if v.kind != INCONCLUSIVE or v.predicate not in CLOCK_QUEUE_PREDICATES:
        return None
    return tuple(
        human_queue.enqueue_clock_inconclusive(sub, rung=f"{table.run_id}:{bits}", at=at)
        for bits in _clock_overrun_rungs(table, plan)
    )
