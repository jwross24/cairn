from collections.abc import Mapping
from dataclasses import dataclass, field

from cairn import canon, keys, runner
from cairn.canon import BOOL, INT, NON_EMPTY_STR, STR, Field, List, Map, Optional, Set, Struct
from cairn.substrate import SubstrateError

KIND = "counterexample_hunt_record"
UNIFORM_INTEGER = "uniform_integer"
VERDICTS = ("SURVIVED", "KILLED", "INCOMPLETE")
HUNT_DOMAIN = "cairn/hunt-trial-seed/v1"
SEED_MODULUS = 1 << 63
RUN_STATUS_BUDGET_EXCEEDED = runner.STATUS_BUDGET_EXCEEDED

DISTRIBUTION = Struct("hunt_distribution", [Field("kind", NON_EMPTY_STR), Field("ranges", Map(STR, List(INT)))])
PLAN = Struct(
    "hunt_plan",
    [
        Field("statement_hash", NON_EMPTY_STR),
        Field("hypothesis_key", NON_EMPTY_STR),
        Field("distribution_hash", NON_EMPTY_STR),
        Field("trial_count", INT),
        Field("family_bounds", Map(STR, List(INT))),
        Field("size_axis", NON_EMPTY_STR),
        Field("method_identity", keys.METHOD_IDENTITY),
        Field("target_family", NON_EMPTY_STR),
        Field("assumption_set", Set(STR)),
        Field("executor_identity", NON_EMPTY_STR),
        Field("verifier_identity", NON_EMPTY_STR),
    ],
)
TRIAL = Struct(
    "hunt_trial",
    [
        Field("trial", INT),
        Field("point", Map(STR, INT)),
        Field("seed", INT),
        Field("attempt_id", Optional(NON_EMPTY_STR)),
        Field("execution_status", Optional(NON_EMPTY_STR)),
        Field("execution_evidence", Optional(NON_EMPTY_STR)),
        Field("outcome", NON_EMPTY_STR),
        Field("verifier_status", Optional(NON_EMPTY_STR)),
        Field("verifier_evidence", Optional(NON_EMPTY_STR)),
        Field("verifier_attempt_id", Optional(NON_EMPTY_STR)),
    ],
)
RUN = Struct(
    "hunt_run",
    [
        Field("plan_hash", NON_EMPTY_STR),
        Field("distribution_hash", NON_EMPTY_STR),
        Field("statement_hash", NON_EMPTY_STR),
        Field("hypothesis_key", NON_EMPTY_STR),
        Field("nonce", NON_EMPTY_STR),
        Field("declared_trial_count", INT),
        Field("completed_trial_count", INT),
        Field("budget_status", NON_EMPTY_STR),
        Field("verdict", NON_EMPTY_STR),
        Field("counterexample_trial", Optional(INT)),
        Field("standing", BOOL),
        Field("trials", List(TRIAL)),
    ],
)
SEED = Struct(
    "hunt_trial_seed",
    [Field("nonce", NON_EMPTY_STR), Field("hypothesis_key", NON_EMPTY_STR), Field("trial", INT)],
)


class HuntError(SubstrateError):
    pass


class DistributionRefused(HuntError):
    pass


class PlanRefused(HuntError):
    pass


class SamplerRefused(HuntError):
    pass


class ExecutionRefused(HuntError):
    pass


class VerificationRefused(HuntError):
    pass


def _range(value, name):
    if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError(f"{name} must be an inclusive [low, high] integer range")
    low, high = value
    if isinstance(low, bool) or isinstance(high, bool) or not isinstance(low, int) or not isinstance(high, int):
        raise ValueError(f"{name} must be an inclusive [low, high] integer range")
    if low > high:
        raise ValueError(f"{name} has low {low} above high {high}")
    return (low, high)


