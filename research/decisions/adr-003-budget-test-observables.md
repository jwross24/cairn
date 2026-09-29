# ADR 003: Budget test observables

Status: accepted

A CPU budget compares measured execution time with a declared expectation. A
random input and an arbitrary host do not guarantee budget exhaustion.

The real ladder integration test verifies its stored success rates against the
observed claimant outcomes. Failure diagnostics identify each seed, terminal
status, measured CPU time and configured ceiling. The deterministic boundary
test covers CPU equal to and strictly greater than the ceiling. An over-budget
trial lowers the aggregate success rate and cannot produce KEEP. The real
CPU-burner integration test supplies subprocess evidence for budget refusal.

Neither a fixed nonce nor a fitted timing constant establishes these properties
across hosts. Synthetic aggregation tests do not establish production wiring;
the real ladder and CPU-burner tests retain that responsibility.

This test contract does not establish correctness of operation accounting or
runtime CPU enforcement. Those questions belong to `cairn-kjgf` and its related
implementation work.

## Reproduction recipe

From the repository root, this command runs the 28-bit fit and 30-bit hold-out
fixture with two trials per rung and `patience_multiplier=1`. Its 25 distinct
64-character lowercase hex nonces are fixed before the run. The values are test
inputs, not production entropy. It calls the real instance maker, runner, and
cost profile without replacing the launcher or changing timing inputs.

```bash
scratch_path=$(mktemp -d /tmp/cairn-uz4g.XXXXXX)
mkdir -p "$scratch_path/tmp" "$scratch_path/data"
TMPDIR="$scratch_path/tmp" CAIRN_UZ4G_TMP="$scratch_path/data" uv run python - <<'PY'
import dataclasses
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

root = Path.cwd()
scratch = Path(os.environ["CAIRN_UZ4G_TMP"])
sys.path[:0] = [str(root / "tests"), str(root / "tests" / "integration")]
import _substrate_helpers as helpers
import test_ladder_run as recipe
from cairn import bundle, instances, ladder, ladderplan, runner
from cairn.skills import bsgs

nonces = [f"{value:064x}" for value in range(1, 26)]
print("PRESELECTED_NONCES=" + json.dumps(nonces))
bundle_dir = scratch / "bundle"
bundle_dir.mkdir()
bundle_path, pin_path = bundle_dir / "gate-bundle.sqlite", bundle_dir / "gate-bundle.pin"
bundle.build(root / "bundle", bundle_path)
bundle.write_pin(bundle_path, pin_path)
shipped = bundle.GateBundle.open(bundle_path, pin_path)
plan = dataclasses.replace(recipe.plan.__wrapped__(), patience_multiplier=1)
hypothesis = recipe.hypothesis_object.__wrapped__()
attest_path = scratch / "attestations.log"
attest_path.touch()
observations = []

for index, nonce in enumerate(nonces, 1):
    run_root = scratch / f"sample-{index}"
    run_root.mkdir()
    writer = helpers.open_writer(run_root)
    run_id = f"uz4g-fixed-{index}"
    try:
        with patch.object(instances, "fresh_nonce", return_value=nonce):
            committed_nonce = recipe._dispatch_run(writer, shipped, run_root, plan, hypothesis, run_id)
        if committed_nonce != nonce:
            raise RuntimeError(f"fixed nonce mismatch: {committed_nonce} != {nonce}")
        run_scratch = run_root / "runs"
        run_scratch.mkdir()
        table, arm_trials = ladder.run(
            writer,
            shipped,
            plan=plan,
            plan_hash=ladderplan.plan_digest(shipped) or "dd" * 32,
            run_id=run_id,
            hypothesis_hash=hypothesis.hash,
            nonce=nonce,
            scratch_root=run_scratch,
            budget_remaining=10_000.0,
            ceiling_multiplier=recipe.MAKER_CEILING,
            attest_path=attest_path,
        )
        claimant = [trial for trial in arm_trials if trial.arm == ladder.CLAIMANT]
        diagnostics = [
            {
                "bits": trial.bits,
                "trial": trial.trial,
                "method_seed": trial.seed,
                "status": trial.status,
                "cpu_seconds": trial.cpu_seconds,
                "ceiling_seconds": runner.ceiling_for(
                    bsgs.COST_PROFILE.evaluate(trial.bits).expected_wall_s,
                    plan.patience_multiplier,
                    subprocess_startup_ms=shipped.tiers["subprocess_startup_ms"],
                ),
                "output_complete": trial.output_complete,
                "recovered": trial.recovered,
            }
            for trial in claimant
        ]
        universal_predicate = bool(claimant) and all(
            trial.status == runner.STATUS_BUDGET_EXCEEDED for trial in claimant
        )
        observations.append({"nonce": nonce, "universal_predicate": universal_predicate, "claimant": diagnostics})
        print("SAMPLE=" + json.dumps(observations[-1], sort_keys=True))
        print("RUNG_RATES=" + json.dumps([{"bits": row.bits, "success_rate": row.success_rate} for row in table.rungs]))
    finally:
        writer.close()

claimant_trials = [trial for item in observations for trial in item["claimant"]]
failures = sum(not item["universal_predicate"] for item in observations)
budget_exceeded = sum(trial["status"] == runner.STATUS_BUDGET_EXCEEDED for trial in claimant_trials)
status_ok = sum(trial["status"] == runner.STATUS_OK for trial in claimant_trials)
print("MEASURED=" + json.dumps({
    "runs": len(observations),
    "universal_predicate_false": failures,
    "universal_predicate_true": len(observations) - failures,
    "claimant_trials": len(claimant_trials),
    "budget_exceeded_trials": budget_exceeded,
    "status_ok_trials": status_ok,
    "other_status_trials": len(claimant_trials) - budget_exceeded - status_ok,
}, sort_keys=True))
if failures == 0:
    raise SystemExit("no witness: every preselected run satisfied the universal predicate")
print("BUG_WITNESS: universal allclaimants-BUDGET_EXCEEDED predicate is false; exit=0")
PY
```

For every claimant trial, the output retains the instance nonce, method seed,
bits, trial index, status, measured CPU seconds, and ceiling. `RUNG_RATES`
reports each stored fraction. A false universal predicate reproduces the
assertion failure. The measured rate describes the fixed sample on that host;
it does not establish a host-independent rate.

`SAMPLE.nonce` is the committed run nonce. `method_seed` is `ArmTrial.seed`,
derived for the claimant arm, bit size, and trial index by
`ladder.method_seed`.

Run the focused controls with a dedicated temporary directory:

```bash
TMPDIR=<dedicated-tempdir> uv run pytest -q tests/integration/test_ladder_run.py tests/unit/test_ladder_engine.py tests/integration/test_runner_clock.py
```

As in-memory planted negatives, remove the `t.status == runner.STATUS_OK and`
term from `laddertable.aggregate_rung` and require the over-budget success-rate
control to fail. Change `cpu_s > ceiling_s` to `cpu_s >= ceiling_s` in
`runner.status_for` and require the equality control to fail. Keep these
mutations out of the checkout.
