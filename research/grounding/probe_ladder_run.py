"""Run one small ladder over the shipped skills and report the patience ceiling it meets.

    uv run python research/grounding/probe_ladder_run.py

Section 1 runs a 30-bit fit rung with the claimant and both baseline arms plus a 40-bit
hold-out rung with the claimant alone, and prints the dispatch rows, the table hash and
every arm trial. Section 2 launches one instance-maker trial under the shipped
`bundle/tiers.json` ceiling multiplier and prints the CPU it spent against the ceiling
that multiplier buys. Exit 0 means the run completed and the ceiling reading was taken.
"""

import dataclasses
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tests"))
import _substrate_helpers as helpers

from cairn import allowlist, bundle, claims, instances, ladder, ladderplan, laddertable, runner
from cairn.skills import bsgs, instance_maker, rho_dp

root = Path(tempfile.mkdtemp())
REPO = Path(__file__).resolve().parents[2]
bundle.build(REPO / "bundle", root / "gate.sqlite")
bundle.write_pin(root / "gate.sqlite", root / "gate.pin")
gate = bundle.GateBundle.open(root / "gate.sqlite", root / "gate.pin")
sub = helpers.open_writer(root)

committed = json.loads((REPO / "bundle" / "ladder_plan.json").read_text())
committed["baseline"]["implementation_revision"] = rho_dp.implementation_revision()
full = ladderplan.LadderPlan.load(committed)
fit = dataclasses.replace(full.rung(30), bits=30, trials=3)
hold_out = dataclasses.replace(full.rung(40), bits=40, role=ladderplan.ROLE_HOLD_OUT, trials=2)
plan = dataclasses.replace(full, rungs=(fit, hold_out), hold_out_m=2, patience_multiplier=60)

obj = claims.HypothesisObject(
    target_family="dlp",
    claimed={"model": "c_sqrt_n_ops"},
    method_identity={"interface_version": bsgs.INTERFACE_VERSION, "params": {}},
    declared_parameter_ranges={"bits": [30, 40]},
    sampling_distribution=None,
)
claims.write_hypothesis_object(sub, obj)
_, nonce = ladder.commit_entropy(sub, hypothesis_hash=obj.hash, run_id="evidence-1")
for module in (bsgs, rho_dp, instance_maker):
    digest = sub.put_identity_bundle(module.identity_bundle())
    if not sub.certified(digest):
        sub.put_certificate(digest, helpers.TRANSCRIPT_HASH, helpers.ENV_MANIFEST_HASH, helpers.SELFTEST_SUMMARY)
scratch = root / "allow"
scratch.mkdir()
allow = allowlist.instantiate(
    gate,
    hypothesis={
        "target_family": obj.target_family,
        "claimed": obj.claimed,
        "method_identity": obj.method_identity,
        "declared_parameter_ranges": obj.declared_parameter_ranges,
        "sampling_distribution": obj.sampling_distribution,
    },
    counted_object=os.path.realpath(sys.executable),
    scratch_dir=scratch,
)
for arm, module in ((ladder.CLAIMANT, bsgs), (ladder.BASELINE, rho_dp), (ladder.BASELINE_AA, rho_dp)):
    ladder.dispatch(
        sub,
        gate,
        plan=plan,
        plan_hash=ladderplan.plan_digest(gate),
        hypothesis_hash=obj.hash,
        nonce=nonce.nonce,
        run_id="evidence-1",
        arm=arm,
        skill=module.__name__,
        allow_list=allow,
    )
runs = root / "runs"
runs.mkdir()
table, arm_trials = ladder.run(
    sub,
    gate,
    plan=plan,
    plan_hash=ladderplan.plan_digest(gate),
    run_id="evidence-1",
    hypothesis_hash=obj.hash,
    nonce=nonce.nonce,
    scratch_root=runs,
    budget_remaining=100_000.0,
    ceiling_multiplier=60,
)
row = sub.conn.execute(
    "SELECT run_id, arm, hypothesis_hash, implementation_revision, allow_list_hash, gate_bundle_hash, plan_hash"
    " FROM ladder_dispatches ORDER BY rowid"
).fetchall()
print("table", table.hash)
print("verdict", laddertable.recorded_verdict(sub, table.hash))
for r in row:
    print("dispatch", dict(r))
for rr in table.rungs:
    print(
        "rung",
        rr.bits,
        rr.role,
        "trials",
        rr.trials,
        "mean_ops",
        rr.mean_ops,
        "success",
        rr.success_rate,
        "ci",
        rr.claim_ci_low,
        rr.claim_ci_high,
    )
for t in arm_trials:
    print(
        "arm",
        t.arm,
        t.bits,
        t.trial,
        "ops",
        t.ops,
        "recovered",
        t.recovered,
        "instance",
        t.instance_hash[:12],
        "seed",
        t.seed,
    )

shipped_nonce = instances.draw_nonce(sub, obj.hash, "ceiling-1")
ceiling_runs = root / "ceiling"
ceiling_runs.mkdir()
attempt, _ = instances.launch_trial(
    sub,
    gate,
    nonce=shipped_nonce.nonce,
    bits=28,
    trial=0,
    scratch_root=ceiling_runs,
    method_identity=obj.method_identity,
    budget_remaining=100_000.0,
)
declared = instance_maker.COST_PROFILE.evaluate(28).expected_wall_s
ceiling = runner.ceiling_for(declared, gate.tiers["ceiling_multiplier"])
cpu = attempt.launch.cpu_user_s + attempt.launch.cpu_sys_s
print(f"ceiling_multiplier={gate.tiers['ceiling_multiplier']} declared_wall_s={declared} ceiling_s={ceiling:.4f}")
print(f"instance_maker cpu_s={cpu:.4f} status={attempt.status}")
sub.close()
