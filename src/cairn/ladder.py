"""Ladder run engine: pre-registration order, dispatch records, arms on one instance stream.

The order check is this module's: `instances` records the nonce it is handed, and only a
caller that wrote the entropy commitment before drawing can show the hypothesis object
came first. Both positions are read off `nodes.rowid`, the substrate's append order.

A method seed is drawn from the run's nonce under an arm-separated hypothesis key, so an
arm's seed is fixed before the method sees the instance and no two arms share a walk.
"""

import dataclasses
import importlib
import json
from decimal import Decimal
from pathlib import Path

from cairn import canon, claims, cli, instances, keys, ladderplan, laddertable, ledger, log, verifier, yank
from cairn.ladder_arm import (
    RUNG_TIER,
    SECONDS_PLACES,
    ArmTrial,
    RunBudget,
    _admit,
    _quantize,
    _receipt_scratch,
    _recipe,
    run_arm,
)
from cairn.ladder_commit import (
    COMMITMENT_KIND,
    COMMITMENT_SCHEMA,
    Commitment,
    _hypothesis,
    check_order,
    commit_entropy,
    commitment_for,
    method_seed,
    sequence_position,
)
from cairn.ladder_dispatch import (
    BASELINE,
    BASELINE_AA,
    CLAIMANT,
    KIND,
    TABLE,
    Dispatch,
    _allow_list,
    check_dispatch,
    dispatches_for,
    expected_identity,
    write_dispatch,
)
from cairn.ladder_refusal import (
    ALLOW_LIST_UNBOUND,
    ARM_UNKNOWN,
    ARMS_MISSING,
    BASELINE_REVISION_MISMATCH,
    COMMITMENT_ABSENT,
    HYPOTHESIS_ABSENT,
    HYPOTHESIS_AFTER_ENTROPY,
    INSTANCE_FAILED,
    METHOD_IDENTITY_MISMATCH,
    NONCE_ABSENT,
    NONCE_FOREIGN,
    NONCE_PUBLISHED,
    PRE_SPAWN_REASONS,
    SUBSTRATE_READABLE,
    TIER_REFUSED,
    UNCERTIFIED_REVISION,
    YANKED_REVISION,
    RunRefused,
)

__all__ = [
    "ALLOW_LIST_UNBOUND",
    "ARMS_MISSING",
    "ARM_UNKNOWN",
    "BASELINE",
    "BASELINE_AA",
    "BASELINE_REVISION_MISMATCH",
    "CLAIMANT",
    "COMMITMENT_ABSENT",
    "COMMITMENT_KIND",
    "COMMITMENT_SCHEMA",
    "HYPOTHESIS_ABSENT",
    "HYPOTHESIS_AFTER_ENTROPY",
    "INSTANCE_FAILED",
    "KIND",
    "LOG_STEP",
    "METHOD_IDENTITY_MISMATCH",
    "NONCE_ABSENT",
    "NONCE_FOREIGN",
    "NONCE_PUBLISHED",
    "PRE_SPAWN_REASONS",
    "RUNG_TIER",
    "SECONDS_PLACES",
    "SUBSTRATE_READABLE",
    "TABLE",
    "TIER_REFUSED",
    "UNCERTIFIED_REVISION",
    "YANKED_REVISION",
    "ArmTrial",
    "Commitment",
    "Dispatch",
    "RunBudget",
    "RunRefused",
    "_admit",
    "_allow_list",
    "_hypothesis",
    "_quantize",
    "_receipt_scratch",
    "_recipe",
    "_rung_row",
    "_table_evidence_nodes",
    "_trial_row",
    "arms_for",
    "check_dispatch",
    "check_order",
    "commit_entropy",
    "commitment_for",
    "dispatch",
    "dispatches_for",
    "expected_identity",
    "method_seed",
    "run",
    "run_arm",
    "sequence_position",
    "write_dispatch",
]

lg = log.get("ladder")

LOG_STEP = "ladder"


def dispatch(
    sub,
    gate_bundle,
    *,
    plan,
    plan_hash,
    hypothesis_hash,
    nonce,
    run_id,
    arm,
    skill,
    allow_list,
    at=None,
    attest_path=None,
):
    if arm not in ladderplan.ARMS:
        raise RunRefused(ARM_UNKNOWN, f"{arm!r} is no arm of {tuple(ladderplan.ARMS)}")
    module = importlib.import_module(skill)
    identity = module.identity_bundle()
    hypothesis = _hypothesis(sub, hypothesis_hash)
    value = Dispatch(
        run_id=run_id,
        arm=arm,
        nonce=nonce,
        hypothesis_hash=hypothesis_hash,
        method_identity=expected_identity(plan, arm, hypothesis),
        skill=skill,
        implementation_revision=identity["implementation_revision"],
        identity_bundle=identity,
        identity_bundle_hash=keys.identity_bundle_hash(identity),
        allow_list=allow_list.as_dict(),
        allow_list_hash=allow_list.hash,
        gate_bundle_hash=gate_bundle.hash,
        plan_hash=plan_hash,
        at=cli.now_iso() if at is None else at,
    )
    check_dispatch(sub, gate_bundle, value, plan, attest_path=attest_path)
    return write_dispatch(sub, value)


