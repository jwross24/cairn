import json
import secrets
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

import blake3

from cairn import canon, claims, instances, justify, keys, ledger, runner, substrate
from cairn.canon import BOOL, INT, NON_EMPTY_STR, STR, Field, List, Map, Optional, Set, Struct
from cairn.substrate import EDGE_INPUT, SubstrateError, _now, blob_hash

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


def _uniform_word(seed, axis, attempt, width):
    size = (width + 7) // 8
    blocks = []
    block = 0
    while len(blocks) * 32 < size:
        blocks.append(blake3.blake3(f"{seed}:{axis}:{attempt}:{block}".encode()).digest())
        block += 1
    word = int.from_bytes(b"".join(blocks)[:size], "big")
    return word & ((1 << width) - 1)


def sample_point(distribution, seed):
    if distribution.kind != UNIFORM_INTEGER:
        raise DistributionRefused(f"unsupported distribution kind {distribution.kind!r}")
    point = {}
    for axis, (low, high) in distribution.ranges.items():
        size = high - low + 1
        width = max(1, (size - 1).bit_length())
        limit = (1 << width) - ((1 << width) % size)
        attempt = 0
        while True:
            word = _uniform_word(seed, axis, attempt, width)
            attempt += 1
            if word < limit:
                point[axis] = low + word % size
                break
    return point


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=_json_default)


def _json_default(value):
    if isinstance(value, (set, frozenset, tuple)):
        return sorted(value)
    raise TypeError(f"value {type(value).__name__} is not JSON serializable")


def _put_evidence_blob(sub, value):
    return sub.put_blob(_json(value).encode())


def _store_plan(sub, plan):
    distribution_hash = sub.put_node(
        "hunt_distribution", distribution_canonical(plan.distribution), producer_identity="gate:hunt"
    )
    if distribution_hash != plan.distribution.hash:
        raise HuntError("distribution hash changed while storing")
    plan_hash = sub.put_node("hunt_plan", plan_canonical(plan), producer_identity="gate:hunt")
    if plan_hash != plan.hash:
        raise HuntError("plan hash changed while storing")
    sub.add_lineage(plan_hash, distribution_hash, EDGE_INPUT)
    if sub.get_node(plan.hypothesis_key) is not None:
        sub.add_lineage(plan_hash, plan.hypothesis_key, EDGE_INPUT)
    return plan_hash


def _scope(sub, plan):
    statement = claims.get_claim_statement(sub, plan.statement_hash)
    if statement is None:
        raise PlanRefused(f"no claim statement {plan.statement_hash}")
    try:
        scope = json.loads(statement["scope"])
    except KeyError, TypeError, ValueError:
        raise PlanRefused("claim statement scope is not valid JSON") from None
    if not isinstance(scope, dict):
        raise PlanRefused("claim statement scope is not a mapping")
    return {
        "target_family": plan.target_family,
        "size_interval": list(next(iter(plan.distribution.ranges.values()))),
        "param_ranges": {axis: list(bounds) for axis, bounds in plan.distribution.ranges.items()},
        "assumption_set": sorted(plan.assumption_set),
    }, statement


def _validate_hypothesis(sub, plan):
    row = sub.get_node(plan.hypothesis_key)
    companion = claims.get_hypothesis_object(sub, plan.hypothesis_key)
    if row is None or row["kind"] != "hypothesis_object" or companion is None:
        raise PlanRefused("hypothesis object is missing")
    try:
        hypothesis = canon.decode(keys.HYPOTHESIS_OBJECT, row["canonical"])
    except canon.CanonError as exc:
        raise PlanRefused(f"hypothesis object is not canonical: {exc}") from None
    if companion["claim_statement_hash"] != plan.statement_hash:
        raise PlanRefused("hypothesis does not bind the planned statement")
    if hypothesis["target_family"] != plan.target_family:
        raise PlanRefused("hypothesis target family differs from the plan")
    if hypothesis["method_identity"] != plan.method_identity:
        raise PlanRefused("hypothesis method identity differs from the plan")
    if _ranges(hypothesis["declared_parameter_ranges"], "hypothesis.declared_parameter_ranges") != dict(
        plan.family_bounds
    ):
        raise PlanRefused("hypothesis declared parameter ranges differ from the plan")
    if hypothesis["sampling_distribution"] != plan.distribution.hash:
        raise PlanRefused("hypothesis sampling distribution differs from the plan")


