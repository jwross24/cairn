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
import statistics
from dataclasses import dataclass, field
from decimal import ROUND_FLOOR as _ROUND_FLOOR
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
ATTEMPT_MEMBERSHIP_KIND = "ladder_attempt_membership"
TABLES = "ladder_tables"
RUNGS = "ladder_rungs"
TRIALS = "ladder_trials"

OPS_EXACT = "exact"
OPS_LOWER_BOUND = "lower_bound"
OPS_UNKNOWN = "unknown"
OPS_KINDS = (OPS_EXACT, OPS_LOWER_BOUND, OPS_UNKNOWN)

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
        Field("arm", NON_EMPTY_STR),
        Field("bits", INT),
        Field("trial", INT),
        Field("seed", INT),
        Field("instance_hash", NON_EMPTY_STR),
        Field("status", NON_EMPTY_STR),
        Field("output_complete", BOOL),
        Field("recovered", BOOL),
        Field("gate_ops_kind", NON_EMPTY_STR),
        Field("gate_ops", Optional(INT)),
        Field("reported_ops", Optional(INT)),
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
        Field("ops_kind", NON_EMPTY_STR),
        Field("mean_ops", Optional(STR)),
        Field("sd_ops", Optional(STR)),
        Field("cpu_seconds", NON_EMPTY_STR),
        Field("reference_rate", NON_EMPTY_STR),
        Field("memory_bytes", INT),
        Field("success_rate", NON_EMPTY_STR),
        Field("radius", NON_EMPTY_STR),
        Field("claim_ci_low", Optional(STR)),
        Field("claim_ci_high", Optional(STR)),
        Field("model_prediction", NON_EMPTY_STR),
        Field("model_band", NON_EMPTY_STR),
        Field("shape_statistic", Optional(STR)),
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

ATTEMPT_MEMBER = Struct(
    "ladder_attempt_member",
    [
        Field("arm", NON_EMPTY_STR),
        Field("bits", INT),
        Field("trial", INT),
        Field("attempt_id", NON_EMPTY_STR),
    ],
)

ATTEMPT_MEMBERSHIP = Struct(
    "ladder_attempt_membership",
    [
        Field("table_hash", NON_EMPTY_STR),
        Field("members", List(ATTEMPT_MEMBER)),
    ],
)


class LadderTableError(SubstrateError):
    pass


@dataclass(frozen=True)
class OpsObservation:
    kind: str
    value: int | None

    def __post_init__(self):
        if self.kind not in OPS_KINDS:
            raise LadderTableError(f"gate observation kind {self.kind!r} is not supported")
        if self.kind == OPS_UNKNOWN:
            if self.value is not None:
                raise LadderTableError("unknown gate observation must not carry a value")
            return
        if isinstance(self.value, bool) or not isinstance(self.value, int) or self.value < 0:
            raise LadderTableError(f"{self.kind} gate observation requires a nonnegative integer value")


def _trial_fields(t):
    return {
        "arm": t.arm,
        "bits": t.bits,
        "trial": t.trial,
        "seed": t.seed,
        "instance_hash": t.instance_hash,
        "status": t.status,
        "output_complete": t.output_complete,
        "recovered": t.recovered,
        "gate_ops_kind": t.gate_ops.kind,
        "gate_ops": t.gate_ops.value,
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
        "ops_kind": r.ops_kind,
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
        "rungs": [_rung_fields(r) for r in sorted(table.rungs, key=lambda rung: rung.bits)],
        "trials": [
            _trial_fields(t) for t in sorted(table.trials, key=lambda trial: (trial.arm, trial.bits, trial.trial))
        ],
    }


def _table_canonical(table):
    return canon.encode(TABLE_STRUCT, _table_fields(table))


@dataclass(frozen=True)
class Trial:
    arm: str
    bits: int
    trial: int
    seed: int
    instance_hash: str
    status: str
    output_complete: bool
    recovered: bool
    gate_ops: OpsObservation
    reported_ops: int | None
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
        if self.arm not in ladderplan.ARMS:
            raise LadderTableError(f"trial arm {self.arm!r} is not one of {ladderplan.ARMS}")
        if self.status not in substrate.TERMINAL_STATUSES:
            raise LadderTableError(f"trial status {self.status!r} is not terminal")
        if not isinstance(self.gate_ops, OpsObservation):
            raise LadderTableError("trial gate_ops must be an OpsObservation")
        if isinstance(self.reported_ops, bool) or (
            self.reported_ops is not None and (not isinstance(self.reported_ops, int) or self.reported_ops < 0)
        ):
            raise LadderTableError("reported_ops must be a nonnegative integer or None")
        object.__setattr__(self, "hash", keys.node_hash("ladder_trial", _trial_canonical(self)))


