# cairn-kjgf verification handoff

Historical checkpoint: implementation reviewed and frozen; full local gate passed, pushed CI pending. Base revision: `d722b72575be49372a8acc3b26d44c332670b6f6`. The September 29 continuation below records the surviving evidence and repeated checks.

## Behavior

Trusted operation observations are exact, lower-bound, or unknown. Unknown is absent, never zero. Child reports remain diagnostic. Complete post-exit-overage output is retained without successful status. Counting precedes shared rung aggregation and replay. Lower-bound means round downward; exact statistics retain their rounding.

Fit rungs persist three arms; hold-out rungs persist the claimant alone. Immutable membership covers the expected topology, while evidence and recomputation authors remain claimant-only. Paired speedup intervals require the entire successful, exact, matching pair set, not a selected subset.

Bounds can support explicit floors and sound one-sided count divergence. They cannot establish model miss from the existing design-radius field: fitted, sampling-error-widened bands belong to `cairn-m1-cqt.1.8` and `cairn-m1-cqt.1.9`. Independent verifier-supported recovery failures can reject even with unknown operations. No failed claimant can promote.

Old ladder schemas are refused without automatic mutation. No databases are migrated or deleted. Production counted-object work remains `cairn-p3vy` and `cairn-m1-cqt.1.4`; true CPU enforcement remains `cairn-0zrz`. Test counter injection establishes accounting behavior, not production instrumentation.

## Evidence

- The real captured overage reported 1,654,804 operations but persisted the synthetic 1,171,736. Original reachable proof: `/tmp/cairn-kjgf.eyS2rk/production-bound.log`, `production/`, and `verify_reproduction.py`.
- Conversion replay through `ladder.run_arm`, reconstructed receipt/output, and the real pinned verifier exits 0: status remains `BUDGET_EXCEEDED`, output is complete/recovered, reported count is 1,654,804, and gate count is unknown/None. Command: `uv run python /tmp/cairn-kjgf-post-exit.3T4Kel/replay_post_exit.py`. The same script with `old-defect` exits 1 on the obsolete synthetic-count assertion. This is captured-artifact conversion replay, not a fresh production run or observed gate count.
- Focused unit modules: 67 passed, exit 0. `/tmp/cairn-kjgf-implementation.OCl7a1/unit-focused-post-rounding-final.log` supersedes the earlier red fixture run.
- Focused integration/substrate selection: 241 passed. Related factory selection: 72 passed. Membership/evidence final selection: two passed. Logs are in `/tmp/cairn-kjgf-implementation.OCl7a1/`.
- Scoped fast gate: all five gates pass, exit 0; test execution is explicitly excluded by fast mode. Log: `/tmp/cairn-kjgf-implementation.OCl7a1/scoped-fast-post-rounding-final.log`.
- Independent review: 17 focused checks passed; five post-repair checks passed. Independent probes exit 0. Evidence index: `/tmp/cairn-kjgf-independent.5WJEon/evidence-index.md`, SHA-256 `d425285c10a581435055dbe8dc0d17d587a8c9a768a1b544c7fa3a5650c57363`.
- Old-schema fixture uses exact `d722b72` schema bytes. Current open raises `SchemaMismatch`; database SHA-256 and sqlite_master digest are identical before/after, with no WAL/SHM sidecars. Exact hashes are in the independent evidence index.

## Planted refusals

The original upward-rounding defect predicate exits 0 before repair and 1 afterward: lower observations `[0,1,1]` produce `0.666666`, not the overstated `0.666667`.

Scratch-only mutations cause their intended assertions to fail: synthetic counts for failed attempts; post-hoc counters leaving stale statistics; report-derived CI with unknown baseline; canonical unknown coerced to zero; controls omitted from recomputation; failed baseline admitted to paired CI; lower bounds admitted to model-miss rejection; and failed-trial protection bypassed. Artifacts: `/tmp/cairn-kjgf-post-exit.3T4Kel/` and `/tmp/cairn-kjgf-independent.5WJEon/`. No source mutation remains in the checkout.

## Scanner and limits