def _invoke(callback, context, execution=None):
    if execution is None:
        return callback(context)
    return callback(context, execution)


@dataclass(frozen=True)
class AttemptEvidence:
    attempt_id: str
    status: str
    output: dict
    output_json_hash: str | None
    output_manifest_hash: str | None
    receipt_hash: str | None
    evidence_hash: str


def _recipe(sub, attempt):
    row = sub.get_node(attempt["recipe_key"])
    if row is None or row["kind"] != "recipe":
        raise ExecutionRefused("attempt recipe node is missing")
    try:
        return canon.decode(keys.RECIPE, row["canonical"])
    except canon.CanonError as exc:
        raise ExecutionRefused(f"attempt recipe is not canonical: {exc}") from None


def _output(sub, attempt):
    manifest_hash = attempt["output_manifest_hash"]
    if manifest_hash is None:
        return None, None
    row = sub.get_node(manifest_hash)
    if row is None or row["kind"] != "output_manifest":
        raise ExecutionRefused("attempt output manifest node is missing")
    try:
        manifest = canon.decode(substrate.OUTPUT_MANIFEST, row["canonical"])
    except canon.CanonError as exc:
        raise ExecutionRefused(f"attempt output manifest is not canonical: {exc}") from None
    artifact = manifest["artifacts"].get("output.json")
    if artifact is None:
        raise ExecutionRefused("attempt output manifest has no output.json")
    output_hash, output_size = artifact
    data = sub.get_blob(output_hash)
    if data is None or len(data) != output_size:
        raise ExecutionRefused("attempt output.json blob is missing or has the wrong size")
    try:
        document = json.loads(data)
    except TypeError, ValueError:
        raise ExecutionRefused("attempt output.json is not JSON") from None
    if not isinstance(document, dict):
        raise ExecutionRefused("attempt output.json is not an object")
    return document, output_hash


def _validate_attempt(sub, attempt_obj, context, identity, required_inputs, seen):
    if not isinstance(attempt_obj, runner.Attempt):
        raise ExecutionRefused("adapter must return runner.Attempt")
    if attempt_obj.attempt_id in seen:
        raise ExecutionRefused("an attempt id was reused")
    seen.add(attempt_obj.attempt_id)
    attempt = sub.get_attempt(attempt_obj.attempt_id)
    if attempt is None or attempt["ended_at"] is None:
        raise ExecutionRefused("adapter returned an unrecorded or running attempt")
    if attempt["status"] != attempt_obj.status or attempt["recipe_key"] != attempt_obj.recipe_key:
        raise ExecutionRefused("adapter attempt does not match its stored attempt")
    if (
        attempt["output_manifest_hash"] != attempt_obj.output_manifest_hash
        or attempt["receipt_hash"] != attempt_obj.receipt_hash
    ):
        raise ExecutionRefused("adapter attempt evidence references do not match its stored attempt")
    if attempt["skip_cache_lookup"] != 1 or attempt["disowned_at"] is not None:
        raise ExecutionRefused("hunt attempts must skip cache lookup and remain admissible")
    recipe = _recipe(sub, attempt)
    recipe_row = sub.get_recipe(attempt["recipe_key"])
    if recipe_row is None or recipe_row["do_not_cache"] != 1:
        raise ExecutionRefused("hunt adapter recipe must be do_not_cache")
    if recipe["skill_identity_hash"] != identity:
        raise ExecutionRefused("attempt program identity does not match the frozen plan")
    if recipe["seed"] != context.seed:
        raise ExecutionRefused("attempt recipe seed does not match the trial seed")
    inputs = recipe["inputs"]
    for name, expected in required_inputs.items():
        got = inputs.get(name)
        if got is None or tuple(got) != tuple(expected):
            raise ExecutionRefused(f"attempt recipe input {name!r} is not bound to the trial")
    receipt = sub.get_receipt(attempt["receipt_hash"]) if attempt["receipt_hash"] else None
    evidence = {"attempt": attempt, "recipe": recipe, "receipt": receipt}
    streams = {}
    if attempt_obj.launch is not None and attempt_obj.launch.argv:
        attempt_dir = Path(attempt_obj.launch.argv[-1]).parent
        for name, expected in (
            ("stdout", None if receipt is None else receipt["stdout_digest"]),
            ("stderr", None if receipt is None else receipt["stderr_digest"]),
        ):
            path = attempt_dir / name
            if path.is_file():
                data = path.read_bytes()
                actual = blob_hash(data)
                if expected is not None and actual != expected:
                    raise ExecutionRefused(f"{name} digest differs from the process receipt")
                streams[name] = sub.put_blob(data)
        evidence["stream_blobs"] = streams
    document, output_hash = _output(sub, attempt)
    if attempt["status"] == runner.STATUS_OK:
        if receipt is None or receipt["exit_status"] != 0:
            raise ExecutionRefused("successful hunt attempt has no successful process receipt")
        if document is None:
            raise ExecutionRefused("successful hunt attempt has no output document")
    evidence_hash = _put_evidence_blob(sub, evidence)
    parents = [attempt["recipe_key"], attempt["output_manifest_hash"], attempt["receipt_hash"]]
    parents.extend(streams.values())
    for parent in parents:
        if parent is not None:
            sub.add_lineage(evidence_hash, parent, EDGE_INPUT)
    return AttemptEvidence(
        attempt["attempt_id"],
        attempt["status"],
        document or {},
        output_hash,
        attempt["output_manifest_hash"],
        attempt["receipt_hash"],
        evidence_hash,
    )


