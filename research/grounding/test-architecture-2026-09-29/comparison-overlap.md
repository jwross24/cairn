# Closure comparison and ordered-plan overlap

**Pinned sources:** `0ef291a2433ff0ceb96737d7631df5c2c27b5a2c`. The links below address this immutable source revision. This is a bounded source map of closure-comparison and ordered-plan tests, not a runtime coverage report.

| Test nodes and source | Exercised boundary and invariant | Overlap assessment |
|---|---|---|
| Unit closure observer: [`test_a_matching_closure_is_the_expectation` through `test_a_comparison_that_exceeds_its_timeout_is_a_step_timeout_and_never_a_mismatch`](https://github.com/jwross24/cairn/blob/0ef291a2433ff0ceb96737d7631df5c2c27b5a2c/tests/unit/test_solution_comparison.py#L67), plus [timeout/mutation cases](https://github.com/jwross24/cairn/blob/0ef291a2433ff0ceb96737d7631df5c2c27b5a2c/tests/unit/test_solution_comparison.py#L126) and [binding refusals](https://github.com/jwross24/cairn/blob/0ef291a2433ff0ceb96737d7631df5c2c27b5a2c/tests/unit/test_solution_comparison.py#L152) | The ordinary observer replaces `lean.run_argv`; its comparator fixture is an empty file. It maps rc 0, missing binary, nonzero output, mutated input, and timeout into comparison outcomes. The timeout and mutation container-observer cases stub `container.run` and bypass the pin check. The binding-negative cases replace `assert_pinned` with a function that raises if reached, proving refusal occurs earlier; they do not replace `container.run`. Production mapping is in [`observe_closure_comparison`](https://github.com/jwross24/cairn/blob/0ef291a2433ff0ceb96737d7631df5c2c27b5a2c/src/cairn/solutionchecks.py#L496) and [`observe_container_comparison`](https://github.com/jwross24/cairn/blob/0ef291a2433ff0ceb96737d7631df5c2c27b5a2c/src/cairn/solutionchecks.py#L155). | Adapter and outcome classification only; these tests do not invoke the comparator or Lean proof authority. Their synthetic positive/refusal cases are not duplicates of the real container tests. |
| Generic plan contract: [`test_a_plan_carrying_the_closure_comparison_loads_with_it_last`, ordering refusals, and comparison pass/refusal cases](https://github.com/jwross24/cairn/blob/0ef291a2433ff0ceb96737d7631df5c2c27b5a2c/tests/unit/test_solution_plan.py#L108), plus [plan outcome and timeout cases](https://github.com/jwross24/cairn/blob/0ef291a2433ff0ceb96737d7631df5c2c27b5a2c/tests/unit/test_solution_plan.py#L221) | `SolutionPlan.load` checks the generic plan shape and selected relative order; `plan_outcomes` classifies synthetic observer verdicts and blocks later steps after failure/timeout ([loader and order checks](https://github.com/jwross24/cairn/blob/0ef291a2433ff0ceb96737d7631df5c2c27b5a2c/src/cairn/solutionplan.py#L115), [outcome reducer](https://github.com/jwross24/cairn/blob/0ef291a2433ff0ceb96737d7631df5c2c27b5a2c/src/cairn/solutionplan.py#L213)). | Owns plan validation and result reduction, not comparison execution. It overlaps the ordered-plan tests only on expected step/result semantics. |
| Gold wrapper order refusal: [`test_the_gold_plan_refuses_a_plan_that_orders_replay_before_axioms`](https://github.com/jwross24/cairn/blob/0ef291a2433ff0ceb96737d7631df5c2c27b5a2c/tests/unit/test_solution_comparison.py#L250) | The test swaps the axiom and replay rows, expects `PlanInvalid`, no recorded subprocess, and no project root. `run_container` requires the complete exact `STEP_KINDS` tuple before resolving paths or observing steps ([wrapper guard](https://github.com/jwross24/cairn/blob/0ef291a2433ff0ceb96737d7631df5c2c27b5a2c/src/cairn/solutionchecks.py#L380)). Generic `_assert_canonical_order` constrains each checker relative to build and comparison but does not order the two checkers relative to each other ([source](https://github.com/jwross24/cairn/blob/0ef291a2433ff0ceb96737d7631df5c2c27b5a2c/src/cairn/solutionplan.py#L281)). | **Planted false duplicate:** it may look as if the generic loader already owns the gold wrapper's checker-order invariant. The pure-Python reproduction below exited 0 against production callables matching the pinned source: generic `SolutionPlan.load` accepts the swapped order, while `run_container` refuses with `gold-plan-requires-axioms-before-replay` before root/work creation. It runs no Lean or Docker. |
| Dev real-prelude ordered plan: [`test_real_prelude_ordered_plan_uses_fresh_replay_and_blocks_later_checks`](https://github.com/jwross24/cairn/blob/0ef291a2433ff0ceb96737d7631df5c2c27b5a2c/tests/integration/test_solution_build_compile.py#L511); comparator fixture at [lines 103–125](https://github.com/jwross24/cairn/blob/0ef291a2433ff0ceb96737d7631df5c2c27b5a2c/tests/integration/test_solution_build_compile.py#L103) | It calls `run_dev` with real host Lean, checks the six ordered results, fresh-replay argv, blocked later steps for `sorry`/timeout, and expected comparator invocation and generated inputs. The fixture checks the pinned comparator/exporter checkout and binary, then sets `COMPARATOR_LANDRUN` to that checkout's `scripts/fake-landrun.sh`; landrun itself is therefore a test boundary, not production landrun evidence. The root `popen_spy` records argv and delegates to its wrapped `Popen` ([fixture](https://github.com/jwross24/cairn/blob/0ef291a2433ff0ceb96737d7631df5c2c27b5a2c/tests/conftest.py#L143)). | Dev integration covers the host-tool path and ordered-plan behavior, with the explicit fake-landrun qualification. It is not the gold Docker proof path. |
| Direct gold comparison: [`test_linux_candidate_closure_comparison_matches_exact_statement`](https://github.com/jwross24/cairn/blob/0ef291a2433ff0ceb96737d7631df5c2c27b5a2c/tests/integration/test_container_statement_hash.py#L294) and [`...refuses_weaker_statement`](https://github.com/jwross24/cairn/blob/0ef291a2433ff0ceb96737d7631df5c2c27b5a2c/tests/integration/test_container_statement_hash.py#L341) | These compile in the pinned Linux image and call `observe_container_comparison` directly. They assert the exact comparator argv, `--network none`, image identity, host user, unchanged project inputs/dependencies, and exact-match or mismatch reason. The positive case also retries with a timeout and asserts closure-step attribution plus a recorded `docker stop`; production maps timeout and checks inputs on that path ([observer](https://github.com/jwross24/cairn/blob/0ef291a2433ff0ceb96737d7631df5c2c27b5a2c/src/cairn/solutionchecks.py#L155), [container timeout cleanup](https://github.com/jwross24/cairn/blob/0ef291a2433ff0ceb96737d7631df5c2c27b5a2c/src/cairn/container.py#L182)). Separate container tests assert stopped-container ownership ([test](https://github.com/jwross24/cairn/blob/0ef291a2433ff0ceb96737d7631df5c2c27b5a2c/tests/integration/test_container_statement_hash.py#L598)), rc/stdout/stderr preservation ([test](https://github.com/jwross24/cairn/blob/0ef291a2433ff0ceb96737d7631df5c2c27b5a2c/tests/integration/test_container_statement_hash.py#L630)), and failed-cleanup reporting ([test](https://github.com/jwross24/cairn/blob/0ef291a2433ff0ceb96737d7631df5c2c27b5a2c/tests/integration/test_container_statement_hash.py#L642)). | Direct tests own comparison invocation, isolation, input integrity, and container timeout/output contracts. These are not ordered-plan persistence assertions. |
| Gold full ordered plan: [`test_linux_ordered_plan_runs_each_step_in_order`](https://github.com/jwross24/cairn/blob/0ef291a2433ff0ceb96737d7631df5c2c27b5a2c/tests/integration/test_container_statement_hash.py#L375) | Four gold-dispatch cases (`exact`, `sorry`, `weaker`, `stale-hash`) assert six step kinds and persist results ([persistence assertions](https://github.com/jwross24/cairn/blob/0ef291a2433ff0ceb96737d7631df5c2c27b5a2c/tests/integration/test_container_statement_hash.py#L419)). `stale-hash` is a preflight refusal: it asserts blocked later steps, an empty subprocess spy, and absent root/work directories, then returns without candidate Docker execution ([preflight branch](https://github.com/jwross24/cairn/blob/0ef291a2433ff0ceb96737d7631df5c2c27b5a2c/tests/integration/test_container_statement_hash.py#L448)). The other cases reach candidate container execution and assert subprocess order/refusals ([execution assertions](https://github.com/jwross24/cairn/blob/0ef291a2433ff0ceb96737d7631df5c2c27b5a2c/tests/integration/test_container_statement_hash.py#L458)). | `exact`/`weaker` share comparison inputs and verdict semantics with the direct gold comparison cases, so there is partial overlap. The full-plan cases separately own orchestration, order, blocking, and persistence; the direct cases separately assert comparison argv/security and timeout cleanup. Source inspection gives no basis to remove either. |

**Execution evidence:** At the pinned revision, `uv run pytest -q tests/unit/test_solution_comparison.py tests/unit/test_solution_plan.py` exited 0: 61 passed in 2.87s. Raw output: `/tmp/cairn-lane3.2ARmLN/comparison-contracts.log`. This is unit adapter/plan evidence only; it does not establish a fresh Lean/Docker proof run or upgrade the historical real-CI results in [the checklist](checklist.md).

## Unit seam inventory

This source-only inventory uses `90401ee50700e119331e9c05727c15a9d3693cfb`. The comparison and plan unit-test blobs match the overlap map's pinned revision. It records what the doubles replace, not a fresh execution result.

- `test_solution_build.py` uses real temporary files for assembly, fingerprint, and dependency contracts. Its timeout test replaces `lean.run_argv`. The command-construction test checks argv only; the integration test `test_an_honest_solution_builds_in_the_assembled_project_and_the_inputs_are_unchanged` supplies the real build boundary with rc 0, an existing `.olean`, and unchanged inputs.
- `test_solution_comparison.py` supplies a zero-byte comparator path and replaces `lean.run_argv` for host outcome mapping. `test_the_comparator_runs_in_the_assembled_root_on_the_config_the_gate_wrote` checks cwd/argv and discards the returned observer result. Other named matching, missing-comparator, nonzero, mutation, and timeout cases assert outcomes or refusal reasons. The direct gold exact/weaker integration cases supply real comparator execution.
- The two container comparison timeout tests replace two callable seams, `container.assert_pinned` and `container.run`, and supply synthetic prior compilation/image state through `container_compilation`. Counting represented authority states yields three boundaries; counting patched callables yields two. Their assertions prove timeout attribution and mutation refusal, not comparison correctness. The gold exact integration also exercises actual timeout attribution and cleanup.
- `test_solution_plan.py` injects one synthetic observer callback and checks the pure plan reducer's pass, failure, timeout, blocking, and reason semantics. Real ordered-plan integration owns actual observers, process ordering, and persisted outcomes.

The command-shape tests have narrower assertions than their named integration counterparts. That is not, by itself, a duplicate or a defective test. No reduction or refactor follows from these source observations, and a suite-wide mock-seam claim remains unproven.

The swapped-checker probe can be reproduced without Lean or Docker:

```bash
uv run python - <<'PY'
from pathlib import Path
from tempfile import mkdtemp

from cairn import container, solutionchecks, solutionplan

rows = [
    {
        "step": kind,
        "kind": kind,
        "expect": solutionplan.KIND_EXPECTATION[kind],
        "blocking": True,
        "timeout_s": 60.0,
    }
    for kind in solutionplan.STEP_KINDS
]
rows[3], rows[4] = rows[4], rows[3]
solutionplan.SolutionPlan.load(rows, arm=container.GOLD_ARM)

directory = Path(mkdtemp(prefix="cairn-order-authority-", dir="/tmp"))
root, work_dir = directory / "candidate", directory / "work"
try:
    solutionchecks.run_container(
        None, None, None, None, None, rows, root=root, work_dir=work_dir, prepared=None
    )
except solutionplan.PlanInvalid as exc:
    assert str(exc) == "gold-plan-requires-axioms-before-replay"
else:
    raise AssertionError("the gold dispatcher accepted swapped checker order")
assert not root.exists()
assert not work_dir.exists()
print("PASS: generic loader accepted swap; gold wrapper refused before project/work creation")
PY
```

The reproduction exited 0 and printed its PASS line. It demonstrates the wrapper-order guard only; it does not run an authority check.

**No-Claim:** This map is not runtime coverage, a whole-suite duplicate or leak audit, a speedup claim, or permission to delete tests. Shared outcomes and repeated setup do not establish waste. No test reduction is recommended without a mechanical reproducer and preserved real authority coverage.
