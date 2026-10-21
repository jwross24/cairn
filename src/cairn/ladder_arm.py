from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

from cairn import allowlist, escrow, laddertable, runner, substrate, tiergate, verifier
from cairn.ladder_commit import _hypothesis, method_seed
from cairn.ladder_dispatch import KIND, _allow_list
from cairn.ladder_refusal import ALLOW_LIST_UNBOUND, SUBSTRATE_READABLE, TIER_REFUSED, RunRefused

RUNG_TIER = tiergate.LADDER_RUNG_TIER

SECONDS_PLACES = Decimal("0.000001")


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


@dataclass(frozen=True)
class ArmTrial:
    arm: str
    bits: int
    trial: int
    seed: int
    status: str
    recovered: bool
    output_complete: bool
    reported_ops: int | None
    gate_ops: laddertable.OpsObservation
    cpu_seconds: str
    wall_seconds: str
    peak_rss_bytes: int
    scratch_bytes: int
    reported_memory_bytes: int
    replay_grade: str
    measurement_scope: str
    attempt_id: str
    instance_hash: str
    allow_list_hash: str | None = None
    writable_root: str | None = None


def _receipt_scratch(sub, attempt):
    if attempt.receipt_hash is None:
        return 0
    row = sub.get_receipt(attempt.receipt_hash)
    return 0 if row is None else int(row["scratch_bytes_written"])


@dataclass
class RunBudget:
    granted_core_s: float
    attempt_ids: list[str] = field(default_factory=list)

    def snapshot(self, sub):
        production = 0.0
        verification = 0.0
        for attempt_id in self.attempt_ids:
            attempt = sub.get_attempt(attempt_id)
            receipt = sub.get_receipt(attempt["receipt_hash"])
            reservation = escrow.reservation(sub, attempt_id)
            if receipt is None or reservation is None:
                raise substrate.SubstrateError(f"run budget cannot reconcile attempt {attempt_id}")
            production += receipt["cpu_user_s"] + receipt["cpu_sys_s"]
            if reservation["released_at"] is None:
                verification += reservation["reserved"]
        return {
            "granted_core_s": self.granted_core_s,
            "production_core_s": production,
            "verification_core_s": verification,
            "budget_remaining_core_s": self.granted_core_s - production - verification,
        }

    def remaining(self, sub):
        return self.snapshot(sub)["budget_remaining_core_s"]


def _admit(sub, gate_bundle, value, *, bits, seed, budget_remaining, attest_path):
    launch = tiergate.Launch(
        cost_profile=value.module.COST_PROFILE,
        inputs={"bits": bits, "seed": seed},
        budget_remaining=budget_remaining,
        hypothesis_key=value.hypothesis_hash,
        method_identity=value.method_identity,
        skill_identity_hash=value.identity_bundle_hash,
        declared_tier=RUNG_TIER,
    )
    decision = tiergate.TierGate(sub, gate_bundle, attest_path=attest_path).admit(launch)
    if isinstance(decision, tiergate.TierRefused):
        raise RunRefused(TIER_REFUSED, f"arm {value.arm} at {bits} bits: {', '.join(decision.reasons)}")
    return decision


def run_arm(
    sub,
    gate_bundle,
    value,
    *,
    plan,
    instance,
    instance_hash,
    bits,
    trial,
    scratch_root,
    budget_remaining,
    attest_path=None,
    backend_paths=None,
):
    module = value.module
    recorded_dispatch = sub.get_node(value.hash)
    if recorded_dispatch is None or recorded_dispatch["kind"] != KIND:
        raise RunRefused(ALLOW_LIST_UNBOUND, "the launch does not name a recorded dispatch")
    recorded_policy = _allow_list(value)
    if recorded_policy.hash != value.allow_list_hash:
        raise RunRefused(ALLOW_LIST_UNBOUND, "the launch allow-list differs from its recorded hash")
    readable = allowlist.unwithheld_store_roots(recorded_policy, sub.path)
    if readable:
        raise RunRefused(SUBSTRATE_READABLE, f"arm {value.arm} would read the substrate through {', '.join(readable)}")
    policy = runner.MethodPolicy(
        gate_bundle=gate_bundle,
        hypothesis=_hypothesis(sub, value.hypothesis_hash),
        allow_list=recorded_policy,
        dispatch_hash=value.hash,
        scratch_root=Path(recorded_policy.writable_root),
        backend_paths=dict(backend_paths or {}),
    )
    seed = method_seed(value.nonce, value.hypothesis_hash, value.arm, bits, trial)
    _admit(
        sub,
        gate_bundle,
        value,
        bits=bits,
        seed=seed,
        budget_remaining=budget_remaining,
        attest_path=attest_path,
    )
    fields = instance.as_dict()
    document = {"bits": bits, "seed": seed, **{name: str(fields[name]) for name in ("p", "a", "b", "n")}}
    document["P"] = [str(c) for c in fields["P"]]
    document["Q"] = [str(c) for c in fields["Q"]]
    if module.INPUTS is not None and any(f.name == "negation_map" for f in module.INPUTS.fields):
        document["negation_map"] = False
    evaluation = module.COST_PROFILE.evaluate(bits)
    attempt = runner.launch(
        sub,
        value.skill,
        _recipe(value, seed, f"ladder/{value.run_id}/{value.arm}/{bits}/{trial}"),
        bundle_hash=gate_bundle.hash,
        evaluation=evaluation,
        ceiling_multiplier=plan.patience_multiplier,
        wall_cap_multiplier=gate_bundle.tiers["wall_cap_multiplier"],
        wall_cap_floor_s=gate_bundle.tiers["wall_cap_floor_s"],
        subprocess_startup_ms=gate_bundle.tiers["subprocess_startup_ms"],
        tool_digests=value.identity_bundle["tool_digests"],
        scratch_root=scratch_root,
        replay=module.REPLAY_GRADE,
        skip_cache_lookup=True,
        do_not_cache=True,
        budget_remaining=budget_remaining - evaluation.expected_verification_core_s,
        stdin_document=document,
        attest_path=attest_path,
        method_policy=policy,
        require_method_policy=True,
    )
    launch = attempt.launch
    parsed = attempt.parsed.document if attempt.parsed is not None else {}
    output_complete = bool(parsed) and "x" in parsed
    reported = parsed.get("ops")
    reported_ops = reported if isinstance(reported, int) and not isinstance(reported, bool) and reported >= 0 else None
    solved = int(parsed["x"]) if output_complete else None
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
        recovered=recovered,
        output_complete=output_complete,
        reported_ops=reported_ops,
        gate_ops=laddertable.OpsObservation(laddertable.OPS_UNKNOWN, None),
        cpu_seconds=_quantize(str(launch.cpu_user_s + launch.cpu_sys_s), SECONDS_PLACES) if launch else "0",
        wall_seconds=_quantize(str(launch.wall_s), SECONDS_PLACES) if launch else "0",
        peak_rss_bytes=launch.peak_rss_bytes if launch else 0,
        scratch_bytes=_receipt_scratch(sub, attempt),
        reported_memory_bytes=int(memory.get("table_bytes", 0)),
        replay_grade=module.REPLAY_GRADE,
        measurement_scope=launch.measurement_scope if launch else runner.SCOPE_UNSAMPLED,
        attempt_id=attempt.attempt_id,
        instance_hash=instance_hash,
        allow_list_hash=attempt.allow_list_hash,
        writable_root=attempt.writable_root,
    )
