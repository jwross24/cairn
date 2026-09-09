"""The ladder result table: a run's rungs and trials, its typed verdict, and its shape diagnostic.

A table is a content-addressed node holding one run's rung rows and trial rows. `verdict`
scans a table against a `ladderplan.LadderPlan` and returns the first predicate that fires,
in the fixed order PLAN section 6 sets: the REJECT predicates, then the INCONCLUSIVE ones,
then a pass. Nothing here measures a claim; the module composes predicates over numbers a
caller already produced. The shape diagnostic is separate from the verdict: a departure is
queued for a human and never moves what the verdict says.

A trial whose receipt scope is weaker than a verified-complete process-tree figure makes the
run INCONCLUSIVE, and that check sits after the REJECT predicates: a scope short of `tree`
undercounts, so a refutation drawn from it stands, while a pass drawn from it does not.
"""

import dataclasses
import json
from dataclasses import dataclass, field
from decimal import Decimal

from cairn import canon, claims, human_queue, keys, ladderplan, ledger, log, repro, runner, substrate
from cairn.canon import BOOL, INT, NON_EMPTY_STR, STR, Field, List, Optional, Struct
from cairn.substrate import SubstrateError, _now

lg = log.get("laddertable")

KEEP = "KEEP"
KEEP_IN_SAMPLE = "KEEP_IN_SAMPLE"
REJECT = "REJECT"
INCONCLUSIVE = "INCONCLUSIVE"
VERDICTS = (KEEP, KEEP_IN_SAMPLE, REJECT, INCONCLUSIVE)

NODE_KIND = "ladder_table"
TABLES = "ladder_tables"
RUNGS = "ladder_rungs"
TRIALS = "ladder_trials"

RECOVERY = "recovery"
COUNT_DIVERGENCE = "count_divergence"
MEMORY_CAP = "memory_cap"
REFUTATION_FLOOR = "refutation_floor"
IN_SAMPLE_MISS = "in_sample_model_miss"
OUT_OF_SAMPLE_MISS = "out_of_sample_model_miss"
UNCOUNTED_BACKEND = "uncounted_backend"
MEASUREMENT_SCOPE = "measurement_scope"
CLOCK = "clock"
WALL = "wall"
FAILED_TRIAL = "failed_trial"
INSIDE_BAND = "inside_band"
ALL_RUNGS_PASS = "all_rungs_pass"

REJECT_PREDICATES = (RECOVERY, COUNT_DIVERGENCE, MEMORY_CAP, REFUTATION_FLOOR, IN_SAMPLE_MISS, OUT_OF_SAMPLE_MISS)
INCONCLUSIVE_PREDICATES = (UNCOUNTED_BACKEND, MEASUREMENT_SCOPE, CLOCK, WALL, FAILED_TRIAL, INSIDE_BAND)
PREDICATES = (*REJECT_PREDICATES, *INCONCLUSIVE_PREDICATES, ALL_RUNGS_PASS)

REFUTATION_KIND = {
    RECOVERY: ledger.IMPLEMENTATION,
    COUNT_DIVERGENCE: ledger.IMPLEMENTATION,
    MEMORY_CAP: ledger.MEASURED,
    REFUTATION_FLOOR: ledger.MEASURED,
    IN_SAMPLE_MISS: ledger.MEASURED,
    OUT_OF_SAMPLE_MISS: ledger.MEASURED,
}

TRIAL = Struct(
    "ladder_trial",
    [
        Field("bits", INT),
        Field("trial", INT),
        Field("seed", INT),
        Field("instance_hash", NON_EMPTY_STR),
        Field("recovered", BOOL),
        Field("completed", BOOL),
        Field("gate_ops", INT),
        Field("reported_ops", INT),
        Field("cpu_seconds", NON_EMPTY_STR),
        Field("wall_seconds", NON_EMPTY_STR),
        Field("peak_rss_bytes", INT),
        Field("scratch_bytes", INT),
        Field("reported_memory_bytes", INT),
        Field("replay_grade", NON_EMPTY_STR),
        Field("measurement_scope", NON_EMPTY_STR),
        Field("witness_hash", Optional(STR)),
    ],
)