def _validate_binding(document, context, *, candidate=False, executor_output_hash=None):
    expected = {
        "statement_hash": context.plan.statement_hash,
        "plan_hash": context.plan.hash,
        "run_id": context.run_id,
        "trial": context.trial,
        "point": dict(context.point),
        "seed": context.seed,
        "input_blob_hash": context.input_blob_hash,
    }
    if any(document.get(name) != value for name, value in expected.items()):
        raise ExecutionRefused("attempt output does not bind the trial context")
    if candidate:
        if not isinstance(document.get("candidate"), bool):
            raise ExecutionRefused("executor output candidate must be boolean")
    else:
        if document.get("executor_output_digest") != executor_output_hash:
            raise VerificationRefused("verifier output does not bind executor output")
        if not isinstance(document.get("counterexample_valid"), bool):
            raise VerificationRefused("verifier output counterexample_valid must be boolean")


def _input_blob(sub, plan, run_id, trial, point, seed):
    data = _json(
        {
            "statement_hash": plan.statement_hash,
            "plan_hash": plan.hash,
            "run_id": run_id,
            "trial": trial,
            "point": dict(point),
            "seed": seed,
        }
    ).encode()
    digest = sub.put_blob(data)
    return digest, len(data)


def _trial_record(context, execution, outcome, verifier_status, verifier_evidence, verifier_attempt_id=None):
    return TrialRecord(
        context.trial,
        context.point,
        context.seed,
        execution.attempt_id,
        execution.status,
        execution.evidence_hash,
        outcome,
        verifier_status,
        verifier_evidence,
        verifier_attempt_id,
    )


