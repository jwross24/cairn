import copy
import dataclasses
import os
import sys
import tempfile
from pathlib import Path
from uuid import uuid4

from cairn import (
    allowlist,
    bundle,
    claims,
    instances,
    ladder,
    ladderplan,
    laddertable,
    selftest,
    selftest_skills,
    substrate,
)
from cairn.skills import rho_dp

FIXTURE = "ladder_selftest"
FIXTURE_FIELDS = (
    "fit_bits",
    "fit_trials",
    "hold_out_bits",
    "hold_out_trials",
    "hold_out_m",
    "budget_remaining",
    "instance_maker_ceiling_multiplier",
)
FIXTURE_VALUES = {
    "fit_bits": 30,
    "fit_trials": 100,
    "hold_out_bits": 40,
    "hold_out_trials": 1,
    "hold_out_m": 1,
    "budget_remaining": 10000,
    "instance_maker_ceiling_multiplier": 60,
}
EXPECT_METHOD_IDENTITY_REFUSAL = f"LadderRefused({ladder.METHOD_IDENTITY_MISMATCH})"
EXPECT_BASELINE_VERDICT = f"{laddertable.INCONCLUSIVE}/{laddertable.UNCOUNTED_BACKEND}"
RUN_PREFIX = "gate-ladder-selftest"


class SelftestFixtureInvalid(ValueError):
    def __init__(self, reason):
        self.reason = reason
        super().__init__(reason)


def _configuration(fixtures):
    raw = fixtures.get(FIXTURE)
    if not isinstance(raw, dict):
        raise SelftestFixtureInvalid(f"fixture-absent:{FIXTURE}")
    if set(raw) != set(FIXTURE_FIELDS):
        missing = sorted(set(FIXTURE_FIELDS) - set(raw))
        extra = sorted(set(raw) - set(FIXTURE_FIELDS))
        raise SelftestFixtureInvalid(f"fixture-fields-invalid:{FIXTURE}:missing={missing}:extra={extra}")
    for field, expected in FIXTURE_VALUES.items():
        value = raw[field]
        if type(value) is not type(expected) or value != expected:
            raise SelftestFixtureInvalid(f"fixture-value-invalid:{FIXTURE}.{field}:{value!r}")
    return dict(raw)