RUNG = Struct(
    "ladder_rung",
    [
        Field("bits", INT),
        Field("role", NON_EMPTY_STR),
        Field("trials", INT),
        Field("mean_ops", NON_EMPTY_STR),
        Field("sd_ops", NON_EMPTY_STR),
        Field("cpu_seconds", NON_EMPTY_STR),
        Field("reference_rate", NON_EMPTY_STR),
        Field("memory_bytes", INT),
        Field("success_rate", NON_EMPTY_STR),
        Field("radius", NON_EMPTY_STR),
        Field("claim_ci_low", Optional(STR)),
        Field("claim_ci_high", Optional(STR)),
        Field("model_prediction", NON_EMPTY_STR),
        Field("model_band", NON_EMPTY_STR),
        Field("shape_statistic", NON_EMPTY_STR),
        Field("declared_shape", NON_EMPTY_STR),
    ],
)

TABLE_STRUCT = Struct(
    "ladder_table",
    [
        Field("run_id", NON_EMPTY_STR),
        Field("nonce", NON_EMPTY_STR),
        Field("hypothesis_hash", NON_EMPTY_STR),
        Field("method_identity", keys.METHOD_IDENTITY),
        Field("implementation_revision", NON_EMPTY_STR),
        Field("gate_bundle_hash", NON_EMPTY_STR),
        Field("plan_hash", NON_EMPTY_STR),
        Field("uncounted_backend", Optional(STR)),
        Field("rungs", List(RUNG)),
        Field("trials", List(TRIAL)),
    ],
)


class LadderTableError(SubstrateError):
    pass


def _trial_fields(t):
    return {
        "bits": t.bits,
        "trial": t.trial,
        "seed": t.seed,
        "instance_hash": t.instance_hash,
        "recovered": t.recovered,
        "completed": t.completed,
        "gate_ops": t.gate_ops,
        "reported_ops": t.reported_ops,
        "cpu_seconds": t.cpu_seconds,
        "wall_seconds": t.wall_seconds,
        "peak_rss_bytes": t.peak_rss_bytes,
        "scratch_bytes": t.scratch_bytes,
        "reported_memory_bytes": t.reported_memory_bytes,
        "replay_grade": t.replay_grade,
        "measurement_scope": t.measurement_scope,
        "witness_hash": t.witness_hash,
    }


def _trial_canonical(t):
    return canon.encode(TRIAL, _trial_fields(t))


def _rung_fields(r):
    return {
        "bits": r.bits,
        "role": r.role,
        "trials": r.trials,
        "mean_ops": r.mean_ops,
        "sd_ops": r.sd_ops,
        "cpu_seconds": r.cpu_seconds,
        "reference_rate": r.reference_rate,
        "memory_bytes": r.memory_bytes,
        "success_rate": r.success_rate,
        "radius": r.radius,
        "claim_ci_low": r.claim_ci_low,
        "claim_ci_high": r.claim_ci_high,
        "model_prediction": r.model_prediction,
        "model_band": r.model_band,
        "shape_statistic": r.shape_statistic,
        "declared_shape": r.declared_shape,
    }


def _rung_canonical(r):
    return canon.encode(RUNG, _rung_fields(r))


def _table_fields(table):
    return {
        "run_id": table.run_id,
        "nonce": table.nonce,
        "hypothesis_hash": table.hypothesis_hash,
        "method_identity": table.method_identity,
        "implementation_revision": table.implementation_revision,
        "gate_bundle_hash": table.gate_bundle_hash,
        "plan_hash": table.plan_hash,
        "uncounted_backend": table.uncounted_backend,
        "rungs": [_rung_fields(r) for r in table.rungs],
        "trials": [_trial_fields(t) for t in table.trials],
    }


def _table_canonical(table):
    return canon.encode(TABLE_STRUCT, _table_fields(table))


@dataclass(frozen=True)
class Trial:
    bits: int
    trial: int
    seed: int
    instance_hash: str
    recovered: bool
    completed: bool
    gate_ops: int
    reported_ops: int
    cpu_seconds: str
    wall_seconds: str
    peak_rss_bytes: int
    scratch_bytes: int
    reported_memory_bytes: int
    replay_grade: str
    measurement_scope: str
    witness_hash: str | None = None
    hash: str = field(init=False, compare=False)

    def __post_init__(self):
        object.__setattr__(self, "hash", keys.node_hash("ladder_trial", _trial_canonical(self)))


