"""Ladder run engine: pre-registration order, dispatch records, arms on one instance stream.

The order check is this module's: `instances` records the nonce it is handed, and only a
caller that wrote the entropy commitment before drawing can show the hypothesis object
came first. Both positions are read off `nodes.rowid`, the substrate's append order.

A method seed is drawn from the run's nonce under an arm-separated hypothesis key, so an
arm's seed is fixed before the method sees the instance and no two arms share a walk.
"""

import importlib
import json
import statistics
from dataclasses import asdict, dataclass
from decimal import Decimal
from uuid import uuid4

from cairn import (
    allowlist,
    bundle,
    canon,
    claims,
    cli,
    instances,
    keys,
    ladderplan,
    laddertable,
    log,
    runner,
    substrate,
    tiergate,
    verifier,
)
from cairn.substrate import node_hash_for

lg = log.get("ladder")

LOG_STEP = "ladder"
KIND = "ladder_dispatch"
COMMITMENT_KIND = "ladder_entropy_commitment"
TABLE = "ladder_dispatches"

CLAIMANT = ladderplan.ARMS[0]
BASELINE = ladderplan.ARMS[1]
BASELINE_AA = ladderplan.ARMS[2]
RUNG_TIER = tiergate.LADDER_RUNG_TIER
COMMITMENT_SCHEMA = canon.Map(canon.STR, canon.STR)

HYPOTHESIS_ABSENT = "hypothesis-absent"
COMMITMENT_ABSENT = "entropy-commitment-absent"
HYPOTHESIS_AFTER_ENTROPY = "hypothesis-after-entropy"
NONCE_ABSENT = "nonce-absent"
NONCE_FOREIGN = "nonce-names-another-hypothesis"
NONCE_PUBLISHED = "nonce-published"
ARM_UNKNOWN = "arm-unknown"
METHOD_IDENTITY_MISMATCH = "method-identity-mismatch"
BASELINE_REVISION_MISMATCH = "baseline-revision-mismatch"
UNCERTIFIED_REVISION = "uncertified-revision"
YANKED_REVISION = "yanked-revision"
ALLOW_LIST_UNBOUND = "allow-list-unbound"
PRE_SPAWN_REASONS = (
    HYPOTHESIS_ABSENT,
    COMMITMENT_ABSENT,
    HYPOTHESIS_AFTER_ENTROPY,
    NONCE_ABSENT,
    NONCE_FOREIGN,
    NONCE_PUBLISHED,
    ARM_UNKNOWN,
    METHOD_IDENTITY_MISMATCH,
    BASELINE_REVISION_MISMATCH,
    UNCERTIFIED_REVISION,
    YANKED_REVISION,
    ALLOW_LIST_UNBOUND,
)

ARMS_MISSING = "arms-missing"
CI_METHOD_UNSUPPORTED = "ci-method-unsupported"
TIER_REFUSED = "tier-refused"
INSTANCE_FAILED = "instance-failed"

OPS_PLACES = Decimal("0.000001")
RATE_PLACES = Decimal("0.000001")
RATIO_PLACES = Decimal("0.000001")
SUCCESS_PLACES = Decimal("0.0001")
SECONDS_PLACES = Decimal("0.000001")


class RunRefused(substrate.SubstrateError):
    def __init__(self, reason, detail):
        self.reason = reason
        self.detail = detail
        super().__init__(f"{reason}: {detail}")


def method_seed(nonce, hypothesis_key, arm, bits, trial):
    return instances.trial_seed(nonce, f"{hypothesis_key}/{arm}", bits, trial)


def sequence_position(sub, node_hash):
    row = sub.conn.execute("SELECT rowid FROM nodes WHERE hash = ?", (node_hash,)).fetchone()
    return None if row is None else row["rowid"]


@dataclass(frozen=True)
class Commitment:
    run_id: str
    hypothesis_hash: str
    nonce: str
    at: str

    def as_dict(self):
        return asdict(self)

    @property
    def hash(self):
        return node_hash_for(COMMITMENT_KIND, bundle.canonical_bytes(COMMITMENT_KIND, self.as_dict()))


def commit_entropy(sub, *, hypothesis_hash, run_id, nonce=None, at=None):
    """Write the run's entropy commitment, then draw the nonce it names."""
    value = Commitment(
        run_id=run_id,
        hypothesis_hash=hypothesis_hash,
        nonce=instances.fresh_nonce() if nonce is None else nonce,
        at=cli.now_iso() if at is None else at,
    )
    canonical = bundle.canonical_bytes(COMMITMENT_KIND, value.as_dict())
    with sub._tx():
        sub._put_node(COMMITMENT_KIND, canonical, value.hash, "Replayable", None)
    record = instances.commit_nonce(sub, hypothesis_hash, run_id, value.nonce, at=value.at)
    lg.info("commit_entropy", run_id=run_id, hypothesis_hash=hypothesis_hash, commitment=value.hash)
    return value, record