@dataclass(frozen=True)
class RungRow:
    bits: int
    role: str
    trials: int
    ops_kind: str
    mean_ops: str | None
    sd_ops: str | None
    cpu_seconds: str
    reference_rate: str
    memory_bytes: int
    success_rate: str
    radius: str
    model_prediction: str
    model_band: str
    shape_statistic: str | None
    declared_shape: str
    claim_ci_low: str | None = None
    claim_ci_high: str | None = None
    hash: str = field(init=False, compare=False)

    def __post_init__(self):
        if self.ops_kind not in OPS_KINDS:
            raise LadderTableError(f"rung operation kind {self.ops_kind!r} is not supported")
        if self.ops_kind == OPS_EXACT and (
            self.mean_ops is None or self.sd_ops is None or self.shape_statistic is None
        ):
            raise LadderTableError("exact rung rows require mean, SD, and shape statistic")
        if self.ops_kind == OPS_LOWER_BOUND and (
            self.mean_ops is None or self.sd_ops is not None or self.shape_statistic is not None
        ):
            raise LadderTableError("lower-bound rung rows carry only a mean lower bound")
        if self.ops_kind == OPS_UNKNOWN and any(
            value is not None for value in (self.mean_ops, self.sd_ops, self.shape_statistic)
        ):
            raise LadderTableError("unknown rung rows carry no operation statistics")
        if self.ops_kind != OPS_EXACT and any(value is not None for value in (self.claim_ci_low, self.claim_ci_high)):
            raise LadderTableError("non-exact rung rows carry no paired speedup interval")
        object.__setattr__(self, "hash", keys.node_hash("ladder_rung", _rung_canonical(self)))


def _decimal_text(value, places, *, rounding=None):
    return str(Decimal(value).quantize(Decimal(places), rounding=rounding))


def _speedup_ci(plan, claimant, baseline):
    if plan.comparison.ci_method != ladderplan.CI_METHODS[0]:
        raise LadderTableError(f"ci method {plan.comparison.ci_method} is not built")
    claimant_by_trial = {t.trial: t for t in claimant}
    baseline_by_trial = {t.trial: t for t in baseline}
    if claimant_by_trial.keys() != baseline_by_trial.keys() or len(claimant_by_trial) < 2:
        return None, None
    pairs = [(claimant_by_trial[key], baseline_by_trial[key]) for key in sorted(claimant_by_trial)]
    if any(
        claim.gate_ops.kind != OPS_EXACT
        or base.gate_ops.kind != OPS_EXACT
        or claim.gate_ops.value == 0
        or claim.status != runner.STATUS_OK
        or base.status != runner.STATUS_OK
        or not claim.output_complete
        or not base.output_complete
        or not claim.recovered
        or not base.recovered
        or claim.instance_hash != base.instance_hash
        for claim, base in pairs
    ):
        return None, None
    ratios = [Decimal(base.gate_ops.value) / Decimal(claim.gate_ops.value) for claim, base in pairs]
    if len(ratios) < 2:
        return None, None
    mean = sum(ratios) / Decimal(len(ratios))
    variance = sum((ratio - mean) ** 2 for ratio in ratios) / Decimal(len(ratios) - 1)
    z = Decimal(str(statistics.NormalDist().inv_cdf(float(1 - (1 - plan.comparison.ci_coverage) / 2))))
    half = z * (variance / Decimal(len(ratios))).sqrt()
    return _decimal_text(mean - half, "0.000001"), _decimal_text(mean + half, "0.000001")