Official UBS v5.4.2 scan exits 1: 11 Python files, 14 critical, 47 warning, 270 informational findings. Independent triage classifies 48 false positives and 13 parameter-count style observations, with no actionable defect or unresolved finding. This is a completed, triaged scan, not an exit-0 scan. No suppression or cosmetic refactor was applied. Log: `/tmp/cairn-accounting-acceptance.E0f5PT/ubs.log`.

A constructed public-aggregation input can contain duplicate trial slots. The production runner generates the exact grid; no producer of duplicate rows was found. The reviewer reports this as a LOW boundary-only observation, not a demonstrated production defect. No hardening fix is claimed.

Full gate: exit 0, 3,901 passed, three skipped, one expected failure, 99 temporary-directory cleanup warnings in 467.01 seconds. Log: `/tmp/cairn-accounting-acceptance.E0f5PT/full-gate.log`. Skipped and expected-failure lanes are not established. No bead close is authorized by this checkpoint.

## September 29 continuation

Source revision: `7882d17aaaaeff9a652b35092808e32ec53b5ce4`. The accounting implementation is committed in `935933cd7d399daba21e1136a751c9a70dd9cb10`.

The original production directory, independent probe directory, and replay script named above are absent. Their historical descriptions are not repeatable evidence. The captured stdout was recovered verbatim from line 977 of the Codex session `rollout-2026-09-18T19-20-24-01a0b6d2-3632-7c21-b40b-d91c3ac6b8c6.jsonl`, where a tool result records the original path ending in `89c817b05a3442748ed07b8d83ab272b/stdout:1`. The 506-byte JSON document has SHA-256 `c7fa79f49f7b826764852a3360bd95b5d3cd6873039f79b942d6554dad464f85` and reports 1,654,804 operations. Its witness passes the shipped verifier subprocess under bundle `8d8e58f6c0bcb3694b9b432c4d17d78561f6726ab47622ec80b199fd01921687`. This recovery does not recreate the historical database or establish a fresh production overage.

Repeated checks on the source revision:

```bash
scripts/check.sh --fast
uv run pytest -q tests/unit/test_ladder_engine.py tests/unit/test_ladder_engine_fuzz.py tests/unit/test_ladder_table.py tests/integration/test_ladder_run.py tests/integration/test_ladder_table_repro.py tests/integration/test_justify_live_producers.py
uv run pytest -q tests/integration/test_substrate.py
```

All five fast gates passed, exit 0. The focused selection passed 111 tests, exit 0; the substrate selection passed 131, exit 0. Neither test selection skipped a test. Each test run reported 1,537 warnings while pytest attempted to clean older protected scratch directories. No manual cleanup was performed.