def commitment_for(sub, nonce):
    rows = sub.conn.execute(
        "SELECT rowid, canonical FROM nodes WHERE kind = ? ORDER BY rowid", (COMMITMENT_KIND,)
    ).fetchall()
    for row in rows:
        data = canon.decode(COMMITMENT_SCHEMA, bytes(row["canonical"]))
        if data["nonce"] == nonce:
            return row["rowid"], Commitment(**data)
    return None, None


@dataclass(frozen=True)
class Dispatch:
    run_id: str
    arm: str
    nonce: str
    hypothesis_hash: str
    method_identity: dict
    skill: str
    implementation_revision: str
    identity_bundle: dict
    identity_bundle_hash: str
    allow_list: dict
    allow_list_hash: str
    gate_bundle_hash: str
    plan_hash: str
    at: str

    def __post_init__(self):
        for name in ("method_identity", "identity_bundle", "allow_list"):
            object.__setattr__(self, name, claims.jsonable(getattr(self, name)))

    def as_dict(self):
        return asdict(self)

    @property
    def hash(self):
        return node_hash_for(KIND, bundle.canonical_bytes(KIND, self.as_dict()))

    @property
    def module(self):
        return importlib.import_module(self.skill)


def expected_identity(plan, arm, hypothesis):
    if arm == CLAIMANT:
        return hypothesis["method_identity"]
    if arm in (BASELINE, BASELINE_AA):
        return plan.baseline.method_identity
    raise RunRefused(ARM_UNKNOWN, f"{arm!r} is no arm of {tuple(ladderplan.ARMS)}")


def _hypothesis(sub, hypothesis_hash):
    row = sub.get_node(hypothesis_hash)
    if row is None or row["kind"] != "hypothesis_object":
        raise RunRefused(HYPOTHESIS_ABSENT, f"no hypothesis object {hypothesis_hash[:12]} is recorded")
    return canon.decode(keys.HYPOTHESIS_OBJECT, bytes(row["canonical"]))


def check_order(sub, *, hypothesis_hash, nonce):
    """The hypothesis object precedes the run's entropy commitment in the substrate's append order."""
    _hypothesis(sub, hypothesis_hash)
    position = sequence_position(sub, hypothesis_hash)
    committed_at, commitment = commitment_for(sub, nonce)
    if commitment is None:
        raise RunRefused(COMMITMENT_ABSENT, f"nonce {nonce[:12]} carries no entropy commitment record")
    if commitment.hypothesis_hash != hypothesis_hash:
        raise RunRefused(NONCE_FOREIGN, f"nonce {nonce[:12]} commits hypothesis {commitment.hypothesis_hash[:12]}")
    if position >= committed_at:
        raise RunRefused(
            HYPOTHESIS_AFTER_ENTROPY,
            f"hypothesis {hypothesis_hash[:12]} sits at record {position}, the commitment at {committed_at}",
        )
    record = instances.get_nonce(sub, nonce)
    if record is None:
        raise RunRefused(NONCE_ABSENT, f"no nonce {nonce[:12]} is recorded")
    if record.hypothesis_key != hypothesis_hash:
        raise RunRefused(NONCE_FOREIGN, f"nonce {nonce[:12]} is drawn for {record.hypothesis_key[:12]}")
    if not record.withheld:
        raise RunRefused(NONCE_PUBLISHED, f"nonce {nonce[:12]} is published at {record.published_at}")
    return commitment


def _allow_list(dispatch):
    data = dispatch.allow_list
    return allowlist.AllowList(
        template_name=data["template_name"],
        template_hash=data["template_hash"],
        bundle_hash=data["bundle_hash"],
        mechanism=data["mechanism"],
        counted_object=data["counted_object"],
        declared_backends=tuple(data["declared_backends"]),
        exec_paths=tuple(data["exec_paths"]),
        network_egress=data["network_egress"],
        writable_root=data["writable_root"],
        profile_hash=data["profile_hash"],
    )