@dataclass(frozen=True)
class RungRow:
    bits: int
    role: str
    trials: int
    mean_ops: str
    sd_ops: str
    cpu_seconds: str
    reference_rate: str
    memory_bytes: int
    success_rate: str
    radius: str
    model_prediction: str
    model_band: str
    shape_statistic: str
    declared_shape: str
    claim_ci_low: str | None = None
    claim_ci_high: str | None = None
    hash: str = field(init=False, compare=False)

    def __post_init__(self):
        object.__setattr__(self, "hash", keys.node_hash("ladder_rung", _rung_canonical(self)))


@dataclass(frozen=True)
class ResultTable:
    run_id: str
    nonce: str
    hypothesis_hash: str
    method_identity: dict
    implementation_revision: str
    gate_bundle_hash: str
    plan_hash: str
    uncounted_backend: str | None
    rungs: tuple
    trials: tuple
    created_at: str | None = None
    hash: str = field(init=False, compare=False)

    def __post_init__(self):
        object.__setattr__(self, "hash", keys.node_hash(NODE_KIND, _table_canonical(self)))


@dataclass(frozen=True)
class Verdict:
    kind: str
    predicate: str
    refutation_kind: str | None = None
    rung_bits: int | None = None
    trial: int | None = None
    measured_points: tuple = ()
    ci: tuple | None = None

    @property
    def caught_by(self):
        return f"{ledger.LADDER}:{self.predicate}"


@dataclass(frozen=True)
class Recomputation:
    verdict: Verdict
    rungs: tuple
    agrees: bool
    divergences: tuple


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


def _recovery(trials):
    for t in trials:
        if t.completed and not t.recovered:
            return Verdict(
                REJECT,
                RECOVERY,
                refutation_kind=REFUTATION_KIND[RECOVERY],
                rung_bits=t.bits,
                trial=t.trial,
                measured_points=(
                    {
                        "numeric": {"bits": t.bits, "trial": t.trial, "gate_ops": t.gate_ops},
                        "categorical": {"predicate": RECOVERY, "instance_hash": t.instance_hash},
                    },
                ),
                ci=None,
            )
    return None


def _count_divergence(trials, plan):
    tolerance = plan.tolerances.count_divergence
    for t in trials:
        gate = Decimal(t.gate_ops)
        reported = Decimal(t.reported_ops)
        divergent = t.reported_ops != 0 if t.gate_ops == 0 else abs(reported - gate) / gate > tolerance
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
                            "gate_ops": t.gate_ops,
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
        if prung.floor_binds and Decimal(row.mean_ops) >= Decimal(prung.refutation_floor.group_ops):
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
        mean = Decimal(row.mean_ops)
        if abs(mean / prediction - 1) > band:
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


def _clock(trials, rows_by_bits, plan):
    tolerance = plan.tolerances.clock
    rate_ratio = plan.rate_ratio
    effective = tolerance if rate_ratio == 0 else min(tolerance, 2 * plan.design_radius / rate_ratio)
    for t in trials:
        row = rows_by_bits.get(t.bits)
        if row is None:
            continue
        expected = Decimal(t.gate_ops) / Decimal(row.reference_rate)
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
    trials = sorted(table.trials, key=lambda t: (t.bits, t.trial))
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
    return tuple(sorted(row.bits for row in table.rungs if abs(Decimal(row.shape_statistic) - 1) > tolerance))


def enqueue_shape_departures(sub, table, plan, *, at=None):
    return tuple(
        human_queue.enqueue_shape_departure(sub, rung=f"{table.run_id}:{bits}", at=at)
        for bits in shape_departures(table, plan)
    )


def _insert_rung(sub, table_hash, row):
    values = {"table_hash": table_hash, **_rung_fields(row)}
    columns = ", ".join(values)
    marks = ", ".join("?" for _ in values)
    sub.conn.execute(f"INSERT OR IGNORE INTO {RUNGS} ({columns}) VALUES ({marks})", tuple(values.values()))


def _insert_trial(sub, table_hash, t):
    values = {"table_hash": table_hash, **_trial_fields(t)}
    values["recovered"] = int(values["recovered"])
    values["completed"] = int(values["completed"])
    columns = ", ".join(values)
    marks = ", ".join("?" for _ in values)
    sub.conn.execute(f"INSERT OR IGNORE INTO {TRIALS} ({columns}) VALUES ({marks})", tuple(values.values()))