def _ranges(value, name):
    if not isinstance(value, Mapping) or not value:
        raise ValueError(f"{name} must be a non-empty mapping of integer ranges")
    out = {}
    for axis, bounds in value.items():
        if not isinstance(axis, str) or not axis:
            raise ValueError(f"{name} has an invalid axis")
        out[axis] = _range(bounds, f"{name}[{axis!r}]")
    return dict(sorted(out.items()))


@dataclass(frozen=True)
class Distribution:
    ranges: Mapping[str, tuple[int, int]]
    kind: str = UNIFORM_INTEGER
    hash: str = field(init=False, compare=False)

    def __post_init__(self):
        if self.kind != UNIFORM_INTEGER:
            raise DistributionRefused(f"unsupported distribution kind {self.kind!r}")
        normalized = _ranges(self.ranges, "distribution.ranges")
        object.__setattr__(self, "ranges", normalized)
        object.__setattr__(self, "hash", keys.node_hash("hunt_distribution", distribution_canonical(self)))


def distribution_canonical(distribution):
    return canon.encode(DISTRIBUTION, {"kind": distribution.kind, "ranges": distribution.ranges})


@dataclass(frozen=True)
class HuntPlan:
    statement_hash: str
    hypothesis_key: str
    distribution: Distribution
    trial_count: int
    family_bounds: Mapping[str, tuple[int, int]]
    size_axis: str | None = None
    method_identity: Mapping[str, object] = field(
        default_factory=lambda: {"interface_version": "counterexample_hunt/1", "params": {}}
    )
    target_family: str = "hunt-family"
    assumption_set: frozenset[str] = frozenset()
    executor_identity: str = "executor"
    verifier_identity: str = "verifier"
    hash: str = field(init=False, compare=False)

    def __post_init__(self):
        if not isinstance(self.statement_hash, str) or not self.statement_hash:
            raise ValueError("statement_hash must be non-empty")
        if not isinstance(self.hypothesis_key, str) or not self.hypothesis_key:
            raise ValueError("hypothesis_key must be non-empty")
        if isinstance(self.trial_count, bool) or not isinstance(self.trial_count, int) or self.trial_count <= 0:
            raise ValueError("trial_count must be a positive integer")
        family_bounds = _ranges(self.family_bounds, "family_bounds")
        size_axis = self.size_axis
        if size_axis is None and len(self.distribution.ranges) == 1:
            size_axis = next(iter(self.distribution.ranges))
        if not isinstance(size_axis, str) or size_axis not in self.distribution.ranges:
            raise PlanRefused("size_axis must name a distribution axis; multi-axis plans require it explicitly")
        if not isinstance(self.target_family, str) or not self.target_family:
            raise ValueError("target_family must be non-empty")
        if not isinstance(self.executor_identity, str) or not self.executor_identity:
            raise ValueError("executor_identity must be non-empty")
        if not isinstance(self.verifier_identity, str) or not self.verifier_identity:
            raise ValueError("verifier_identity must be non-empty")
        if not isinstance(self.assumption_set, (set, frozenset, tuple, list)):
            raise ValueError("assumption_set must be a collection of strings")
        assumptions = frozenset(self.assumption_set)
        if not all(isinstance(item, str) and item for item in assumptions):
            raise ValueError("assumption_set must contain non-empty strings")
        if set(self.distribution.ranges) - set(family_bounds):
            raise PlanRefused("distribution has an axis outside family_bounds")
        for axis, (low, high) in self.distribution.ranges.items():
            family_low, family_high = family_bounds[axis]
            if low < family_low or high > family_high:
                raise PlanRefused(f"distribution range for {axis!r} is outside family_bounds")
        method = dict(self.method_identity)
        try:
            canon.encode(keys.METHOD_IDENTITY, method)
        except canon.CanonError as exc:
            raise ValueError(f"method_identity is invalid: {exc}") from None
        object.__setattr__(self, "family_bounds", family_bounds)
        object.__setattr__(self, "size_axis", size_axis)
        object.__setattr__(self, "assumption_set", assumptions)
        object.__setattr__(self, "method_identity", method)
        object.__setattr__(self, "hash", keys.node_hash("hunt_plan", plan_canonical(self)))