def _fixture_plan(gate_bundle, sub, fixtures, runtime):
    cached = runtime.get("ladder_fixture_plan")
    if cached is not None:
        return cached
    config = _configuration(fixtures)
    try:
        source = gate_bundle.object(ladderplan.KIND)
        production_plan_hash = gate_bundle.digest_of(ladderplan.KIND)
        raw = copy.deepcopy(source)
    except bundle.BundleError as exc:
        raise SelftestFixtureInvalid(f"ladder-plan-absent:{exc}") from None
    selected = {}
    for bits in (config["fit_bits"], config["hold_out_bits"]):
        matches = [rung for rung in raw.get("rungs", ()) if isinstance(rung, dict) and rung.get("bits") == bits]
        if len(matches) != 1 or matches[0].get("role") != ladderplan.ROLE_FIT:
            raise SelftestFixtureInvalid(f"measured-fit-rung-absent:{bits}")
        selected[bits] = copy.deepcopy(matches[0])
    baseline = copy.deepcopy(raw.get("baseline"))
    expected_identity = {
        "interface_version": rho_dp.INTERFACE_VERSION,
        "params": {"variant": rho_dp.VARIANT_PLAIN, "r": str(rho_dp.R)},
    }
    if not isinstance(baseline, dict) or baseline.get("skill") != "rho_dp":
        raise SelftestFixtureInvalid("baseline-skill-mismatch")
    if baseline.get("method_identity") != expected_identity:
        raise SelftestFixtureInvalid("baseline-method-identity-mismatch")
    if baseline.get("implementation_revision") != rho_dp.implementation_revision():
        raise SelftestFixtureInvalid("baseline-implementation-revision-mismatch")
    fit = selected[config["fit_bits"]]
    fit["trials"] = config["fit_trials"]
    hold_out = selected[config["hold_out_bits"]]
    hold_out["role"] = ladderplan.ROLE_HOLD_OUT
    hold_out["trials"] = config["hold_out_trials"]
    raw["rungs"] = [fit, hold_out]
    raw["hold_out_m"] = config["hold_out_m"]
    canonical = bundle.canonical_bytes(ladderplan.KIND, raw)
    digest = substrate.blob_hash(canonical)
    if digest == production_plan_hash:
        raise SelftestFixtureInvalid("fixture-plan-hash-is-production-plan")
    if sub.put_blob(canonical) != digest or sub.get_blob(digest) != canonical:
        raise SelftestFixtureInvalid("fixture-plan-blob-mismatch")
    tiers = gate_bundle.tiers
    ceiling = tiers.get("ceiling_multiplier") if isinstance(tiers, dict) else None
    try:
        plan = ladderplan.LadderPlan.load(
            raw,
            tiers_ceiling=ceiling,
            plan_hash=digest,
            bundle_hash=gate_bundle.hash,
        )
    except ladderplan.LadderPlanInvalid as exc:
        raise SelftestFixtureInvalid(f"fixture-plan-invalid:{exc.reason}") from None
    if plan.hash != digest or plan.bundle_hash != gate_bundle.hash:
        raise SelftestFixtureInvalid("fixture-plan-binding-mismatch")
    if plan.baseline.implementation_revision != baseline["implementation_revision"]:
        raise SelftestFixtureInvalid("fixture-baseline-revision-changed")
    if (
        plan.rung(config["fit_bits"]).role != ladderplan.ROLE_FIT
        or plan.rung(config["fit_bits"]).trials != 100
        or plan.hold_out_rung.bits != config["hold_out_bits"]
        or plan.hold_out_rung.trials != 1
        or plan.hold_out_m != 1
    ):
        raise SelftestFixtureInvalid("fixture-plan-selection-mismatch")
    result = (plan, raw, digest, config)
    runtime["ladder_fixture_plan"] = result
    return result


def _certify(sub, gate_bundle, runtime):
    cached = runtime.get("ladder_selftest_certifications")
    if cached is not None:
        return cached
    config = gate_bundle.verifier_config()
    certified = {}
    for which in (selftest_skills.RHO_DP, selftest_skills.INSTANCE_MAKER):
        result = selftest_skills.certify(sub, config, which)
        identity_hash = result["identity_bundle_hash"]
        if not sub.certified(identity_hash):
            raise SelftestFixtureInvalid(f"certificate-absent:{which}")
        certified[which] = result
    runtime["ladder_selftest_certifications"] = certified
    return certified


def _hypothesis(plan, config):
    return claims.HypothesisObject(
        target_family="gate_plan_fixture",
        claimed={"model": rho_dp.COST_PROFILE.production.model},
        method_identity=plan.baseline.method_identity,
        declared_parameter_ranges={"bits": [config["fit_bits"], config["hold_out_bits"]]},
        sampling_distribution=None,
    )


def _run_context(gate_bundle, sub, plan, plan_hash, hypothesis, run_id, scratch_root, arms, *, attest_path=None):
    claims.write_hypothesis_object(sub, hypothesis)
    _, nonce = ladder.commit_entropy(sub, hypothesis_hash=hypothesis.hash, run_id=run_id)
    allow_scratch = scratch_root / f"allow-{run_id}"
    allow_scratch.mkdir()
    hypothesis_value = {
        "target_family": hypothesis.target_family,
        "claimed": hypothesis.claimed,
        "method_identity": hypothesis.method_identity,
        "declared_parameter_ranges": hypothesis.declared_parameter_ranges,
        "sampling_distribution": hypothesis.sampling_distribution,
    }
    allow = allowlist.instantiate(
        gate_bundle,
        hypothesis=hypothesis_value,
        counted_object=os.path.realpath(sys.executable),
        scratch_dir=allow_scratch,
    )
    values = {}
    for arm in arms:
        values[arm] = ladder.dispatch(
            sub,
            gate_bundle,
            plan=plan,
            plan_hash=plan_hash,
            hypothesis_hash=hypothesis.hash,
            nonce=nonce.nonce,
            run_id=run_id,
            arm=arm,
            skill=rho_dp.__name__,
            allow_list=allow,
            attest_path=attest_path,
        )
    return hypothesis, nonce, allow, values


