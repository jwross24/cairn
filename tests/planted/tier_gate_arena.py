import dataclasses
import json
import os
import sys
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import _substrate_helpers as helpers
import factories

from cairn import (
    attest,
    bundle,
    claims,
    human_authority,
    hunt,
    ladderplan,
    laddertable,
    repro,
    runner,
    substrate,
    ticketlattice,
    tiergate,
)
from cairn.profile import CostProfile, Production, SizeCost, Verification

OWNER = "cairn-m1-cqt.3.5"
FAMILY = "tier_gate"
REJECT = "REJECT"
ADMIT = "ADMIT"
ACCEPT = "ACCEPT"
AT = "2026-10-20T00:00:00.000000+00:00"
METHOD = {"interface_version": "toy_curve/1", "params": {"r": "20"}}
OTHER_METHOD = {"interface_version": "toy_curve/2", "params": {"r": "20"}}
REVISION = "aa" * 32
FIT_BITS = 50
HOLD_OUT_BITS = 60
BUDGET_PLENTY = 10_000_000.0
CHEAP_CORE_S = 0.01
TIER_TWO_CORE_S = 4000.0

TRIAL_BASE = laddertable.Trial(
    arm=ladderplan.ARMS[0],
    bits=0,
    trial=0,
    seed=1,
    instance_hash="aa" * 32,
    status=runner.STATUS_OK,
    output_complete=True,
    recovered=True,
    gate_ops=laddertable.OpsObservation(laddertable.OPS_EXACT, 1000000),
    reported_ops=1000000,
    cpu_seconds="1",
    wall_seconds="1",
    peak_rss_bytes=1000,
    scratch_bytes=1000,
    reported_memory_bytes=1000,
    replay_grade="Replayable",
    measurement_scope=runner.SCOPE_TREE,
)
RUNG_BASE = laddertable.RungRow(
    bits=0,
    role=ladderplan.ROLE_FIT,
    trials=2,
    ops_kind=laddertable.OPS_EXACT,
    mean_ops="1000000",
    sd_ops="0",
    cpu_seconds="1",
    reference_rate="1000000",
    memory_bytes=100000,
    success_rate="1",
    radius="0.1216",
    claim_ci_low="1.5",
    claim_ci_high="1.8",
    model_prediction="1000000",
    model_band="0.05",
    shape_statistic="1",
    declared_shape="stable",
)
TABLE_BASE = laddertable.ResultTable(
    run_id="run-keep",
    nonce="nonce-1",
    hypothesis_hash="aa" * 32,
    method_identity=METHOD,
    implementation_revision=REVISION,
    gate_bundle_hash="cc" * 32,
    plan_hash="dd" * 32,
    uncounted_backend=None,
    rungs=(),
    trials=(),
)


@dataclass(frozen=True)
class Arena:
    sub: object
    bundle: object
    attest_path: str
    plan: object

    @property
    def gate(self):
        return tiergate.TierGate(self.sub, self.bundle, attest_path=self.attest_path)


def arena(cold, *, session=True):
    root = cold.scratch_root
    root.mkdir(parents=True, exist_ok=True)
    path, pin = root / "gate-bundle.sqlite", root / "gate-bundle.pin"
    bundle.build(bundle.REPO_ROOT / "bundle", path)
    bundle.write_pin(path, pin)
    if hasattr(os, "chflags"):
        os.chflags(pin, 0)
    gate_bundle = bundle.GateBundle.open(path, pin)
    attest_path = str(root / "attest.bin")
    attest.init(attest_path, gate_bundle.waiver_target())
    if session:
        opened = datetime.now(UTC)
        human_authority.append(
            cold.sub,
            attest_path,
            human_authority.OPERATOR_SESSION,
            {
                "session_id": "tier-gate-family-session",
                "issued_by": "test-operator",
                "opened_at": opened.isoformat(),
                "expires_at": (opened + timedelta(seconds=3600)).isoformat(),
            },
            gate_bundle_hash=gate_bundle.hash,
        )
    plan = ladderplan.LadderPlan.load(json.loads((bundle.REPO_ROOT / "bundle" / "ladder_plan.json").read_text()))
    return Arena(cold.sub, gate_bundle, attest_path, plan)


def certify(env, identity=None):
    identity_hash = env.sub.put_identity_bundle(identity or helpers.IDENTITY_A)
    env.sub.put_certificate(identity_hash, helpers.TRANSCRIPT_HASH, helpers.ENV_MANIFEST_HASH, helpers.SELFTEST_SUMMARY)
    return identity_hash


def hypothesis(env, *, marker=None, family="toy_curve"):
    claimed = {"kind": "cost_model", "exponent": "0.5", "constant": "1", "crossover": "30"}
    if marker is not None:
        claimed["correctness_conjecture"] = marker
    obj = factories.hypothesis_object(family=family, claimed=claimed, method_identity=METHOD)
    claims.write_hypothesis_object(env.sub, obj)
    return obj.hash


