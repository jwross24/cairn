import json
from dataclasses import dataclass
from pathlib import Path

from cairn import canon, claims, keys, runner, substrate
from cairn.hunt_record import RUN, ExecutionRefused, HuntRecord, PlanRefused, TrialRecord, _ranges
from cairn.substrate import EDGE_INPUT, blob_hash


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=_json_default)


def _json_default(value):
    if isinstance(value, (set, frozenset, tuple)):
        return sorted(value)
    raise TypeError(f"value {type(value).__name__} is not JSON serializable")


def _put_evidence_blob(sub, value):
    return sub.put_blob(_json(value).encode())


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
        "size_interval": list(plan.distribution.ranges[plan.size_axis]),
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


def _output(sub, attempt, receipt):
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
    if receipt is None or output_hash != receipt["stdout_digest"]:
        raise ExecutionRefused("attempt output.json digest differs from the process receipt stdout digest")
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
    document, output_hash = _output(sub, attempt, receipt)
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


def record_for_evidence(sub, evidence):
    bindings = [
        edge["parent_hash"]
        for edge in sub.lineage_of(evidence["hash"])
        if edge["edge_kind"] == EDGE_INPUT
        and (node := sub.get_node(edge["parent_hash"])) is not None
        and node["kind"] == "hunt_run"
    ]
    if len(bindings) != 1:
        return None
    try:
        record = record_for(sub, bindings[0])
    except canon.CanonError, ValueError, TypeError:
        return None
    if (
        record is None
        or record.hash != bindings[0]
        or record.statement_hash != evidence["target_statement_hash"]
        or record.verdict != evidence["verdict"]
    ):
        return None
    return record


def required_attempt_ids(sub, evidence):
    record = record_for_evidence(sub, evidence)
    if record is None:
        return None
    if record.verdict == "SURVIVED":
        members = tuple(trial.attempt_id for trial in record.trials)
    elif record.verdict == "KILLED":
        trial = record.trials[record.counterexample_trial]
        members = (trial.attempt_id, trial.verifier_attempt_id)
    else:
        return None
    if len(set(members)) != len(members) or any(
        attempt_id is None or sub.get_attempt(attempt_id) is None for attempt_id in members
    ):
        return None
    return members


def attempts_admissible(sub, evidence):
    members = required_attempt_ids(sub, evidence)
    return members is not None and all(
        (row := sub.get_attempt(attempt_id)) is not None and row["disowned_at"] is None and not row["inadmissible"]
        for attempt_id in members
    )