def aggregate_rung(plan, rung, trials, *, model_prediction, reference_rate, declared_shape):
    by_arm = {}
    for trial in trials:
        by_arm.setdefault(trial.arm, []).append(trial)
    claimant = sorted(by_arm.get(ladderplan.ARMS[0], ()), key=lambda t: t.trial)
    if not claimant:
        raise LadderTableError(f"rung {rung.bits} has no claimant observations")
    observations = [t.gate_ops for t in claimant]
    if any(observation.kind == OPS_UNKNOWN for observation in observations):
        ops_kind, mean_ops, sd_ops, shape = OPS_UNKNOWN, None, None, None
    else:
        values = [Decimal(observation.value) for observation in observations]
        mean = sum(values) / Decimal(len(values))
        if any(observation.kind == OPS_LOWER_BOUND for observation in observations):
            ops_kind, mean_ops, sd_ops, shape = (
                OPS_LOWER_BOUND,
                _decimal_text(mean, "0.000001", rounding=_ROUND_FLOOR),
                None,
                None,
            )
        else:
            sd = (
                (sum((value - mean) ** 2 for value in values) / Decimal(len(values) - 1)).sqrt()
                if len(values) >= 2
                else Decimal(0)
            )
            prediction = Decimal(model_prediction)
            ops_kind = OPS_EXACT
            mean_ops = _decimal_text(mean, "0.000001")
            sd_ops = _decimal_text(sd, "0.000001")
            shape = _decimal_text(mean / prediction, "0.000001")
    baseline = by_arm.get(ladderplan.ARMS[1], ())
    low, high = _speedup_ci(plan, claimant, baseline) if baseline else (None, None)
    successes = sum(t.status == runner.STATUS_OK and t.output_complete and t.recovered for t in claimant)
    prediction = Decimal(model_prediction)
    rate = Decimal(reference_rate)
    return RungRow(
        bits=rung.bits,
        role=rung.role,
        trials=len(claimant),
        ops_kind=ops_kind,
        mean_ops=mean_ops,
        sd_ops=sd_ops,
        cpu_seconds=_decimal_text(sum(Decimal(t.cpu_seconds) for t in claimant), "0.000001"),
        reference_rate=_decimal_text(rate, "0.000001"),
        memory_bytes=max(t.reported_memory_bytes for t in claimant),
        success_rate=_decimal_text(Decimal(successes) / Decimal(len(claimant)), "0.0001"),
        radius=str(plan.design_radius),
        claim_ci_low=low,
        claim_ci_high=high,
        model_prediction=_decimal_text(prediction, "0.000001"),
        model_band=str(plan.design_radius),
        shape_statistic=shape,
        declared_shape=declared_shape,
    )


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


def _clock(trials, rows_by_bits, plan):
    tolerance = plan.tolerances.clock
    rate_ratio = plan.rate_ratio
    effective = tolerance if rate_ratio == 0 else min(tolerance, 2 * plan.design_radius / rate_ratio)
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


def _insert_rung(sub, table_hash, row):
    values = {"table_hash": table_hash, **_rung_fields(row)}
    columns = ", ".join(values)
    marks = ", ".join("?" for _ in values)
    sub.conn.execute(f"INSERT OR IGNORE INTO {RUNGS} ({columns}) VALUES ({marks})", tuple(values.values()))


def _insert_trial(sub, table_hash, t):
    values = {"table_hash": table_hash, **_trial_fields(t)}
    values["output_complete"] = int(values["output_complete"])
    values["recovered"] = int(values["recovered"])
    columns = ", ".join(values)
    marks = ", ".join("?" for _ in values)
    sub.conn.execute(f"INSERT OR IGNORE INTO {TRIALS} ({columns}) VALUES ({marks})", tuple(values.values()))


def _members_fields(table_hash, members):
    return {
        "table_hash": table_hash,
        "members": [
            {"arm": arm, "bits": bits, "trial": trial, "attempt_id": attempt_id}
            for arm, bits, trial, attempt_id in members
        ],
    }


def _canonical_members(trial_attempts):
    if not isinstance(trial_attempts, dict):
        raise LadderTableError("trial_attempts must map (arm, bits, trial) to attempt_id")
    members = []
    for key, attempt_id in trial_attempts.items():
        if not isinstance(key, tuple) or len(key) != 3:
            raise LadderTableError("trial_attempts keys must be (arm, bits, trial) tuples")
        arm, bits, trial = key
        if arm not in ladderplan.ARMS:
            raise LadderTableError("trial_attempts keys must name a ladder arm")
        if isinstance(bits, bool) or isinstance(trial, bool) or not isinstance(bits, int) or not isinstance(trial, int):
            raise LadderTableError("trial_attempts keys must contain integer bits and trial")
        if not isinstance(attempt_id, str) or not attempt_id:
            raise LadderTableError("trial_attempts values must be non-empty attempt IDs")
        members.append((arm, bits, trial, attempt_id))
    members.sort()
    if len({attempt_id for _, _, _, attempt_id in members}) != len(members):
        raise LadderTableError("every ladder trial must name a distinct attempt")
    return tuple(members)