def _scratch_root(sub):
    root = Path(tempfile.mkdtemp(prefix="cairn-ladder-selftest-", dir=Path(sub.path).parent)).resolve()
    (root / "runs").mkdir()
    return root


def _reasons_for_certificates(certifications):
    return tuple(
        f"certificate:{which}:{result['identity_bundle_hash']}:{result['transcript_hash']}"
        for which, result in sorted(certifications.items())
    )


def _fixture_failure(exc):
    reason = getattr(exc, "reason", str(exc))
    return f"SelftestRefused({reason})", (reason,), (None, None)


def method_identity_refusal(gate_bundle, sub, attest_path, fixtures, runtime):
    try:
        plan, _, plan_hash, config = _fixture_plan(gate_bundle, sub, fixtures, runtime)
        certifications = _certify(sub, gate_bundle, runtime)
        hypothesis = _hypothesis(plan, config)
        run_id = f"{RUN_PREFIX}-method-{uuid4().hex}"
        scratch_root = _scratch_root(sub)
        try:
            _, _, _, dispatches = _run_context(
                gate_bundle,
                sub,
                plan,
                plan_hash,
                hypothesis,
                run_id,
                scratch_root,
                (ladder.CLAIMANT,),
                attest_path=attest_path,
            )
        except ladder.RunRefused as refusal:
            return f"SelftestRefused(dispatch-{refusal.reason})", (f"dispatch-refusal:{refusal.reason}",), (None, None)
        dispatch = dispatches[ladder.CLAIMANT]
        identity = copy.deepcopy(dispatch.method_identity)
        identity["params"]["r"] = str(int(identity["params"]["r"]) + 1)
        candidate = dataclasses.replace(dispatch, method_identity=identity)
        reasons = (
            f"fixture-plan:{plan_hash}",
            f"dispatch:{dispatch.hash}",
            f"candidate:{candidate.hash}",
            *_reasons_for_certificates(certifications),
        )
        try:
            ladder.check_dispatch(sub, gate_bundle, candidate, plan, attest_path=attest_path)
        except ladder.RunRefused as refusal:
            observed = f"LadderRefused({refusal.reason})"
            return observed, (*reasons, f"refusal:{refusal.reason}"), (None, None)
        return "admitted", (*reasons, "method-identity-mismatch-not-refused"), (None, None)
    except (SelftestFixtureInvalid, bundle.BundleError, selftest.SelftestFailed) as exc:
        return _fixture_failure(exc)


def _expected_memberships(plan):
    return {
        (arm, rung.bits, trial) for rung in plan.rungs for arm in ladder.arms_for(rung) for trial in range(rung.trials)
    }


