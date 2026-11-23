from dataclasses import dataclass, field

from cairn import canon, keys, ladderplan, ledger, substrate
from cairn.canon import BOOL, INT, NON_EMPTY_STR, STR, Field, List, Optional, Struct
from cairn.substrate import SubstrateError

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
CLOCK_QUEUE_PREDICATES = (CLOCK, WALL)
PREDICATES = (*REJECT_PREDICATES, *INCONCLUSIVE_PREDICATES, ALL_RUNGS_PASS)

REFUTATION_KIND = {
    RECOVERY: ledger.IMPLEMENTATION,
    COUNT_DIVERGENCE: ledger.IMPLEMENTATION,
    MEMORY_CAP: ledger.MEASURED,
    REFUTATION_FLOOR: ledger.MEASURED,
    IN_SAMPLE_MISS: ledger.MEASURED,
    OUT_OF_SAMPLE_MISS: ledger.MEASURED,
}
_MEASURED_SETTLEMENT_PREDICATES = (REFUTATION_FLOOR, IN_SAMPLE_MISS, OUT_OF_SAMPLE_MISS)

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