def _claimant_dispatch(sub, table):
    rows = sub.conn.execute("SELECT record_json FROM ladder_dispatches ORDER BY rowid").fetchall()
    matches = []
    for row in rows:
        value = json.loads(row["record_json"])
        if (
            value.get("run_id") == table.run_id
            and value.get("nonce") == table.nonce
            and value.get("hypothesis_hash") == table.hypothesis_hash
            and value.get("arm") == ladderplan.ARMS[0]
        ):
            matches.append(value)
    if len(matches) != 1:
        raise LadderTableError(f"table {table.hash} has {len(matches)} claimant dispatches")
    dispatch = matches[0]
    if (
        dispatch.get("method_identity") != table.method_identity
        or dispatch.get("implementation_revision") != table.implementation_revision
        or dispatch.get("gate_bundle_hash") != table.gate_bundle_hash
        or dispatch.get("plan_hash") != table.plan_hash
    ):
        raise LadderTableError(f"claimant dispatch for table {table.hash} disagrees with the table identity")
    return dispatch


def _expected_trial_slots(plan):
    return {
        (arm, rung.bits, trial)
        for rung in plan.rungs
        for arm in ((ladderplan.ARMS[0],) if rung.role == ladderplan.ROLE_HOLD_OUT else ladderplan.ARMS)
        for trial in range(rung.trials)
    }


def _validate_trial_attempts(sub, table, plan, trial_attempts):
    from cairn import instances

    members = _canonical_members(trial_attempts)
    expected = _expected_trial_slots(plan)
    actual = {(t.arm, t.bits, t.trial) for t in table.trials}
    if actual != expected:
        raise LadderTableError("table trials must match the plan arm topology")
    found = {(arm, bits, trial) for arm, bits, trial, _ in members}
    if found != expected:
        raise LadderTableError("trial_attempts must name every and only table trial")
    trials = {(t.arm, t.bits, t.trial): t for t in table.trials}
    dispatches = {
        value["arm"]: value
        for row in sub.conn.execute("SELECT record_json FROM ladder_dispatches ORDER BY rowid").fetchall()
        if (value := json.loads(row["record_json"])).get("run_id") == table.run_id
    }
    for arm, bits, trial, attempt_id in members:
        attempt = sub.get_attempt(attempt_id)
        if attempt is None:
            raise LadderTableError(f"trial {bits}/{trial} names no attempt {attempt_id}")
        recipe = sub.get_recipe(attempt["recipe_key"])
        dispatch_for_arm = dispatches.get(arm)
        expected_seed = instances.trial_seed(table.nonce, f"{table.hypothesis_hash}/{arm}", bits, trial)
        expected_salt = f"ladder/{table.run_id}/{arm}/{bits}/{trial}"
        if (
            trials[(arm, bits, trial)].seed != expected_seed
            or recipe is None
            or recipe["seed"] != expected_seed
            or recipe["salt"] != expected_salt
            or dispatch_for_arm is None
            or recipe["skill_identity_hash"] != dispatch_for_arm["identity_bundle_hash"]
        ):
            raise LadderTableError(f"attempt {attempt_id} is not the {arm} trial {bits}/{trial} for table {table.hash}")
    return members


def _membership_rows(sub, table_hash):
    rows = sub.conn.execute(
        "SELECT n.hash, n.canonical FROM nodes n JOIN lineage l ON l.child_hash = n.hash "
        "WHERE n.kind = ? AND l.parent_hash = ? AND l.edge_kind = ? ORDER BY n.hash",
        (ATTEMPT_MEMBERSHIP_KIND, table_hash, substrate.EDGE_INPUT),
    ).fetchall()
    memberships = []
    for row in rows:
        value = canon.decode(ATTEMPT_MEMBERSHIP, bytes(row["canonical"]))
        if value["table_hash"] != table_hash:
            raise substrate.HashCollision(f"membership node {row['hash']} names another table")
        members = tuple((m["arm"], m["bits"], m["trial"], m["attempt_id"]) for m in value["members"])
        if tuple(sorted(members)) != members or len({(arm, bits, trial) for arm, bits, trial, _ in members}) != len(
            members
        ):
            raise substrate.HashCollision(f"membership node {row['hash']} is not canonical")
        memberships.append((row["hash"], members))
    return memberships


def membership_for_table(sub, table_hash):
    memberships = _membership_rows(sub, table_hash)
    if not memberships:
        return None
    values = {members for _, members in memberships}
    if len(values) != 1:
        raise substrate.HashCollision(f"table {table_hash} has conflicting attempt memberships")
    return next(iter(values))