def check_dispatch(sub, gate_bundle, dispatch, plan):
    """Every refusal this dispatch can earn, before a trial spawns anything."""
    hypothesis = _hypothesis(sub, dispatch.hypothesis_hash)
    check_order(sub, hypothesis_hash=dispatch.hypothesis_hash, nonce=dispatch.nonce)
    expected = expected_identity(plan, dispatch.arm, hypothesis)
    if dispatch.method_identity != expected:
        raise RunRefused(
            METHOD_IDENTITY_MISMATCH,
            f"arm {dispatch.arm} dispatches {dispatch.method_identity} against registered {expected}",
        )
    if dispatch.arm != CLAIMANT and dispatch.implementation_revision != plan.baseline.implementation_revision:
        raise RunRefused(
            BASELINE_REVISION_MISMATCH,
            f"arm {dispatch.arm} runs revision {dispatch.implementation_revision[:12]}, "
            f"the plan registers {plan.baseline.implementation_revision[:12]}",
        )
    if dispatch.identity_bundle_hash != keys.identity_bundle_hash(dispatch.identity_bundle):
        raise RunRefused(UNCERTIFIED_REVISION, "the dispatched identity bundle does not hash to its named hash")
    if dispatch.identity_bundle["implementation_revision"] != dispatch.implementation_revision:
        raise RunRefused(UNCERTIFIED_REVISION, "the dispatched identity bundle names another implementation revision")
    if not sub.certified(dispatch.identity_bundle_hash):
        raise RunRefused(
            UNCERTIFIED_REVISION, f"skill identity {dispatch.identity_bundle_hash[:12]} carries no certificate"
        )
    if sub.yanked(dispatch.identity_bundle_hash):
        raise RunRefused(YANKED_REVISION, f"skill identity {dispatch.identity_bundle_hash[:12]} is yanked")
    if dispatch.allow_list.get("bundle_hash") != gate_bundle.hash:
        raise RunRefused(ALLOW_LIST_UNBOUND, "the instantiated allow-list names another gate bundle")
    if not allowlist.check_instantiation(_allow_list(dispatch), gate_bundle):
        raise RunRefused(ALLOW_LIST_UNBOUND, "the instantiated allow-list does not match the bundle template")
    return dispatch


def dispatch(sub, gate_bundle, *, plan, plan_hash, hypothesis_hash, nonce, run_id, arm, skill, allow_list, at=None):
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
    check_dispatch(sub, gate_bundle, value, plan)
    return write_dispatch(sub, value)


def write_dispatch(sub, value):
    canonical = bundle.canonical_bytes(KIND, value.as_dict())
    with sub._tx():
        sub._put_node(KIND, canonical, value.hash, "Replayable", None)
        sub.conn.execute(
            f"INSERT INTO {TABLE} (dispatch_id, record_hash, run_id, arm, nonce, hypothesis_hash,"
            " implementation_revision, allow_list_hash, gate_bundle_hash, plan_hash, record_json)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                str(uuid4()),
                value.hash,
                value.run_id,
                value.arm,
                value.nonce,
                value.hypothesis_hash,
                value.implementation_revision,
                value.allow_list_hash,
                value.gate_bundle_hash,
                value.plan_hash,
                json.dumps(value.as_dict(), sort_keys=True, separators=(",", ":")),
            ),
        )
        sub._add_root("ledger_row", value.hash)
    lg.info("dispatch", run_id=value.run_id, arm=value.arm, record=value.hash)
    return value


def dispatches_for(sub, run_id):
    rows = sub.conn.execute(f"SELECT record_json FROM {TABLE} WHERE run_id = ? ORDER BY rowid", (run_id,)).fetchall()
    return {d.arm: d for d in (Dispatch(**json.loads(row["record_json"])) for row in rows)}


def _recipe(value, seed, salt):
    identity = value.identity_bundle
    return {
        "skill_identity_hash": value.identity_bundle_hash,
        "inputs": {},
        "seed": seed,
        "tool_versions": dict(identity["tool_digests"]),
        "container_digest": identity["container_digest"],
        "salt": salt,
    }


def _quantize(value, places):
    return str(Decimal(value).quantize(places))


def _ceiling_ops(module, bits, multiplier):
    cost = module.COST_PROFILE.production.per_size[bits]
    ceiling_s = runner.ceiling_for(module.COST_PROFILE.evaluate(bits).expected_wall_s, multiplier)
    return int(ceiling_s / cost.per_try_s)


def _reference_rate(module, bits):
    return Decimal(1) / Decimal(str(module.COST_PROFILE.production.per_size[bits].per_try_s))


@dataclass(frozen=True)
class ArmTrial:
    arm: str
    bits: int
    trial: int
    seed: int
    status: str
    ops: int
    recovered: bool
    completed: bool
    cpu_seconds: str
    wall_seconds: str
    peak_rss_bytes: int
    scratch_bytes: int
    reported_memory_bytes: int
    replay_grade: str
    measurement_scope: str
    attempt_id: str
    instance_hash: str