def keep_table(env, hypothesis_key, *, revision=REVISION, hold_out=True, run_id="run-keep"):
    sizes = [30, 40, FIT_BITS] + ([HOLD_OUT_BITS] if hold_out else [])
    table = dataclasses.replace(
        TABLE_BASE,
        run_id=run_id,
        hypothesis_hash=hypothesis_key,
        implementation_revision=revision,
        rungs=tuple(
            dataclasses.replace(
                RUNG_BASE, bits=b, role=ladderplan.ROLE_HOLD_OUT if b == HOLD_OUT_BITS else ladderplan.ROLE_FIT
            )
            for b in sizes
        ),
        trials=tuple(dataclasses.replace(TRIAL_BASE, bits=b, trial=t) for b in sizes for t in (0, 1)),
    )
    laddertable.write(env.sub, table, env.plan)
    return table


def survived_hunt(env, hypothesis_key, statement_hash, *, trials=2, seed_base=0):
    sub = env.sub
    plan = hunt.HuntPlan(
        statement_hash,
        hypothesis_key,
        hunt.Distribution({"n": (0, trials - 1)}),
        trials,
        {"n": (0, trials - 1)},
        method_identity=METHOD,
    )
    sub.put_node("hunt_plan", hunt.plan_canonical(plan), producer_identity="gate:hunt")
    attempts = [
        helpers.launch(sub, sub.put_recipe(helpers.recipe(seed=seed_base + index + 1)), skip_cache_lookup=True)[0]
        for index in range(trials)
    ]
    survived = tuple(
        hunt.TrialRecord(
            trial=index,
            point={"n": index},
            seed=seed_base + index + 1,
            attempt_id=attempts[index],
            execution_status="OK",
            execution_evidence=f"{index:02d}" * 32,
            outcome="SURVIVED_TRIAL",
            verifier_status="NOT_REQUIRED",
            verifier_evidence=None,
        )
        for index in range(trials)
    )
    record = hunt.HuntRecord(
        plan.hash,
        plan.distribution.hash,
        statement_hash,
        hypothesis_key,
        f"hunt-nonce-{seed_base}",
        trials,
        len(survived),
        "FULL_DECLARED_BUDGET",
        "SURVIVED",
        None,
        True,
        survived,
    )
    run_hash = sub.put_node("hunt_run", hunt.run_canonical(record), producer_identity="gate:hunt")
    evidence_hash = claims.write_evidence_node(
        sub,
        claims.EvidenceNode(
            kind=hunt.KIND,
            target_statement_hash=statement_hash,
            population=factories.scope(),
            assumptions=frozenset({factories.assumption_id("A1")}),
            producer_identity="gate:hunt",
            producer_tag="gate",
            verdict="SURVIVED",
        ),
    )
    sub.add_lineage(evidence_hash, run_hash, substrate.EDGE_INPUT)
    return evidence_hash


def bind_tier_two(env, hypothesis_key, ticket_hash):
    attempt_id = env.sub.start_attempt(env.sub.put_recipe(helpers.recipe(seed=3)), skip_cache_lookup=True)
    claims.write_repro_record(
        env.sub, claims.ReproRecord(attempt_id=attempt_id, kind=repro.WITNESS_CHECK, passed=True, at=AT)
    )
    ticketlattice.bind_attempt(
        env.sub,
        env.bundle,
        attempt_id=attempt_id,
        hypothesis_key=hypothesis_key,
        method_identity=METHOD,
        ticket_hash=ticket_hash,
        tier=2,
        at=AT,
    )


def profile_at(core_s, bits):
    return CostProfile(
        tier=0,
        production=Production(
            model="synthetic",
            per_size={bits: SizeCost(mean_tries=1.0, sd_tries=0.0, per_try_s=core_s, mean_wall_s=core_s)},
        ),
        verification=Verification(grade="Verifiable", cost_model="same_as_production"),
        source="tests/planted/tier_gate_arena.py",
    )


def launch(key, skill, *, tier, bits=HOLD_OUT_BITS, core_s=CHEAP_CORE_S, method=METHOD, statement_hash=None, **kw):
    return tiergate.Launch(
        cost_profile=profile_at(core_s, bits),
        inputs=bits,
        budget_remaining=BUDGET_PLENTY,
        hypothesis_key=key,
        method_identity=method,
        skill_identity_hash=skill,
        declared_tier=tier,
        statement_hash=statement_hash,
        **kw,
    )


def refused_with(decision, *reasons, ticket_tier=None):
    return (
        isinstance(decision, tiergate.TierRefused)
        and set(reasons) <= set(decision.reasons)
        and (ticket_tier is None or decision.ticket_tier == ticket_tier)
    )


def admitted_at(decision, ticket_tier):
    return isinstance(decision, tiergate.Admitted) and decision.ticket_tier == ticket_tier


def verdict(refused):
    return REJECT if refused else ACCEPT