def _validate_table(sub, gate_bundle, plan, plan_hash, table, arm_trials, certifications):
    expected = _expected_memberships(plan)
    actual = {(trial.arm, trial.bits, trial.trial) for trial in table.trials}
    if len(expected) != 301 or len(table.trials) != 301 or actual != expected or len(actual) != 301:
        raise SelftestFixtureInvalid("table-trial-membership-mismatch")
    if len(arm_trials) != 301:
        raise SelftestFixtureInvalid(f"executed-trial-count-mismatch:{len(arm_trials)}")
    if table.plan_hash != plan_hash or table.gate_bundle_hash != gate_bundle.hash:
        raise SelftestFixtureInvalid("table-plan-binding-mismatch")
    if table.method_identity != plan.baseline.method_identity:
        raise SelftestFixtureInvalid("table-method-identity-mismatch")
    if table.implementation_revision != plan.baseline.implementation_revision:
        raise SelftestFixtureInvalid("table-baseline-revision-mismatch")
    if table.uncounted_backend != os.path.realpath(sys.executable):
        raise SelftestFixtureInvalid("table-uncounted-backend-mismatch")
    if any(
        trial.gate_ops.kind != laddertable.OPS_UNKNOWN or trial.gate_ops.value is not None for trial in table.trials
    ):
        raise SelftestFixtureInvalid("table-has-unsupported-operation-counts")
    if any(trial.output_complete and not trial.recovered for trial in table.trials):
        raise SelftestFixtureInvalid("completed-output-witness-invalid")
    grouped = {}
    for trial in table.trials:
        grouped.setdefault((trial.bits, trial.trial), []).append(trial)
    for trials in grouped.values():
        if len({trial.instance_hash for trial in trials}) != 1:
            raise SelftestFixtureInvalid("trial-arms-use-different-instances")
        if len({trial.seed for trial in trials}) != len(trials):
            raise SelftestFixtureInvalid("trial-arms-share-a-seed")
    stored = laddertable.read(sub, table.hash)
    if stored is None or stored.hash != table.hash or stored.trials != table.trials or stored.rungs != table.rungs:
        raise SelftestFixtureInvalid("stored-table-mismatch")
    if stored.plan_hash != plan_hash:
        raise SelftestFixtureInvalid("stored-table-plan-hash-mismatch")
    nonce_trials = instances.trials_for(sub, table.nonce)
    expected_instances = {(bits, trial) for _, bits, trial in expected}
    actual_instances = {(trial["bits"], trial["trial"]) for trial in nonce_trials}
    if len(nonce_trials) != 101 or actual_instances != expected_instances:
        raise SelftestFixtureInvalid("instance-stream-membership-mismatch")
    computed = laddertable.verdict(stored, plan)
    recorded = laddertable.recorded_verdict(sub, table.hash)
    if recorded is None:
        raise SelftestFixtureInvalid("recorded-verdict-absent")
    if (computed.kind, computed.predicate) != (laddertable.INCONCLUSIVE, laddertable.UNCOUNTED_BACKEND):
        raise SelftestFixtureInvalid(f"unexpected-computed-verdict:{computed.kind}/{computed.predicate}")
    if (recorded.kind, recorded.predicate) != (computed.kind, computed.predicate):
        raise SelftestFixtureInvalid("recorded-verdict-mismatch")
    if not all(sub.certified(result["identity_bundle_hash"]) for result in certifications.values()):
        raise SelftestFixtureInvalid("certificate-lost")
    return stored, recorded


def baseline_run(gate_bundle, sub, attest_path, fixtures, runtime):
    try:
        plan, _, plan_hash, config = _fixture_plan(gate_bundle, sub, fixtures, runtime)
        certifications = _certify(sub, gate_bundle, runtime)
        hypothesis = _hypothesis(plan, config)
        run_id = f"{RUN_PREFIX}-baseline-{uuid4().hex}"
        scratch_root = _scratch_root(sub)
        _, nonce, _, _ = _run_context(
            gate_bundle,
            sub,
            plan,
            plan_hash,
            hypothesis,
            run_id,
            scratch_root,
            ladderplan.ARMS,
            attest_path=attest_path,
        )
        table, arm_trials = ladder.run(
            sub,
            gate_bundle,
            plan=plan,
            plan_hash=plan_hash,
            run_id=run_id,
            hypothesis_hash=hypothesis.hash,
            nonce=nonce.nonce,
            scratch_root=scratch_root / "runs",
            budget_remaining=float(config["budget_remaining"]),
            attest_path=attest_path,
            ceiling_multiplier=config["instance_maker_ceiling_multiplier"],
            ops_counter=None,
        )
        stored, recorded = _validate_table(
            sub,
            gate_bundle,
            plan,
            plan_hash,
            table,
            arm_trials,
            certifications,
        )
    except ladder.RunRefused as refusal:
        return f"LadderRefused({refusal.reason})", (f"refusal:{refusal.reason}",), (None, None)
    except (SelftestFixtureInvalid, bundle.BundleError, selftest.SelftestFailed, laddertable.LadderTableError) as exc:
        return _fixture_failure(exc)
    return (
        f"{recorded.kind}/{recorded.predicate}",
        (
            f"table:{stored.hash}",
            f"predicate:{recorded.predicate}",
            f"fixture-plan:{plan_hash}",
            f"trials:{len(stored.trials)}",
            *_reasons_for_certificates(certifications),
        ),
        (None, None),
    )