def run_hunt(sub, plan, executor: Callable, verifier: Callable, *, run_id=None, attest_path=None):
    if not isinstance(plan, HuntPlan):
        raise PlanRefused("run_hunt requires HuntPlan")
    if plan.distribution.kind != UNIFORM_INTEGER:
        raise DistributionRefused(f"unsupported distribution kind {plan.distribution.kind!r}")
    _store_plan(sub, plan)
    _validate_hypothesis(sub, plan)
    population, statement = _scope(sub, plan)
    run_id = run_id or secrets.token_hex(16)
    nonce_record = instances.draw_nonce(sub, plan.hypothesis_key, run_id)
    nonce = nonce_record.nonce
    contexts = []
    for trial in range(plan.trial_count):
        seed = hunt_trial_seed(nonce, plan.hypothesis_key, trial)
        point = sample_point(plan.distribution, seed)
        if set(point) != set(plan.distribution.ranges):
            raise SamplerRefused("sampler axes differ from the declared distribution")
        if any(point[axis] < low or point[axis] > high for axis, (low, high) in plan.distribution.ranges.items()):
            raise SamplerRefused("sampler produced a point outside the declared distribution")
        if any(
            point[axis] < low or point[axis] > high for axis, (low, high) in plan.family_bounds.items() if axis in point
        ):
            raise SamplerRefused("sampler produced a point outside family_bounds")
        input_hash, input_size = _input_blob(sub, plan, run_id, trial, point, seed)
        contexts.append(TrialContext(plan, run_id, trial, point, seed, input_hash, input_size))
    trials = []
    counterexample_trial = None
    budget_status = "FULL_DECLARED_BUDGET"
    verification_problem = False
    seen_attempts = set()
    for context in contexts:
        execution = _validate_attempt(
            sub,
            _invoke(executor, context),
            context,
            plan.executor_identity,
            {"hunt_input": (context.input_blob_hash, context.input_blob_size)},
            seen_attempts,
        )
        if execution.status == RUN_STATUS_BUDGET_EXCEEDED:
            trials.append(
                _trial_record(
                    context,
                    execution,
                    RUN_STATUS_BUDGET_EXCEEDED,
                    "NOT_RUN",
                    _put_evidence_blob(sub, {"status": "NOT_RUN"}),
                )
            )
            budget_status = RUN_STATUS_BUDGET_EXCEEDED
            break
        if execution.status != runner.STATUS_OK:
            trials.append(
                _trial_record(
                    context,
                    execution,
                    "EXECUTION_FAILED",
                    "NOT_RUN",
                    _put_evidence_blob(sub, {"status": "NOT_RUN"}),
                )
            )
            budget_status = execution.status
            verification_problem = True
            break
        try:
            _validate_binding(execution.output, context, candidate=True)
        except ExecutionRefused:
            verification_problem = True
            trials.append(
                _trial_record(
                    context,
                    execution,
                    "EXECUTION_UNVERIFIED",
                    "NOT_RUN",
                    _put_evidence_blob(sub, {"status": "NOT_RUN"}),
                )
            )
            break
        if not execution.output["candidate"]:
            trials.append(
                _trial_record(
                    context,
                    execution,
                    "SURVIVED_TRIAL",
                    "NOT_REQUIRED",
                    _put_evidence_blob(sub, {"status": "NOT_REQUIRED", "candidate": False}),
                )
            )
            continue
        verification = _validate_attempt(
            sub,
            _invoke(verifier, context, execution),
            context,
            plan.verifier_identity,
            {
                "hunt_input": (context.input_blob_hash, context.input_blob_size),
                "executor_output": (execution.output_json_hash, len(sub.get_blob(execution.output_json_hash))),
            },
            seen_attempts,
        )
        if verification.status == RUN_STATUS_BUDGET_EXCEEDED:
            trials.append(
                _trial_record(
                    context,
                    execution,
                    RUN_STATUS_BUDGET_EXCEEDED,
                    "BUDGET_EXCEEDED",
                    verification.evidence_hash,
                    verification.attempt_id,
                )
            )
            budget_status = RUN_STATUS_BUDGET_EXCEEDED
            break
        if verification.status != runner.STATUS_OK:
            trials.append(
                _trial_record(
                    context,
                    execution,
                    "VERIFIER_FAILED",
                    verification.status,
                    verification.evidence_hash,
                    verification.attempt_id,
                )
            )
            verification_problem = True
            break
        try:
            _validate_binding(verification.output, context, executor_output_hash=execution.output_json_hash)
        except ExecutionRefused, VerificationRefused:
            trials.append(
                _trial_record(
                    context,
                    execution,
                    "VERIFIER_UNVERIFIED",
                    runner.STATUS_FAIL,
                    verification.evidence_hash,
                    verification.attempt_id,
                )
            )
            verification_problem = True
            break
        if not verification.output["counterexample_valid"]:
            trials.append(
                _trial_record(
                    context,
                    execution,
                    "VERIFIER_FAILED",
                    runner.STATUS_FAIL,
                    verification.evidence_hash,
                    verification.attempt_id,
                )
            )
            verification_problem = True
            break
        point_population = {
            **population,
            "size_interval": [next(iter(context.point.values()))] * 2,
            "param_ranges": {axis: [value, value] for axis, value in context.point.items()},
        }
        if justify.counterexample_coverage_violation(point_population, json.loads(statement["scope"])) is not None:
            trials.append(
                _trial_record(
                    context,
                    execution,
                    "COUNTEREXAMPLE_OUT_OF_SCOPE",
                    runner.STATUS_OK,
                    verification.evidence_hash,
                    verification.attempt_id,
                )
            )
            verification_problem = True
            break
        population = point_population
        trials.append(
            _trial_record(
                context,
                execution,
                "COUNTEREXAMPLE",
                runner.STATUS_OK,
                verification.evidence_hash,
                verification.attempt_id,
            )
        )
        counterexample_trial = context.trial
        break
    if counterexample_trial is not None:
        verdict = "KILLED"
        standing = False
    elif len(trials) == plan.trial_count and not verification_problem and budget_status == "FULL_DECLARED_BUDGET":
        verdict = "SURVIVED"
        standing = True
    else:
        verdict = "INCOMPLETE"
        standing = False
    record = HuntRecord(
        plan.hash,
        plan.distribution.hash,
        plan.statement_hash,
        plan.hypothesis_key,
        nonce,
        plan.trial_count,
        len(trials),
        budget_status,
        verdict,
        counterexample_trial,
        standing,
        tuple(trials),
    )
    run_hash = sub.put_node("hunt_run", run_canonical(record), producer_identity="gate:hunt")
    for parent in (plan.hash, plan.distribution.hash):
        sub.add_lineage(run_hash, parent, EDGE_INPUT)
    for trial in trials:
        for evidence_hash in (trial.execution_evidence, trial.verifier_evidence):
            if evidence_hash is not None:
                sub.add_lineage(run_hash, evidence_hash, EDGE_INPUT)
    evidence = claims.EvidenceNode(
        kind=KIND,
        target_statement_hash=plan.statement_hash,
        population=population,
        assumptions=plan.assumption_set,
        producer_identity="gate:hunt",
        producer_tag="gate",
        verdict=verdict,
        in_sample_sizes=tuple(next(iter(plan.distribution.ranges.values()))),
        attempt_id=trials[-1].attempt_id if trials else None,
    )
    evidence_hash = claims.write_evidence_node(sub, evidence)
    sub.add_lineage(evidence_hash, run_hash, EDGE_INPUT)
    ledger_hash = None
    derivation = None
    if verdict == "KILLED":
        if counterexample_trial is None:
            raise HuntError("KILLED hunt has no counterexample trial")
        point = trials[counterexample_trial].point
        ledger_hash = ledger.write(
            sub,
            hypothesis_key=plan.hypothesis_key,
            decision=ledger.REFUTED,
            refutation_kind=ledger.MEASURED,
            evidence_node=evidence_hash,
            method=plan.method_identity,
            measured_points=({"numeric": dict(point), "categorical": {}},),
            result={
                "summary": "verified counterexample count at the recorded point",
                "value": "1",
                "ci": ["1", "1"],
            },
            caught_by="hunt:verified_counterexample",
            at=_now(),
        )
        derivation = justify.derive_tag(sub, plan.statement_hash, attest_path)
        if derivation.refuted_by != evidence_hash:
            raise HuntError("hunt KILLED but justify did not derive a refutation")
    if nonce_record.withheld:
        instances.publish_nonce(sub, nonce)
    return HuntResult(record, run_hash, evidence_hash, ledger_hash, derivation)


@dataclass(frozen=True)
class HuntResult:
    record: HuntRecord
    run_hash: str
    evidence_hash: str
    ledger_hash: str | None
    judgment: object | None

    @property
    def verdict(self):
        return self.record.verdict

    @property
    def standing(self):
        return self.record.standing


def record_for(sub, digest):
    row = sub.get_node(digest)
    if row is None or row["kind"] != "hunt_run":
        return None
    value = canon.decode(RUN, row["canonical"])
    trials = tuple(TrialRecord(**trial) for trial in value["trials"])
    return HuntRecord(
        value["plan_hash"],
        value["distribution_hash"],
        value["statement_hash"],
        value["hypothesis_key"],
        value["nonce"],
        value["declared_trial_count"],
        value["completed_trial_count"],
        value["budget_status"],
        value["verdict"],
        value["counterexample_trial"],
        value["standing"],
        trials,
    )