def write(sub, table, plan, *, at=None, attempt_id=None):
    v = verdict(table, plan)
    grade = replay_grade(table)
    canonical = _table_canonical(table)
    created_at = table.created_at or at or _now()
    with sub._tx():
        sub._put_node(NODE_KIND, canonical, table.hash, grade, None)
        inserted = claims._insert_once(
            sub,
            TABLES,
            "hash",
            {
                "hash": table.hash,
                "run_id": table.run_id,
                "nonce": table.nonce,
                "hypothesis_hash": table.hypothesis_hash,
                "method_identity": claims.to_json(table.method_identity),
                "implementation_revision": table.implementation_revision,
                "gate_bundle_hash": table.gate_bundle_hash,
                "plan_hash": table.plan_hash,
                "uncounted_backend": table.uncounted_backend,
                "attempt_id": attempt_id,
                "verdict": v.kind,
                "verdict_predicate": v.predicate,
                "refutation_kind": v.refutation_kind,
                "verdict_rung": v.rung_bits,
                "replay_grade": grade,
                "created_at": created_at,
            },
            table.hash,
        )
        if inserted:
            for row in table.rungs:
                _insert_rung(sub, table.hash, row)
            for t in table.trials:
                _insert_trial(sub, table.hash, t)
    return table.hash


def _rung_from_row(r):
    return RungRow(
        bits=r["bits"],
        role=r["role"],
        trials=r["trials"],
        mean_ops=r["mean_ops"],
        sd_ops=r["sd_ops"],
        cpu_seconds=r["cpu_seconds"],
        reference_rate=r["reference_rate"],
        memory_bytes=r["memory_bytes"],
        success_rate=r["success_rate"],
        radius=r["radius"],
        model_prediction=r["model_prediction"],
        model_band=r["model_band"],
        shape_statistic=r["shape_statistic"],
        declared_shape=r["declared_shape"],
        claim_ci_low=r["claim_ci_low"],
        claim_ci_high=r["claim_ci_high"],
    )


def _trial_from_row(r):
    return Trial(
        bits=r["bits"],
        trial=r["trial"],
        seed=r["seed"],
        instance_hash=r["instance_hash"],
        recovered=bool(r["recovered"]),
        completed=bool(r["completed"]),
        gate_ops=r["gate_ops"],
        reported_ops=r["reported_ops"],
        cpu_seconds=r["cpu_seconds"],
        wall_seconds=r["wall_seconds"],
        peak_rss_bytes=r["peak_rss_bytes"],
        scratch_bytes=r["scratch_bytes"],
        reported_memory_bytes=r["reported_memory_bytes"],
        replay_grade=r["replay_grade"],
        measurement_scope=r["measurement_scope"],
        witness_hash=r["witness_hash"],
    )


def inputs_for_attempt(sub, attempt_id):
    """The size bound the run behind this attempt spanned, as a param_ranges map: an interval, not the set of sizes run."""
    row = sub.conn.execute(f"SELECT hash FROM {TABLES} WHERE attempt_id = ? ORDER BY rowid", (attempt_id,)).fetchone()
    if row is None:
        return None
    bits = [
        r["bits"] for r in sub.conn.execute(f"SELECT DISTINCT bits FROM {TRIALS} WHERE table_hash = ?", (row["hash"],))
    ]
    return {"bits": [min(bits), max(bits)]} if bits else None


def read(sub, table_hash):
    row = sub.conn.execute(f"SELECT * FROM {TABLES} WHERE hash = ?", (table_hash,)).fetchone()
    if row is None:
        return None
    rung_rows = sub.conn.execute(f"SELECT * FROM {RUNGS} WHERE table_hash = ? ORDER BY bits", (table_hash,)).fetchall()
    trial_rows = sub.conn.execute(
        f"SELECT * FROM {TRIALS} WHERE table_hash = ? ORDER BY bits, trial", (table_hash,)
    ).fetchall()
    table = ResultTable(
        run_id=row["run_id"],
        nonce=row["nonce"],
        hypothesis_hash=row["hypothesis_hash"],
        method_identity=json.loads(row["method_identity"]),
        implementation_revision=row["implementation_revision"],
        gate_bundle_hash=row["gate_bundle_hash"],
        plan_hash=row["plan_hash"],
        uncounted_backend=row["uncounted_backend"],
        rungs=tuple(_rung_from_row(r) for r in rung_rows),
        trials=tuple(_trial_from_row(r) for r in trial_rows),
        created_at=row["created_at"],
    )
    if table.hash != table_hash:
        raise LadderTableError(f"reconstructed table hash {table.hash} does not match {table_hash}")
    return table