def _rung_row(plan, rung, module, trials):
    production = module.COST_PROFILE.production.per_size[rung.bits]
    return laddertable.aggregate_rung(
        plan,
        rung,
        tuple(_trial_row(trial) for trial in trials),
        model_prediction=str(production.mean_tries),
        reference_rate=str(Decimal(1) / Decimal(str(production.per_try_s))),
        declared_shape=module.COST_PROFILE.production.model,
    )


def _trial_row(claim):
    return laddertable.Trial(
        arm=claim.arm,
        bits=claim.bits,
        trial=claim.trial,
        seed=claim.seed,
        instance_hash=claim.instance_hash,
        recovered=claim.recovered,
        status=claim.status,
        output_complete=claim.output_complete,
        gate_ops=claim.gate_ops,
        reported_ops=claim.reported_ops,
        cpu_seconds=claim.cpu_seconds,
        wall_seconds=claim.wall_seconds,
        peak_rss_bytes=claim.peak_rss_bytes,
        scratch_bytes=claim.scratch_bytes,
        reported_memory_bytes=claim.reported_memory_bytes,
        replay_grade=claim.replay_grade,
        measurement_scope=claim.measurement_scope,
    )


def _table_evidence_nodes(sub, table, plan, trial_attempts, claimant):
    hypothesis_node = sub.get_node(table.hypothesis_hash)
    hypothesis = (
        None
        if hypothesis_node is None or hypothesis_node["kind"] != "hypothesis_object"
        else canon.decode(keys.HYPOTHESIS_OBJECT, bytes(hypothesis_node["canonical"]))
    )
    hypothesis_row = claims.get_hypothesis_object(sub, table.hypothesis_hash)
    statement_hash = None if hypothesis_row is None else hypothesis_row["claim_statement_hash"]
    if statement_hash is None:
        return ()
    if hypothesis is None:
        raise laddertable.LadderTableError(f"table {table.hash} names missing hypothesis {table.hypothesis_hash}")
    statement = claims.get_claim_statement(sub, statement_hash)
    if statement is None:
        raise laddertable.LadderTableError(
            f"hypothesis {table.hypothesis_hash} names missing claim statement {statement_hash}"
        )
    scope = json.loads(statement["scope"])
    bits = sorted({trial.bits for trial in table.trials})
    population = {
        "target_family": hypothesis["target_family"],
        "size_interval": [bits[0], bits[-1]],
        "param_ranges": {"bits": [bits[0], bits[-1]]},
        "assumption_set": scope["assumption_set"],
    }
    assumptions = frozenset(scope["assumption_set"])
    return tuple(
        laddertable.evidence_node(
            table,
            plan,
            target_statement_hash=statement_hash,
            population=population,
            assumptions=assumptions,
            producer_identity=claimant.identity_bundle_hash,
            producer_tag="skill",
            attempt_id=attempt_id,
        )
        for _, attempt_id in sorted(trial_attempts.items())
    )


def arms_for(rung):
    return (CLAIMANT,) if rung.role == ladderplan.ROLE_HOLD_OUT else tuple(ladderplan.ARMS)


