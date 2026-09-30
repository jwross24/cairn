import json
import math
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path

from cairn import bundle, hunt, keys, ladder, repro, runner
from cairn.profile import Evaluation
from cairn.substrate import EDGE_INPUT, SubstrateError, blob_hash

PROTOCOL_KIND = "small_numbers_floor_protocol"
STUDY_KIND = "small_numbers_floor_study"
RUN_KIND = "small_numbers_floor_registration"
RESULT_KIND = "small_numbers_floor_result"
REPRO_KIND = "small_numbers_floor_reproduction"
DISPATCH_KIND = "small_numbers_floor_dispatch"
FAILURE_CODING = "SURVIVED_TRIAL=0;verified COUNTEREXAMPLE=1;other outcomes incomplete"
STAKE_RULE = "fixed_maximum"
COMPARISON = "completed_full_budget"


class FloorRefused(SubstrateError):
    pass


def rational(value):
    if isinstance(value, bool) or not isinstance(value, (str, int, Fraction)):
        raise FloorRefused("an exact finite rational is required")
    try:
        if isinstance(value, str) and value.startswith("hex:"):
            numerator, denominator = value[4:].split("/")
            return Fraction(int(numerator, 16), int(denominator, 16))
        return Fraction(value)
    except ValueError, ZeroDivisionError:
        raise FloorRefused("an exact finite rational is required") from None


def probability(value):
    result = rational(value)
    if not 0 < result < 1:
        raise FloorRefused("epsilon and alpha must lie strictly between zero and one")
    return result


def exact_text(value):
    value = rational(value)
    return f"hex:{value.numerator:x}/{value.denominator:x}"


def update(wealth, outcome, epsilon, stake):
    epsilon = probability(epsilon)
    wealth, stake = rational(wealth), rational(stake)
    if wealth < 0 or not 0 <= stake <= 1 / (1 - epsilon):
        raise FloorRefused("wealth must be nonnegative and stake must satisfy its predictable bound")
    if isinstance(outcome, bool) or not isinstance(outcome, int) or outcome not in (0, 1):
        raise FloorRefused("outcome must be binary integer zero or one")
    return wealth * (1 - stake * (outcome - epsilon))


def passes(wealth, alpha):
    wealth = rational(wealth)
    if wealth < 0:
        raise FloorRefused("wealth must be nonnegative")
    return wealth >= 1 / probability(alpha)


def _bytes(value):
    return bundle.canonical_bytes("small_numbers_floor", value)


def _read(sub, digest, kind):
    row = sub.get_node(digest)
    if row is None or row["kind"] != kind or keys.node_hash(kind, row["canonical"]) != digest:
        raise FloorRefused(f"missing or invalid {kind}")
    return bundle._decode(row["canonical"])


def _write(sub, kind, value, parents=()):
    digest = sub.put_node(kind, _bytes(value), producer_identity="gate:small_numbers_floor")
    for parent in parents:
        sub.add_lineage(digest, parent, EDGE_INPUT)
    return digest


def sampler_identity():
    return blob_hash(Path(hunt.__file__).read_bytes())


@dataclass(frozen=True)
class Protocol:
    plan_hash: str
    hypothesis_hash: str
    distribution_hash: str
    epsilon: Fraction | str
    alpha: Fraction | str
    budget: int
    study_hash: str
    sampler_hash: str = field(default_factory=sampler_identity)
    stake_rule: str = STAKE_RULE
    failure_coding: str = FAILURE_CODING
    comparison: str = COMPARISON
    hash: str = field(init=False)

    def __post_init__(self):
        object.__setattr__(self, "epsilon", probability(self.epsilon))
        object.__setattr__(self, "alpha", probability(self.alpha))
        if isinstance(self.budget, bool) or not isinstance(self.budget, int) or self.budget <= 0:
            raise FloorRefused("budget must be positive integer")
        if any(
            not isinstance(value, str) or not value
            for value in (
                self.plan_hash,
                self.hypothesis_hash,
                self.distribution_hash,
                self.study_hash,
                self.sampler_hash,
            )
        ):
            raise FloorRefused("protocol identities must be nonempty")
        if (self.stake_rule, self.failure_coding, self.comparison) != (STAKE_RULE, FAILURE_CODING, COMPARISON):
            raise FloorRefused("unsupported floor protocol")
        object.__setattr__(self, "hash", keys.node_hash(PROTOCOL_KIND, _bytes(self.value())))

    def value(self):
        return {
            "plan_hash": self.plan_hash,
            "hypothesis_hash": self.hypothesis_hash,
            "distribution_hash": self.distribution_hash,
            "epsilon": str(self.epsilon),
            "alpha": str(self.alpha),
            "budget": self.budget,
            "study_hash": self.study_hash,
            "sampler_hash": self.sampler_hash,
            "stake_rule": self.stake_rule,
            "failure_coding": self.failure_coding,
            "comparison": self.comparison,
        }