def _receipt_scratch(sub, attempt):
    if attempt.receipt_hash is None:
        return 0
    row = sub.get_receipt(attempt.receipt_hash)
    return 0 if row is None else int(row["scratch_bytes_written"])


def _admit(sub, gate_bundle, value, *, bits, seed, budget_remaining):
    launch = tiergate.Launch(
        cost_profile=value.module.COST_PROFILE,
        inputs={"bits": bits, "seed": seed},
        budget_remaining=budget_remaining,
        hypothesis_key=value.hypothesis_hash,
        method_identity=value.method_identity,
        skill_identity_hash=value.identity_bundle_hash,
        declared_tier=RUNG_TIER,
    )
    decision = tiergate.TierGate(sub, gate_bundle).admit(launch)
    if isinstance(decision, tiergate.TierRefused):
        raise RunRefused(TIER_REFUSED, f"arm {value.arm} at {bits} bits: {', '.join(decision.reasons)}")
    return decision


def run_arm(sub, gate_bundle, value, *, plan, instance, instance_hash, bits, trial, scratch_root, budget_remaining):
    module = value.module
    seed = method_seed(value.nonce, value.hypothesis_hash, value.arm, bits, trial)
    _admit(sub, gate_bundle, value, bits=bits, seed=seed, budget_remaining=budget_remaining)
    fields = instance.as_dict()
    document = {"bits": bits, "seed": seed, **{name: str(fields[name]) for name in ("p", "a", "b", "n")}}
    document["P"] = [str(c) for c in fields["P"]]
    document["Q"] = [str(c) for c in fields["Q"]]
    if module.INPUTS is not None and any(f.name == "negation_map" for f in module.INPUTS.fields):
        document["negation_map"] = False
    attempt = runner.launch(
        sub,
        value.skill,
        _recipe(value, seed, f"ladder/{value.run_id}/{value.arm}/{bits}/{trial}"),
        bundle_hash=gate_bundle.hash,
        evaluation=module.COST_PROFILE.evaluate(bits),
        ceiling_multiplier=plan.patience_multiplier,
        wall_cap_multiplier=gate_bundle.tiers["wall_cap_multiplier"],
        wall_cap_floor_s=gate_bundle.tiers["wall_cap_floor_s"],
        tool_digests=value.identity_bundle["tool_digests"],
        scratch_root=scratch_root,
        replay=module.REPLAY_GRADE,
        skip_cache_lookup=True,
        do_not_cache=True,
        stdin_document=document,
    )
    launch = attempt.launch
    parsed = attempt.parsed.document if attempt.parsed is not None else {}
    completed = attempt.status == runner.STATUS_OK and bool(parsed)
    ops = int(parsed.get("ops", 0)) if completed else _ceiling_ops(module, bits, plan.patience_multiplier)
    solved = int(parsed["x"]) if completed and "x" in parsed else None
    recovered = False
    if solved is not None:
        recovered = verifier.Verifier(gate_bundle.verifier_config()).run(instance, solved).accepted
    memory = parsed.get("memory") or {}
    return ArmTrial(
        arm=value.arm,
        bits=bits,
        trial=trial,
        seed=seed,
        status=attempt.status,
        ops=ops,
        recovered=recovered,
        completed=completed,
        cpu_seconds=_quantize(str(launch.cpu_user_s + launch.cpu_sys_s), SECONDS_PLACES) if launch else "0",
        wall_seconds=_quantize(str(launch.wall_s), SECONDS_PLACES) if launch else "0",
        peak_rss_bytes=launch.peak_rss_bytes if launch else 0,
        scratch_bytes=_receipt_scratch(sub, attempt),
        reported_memory_bytes=int(memory.get("table_bytes", 0)),
        replay_grade=module.REPLAY_GRADE,
        measurement_scope=launch.measurement_scope if launch else runner.SCOPE_UNSAMPLED,
        attempt_id=attempt.attempt_id,
        instance_hash=instance_hash,
    )


def _z(coverage):
    return Decimal(str(statistics.NormalDist().inv_cdf(float(1 - (1 - coverage) / 2))))


def _speedup_ci(plan, claim, base):
    if plan.comparison.ci_method != ladderplan.CI_METHODS[0]:
        raise RunRefused(CI_METHOD_UNSUPPORTED, f"ci method {plan.comparison.ci_method} is not built")
    ratios = [Decimal(b.ops) / Decimal(c.ops) for c, b in zip(claim, base, strict=True) if c.ops]
    if len(ratios) < 2:
        return None, None
    mean = sum(ratios) / Decimal(len(ratios))
    variance = sum((r - mean) ** 2 for r in ratios) / Decimal(len(ratios) - 1)
    half = _z(plan.comparison.ci_coverage) * (variance / Decimal(len(ratios))).sqrt()
    return _quantize(mean - half, RATIO_PLACES), _quantize(mean + half, RATIO_PLACES)