def run(
    sub,
    gate_bundle,
    *,
    plan,
    plan_hash,
    run_id,
    hypothesis_hash,
    nonce,
    scratch_root,
    budget_remaining,
    attest_path,
    ceiling_multiplier=None,
    ops_counter=None,
    at=None,
    backend_paths=None,
):
    """One ladder run: every rung, every trial, every arm on the gate's instance stream."""
    with Path(attest_path).open("rb"):
        pass
    records = dispatches_for(sub, run_id)
    missing = [arm for arm in ladderplan.ARMS if arm not in records]
    if missing:
        raise RunRefused(ARMS_MISSING, f"run {run_id} holds no dispatch for {', '.join(missing)}")
    for value in records.values():
        check_dispatch(sub, gate_bundle, value, plan, attest_path=attest_path)
    claimant = records[CLAIMANT]

    budget = RunBudget(budget_remaining)
    arm_trials = []
    for rung in plan.rungs:
        by_arm = {arm: [] for arm in arms_for(rung)}
        for trial in range(rung.trials):
            attempt, out = instances.launch_trial(
                sub,
                gate_bundle,
                nonce=nonce,
                bits=rung.bits,
                trial=trial,
                scratch_root=scratch_root,
                method_identity=claimant.method_identity,
                budget_remaining=budget.remaining(sub),
                ceiling_multiplier=ceiling_multiplier,
                attest_path=attest_path,
            )
            budget.attempt_ids.append(attempt.attempt_id)
            if out is None:
                raise RunRefused(
                    INSTANCE_FAILED, f"the instance stream stopped at {rung.bits}/{trial} with {attempt.status}"
                )
            for arm in by_arm:
                by_arm[arm].append(
                    run_arm(
                        sub,
                        gate_bundle,
                        records[arm],
                        plan=plan,
                        instance=verifier.Instance(**out.instance()),
                        instance_hash=out.instance_hash,
                        bits=rung.bits,
                        trial=trial,
                        scratch_root=scratch_root,
                        budget_remaining=budget.remaining(sub),
                        attest_path=attest_path,
                        backend_paths=backend_paths,
                    )
                )
                budget.attempt_ids.append(by_arm[arm][-1].attempt_id)
        for values in by_arm.values():
            arm_trials.extend(values)

    if ops_counter is not None:
        observed = []
        for trial in arm_trials:
            observation = ops_counter(trial)
            if not isinstance(observation, laddertable.OpsObservation):
                raise laddertable.LadderTableError("ops_counter must return an OpsObservation")
            observed.append(dataclasses.replace(trial, gate_ops=observation))
        arm_trials = observed

    canonical_trials = tuple(
        sorted((_trial_row(trial) for trial in arm_trials), key=lambda trial: (trial.arm, trial.bits, trial.trial))
    )
    rungs = []
    for rung in plan.rungs:
        rung_trials = tuple(trial for trial in arm_trials if trial.bits == rung.bits)
        rungs.append(_rung_row(plan, rung, claimant.module, rung_trials))
    uncounted = any(trial.gate_ops.kind == laddertable.OPS_UNKNOWN for trial in arm_trials)

    table = laddertable.ResultTable(
        run_id=run_id,
        nonce=nonce,
        hypothesis_hash=hypothesis_hash,
        method_identity=claimant.method_identity,
        implementation_revision=claimant.implementation_revision,
        gate_bundle_hash=gate_bundle.hash,
        plan_hash=plan_hash,
        uncounted_backend=claimant.allow_list["counted_object"] if uncounted else None,
        rungs=tuple(rungs),
        trials=canonical_trials,
        created_at=cli.now_iso() if at is None else at,
    )
    trial_attempts = {(trial.arm, trial.bits, trial.trial): trial.attempt_id for trial in arm_trials}
    claimant_attempts = {
        (bits, trial): attempt_id for (arm, bits, trial), attempt_id in trial_attempts.items() if arm == CLAIMANT
    }
    evidence_nodes = _table_evidence_nodes(sub, table, plan, claimant_attempts, claimant)
    verdict = laddertable.verdict(table, plan)
    if (
        verdict.kind == laddertable.REJECT
        and verdict.refutation_kind == ledger.MEASURED
        and verdict.predicate not in laddertable._MEASURED_SETTLEMENT_PREDICATES
    ):
        raise RunRefused(
            "measured-settlement-unavailable", f"measured REJECT settlement has no producer for {verdict.predicate}"
        )
    with sub.transaction():
        laddertable.write(sub, table, plan, trial_attempts=trial_attempts, evidence_nodes=evidence_nodes)
        if verdict.kind == laddertable.REJECT:
            if verdict.refutation_kind == ledger.MEASURED:
                ledger.write_ladder_measured_refutation(sub, table.hash)
            elif verdict.refutation_kind == ledger.IMPLEMENTATION:
                entry = ledger.write(
                    sub,
                    hypothesis_key=table.hypothesis_hash,
                    decision=ledger.REFUTED,
                    refutation_kind=ledger.IMPLEMENTATION,
                    evidence_node=table.hash,
                    method=table.method_identity,
                    faulting_revision=claimant.identity_bundle_hash,
                    caught_by=f"ladder:{verdict.predicate}",
                    at=table.created_at,
                )
                yank.record(
                    sub,
                    yank_id=f"ladder:{entry}",
                    skill_identity_hash=claimant.identity_bundle_hash,
                    kind=yank.GATE_VERDICT,
                    attest_path=attest_path,
                    verdict_ref=entry,
                    at=table.created_at,
                )
    lg.info(
        "run", run_id=run_id, table=table.hash, rungs=len(rungs), trials=len(canonical_trials), **budget.snapshot(sub)
    )
    return table, tuple(arm_trials)