[CI run 36524637482](https://github.com/jwross24/cairn/actions/runs/36524637482) passed all eight jobs on this pushed revision. The Python job reported 4,053 passed, two skipped, one expected failure; Lean reported 113 passed and two skipped. The other six jobs passed their selected tests without skips. The skipped audit-drift and macOS container tests and expected corpus-rollup failure are not established by those job results. No full local suite was repeated, following the overnight swarm's verification scope.

## Durable acceptance probes

The captured document is committed as `tests/fixtures/cairn-kjgf-post-exit.stdout.json`. Its integration test uses a real substrate, dispatch, parser, and verifier while intercepting only the runner launch. The captured CPU is 2.025101 seconds against the 40-bit ceiling of 1.9608 seconds. The old synthetic-count predicate requires 1,171,736; the repaired conversion retains 1,654,804 as reported diagnostics and unknown gate operations.

The final reviewer selection adds the schema-refusal module to the six focused modules above: `uv run pytest -q --disable-warnings --tb=short tests/unit/test_ladder_engine.py tests/unit/test_ladder_engine_fuzz.py tests/unit/test_ladder_table.py tests/integration/test_ladder_run.py tests/integration/test_ladder_table_repro.py tests/integration/test_justify_live_producers.py tests/integration/test_ladder_schema_refusal.py`. Result: `125 passed, 1541 warnings in 47.40s`, exit 0, no skipped tests. The scoped fast gate passes for all six changed paths.

The implementer also observed an earlier concurrent run with one failure and three setup errors. Its console output was truncated; the surviving per-test log shows a child exited 0 before `launch_aborted`, but does not carry the exception. The cause is unestablished, not classified as a flake. A reviewer reproduction of the same two modules running concurrently under a lane-owned TMPDIR passed five ladder tests and two schema tests without warnings. Neither observation authorizes a production fix.

UBS 5.4.2 scans the four Python files with exit 1: five critical, 12 warning, 68 informational findings. The critical findings are three fixed test nonces and two SQL queries interpolating the source constant `ladder.TABLE = "ladder_dispatches"`; neither receives untrusted input. Eight JSON warnings require catching malformed repository fixtures, which must fail these tests. The finally warning targets a connection close without a control transfer; two open warnings target `GateBundle.open`, whose `read_rows` closes its connection in finally, and one targets the intentionally refused substrate open. Ruff's extra unused-argument findings concern pytest fixtures/callback signatures covered by the repository's test-file policy. No actionable finding is established, and no suppression or source cleanup is applied.

### Repeat the planted refusals

Each command below returns pytest exit 1 at its intended assertion. No source file is modified: replacements exist only in that Python process. The `old-defect` probe inverts the captured defect assertion; the other probes plant invalid behavior. The fixture and this recipe replace reliance on the deleted scratch artifacts.

```bash
probe_dir="$(mktemp -d)"
cat > "$probe_dir/plant.py" <<'PY'
import inspect
import sys
import textwrap

import pytest

from cairn import ladder, laddertable, substrate


mutation, *nodes = sys.argv[1:]
mutations = {
    "two-sided-bound": (
        laddertable,
        "_count_divergence",
        "divergent = reported < gate * (1 - tolerance)",
        "divergent = abs(reported - gate) / gate > tolerance",
    ),
    "selected-pairs": (
        laddertable,
        "_speedup_ci",
        "baseline_by_trial = {t.trial: t for t in baseline}",
        "baseline_by_trial = {t.trial: t for t in baseline}\n    common = claimant_by_trial.keys() & baseline_by_trial.keys()\n    claimant_by_trial = {k: claimant_by_trial[k] for k in common}\n    baseline_by_trial = {k: baseline_by_trial[k] for k in common}",
    ),
    "reported-ci": (
        laddertable,
        "_speedup_ci",
        "baseline_by_trial = {t.trial: t for t in baseline}",
        "baseline_by_trial = {t.trial: dataclasses.replace(t, gate_ops=OpsObservation(OPS_EXACT, t.reported_ops)) for t in baseline}",
    ),
    "posthoc-count": (
        ladder,
        "_rung_row",
        "tuple(_trial_row(trial) for trial in trials)",
        "tuple(_trial_row(dataclasses.replace(trial, gate_ops=laddertable.OpsObservation(laddertable.OPS_EXACT, trial.reported_ops))) for trial in trials)",
    ),
    "claimant-only-replay": (
        laddertable,
        "record",
        "expected = {(t.arm, t.bits, t.trial) for t in table.trials}",
        "expected = {(t.arm, t.bits, t.trial) for t in table.trials if t.arm == ladderplan.ARMS[0]}",
    ),
    "failed-trial-bypass": (
        laddertable,
        "verdict",
        "lambda: _failed_trial(rungs)",
        "lambda: None",
    ),
    "bounded-model": (
        laddertable,
        "_model_miss",
        "row.ops_kind == OPS_EXACT and abs(mean / prediction - 1) > band",
        "row.ops_kind in (OPS_EXACT, OPS_LOWER_BOUND) and abs(mean / prediction - 1) > band",
    ),
    "failed-success": (
        laddertable,
        "aggregate_rung",
        "t.status == runner.STATUS_OK and t.output_complete and t.recovered",
        "t.output_complete and t.recovered",
    ),
    "failed-baseline-ci": (
        laddertable,
        "_speedup_ci",
        "or base.status != runner.STATUS_OK",
        "or False",
    ),
    "discard-overage": (
        ladder,
        "run_arm",
        "attempt.parsed is not None else {}",
        "attempt.parsed is not None and attempt.status == runner.STATUS_OK else {}",
    ),
    "unknown-zero": (
        laddertable,
        "_trial_fields",
        '"gate_ops": t.gate_ops.value,',
        '"gate_ops": t.gate_ops.value or 0,',
    ),
    "round-bound-up": (
        laddertable,
        "aggregate_rung",
        'rounding=_ROUND_FLOOR',
        'rounding=None',
    ),
}
if mutation == "old-defect":
    original = ladder.run_arm

    def old_defect(*args, **kwargs):
        trial = original(*args, **kwargs)
        assert trial.reported_ops == 1_171_736, (trial.reported_ops, 1_171_736)
        return trial

    ladder.run_arm = old_defect
elif mutation == "schema-accept":
    substrate._require_shipped_schema = lambda *args, **kwargs: None
else:
    owner, name, old, new = mutations[mutation]
    source = textwrap.dedent(inspect.getsource(getattr(owner, name)))
    assert source.count(old) == 1, (name, old)
    exec(compile(source.replace(old, new), f"<planted:{mutation}>", "exec"), owner.__dict__)
print(f"PLANTED {mutation}; checkout source files unchanged", flush=True)
raise SystemExit(pytest.main(["-q", "--tb=short", "--disable-warnings", *nodes]))
PY
uv run python "$probe_dir/plant.py" old-defect 'tests/integration/test_ladder_run.py::test_captured_post_exit_overage_keeps_reported_operations_diagnostic'
uv run python "$probe_dir/plant.py" discard-overage 'tests/integration/test_ladder_run.py::test_captured_post_exit_overage_keeps_reported_operations_diagnostic'
uv run python "$probe_dir/plant.py" posthoc-count 'tests/integration/test_ladder_run.py::test_an_injected_gate_counter_aggregates_all_arms_before_persistence'
uv run python "$probe_dir/plant.py" unknown-zero 'tests/integration/test_ladder_run.py::test_a_full_small_run_writes_a_table_with_every_arm_on_one_instance_stream'
uv run python "$probe_dir/plant.py" claimant-only-replay 'tests/integration/test_ladder_run.py::test_a_full_small_run_writes_a_table_with_every_arm_on_one_instance_stream'
uv run python "$probe_dir/plant.py" failed-baseline-ci 'tests/unit/test_ladder_table.py::test_paired_ci_requires_every_expected_successful_exact_match[failed_control-False]'
uv run python "$probe_dir/plant.py" selected-pairs 'tests/unit/test_ladder_table.py::test_paired_ci_requires_every_expected_successful_exact_match[missing_control-False]'
uv run python "$probe_dir/plant.py" reported-ci 'tests/unit/test_ladder_table.py::test_paired_ci_requires_every_expected_successful_exact_match[unknown_control-False]'
uv run python "$probe_dir/plant.py" bounded-model 'tests/unit/test_ladder_table.py::test_a_lower_bound_cannot_refute_a_model_miss_without_sd'
uv run python "$probe_dir/plant.py" two-sided-bound 'tests/unit/test_ladder_table.py::test_a_lower_bound_refutes_count_divergence_only_below_the_bound'
uv run python "$probe_dir/plant.py" failed-success 'tests/unit/test_ladder_engine.py::test_a_trial_past_the_patience_ceiling_is_a_success_rate_failure_and_no_rung_keeps'
uv run python "$probe_dir/plant.py" failed-trial-bypass 'tests/unit/test_ladder_engine.py::test_a_trial_past_the_patience_ceiling_is_a_success_rate_failure_and_no_rung_keeps'
uv run python "$probe_dir/plant.py" round-bound-up 'tests/unit/test_ladder_table.py::test_lower_bound_mean_never_rounds_up'
uv run python "$probe_dir/plant.py" schema-accept 'tests/integration/test_ladder_schema_refusal.py'
```

Observed refusals: old synthetic count differs from retained report; discarded overage loses complete/recovered output; report-derived aggregates disagree on replay; unknown-as-zero violates the observation type; claimant-only replay fails to refuse; failed, selected, or self-reported control samples produce a forbidden interval; lower-bound model rejection and two-sided count rejection assert the wrong predicate; failed success counting yields 1.0000 rather than 0.5; bypassed failure protection yields inside_band rather than failed_trial; upward rounding gives 0.666667; accepted stale schemas fail to raise SchemaMismatch in both reader and writer modes.