def plan_canonical(plan):
    return canon.encode(
        PLAN,
        {
            "statement_hash": plan.statement_hash,
            "hypothesis_key": plan.hypothesis_key,
            "distribution_hash": plan.distribution.hash,
            "trial_count": plan.trial_count,
            "family_bounds": plan.family_bounds,
            "size_axis": plan.size_axis,
            "method_identity": plan.method_identity,
            "target_family": plan.target_family,
            "assumption_set": plan.assumption_set,
            "executor_identity": plan.executor_identity,
            "verifier_identity": plan.verifier_identity,
        },
    )


@dataclass(frozen=True)
class TrialContext:
    plan: HuntPlan
    run_id: str
    trial: int
    point: Mapping[str, int]
    seed: int
    input_blob_hash: str
    input_blob_size: int


@dataclass(frozen=True)
class TrialRecord:
    trial: int
    point: Mapping[str, int]
    seed: int
    attempt_id: str | None
    execution_status: str | None
    execution_evidence: str | None
    outcome: str
    verifier_status: str | None
    verifier_evidence: str | None
    verifier_attempt_id: str | None = None

    def canonical_value(self):
        return {
            "trial": self.trial,
            "point": dict(self.point),
            "seed": self.seed,
            "attempt_id": self.attempt_id,
            "execution_status": self.execution_status,
            "execution_evidence": self.execution_evidence,
            "outcome": self.outcome,
            "verifier_status": self.verifier_status,
            "verifier_evidence": self.verifier_evidence,
            "verifier_attempt_id": self.verifier_attempt_id,
        }


@dataclass(frozen=True)
class HuntRecord:
    plan_hash: str
    distribution_hash: str
    statement_hash: str
    hypothesis_key: str
    nonce: str
    declared_trial_count: int
    completed_trial_count: int
    budget_status: str
    verdict: str
    counterexample_trial: int | None
    standing: bool
    trials: tuple[TrialRecord, ...]
    hash: str = field(init=False, compare=False)

    def __post_init__(self):
        if self.verdict not in VERDICTS:
            raise ValueError(f"verdict must be one of {VERDICTS}")
        if (
            isinstance(self.declared_trial_count, bool)
            or not isinstance(self.declared_trial_count, int)
            or self.declared_trial_count <= 0
        ):
            raise ValueError("declared_trial_count must be positive")
        if self.completed_trial_count != len(self.trials):
            raise ValueError("completed_trial_count must equal the recorded trial count")
        if self.declared_trial_count < self.completed_trial_count:
            raise ValueError("completed_trial_count exceeds declared_trial_count")
        object.__setattr__(self, "trials", tuple(self.trials))
        _validate_record_trials(self)
        object.__setattr__(self, "hash", keys.node_hash("hunt_run", run_canonical(self)))