def recorded_verdict(sub, table_hash):
    row = sub.conn.execute(
        f"SELECT verdict, verdict_predicate, refutation_kind, verdict_rung FROM {TABLES} WHERE hash = ?",
        (table_hash,),
    ).fetchone()
    if row is None:
        return None
    return Verdict(
        kind=row["verdict"],
        predicate=row["verdict_predicate"],
        refutation_kind=row["refutation_kind"],
        rung_bits=row["verdict_rung"],
    )


def _decimal_places(text):
    return len(text.split(".", 1)[1]) if "." in text else 0


def _quantize(value, places):
    quantum = Decimal(1).scaleb(-places)
    return str(value.quantize(quantum))


def recompute(table, plan, verified):
    verified_set = set(verified)
    restricted_trials = tuple(t for t in table.trials if (t.bits, t.trial) in verified_set)
    grouped = {}
    for t in restricted_trials:
        grouped.setdefault(t.bits, []).append(t)

    new_rows = []
    divergences = []
    for row in table.rungs:
        group = grouped.get(row.bits, [])
        if not group:
            new_rows.append(row)
            divergences.append(f"{row.bits}: no verified trials")
            continue

        count = len(group)
        gate_ops_values = [Decimal(t.gate_ops) for t in group]
        mean = sum(gate_ops_values) / Decimal(count)
        if count >= 2:
            variance = sum((v - mean) ** 2 for v in gate_ops_values) / Decimal(count - 1)
            sd = variance.sqrt()
        else:
            sd = Decimal(0)
        successes = sum(1 for t in group if t.completed and t.recovered)
        success_rate = Decimal(successes) / Decimal(count)

        new_mean = _quantize(mean, _decimal_places(row.mean_ops))
        new_sd = _quantize(sd, _decimal_places(row.sd_ops))
        new_success = _quantize(success_rate, _decimal_places(row.success_rate))

        for name, old, new in (
            ("trials", row.trials, count),
            ("mean_ops", row.mean_ops, new_mean),
            ("sd_ops", row.sd_ops, new_sd),
            ("success_rate", row.success_rate, new_success),
        ):
            if str(old) != str(new):
                divergences.append(f"{row.bits}: {name} recorded {old} recomputed {new}")

        new_rows.append(
            dataclasses.replace(row, trials=count, mean_ops=new_mean, sd_ops=new_sd, success_rate=new_success)
        )

    new_table = dataclasses.replace(table, rungs=tuple(new_rows), trials=restricted_trials)
    recomputed_verdict = verdict(new_table, plan)
    original_verdict = verdict(table, plan)
    if (recomputed_verdict.kind, recomputed_verdict.predicate) != (original_verdict.kind, original_verdict.predicate):
        divergences.append(
            f"verdict recorded {original_verdict.kind}/{original_verdict.predicate} "
            f"recomputed {recomputed_verdict.kind}/{recomputed_verdict.predicate}"
        )

    ordered = tuple(sorted(divergences))
    return Recomputation(verdict=recomputed_verdict, rungs=tuple(new_rows), agrees=not ordered, divergences=ordered)


def policy(table, tier):
    return {(t.bits, t.trial): repro.policy(t.replay_grade, tier) for t in table.trials}


def record(sub, table, plan, verified, *, attempt_id, at=None):
    """A second derivation of the table; its agreement with the first is what the record carries."""
    recomputation = recompute(table, plan, verified)
    repro_record = claims.ReproRecord(
        attempt_id=attempt_id, kind=claims.REPRO_KINDS[0], passed=recomputation.agrees, at=at or _now()
    )
    claims.write_repro_record(sub, repro_record)
    return repro_record, recomputation


def evidence_node(
    table,
    plan,
    *,
    target_statement_hash,
    population,
    assumptions,
    producer_identity,
    producer_tag,
    attempt_id=None,
    repro_record_hash=None,
):
    return claims.EvidenceNode(
        kind=NODE_KIND,
        target_statement_hash=target_statement_hash,
        population=population,
        assumptions=assumptions,
        producer_identity=producer_identity,
        producer_tag=producer_tag,
        verdict=verdict(table, plan).kind,
        in_sample_sizes=in_sample_sizes(table),
        attempt_id=attempt_id,
        repro_record_hash=repro_record_hash,
    )
