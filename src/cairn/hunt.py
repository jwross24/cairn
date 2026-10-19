import json
import secrets
from collections.abc import Callable
from dataclasses import dataclass

import blake3

from cairn import canon as canon
from cairn import claims, instances, justify, ledger, repro, runner
from cairn.hunt_attempt import (
    _input_blob,
    _invoke,
    _put_evidence_blob,
    _scope,
    _trial_record,
    _validate_attempt,
    _validate_hypothesis,
)
from cairn.hunt_attempt import _recipe as _recipe
from cairn.hunt_attempt import attempts_admissible as attempts_admissible
from cairn.hunt_attempt import record_for as record_for
from cairn.hunt_attempt import record_for_evidence as record_for_evidence
from cairn.hunt_attempt import required_attempt_ids as required_attempt_ids
from cairn.hunt_record import (
    DISTRIBUTION as DISTRIBUTION,
)
from cairn.hunt_record import (
    KIND,
    RUN_STATUS_BUDGET_EXCEEDED,
    UNIFORM_INTEGER,
    DistributionRefused,
    ExecutionRefused,
    HuntError,
    HuntPlan,
    HuntRecord,
    PlanRefused,
    SamplerRefused,
    TrialContext,
    VerificationRefused,
    distribution_canonical,
    hunt_trial_seed,
    plan_canonical,
    run_canonical,
)
from cairn.hunt_record import (
    PLAN as PLAN,
)
from cairn.hunt_record import (
    RUN as RUN,
)
from cairn.hunt_record import (
    Distribution as Distribution,
)
from cairn.hunt_record import (
    TrialRecord as TrialRecord,
)
from cairn.substrate import EDGE_INPUT, _now


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


def run_hunt(sub, plan, executor: Callable, verifier: Callable, *, run_id=None, attest_path=None, floor_protocol=None):
    if not isinstance(plan, HuntPlan):
        raise PlanRefused("run_hunt requires HuntPlan")
    if plan.distribution.kind != UNIFORM_INTEGER:
        raise DistributionRefused(f"unsupported distribution kind {plan.distribution.kind!r}")
    _store_plan(sub, plan)
    _validate_hypothesis(sub, plan)
    population, statement = _scope(sub, plan)
    run_id = run_id or secrets.token_hex(16)
    floor_registration = None
    from cairn import ladder, small_numbers_floor

    if floor_protocol is not None:
        small_numbers_floor.validate_protocol(sub, floor_protocol, plan)
    commitment, nonce_record = ladder.commit_entropy(sub, hypothesis_hash=plan.hypothesis_key, run_id=run_id)
    ladder.check_order(sub, hypothesis_hash=plan.hypothesis_key, nonce=nonce_record.nonce)
    if floor_protocol is not None:
        floor_registration = small_numbers_floor.register_run(sub, floor_protocol, plan, commitment)
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
            "size_interval": [context.point[plan.size_axis]] * 2,
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
        verifier_standing, reason = _verifier_standing(sub, plan)
        if not verifier_standing:
            trials.append(
                _trial_record(
                    context,
                    execution,
                    "VERIFIER_UNVERIFIED",
                    reason,
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
    if floor_registration is not None:
        sub.add_lineage(run_hash, floor_registration, EDGE_INPUT)
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
        in_sample_sizes=tuple(plan.distribution.ranges[plan.size_axis]),
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
        derivation = justify.derive_tag(sub, plan.statement_hash, attest_path)
        if derivation.refuted_by != evidence_hash:
            raise HuntError("hunt KILLED but justify did not derive a refutation")
        ledger_hash = ledger.write(
            sub,
            hypothesis_key=plan.hypothesis_key,
            decision=ledger.REFUTED,
            refutation_kind=ledger.MEASURED,
            evidence_node=evidence_hash,
            method=plan.method_identity,
            measured_points=({"numeric": dict(point), "categorical": {}},),
            result={
                "kind": ledger.EXACT,
                "quantity": "counterexample_count",
                "summary": "verified counterexample count at the recorded point",
                "value": "1",
                "ci": None,
                "ci_method": None,
                "coverage": None,
            },
            caught_by="hunt:verified_counterexample",
            at=_now(),
        )
    if nonce_record.withheld:
        instances.publish_nonce(sub, nonce)
    return HuntResult(record, run_hash, evidence_hash, ledger_hash, derivation)


def _verifier_standing(sub, plan):
    grade, reason = repro.owner_grade(
        sub, plan.executor_identity, repro.Verifier(repro.SKILL_VERIFIER, plan.verifier_identity)
    )
    return grade == repro.VERIFIABLE, reason


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