def _rung_row(plan, rung, module, claim, arms):
    ops = [Decimal(t.ops) for t in claim]
    count = len(ops)
    mean = sum(ops) / Decimal(count)
    sd = (sum((v - mean) ** 2 for v in ops) / Decimal(count - 1)).sqrt() if count >= 2 else Decimal(0)
    successes = sum(1 for t in claim if t.completed and t.recovered)
    prediction = Decimal(str(module.COST_PROFILE.production.per_size[rung.bits].mean_tries))
    low, high = (None, None)
    if arms.get(BASELINE):
        low, high = _speedup_ci(plan, claim, arms[BASELINE])
    return laddertable.RungRow(
        bits=rung.bits,
        role=rung.role,
        trials=count,
        mean_ops=_quantize(mean, OPS_PLACES),
        sd_ops=_quantize(sd, OPS_PLACES),
        cpu_seconds=_quantize(sum(Decimal(t.cpu_seconds) for t in claim), SECONDS_PLACES),
        reference_rate=_quantize(_reference_rate(module, rung.bits), RATE_PLACES),
        memory_bytes=max(t.reported_memory_bytes for t in claim),
        success_rate=_quantize(Decimal(successes) / Decimal(count), SUCCESS_PLACES),
        radius=str(plan.design_radius),
        claim_ci_low=low,
        claim_ci_high=high,
        model_prediction=_quantize(prediction, OPS_PLACES),
        model_band=str(plan.design_radius),
        shape_statistic=_quantize(mean / prediction, RATIO_PLACES),
        declared_shape=module.COST_PROFILE.production.model,
    )


def _trial_row(claim):
    return laddertable.Trial(
        bits=claim.bits,
        trial=claim.trial,
        seed=claim.seed,
        instance_hash=claim.instance_hash,
        recovered=claim.recovered,
        completed=claim.completed,
        gate_ops=claim.ops,
        reported_ops=claim.ops,
        cpu_seconds=claim.cpu_seconds,
        wall_seconds=claim.wall_seconds,
        peak_rss_bytes=claim.peak_rss_bytes,
        scratch_bytes=claim.scratch_bytes,
        reported_memory_bytes=claim.reported_memory_bytes,
        replay_grade=claim.replay_grade,
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
    ceiling_multiplier=None,
    ops_counter=None,
    at=None,
):
    """One ladder run: every rung, every trial, every arm on the gate's instance stream."""
    records = dispatches_for(sub, run_id)
    missing = [arm for arm in ladderplan.ARMS if arm not in records]
    if missing:
        raise RunRefused(ARMS_MISSING, f"run {run_id} holds no dispatch for {', '.join(missing)}")
    for value in records.values():
        check_dispatch(sub, gate_bundle, value, plan)
    claimant = records[CLAIMANT]

    rungs, trials, arm_trials = [], [], []
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
                budget_remaining=budget_remaining,
                ceiling_multiplier=ceiling_multiplier,
            )
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
                        budget_remaining=budget_remaining,
                    )
                )
        claim = by_arm[CLAIMANT]
        rungs.append(_rung_row(plan, rung, claimant.module, claim, by_arm))
        trials.extend(_trial_row(t) for t in claim)
        for values in by_arm.values():
            arm_trials.extend(values)

    table = laddertable.ResultTable(
        run_id=run_id,
        nonce=nonce,
        hypothesis_hash=hypothesis_hash,
        method_identity=claimant.method_identity,
        implementation_revision=claimant.implementation_revision,
        gate_bundle_hash=gate_bundle.hash,
        plan_hash=plan_hash,
        uncounted_backend=None if ops_counter is not None else claimant.allow_list["counted_object"],
        rungs=tuple(rungs),
        trials=tuple(trials),
        created_at=cli.now_iso() if at is None else at,
    )
    if ops_counter is not None:
        table = _counted(table, ops_counter)
    laddertable.write(sub, table, plan)
    lg.info("run", run_id=run_id, table=table.hash, rungs=len(rungs), trials=len(trials))
    return table, tuple(arm_trials)


def _counted(table, ops_counter):
    import dataclasses

    counted = tuple(dataclasses.replace(t, gate_ops=ops_counter(t)) for t in table.trials)
    return dataclasses.replace(table, trials=counted)