def _validate_plan(protocol, plan):
    if not isinstance(protocol, Protocol) or not isinstance(plan, hunt.HuntPlan):
        raise FloorRefused("typed protocol and HuntPlan required")
    if keys.node_hash(PROTOCOL_KIND, _bytes(protocol.value())) != protocol.hash:
        raise FloorRefused("protocol mutation refused")
    if keys.node_hash("hunt_distribution", hunt.distribution_canonical(plan.distribution)) != plan.distribution.hash:
        raise FloorRefused("distribution mutation refused")
    if keys.node_hash("hunt_plan", hunt.plan_canonical(plan)) != plan.hash:
        raise FloorRefused("plan mutation refused")
    if (protocol.plan_hash, protocol.hypothesis_hash, protocol.distribution_hash, protocol.budget) != (
        plan.hash,
        plan.hypothesis_key,
        plan.distribution.hash,
        plan.trial_count,
    ):
        raise FloorRefused("protocol does not bind this plan and distribution")
    if protocol.sampler_hash != sampler_identity():
        raise FloorRefused("sampler source identity differs")


def register_protocol(sub, protocol, plan):
    _validate_plan(protocol, plan)
    _read(sub, protocol.study_hash, STUDY_KIND)
    hunt._validate_hypothesis(sub, plan)
    if sub.conn.execute("SELECT 1 FROM instance_nonces WHERE hypothesis_key = ?", (plan.hypothesis_key,)).fetchone():
        raise FloorRefused("protocol must precede entropy and sampling")
    hunt._store_plan(sub, plan)
    return _write(sub, PROTOCOL_KIND, protocol.value(), (plan.hash, plan.hypothesis_key, protocol.study_hash))


def validate_protocol(sub, protocol, plan):
    _validate_plan(protocol, plan)
    if _read(sub, protocol.hash, PROTOCOL_KIND) != protocol.value():
        raise FloorRefused("stored protocol differs")
    for row in sub.conn.execute(
        "SELECT nonce FROM instance_nonces WHERE hypothesis_key = ?", (plan.hypothesis_key,)
    ).fetchall():
        position, commitment = ladder.commitment_for(sub, row["nonce"])
        if commitment is None or ladder.sequence_position(sub, protocol.hash) >= position:
            raise FloorRefused("protocol must precede every entropy draw for this hypothesis")


def register_run(sub, protocol, plan, commitment):
    validate_protocol(sub, protocol, plan)
    checked = ladder.check_order(sub, hypothesis_hash=plan.hypothesis_key, nonce=commitment.nonce)
    if checked != commitment or ladder.sequence_position(sub, protocol.hash) >= ladder.sequence_position(
        sub, commitment.hash
    ):
        raise FloorRefused("protocol must precede gate entropy commitment")
    value = {
        "protocol_hash": protocol.hash,
        "plan_hash": plan.hash,
        "hypothesis_hash": plan.hypothesis_key,
        "distribution_hash": plan.distribution.hash,
        "commitment_hash": commitment.hash,
        "nonce": commitment.nonce,
        "run_id": commitment.run_id,
        "sampler_hash": sampler_identity(),
    }
    return _write(sub, RUN_KIND, value, (protocol.hash, plan.hash, plan.hypothesis_key, commitment.hash))