def _validate_record_trials(record):
    outcomes = {
        "SURVIVED_TRIAL",
        "COUNTEREXAMPLE",
        "EXECUTION_FAILED",
        "EXECUTION_UNVERIFIED",
        "VERIFIER_FAILED",
        "VERIFIER_UNVERIFIED",
        "COUNTEREXAMPLE_OUT_OF_SCOPE",
        RUN_STATUS_BUDGET_EXCEEDED,
    }
    for index, trial in enumerate(record.trials):
        if trial.trial != index:
            raise ValueError("trial indexes must be contiguous from zero")
        if not trial.attempt_id or not trial.execution_evidence:
            raise ValueError("every trial needs an execution attempt and evidence")
        if trial.outcome not in outcomes:
            raise ValueError(f"unsupported trial outcome {trial.outcome!r}")
        if trial.outcome == "SURVIVED_TRIAL":
            if (
                trial.execution_status != runner.STATUS_OK
                or trial.verifier_status != "NOT_REQUIRED"
                or trial.verifier_attempt_id is not None
            ):
                raise ValueError("a survived trial has inconsistent execution or verifier status")
        elif trial.outcome == "COUNTEREXAMPLE":
            if (
                trial.execution_status != runner.STATUS_OK
                or trial.verifier_status != runner.STATUS_OK
                or not trial.verifier_attempt_id
                or not trial.verifier_evidence
            ):
                raise ValueError("a counterexample trial needs a passed verifier attempt")
        elif trial.outcome == "EXECUTION_FAILED":
            if (
                trial.execution_status in (None, runner.STATUS_OK)
                or trial.verifier_status != "NOT_RUN"
                or trial.verifier_attempt_id is not None
            ):
                raise ValueError("a failed execution trial has inconsistent status")
        elif trial.outcome == "EXECUTION_UNVERIFIED":
            if trial.verifier_status != "NOT_RUN" or trial.verifier_attempt_id is not None:
                raise ValueError("an unverified execution has inconsistent verifier status")
        elif trial.outcome in ("VERIFIER_FAILED", "VERIFIER_UNVERIFIED", "COUNTEREXAMPLE_OUT_OF_SCOPE"):
            if (
                trial.execution_status != runner.STATUS_OK
                or not trial.verifier_attempt_id
                or not trial.verifier_evidence
            ):
                raise ValueError("a verifier failure needs a recorded verifier attempt")
        elif (
            trial.execution_status != RUN_STATUS_BUDGET_EXCEEDED and trial.verifier_status != RUN_STATUS_BUDGET_EXCEEDED
        ):
            raise ValueError("a budget trial needs a budget-exceeded attempt")
    if any(trial.outcome != "SURVIVED_TRIAL" for trial in record.trials[:-1]):
        raise ValueError("only the final trial may terminate a hunt")
    counterexamples = [trial.trial for trial in record.trials if trial.outcome == "COUNTEREXAMPLE"]
    if record.verdict == "SURVIVED":
        if (
            record.standing is not True
            or record.budget_status != "FULL_DECLARED_BUDGET"
            or record.counterexample_trial is not None
            or len(record.trials) != record.declared_trial_count
            or any(trial.outcome != "SURVIVED_TRIAL" for trial in record.trials)
        ):
            raise ValueError("SURVIVED requires a complete all-survived transcript")
    elif record.verdict == "KILLED":
        if (
            record.standing is not False
            or len(counterexamples) != 1
            or record.counterexample_trial != counterexamples[0]
            or record.counterexample_trial != len(record.trials) - 1
        ):
            raise ValueError("KILLED requires one final verifier-passed counterexample")
    elif record.standing is not False or record.counterexample_trial is not None or counterexamples:
        raise ValueError("INCOMPLETE cannot carry standing or a counterexample")


def run_canonical(record):
    return canon.encode(
        RUN,
        {
            "plan_hash": record.plan_hash,
            "distribution_hash": record.distribution_hash,
            "statement_hash": record.statement_hash,
            "hypothesis_key": record.hypothesis_key,
            "nonce": record.nonce,
            "declared_trial_count": record.declared_trial_count,
            "completed_trial_count": record.completed_trial_count,
            "budget_status": record.budget_status,
            "verdict": record.verdict,
            "counterexample_trial": record.counterexample_trial,
            "standing": record.standing,
            "trials": [trial.canonical_value() for trial in record.trials],
        },
    )


def hunt_trial_seed(nonce, hypothesis_key, trial):
    if not isinstance(trial, int) or isinstance(trial, bool) or trial < 0:
        raise ValueError("trial must be a non-negative integer")
    digest = canon.hash_object(HUNT_DOMAIN, SEED, {"nonce": nonce, "hypothesis_key": hypothesis_key, "trial": trial})
    return int.from_bytes(bytes.fromhex(digest)[:8], "big") % SEED_MODULUS or 1