def mapped_table_for_attempt(sub, attempt_id):
    tables = set()
    rows = sub.conn.execute(
        "SELECT n.hash, n.canonical, l.parent_hash FROM nodes n JOIN lineage l ON l.child_hash = n.hash "
        "WHERE n.kind = ? AND l.edge_kind = ? ORDER BY n.hash",
        (ATTEMPT_MEMBERSHIP_KIND, substrate.EDGE_INPUT),
    ).fetchall()
    for row in rows:
        value = canon.decode(ATTEMPT_MEMBERSHIP, bytes(row["canonical"]))
        if value["table_hash"] != row["parent_hash"]:
            raise substrate.HashCollision(f"membership node {row['hash']} has a conflicting table lineage")
        if any(member["attempt_id"] == attempt_id for member in value["members"]):
            tables.add(value["table_hash"])
    if len(tables) > 1:
        raise substrate.HashCollision(f"attempt {attempt_id} resolves to multiple ladder memberships")
    return next(iter(tables), None)


def table_for_attempt(sub, attempt_id):
    mapped = mapped_table_for_attempt(sub, attempt_id)
    legacy = {
        row["hash"]
        for row in sub.conn.execute(f"SELECT hash FROM {TABLES} WHERE attempt_id = ?", (attempt_id,)).fetchall()
    }
    all_tables = ({mapped} if mapped is not None else set()) | legacy
    if len(all_tables) > 1:
        raise substrate.HashCollision(f"attempt {attempt_id} resolves to multiple ladder tables")
    return next(iter(all_tables), None)


def attempt_ids_for_table(sub, table_hash):
    members = membership_for_table(sub, table_hash)
    return () if members is None else tuple(attempt_id for _, _, _, attempt_id in members)


def _store_membership(sub, table, members):
    existing = membership_for_table(sub, table.hash)
    if existing is not None and existing != members:
        raise substrate.HashCollision(f"table {table.hash} exists with different trial_attempts")
    canonical = canon.encode(ATTEMPT_MEMBERSHIP, _members_fields(table.hash, members))
    digest = keys.node_hash(ATTEMPT_MEMBERSHIP_KIND, canonical)
    sub._put_node(ATTEMPT_MEMBERSHIP_KIND, canonical, digest, "Replayable", None)
    sub._add_lineage(digest, table.hash, substrate.EDGE_INPUT)
    return digest


def _binding_table_hashes(sub, node_hash):
    rows = sub.conn.execute(
        "SELECT l.parent_hash FROM lineage l JOIN nodes n ON n.hash = l.parent_hash "
        "WHERE l.child_hash = ? AND l.edge_kind = ? AND n.kind = ?",
        (node_hash, substrate.EDGE_INPUT, NODE_KIND),
    ).fetchall()
    return {row["parent_hash"] for row in rows}


def _validate_evidence_node(sub, table, node):
    if node.kind != NODE_KIND:
        raise LadderTableError("a ladder table can bind only ladder_table evidence")
    members = membership_for_table(sub, table.hash)
    claimant_ids = {attempt_id for arm, _, _, attempt_id in members or () if arm == ladderplan.ARMS[0]}
    if members is None or node.attempt_id not in claimant_ids:
        raise LadderTableError(f"evidence attempt {node.attempt_id} is not a claimant member of table {table.hash}")
    hypothesis = claims.get_hypothesis_object(sub, table.hypothesis_hash)
    statement_hash = None if hypothesis is None else hypothesis["claim_statement_hash"]
    if statement_hash is None or node.target_statement_hash != statement_hash:
        raise LadderTableError(
            f"evidence target {node.target_statement_hash} is not table {table.hash}'s bound statement"
        )
    if claims.get_claim_statement(sub, statement_hash) is None:
        raise LadderTableError(f"table {table.hash} names missing claim statement {statement_hash}")
    dispatch = _claimant_dispatch(sub, table)
    if node.producer_tag != "skill" or node.producer_identity != dispatch["identity_bundle_hash"]:
        raise LadderTableError(f"evidence producer is not table {table.hash}'s claimant skill")


def write_evidence_node(sub, table, node):
    if membership_for_table(sub, table.hash) is None:
        raise LadderTableError(f"table {table.hash} has no claimant membership")
    _validate_evidence_node(sub, table, node)
    with sub._tx():
        bindings = _binding_table_hashes(sub, node.hash)
        if bindings and bindings != {table.hash}:
            raise substrate.HashCollision(f"evidence {node.hash} is already bound to another ladder table")
        claims.write_evidence_node(sub, node)
        sub._add_lineage(node.hash, table.hash, substrate.EDGE_INPUT)
    return node.hash