def registration_for(sub, result):
    rows = sub.conn.execute(
        "SELECT parent_hash FROM lineage WHERE child_hash = ? AND edge_kind = ?", (result.run_hash, EDGE_INPUT)
    ).fetchall()
    found = [
        row["parent_hash"]
        for row in rows
        if (node := sub.get_node(row["parent_hash"])) is not None and node["kind"] == RUN_KIND
    ]
    if len(found) != 1:
        raise FloorRefused("hunt must bind exactly one floor registration")
    return found[0], _read(sub, found[0], RUN_KIND)


def transcript(protocol, trials):
    wealth = Fraction(1)
    entries = []
    for trial in trials:
        outcome = {"SURVIVED_TRIAL": 0, "COUNTEREXAMPLE": 1}.get(trial.outcome)
        if outcome is not None:
            wealth = update(wealth, outcome, protocol.epsilon, 1 / (1 - protocol.epsilon))
        entries.append(
            {
                "trial": trial.trial,
                "point": dict(trial.point),
                "seed": trial.seed,
                "outcome": trial.outcome,
                "X": outcome,
            }
        )
    return entries, wealth


def record_result(sub, protocol, result):
    if not isinstance(result, hunt.HuntResult) or hunt.record_for(sub, result.run_hash) != result.record:
        raise FloorRefused("a stored real HuntResult is required")
    registration_hash, registration = registration_for(sub, result)
    if registration["protocol_hash"] != protocol.hash or registration["nonce"] != result.record.nonce:
        raise FloorRefused("hunt differs from registered protocol or entropy")
    if _read(sub, protocol.hash, PROTOCOL_KIND) != protocol.value():
        raise FloorRefused("protocol mutation refused")
    entries, wealth = transcript(protocol, result.record.trials)
    complete = result.verdict == "SURVIVED" and result.record.completed_trial_count == protocol.budget
    display = None if wealth == 0 else str(math.log10(wealth.numerator) - math.log10(wealth.denominator))
    value = {
        "registration_hash": registration_hash,
        "hunt_hash": result.run_hash,
        "protocol_hash": protocol.hash,
        "verdict": result.verdict,
        "completed": result.record.completed_trial_count,
        "E": exact_text(wealth),
        "log10E": display,
        "threshold": exact_text(1 / protocol.alpha),
        "resource_observation_pass": complete and passes(wealth, protocol.alpha),
        "transcript": entries,
    }
    return _write(sub, RESULT_KIND, value, (registration_hash, result.run_hash))


def launch_dispatch(sub, recipe, dispatch, scratch_root):
    if blob_hash(Path(dispatch["source_path"]).read_bytes()) != dispatch["source_hash"]:
        raise FloorRefused("worker source changed from pinned dispatch")
    return runner.launch(
        sub,
        dispatch["module"],
        recipe,
        bundle_hash=dispatch["bundle_hash"],
        evaluation=Evaluation(*(float(value) for value in dispatch["evaluation"])),
        ceiling_multiplier=float(dispatch["ceiling_multiplier"]),
        tool_digests=dispatch["tool_digests"],
        scratch_root=scratch_root,
        wall_cap_multiplier=float(dispatch["wall_cap_multiplier"]),
        wall_cap_floor_s=float(dispatch["wall_cap_floor_s"]),
        subprocess_startup_ms=dispatch["subprocess_startup_ms"],
        replay=dispatch["replay"],
        skip_cache_lookup=True,
        do_not_cache=True,
        budget_remaining=dispatch["budget_remaining"],
        env_extra=dispatch["env_extra"],
        stdin_document=dispatch["stdin_document"],
    )


def dispatch_for(sub, recipe):
    digest, size = recipe["inputs"]["floor_dispatch"]
    data = sub.get_blob(digest)
    if data is None or len(data) != size:
        raise FloorRefused("dispatch blob missing or size differs")
    document = bundle._decode(data)
    if _bytes(document) != data:
        raise FloorRefused("dispatch blob is not canonical")
    return document


def reproduce(sub, protocol, plan, result, floor_hash, *, scratch_root, attest_path):
    validate_protocol(sub, protocol, plan)
    original = _read(sub, floor_hash, RESULT_KIND)
    if original["hunt_hash"] != result.run_hash or result.record.verdict == "INCOMPLETE":
        raise FloorRefused("only completed or verified-killed registered hunts can be reproduced")
    _, registration = registration_for(sub, result)
    seen = {
        identifier
        for trial in result.record.trials
        for identifier in (trial.attempt_id, trial.verifier_attempt_id)
        if identifier is not None
    }
    records, reruns, trials = [], [], []
    for trial in result.record.trials:
        seed = hunt.hunt_trial_seed(registration["nonce"], plan.hypothesis_key, trial.trial)
        point = hunt.sample_point(plan.distribution, seed)
        if point != dict(trial.point) or seed != trial.seed:
            raise FloorRefused("committed nonce does not reproduce original points")
        first = sub.get_attempt(trial.attempt_id)
        recipe = hunt._recipe(sub, first)
        input_hash, input_size = recipe["inputs"]["hunt_input"]
        document = json.loads(sub.get_blob(input_hash))
        context = hunt.TrialContext(plan, document["run_id"], trial.trial, point, seed, input_hash, input_size)
        executions = []
        for attempt_id, identity in (
            (trial.attempt_id, plan.executor_identity),
            (trial.verifier_attempt_id, plan.verifier_identity),
        ):
            if attempt_id is None:
                continue
            first = sub.get_attempt(attempt_id)
            recipe = hunt._recipe(sub, first)
            dispatch = dispatch_for(sub, recipe)
            attempt = launch_dispatch(sub, recipe, dispatch, scratch_root)
            required = {"hunt_input": (input_hash, input_size)}
            if executions:
                output_hash = executions[0].output_json_hash
                required["executor_output"] = (output_hash, len(sub.get_blob(output_hash)))
            checked = hunt._validate_attempt(sub, attempt, context, identity, required, seen)
            if checked.status != runner.STATUS_OK:
                raise FloorRefused("reproduction attempt did not succeed")
            if executions:
                hunt._validate_binding(checked.output, context, executor_output_hash=executions[0].output_json_hash)
                if checked.output["counterexample_valid"] is not True:
                    raise FloorRefused("counterexample reproduction was not verified")
            else:
                hunt._validate_binding(checked.output, context, candidate=True)
                if checked.output["candidate"] != (trial.outcome == "COUNTEREXAMPLE"):
                    raise FloorRefused("reproduced outcome differs")
            recorded, _ = repro.record_rerun(sub, attempt_id, attempt.attempt_id, attest_path=attest_path)
            records.append(recorded.hash)
            reruns.append(attempt.attempt_id)
            executions.append(checked)
            if not recorded.passed:
                raise FloorRefused("reproduction manifest differs")
        trials.append(
            hunt.TrialRecord(
                trial.trial,
                point,
                seed,
                executions[0].attempt_id,
                executions[0].status,
                executions[0].evidence_hash,
                trial.outcome,
                trial.verifier_status,
                trial.verifier_evidence,
                executions[1].attempt_id if len(executions) == 2 else None,
            )
        )
    entries, wealth = transcript(protocol, trials)
    substantive = {"transcript": entries, "E": exact_text(wealth), "verdict": result.verdict}
    expected = {name: original[name] for name in substantive}
    if _bytes(substantive) != _bytes(expected):
        raise FloorRefused("canonical substantive transcript differs")
    return _write(
        sub,
        REPRO_KIND,
        {
            "floor_hash": floor_hash,
            "hunt_hash": result.run_hash,
            "repro_records": records,
            "rerun_attempts": reruns,
            "passed": True,
            "substantive_hash": blob_hash(_bytes(substantive)),
            "substantive_bytes": len(_bytes(substantive)),
            "independent_sample": False,
        },
        (floor_hash, result.run_hash, *records),
    )