def write(sub, table, plan, *, at=None, attempt_id=None, trial_attempts=None, evidence_nodes=()):
    v = verdict(table, plan)
    grade = replay_grade(table)
    canonical = _table_canonical(table)
    created_at = table.created_at or at or _now()
    members = None if trial_attempts is None else _validate_trial_attempts(sub, table, plan, trial_attempts)
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
        if members is not None:
            _store_membership(sub, table, members)
        for node in evidence_nodes:
            write_evidence_node(sub, table, node)
    return table.hash


def _rung_from_row(r):
    return RungRow(
        bits=r["bits"],
        role=r["role"],
        trials=r["trials"],
        ops_kind=r["ops_kind"],
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
        arm=r["arm"],
        bits=r["bits"],
        trial=r["trial"],
        seed=r["seed"],
        instance_hash=r["instance_hash"],
        status=r["status"],
        output_complete=bool(r["output_complete"]),
        recovered=bool(r["recovered"]),
        gate_ops=OpsObservation(r["gate_ops_kind"], r["gate_ops"]),
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
    table_hash = table_for_attempt(sub, attempt_id)
    if table_hash is None:
        return None
    bits = [
        r["bits"] for r in sub.conn.execute(f"SELECT DISTINCT bits FROM {TRIALS} WHERE table_hash = ?", (table_hash,))
    ]
    return {"bits": [min(bits), max(bits)]} if bits else None


def read(sub, table_hash):
    row = sub.conn.execute(f"SELECT * FROM {TABLES} WHERE hash = ?", (table_hash,)).fetchone()
    if row is None:
        return None
    rung_rows = sub.conn.execute(f"SELECT * FROM {RUNGS} WHERE table_hash = ? ORDER BY bits", (table_hash,)).fetchall()
    trial_rows = sub.conn.execute(
        f"SELECT * FROM {TRIALS} WHERE table_hash = ? ORDER BY arm, bits, trial", (table_hash,)
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


def recompute(table, plan, verified):
    verified_set = set(verified)
    restricted_trials = tuple(t for t in table.trials if (t.arm, t.bits, t.trial) in verified_set)
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

        prung = plan.rung(row.bits)
        rebuilt = aggregate_rung(
            plan,
            prung,
            group,
            model_prediction=row.model_prediction,
            reference_rate=row.reference_rate,
            declared_shape=row.declared_shape,
        )
        for name in (
            "trials",
            "ops_kind",
            "mean_ops",
            "sd_ops",
            "success_rate",
            "claim_ci_low",
            "claim_ci_high",
            "shape_statistic",
        ):
            old, new = getattr(row, name), getattr(rebuilt, name)
            if str(old) != str(new):
                divergences.append(f"{row.bits}: {name} recorded {old} recomputed {new}")
        new_rows.append(rebuilt)

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
    return {(t.arm, t.bits, t.trial): repro.policy(t.replay_grade, tier) for t in table.trials}


def record(sub, table, plan, verified, *, attempt_id, at=None):
    """A second derivation of the table; its agreement with the first is what the record carries."""
    members = membership_for_table(sub, table.hash)
    if members is not None:
        member_ids = {member_attempt_id for arm, _, _, member_attempt_id in members if arm == ladderplan.ARMS[0]}
        expected = {(t.arm, t.bits, t.trial) for t in table.trials}
        if attempt_id not in member_ids:
            raise LadderTableError(f"recomputation attempt {attempt_id} is not a claimant member of table {table.hash}")
        if set(verified) != expected:
            raise LadderTableError(f"recomputation for table {table.hash} must verify every trial")
    recomputation = recompute(table, plan, verified)
    repro_record = claims.ReproRecord(
        attempt_id=attempt_id, kind=claims.REPRO_KINDS[0], passed=recomputation.agrees, at=at or _now()
    )
    with sub._tx():
        bindings = _binding_table_hashes(sub, repro_record.hash)
        if bindings and bindings != {table.hash}:
            raise substrate.HashCollision(f"repro record {repro_record.hash} is already bound to another ladder table")
        claims.write_repro_record(sub, repro_record)
        sub._add_lineage(repro_record.hash, table.hash, substrate.EDGE_INPUT)
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
