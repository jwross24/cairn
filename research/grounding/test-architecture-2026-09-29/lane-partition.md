# Owner-directed test-lane partition evidence

The 19-lane layout passes all jobs in [CI run 36618973095](https://github.com/jwross24/cairn/actions/runs/36618973095) at `9f68240ae5bf7f3c060d2560e6df7f86a06721ed`. The aggregate result is 4,706 passed, two external-skill skips, and one corpus-completeness xfail, with no failed tests or errors. Skips and xfails are exclusions, not passes. Every affected heavy leaf has zero skips. This establishes completion under the fixed job/session ceilings, not a causal speedup or completion of the broader test audit.

## Descendant verification at `135f020`

[Run 36624207935](https://github.com/jwross24/cairn/actions/runs/36624207935) is a terminal failure at `135f0200d2ca1577b6dcac0262bad0ed324a34ba`: 17 jobs passed, GatePlan failed, and Python recorded ten failed nodes before exhausting its 1,080-second session budget. This does not invalidate the source-specific receipt at `9f68240`, and it does not establish green for descendant code.

GatePlan reported `1 failed, 27 passed, 4727 deselected in 607.20s`. The method-identity mutation wrapper rejected the keyword-only `attest_path` argument before reaching its intended assertion. Commit `ec76ff7794eb7fbee6329d9f0c0584f7a03addc5` accepts and forwards that argument, with the mutation and refusal assertions preserved. The committed module passed both tests in 40.10 seconds; the independent refusal case passed in 0.64 seconds. These local receipts cover the wrapper repair, not the full workflow.

Python selected 4,519 of 4,755 collected cases and emitted `Timeout (0:18:00)!` at 82% completion. The active node was `test_the_status_is_always_one_of_the_five`; its position at the deadline is not evidence that this test caused the overrun. Completed integration-result timestamps span 20:30:41.754753 to 20:38:29.585771 UTC. That approximately 468-second interval includes work between result lines; it is not a pytest phase-duration measurement. The [raw failure log](lane-partition/raw/second-python-failure.log.gz) and [terminal metadata](lane-partition/raw/second-terminal.json.gz) retain the deadline and incomplete population explicitly.

The ten explicit `FAILED` lines name two tier-two maker cases, seven bound-production justification cases, and the bound-evidence wrong-answer ledger case. An affected-leaf local run at `c2e406b` with the routing edit reproduces these as two `operator-session-absent` and eight `ticket-absent` refusals. It reports 11 failed, 1,277 passed, and one skipped in 280.92 seconds. The additional failure is the external compliance gatherer drift, independently reproduced on an unchanged `c2e406b` archive. These admission failures require their own repairs; partitioning cannot resolve them. Local pytest also emitted 2,101 cleanup warnings for protected scratch from earlier runs. The skipped framework-interpreter parameter remains an exclusion.

## Python integration partition

The `python-integration` leaf owns integration files outside the explicit heavy-lane manifests. `python` owns the remaining fallback tests. Explicit M0, GatePlan, Lean, Solution, library, and container routing takes precedence. Both Python leaves use macOS without Lean or comparator provisioning; the workflow has 20 leaves with the same 1,080-second session and 20-minute job ceilings.

Collection against the `c2e406b` baseline preserves all 4,522 original Python cases: 1,289 integration cases and 3,233 other cases. The routing contracts add 20 cases, giving 3,253 Python and 1,289 Python-integration cases in the reviewed tree. Thirty-one contract IDs contain incremented expected fixture counts; the receipt maps each old ID to its corresponding count-adjusted ID. All 18 other lane selections are byte-equal node sets when both routers receive the same collected items. The 20 sets are disjoint and cover all 4,778 collected items.

The parent ran the three lane contract modules: 477 passed in 95.12 seconds. A focused final union-contract check passed in 3.65 seconds. Scoped format, lint, spelling, types, and theater gates passed. The physical scratch mutation routing integration items back to `python` failed the real collection contract: `python-integration` collected zero tests, returned exit 5, and caused the outer test to fail with exit 1. The parent reproduced this refusal in 3.46 seconds. Cleanup warnings remain distinct from test outcomes. These checks establish routing and failure propagation, not completion of either lane under CI timing.

The partition is committed at `ba11d1d2cc5a297b839c596a1ef13b4eaf9e0ce8`. Its local `python` leaf completed with 3,252 passed, one corpus-completeness xfail, and 1,525 deselected in 310.29 seconds. The xfail is not a pass. The run emitted 2,101 protected-scratch cleanup warnings. A parent rerun of the maker fixture module at `6d21eaf06ddec965480e9c104957a3bd46b00317` passed all 13 tests in 3.48 seconds. These local observations are separate from the required pushed-CI result.

Commit `e8263798d851ee751b1aa2989e9e95281657e96a` supplies the missing ratification prerequisite in the eight bound-statement fixtures. `TierGate._selected_ticket` requires a visible ratification for the statement and gate bundle before selecting their Tier-1 hypothesis ticket. The fixtures initialize dedicated attestation logs and append matching records through `human_authority.append`. Production gates and shared fixtures are unchanged; all 132 assertions in the two affected modules are structurally identical to their parent commit.

Both modules passed 39 tests in 28.70 seconds in the checkout and 28.30 seconds from an isolated archive of committed `e826379`. The isolated wrong-statement mutation changes only each appended ratification's statement hash to `"f" * 64`. Both repaired positive cases then fail with `ticket-absent` at the first claimant trial, as required: two failures in 0.53 seconds, expected exit 1. [The source binding](lane-partition/raw/ratification-source-binding.json.gz) records committed and mutated file hashes. [Committed positive output](lane-partition/raw/ratification-committed-modules.log.gz) and [planted refusal output](lane-partition/raw/ratification-parent-negative.log.gz) retain the raw results, including 2,127 protected-scratch cleanup warnings. UBS exit 1 has an [explicit adjudication](lane-partition/raw/ratification-ubs-review.md.gz); it is not a clean-scan result. This fixture verification establishes neither a full green workflow nor completion of the broader audit.

## Terminal 19-lane receipt

All macOS jobs collected 4,709 items; the five Linux jobs collected their scoped 45 items. The selected populations below sum to 4,709, with disjoint ownership checked separately by the lane contracts. Pytest seconds include setup, calls, and teardown. Job seconds include Actions setup and post-job work. Queue seconds are run creation to job start; this timestamp difference does not identify why a runner waited.

| Lane | Passed / skipped / xfailed | Pytest seconds | Job seconds | Queue seconds |
|---|---:|---:|---:|---:|
| python | 4470 / 2 / 1 | 936.76 | 980 | 8 |
| m0-lineage | 4 / 0 / 0 | 437.98 | 471 | 8 |
| m0-replay | 2 / 0 / 0 | 386.30 | 413 | 8 |
| m0-transcript | 3 / 0 / 0 | 453.43 | 496 | 431 |
| m0-boundaries | 8 / 0 / 0 | 545.17 | 575 | 996 |
| gateplan | 28 / 0 / 0 | 638.03 | 680 | 936 |
| lean-core | 121 / 0 / 0 | 552.51 | 668 | 1624 |
| lean-replay | 1 / 0 / 0 | 640.15 | 822 | 11 |
| solution | 18 / 0 / 0 | 397.08 | 543 | 1252 |
| solution-library-dlp | 1 / 0 / 0 | 814.91 | 932 | 10 |
| solution-library-finite-point | 1 / 0 / 0 | 648.65 | 765 | 950 |
| solution-library-binding | 1 / 0 / 0 | 136.97 | 281 | 1581 |
| solution-plan-exact | 1 / 0 / 0 | 833.83 | 976 | 842 |
| solution-plan-refusals | 2 / 0 / 0 | 635.54 | 756 | 488 |
| container | 35 / 0 / 0 | 693.74 | 834 | 6 |
| container-replay-exact | 2 / 0 / 0 | 462.27 | 595 | 6 |
| container-replay-refusals | 4 / 0 / 0 | 551.08 | 688 | 8 |
| container-plan-exact | 1 / 0 / 0 | 447.45 | 585 | 7 |
| container-plan-refusals | 3 / 0 / 0 | 509.25 | 644 | 6 |

Run creation was 19:24:06 UTC and the final job completed at 20:02:18 UTC, an elapsed 38 minutes 12 seconds. Each individual job remained below 20 minutes. The 27-minute-4-second Lean-core queue interval is distinct from its 11-minute-8-second execution. More leaves permit bounded jobs but consume runner slots; these observations do not establish that further partitioning improves whole-workflow latency.

The two skipped nodes are the live gatherer and renderer checks in `test_audit_missing_items_drift.py`; their external compliance skill is absent from CI. The xfailed node is `test_the_corpus_bars_are_met`. The largest M0 call phases were 235.54 seconds for cache bypass, 227.31 for different seeds, and 218.99 for refusal remediation. These completed real-work calls exceed the 180-second default while remaining within their 600-second markers. The DLP and finite-point development-arm passes establish no `PROVEN` claim.

The parent independently extracted all summaries, durations, and step metadata from the [complete job log](lane-partition/raw/afternoon-terminal.log.gz) and [terminal metadata](lane-partition/raw/afternoon-terminal.json.gz). The [profile](lane-partition/raw/afternoon-profile.json.gz) retains collected/deselected counts, top durations, provisioning/cache step times, and source lines. The [adapter](lane-partition/raw/afternoon-profile_nineteen.py.gz) uses the pinned historical extractor with the exact 19-leaf manifest from `9f68240`; it refuses a nonterminal run, failed run, missing lane, and failed job. [The refusal receipt](lane-partition/raw/afternoon-profile-result.log.gz) records all four expected diagnostics. Independent per-job extraction agrees with the parent summaries. This is evidence for the pushed source SHA, not for queued descendant code.

## Ownership and measured runs

The 13-lane source measurements below inventory `m0`, `gateplan`, and `solution-library`. Run `36604519180` is a terminal failure: nine jobs passed, M0 and Python failed, and solution-library and Lean were canceled. Partial observations remain bounded to that run and are not green evidence.

| Lane | Collected cases | Run evidence |
|---|---:|---|
| `m0` | 17 from `tests/e2e/test_m0_slice.py` | Peer run: 17 passed in 826.21 s; peak footprint 0.21 GiB. The JUnit case-time sum is 826.07 s. |
| `gateplan` | 28: 19 in `tests/integration/test_gateplan.py`, 7 in `tests/integration/test_gateplan_cli.py`, and 2 in `tests/integration/test_ladder_gate_selftest.py` | These cases have a JUnit duration sum of 271.49 s. A separate, broader peer batch passed 125 tests in 273.79 s with 0.14 GiB peak footprint; that batch duration is not a lane-only measurement. |
| `solution-library` | 3 in `tests/integration/test_challenge_gate.py` | Peer run: 3 passed in 559.09 s; peak footprint 1.37 GiB. Two library items passed the development-gate checks; a stale formal statement hash stopped at statement binding without a subprocess. No item reached the gold arm, so this is not a `PROVEN` result. |

The M0 and GatePlan test sources are present in commit `9540b6ad8870c6743e7705e5eb92f09c34032996`; the library test source is in `79992cdcd04688274c41ec261e8a533df426cc69`. The M0/GatePlan run's final-tree receipt records head `bf3d9eda9ba053b43aaf394040e74607056e4c45` and file digests. The 48-node baseline collection was run against an isolated snapshot at `79992cdcd04688274c41ec261e8a533df426cc69`.

During the library run, `bundle/gate_plan.json` had an uncommitted edit associated with another lane. The library tests supplied their own plan rows, so that edit was not their plan input. The measured runs were separate peer runs on a shared host. Their durations do not measure one combined CI job, a quiet-host benchmark, or a speedup.

## Local routing verification

The local population receipt records exactly the 48 baseline node IDs in disjoint lanes: 17 `m0`, 28 `gateplan`, and 3 `solution-library`; none of those 48 belongs to `python`. The routing-contract suite passed 288 tests in 41.58 s, with 23 pytest cleanup warnings from retained scratch belonging to an earlier cleanup-contract run and no skips. It includes 30 Lean-provisioning negative cases and selected-failure coverage. The exact-condition Lean-setup contract has a focused receipt of 98 passed in 0.12 s with no warnings. Those 98 tests overlap with the 288-test run and are not an additional disjoint count. The raw population, contract, wrong-owner, setup-rerun, exclusion-refusal, and tested-tree receipts are in [`lane-partition/raw/`](lane-partition/raw/).

The measured three-module invocation used this working directory and command:

```bash
cd /tmp/cairn-day-lane3.uMzz8z/partition-verify
PYTHONPATH=/tmp/cairn-day-lane3.uMzz8z/partition-verify/src:/tmp/cairn-day-lane3.uMzz8z/partition-verify/tests PYTEST_DEBUG_TEMPROOT=/tmp/cairn-day-lane3.uMzz8z/db-test-tmp uv run --no-project /Users/jwross/Documents/cairn/.venv/bin/python -m pytest -q tests/unit/test_ci_lanes.py tests/unit/test_lean_ci_setup.py tests/hook_contract/test_ci_lane_dispatch.py
```

The focused setup invocation used:

```bash
cd /Users/jwross/Documents/cairn
PYTHONPATH=/tmp/cairn-day-lane3.uMzz8z/partition-verify/src:/tmp/cairn-day-lane3.uMzz8z/partition-verify/tests PYTEST_DEBUG_TEMPROOT=/tmp/cairn-day-lane3.uMzz8z/partition-setup-tmp uv run --no-project /Users/jwross/Documents/cairn/.venv/bin/python -m pytest -q /tmp/cairn-day-lane3.uMzz8z/partition-verify/tests/unit/test_lean_ci_setup.py
```

The planted wrong-owner run moved `m0` to `python`. Its collection command returned pytest exit 5 with no tests collected, and the lane ownership contract failed as expected. A planted `solution-library` exclusion also exited 1 at the exact-condition assertion. The final local fast check passed on the recorded final tree. An AST-equivalence check passed for the earlier formatting-only edits to three test files; the later assertion strengthening has its separate focused test receipt. The final tree receipt is headed at `822498a3beca1eefcba55c3a25fd45eb68bd4f78`. The pushed CI result is incomplete; the M0 failure and passing GatePlan job are recorded below.

The listed counts come from the full 48-node baseline collection; this partition report does not establish that tests elsewhere were never deleted, skipped, or sampled. The 1080-second session limit and 20-minute job limit are unchanged. Historical ten-lane profiles remain historical evidence. The separate Lean runtime observation is recorded in [timeout-evidence.md](timeout-evidence.md).

The verified 82.857811-second Lean receipt is CI run `36596493998` at `2de797830071146bc4433983e8ff8e5d3f90bebe`. The attribution to `90401ee` in the body of commit `822498a` does not identify that receipt. The corresponding 177.537110-second receipt is run `36598858989` at `0e9b47018c788df4904b836865deab755b814429`.

## Pushed CI evidence

CI run `36604519180` tested `6953d46a33b70fd66f0ac404168f5fcd88e8bb3d`, which contains lane commit `8c23c7d65205e6f2cfb30af67c77613eb54d2826`. Their diff across the eight owned paths is empty. The M0 job collected 17 selected tests; the first three passed, and the fourth reached pytest's 180 s per-test timeout. Its stack was in `cairn.runner.spawn_and_wait`, not at the 1080 s session deadline.

| M0 test | CI phase-start to result | Peer JUnit time |
|---|---:|---:|
| `test_the_operator_sequence_produces_four_nodes_two_negatives_and_one_refusal` | 120.914 s, passed | 43.598 s |
| `test_the_slice_records_its_hypothesis_object_and_the_derivation_lineage` | 122.276 s, passed | 50.198 s |
| `test_the_derivation_commits_to_the_x_the_generator_output_determines` | 98.081 s, passed | 49.523 s |
| `test_the_same_seed_replays_from_cache_without_another_toy_curve_attempt` | 180.090 s, timed out | 89.027 s |

The intervals use each CI JSONL `phase=start` timestamp and the matching job outcome line; the peer values come from `ladder-m0.xml`. In the timed-out test log, `step=runner,event=exit` has 784 records totaling 150.456756 s, with a maximum of 2.722107 s. `step=gp,event=exit` has 693 records totaling 16.327351 s, with a maximum of 0.157757 s. The logger records 2,353 total `runner`-step events. Its tail writes a `RUNNING` attempt and then an escrow insert, with no completion record for that attempt. This identifies the outstanding wait at timeout but does not establish its cause.

The peer M0 run passed all 17 tests in 826.21 s with 0.21 GiB peak footprint. The separate GatePlan CI job passed 28 tests in 658.07 s. CI job `109530013940` tested commit `6953d46a33b70fd66f0ac404168f5fcd88e8bb3d` and selected all three `solution-library` cases. The DLP case passed in 759,148.608 ms overall; its recorded steps were statement binding 0 ms, import allowlist 1 ms, build 41,833.014 ms, axiom computation 75,264 ms, kernel replay 375,606 ms, and closure comparison 66,344 ms. The `finite_point` case completed statement binding (0 ms), import allowlist (0 ms), build (41,147.468 ms), and axiom computation (56,347 ms). Its last JSONL event spawned `lake ... env leanchecker --fresh -v Solution.S_c8d4bddcdf9af0c1`; no exit event for that process, kernel-replay step result, or test phase-end was recorded before the 1080-second session watchdog fired at 17:43:13 UTC. The stale-hash case was unrun. The recorded failure is the session-deadline timeout. DLP development-gate passage does not establish a gold result or `PROVEN` claim. The remaining CI jobs' terminal states are not established here, so there is no whole-workflow green result. These separate runs establish neither a speedup nor a cause or flake.

Python job `109530013989` tested the same commit and selected 4,310 tests; its result was 1 failed, 4,306 passed, 2 skipped, and 1 xfailed, with 236 deselected, in 974.46 s. Its only failure was `tests/unit/test_gateplan_fuzz.py::test_a_ten_thousand_step_plan_is_refused_on_the_first_duplicate_not_by_running_out_of_memory` at line 114: the assertion expected `duplicate-step-name:7.` while the raised message was `duplicate-step-name:9.canon_kat`, the first duplicate in the committed nine-step plan. The job records the mismatch; this report does not infer a broader cause. Skips and xfails remain separate outcomes, not passes.

The raw M0 job log, four per-test JSONLs, GatePlan job log, peer M0 XML/log, Python [job log](lane-partition/raw/ci-109530013989-python-job.log.gz), and `solution-library` [job log](lane-partition/raw/ci-109530013940-solution-library-job.log.gz), [DLP JSONL](lane-partition/raw/ci-109530013940-solution-library-dlp.jsonl.gz), and [interrupted `finite_point` JSONL](lane-partition/raw/ci-109530013940-solution-library-finite-point.jsonl.gz) are preserved under [`lane-partition/raw/`](lane-partition/raw/). The manifest records original source paths and hashes.

## Afternoon capacity measurements

Run `36608535105` at `2e31531d4d211ee41e23ec9700e173505dfd8387` completed with 11 passing jobs, a failing M0 job, and a canceled solution-library job. Python and Lean passed. These outcomes supersede the earlier run's status for those two lanes; they do not establish a passing whole workflow.

M0 job `109543708095` passed the operator case in approximately 108.9 seconds, then hit the 180-second per-test limit in the lineage case. The stack passed through the real ladder baseline to `runner.spawn_and_wait`. The earlier run timed out in the two-invocation cache-replay case. The outstanding wait's cause is unestablished. A lane split addresses aggregate capacity but cannot by itself change this per-test limit.

The four M0 partitions preserve all 17 collected IDs. Their peer-run JUnit sums are 194.362 seconds for lineage, 196.856 for replay, 200.660 for transcript, and 234.188 for boundaries. Applying the observed approximate two-to-three-times CI/local ratio gives planning ranges of 389–583, 394–591, 401–602, and 468–703 seconds. These are projections, not measurements of the partitions. The full-M0 tests use a 600-second test budget, matching the existing module-entry test's 600-second subprocess budget. The early refusal and certification-only cases retain the 180-second default; only the full-plan uncertified-skill refusal parameter receives 600 seconds. The 1080-second session and 20-minute job limits remain fixed.

Solution-library job `109543708066` selected all three cases. DLP passed in 615.133467 seconds; build, axiom computation, fresh replay, and closure comparison recorded 50.218, 76.314, 284.104, and 48.462 seconds respectively. Finite-point completed its build and axiom computation in 43.205 and 49.587 seconds, then spawned fresh replay without a recorded exit before the shared session deadline. The binding-refusal case was unrun. Each library case has an independent leaf job, with the aggregate command retaining all three cases.

The new leaves use macOS. M0's refusal setup directly calls `os.chflags`; bundle and attestation pinning log a weaker mode-bits-only boundary on platforms without that API. The library fixture also uses bundle pinning. Linux installer availability alone does not establish equivalent runtime boundaries. The five existing container leaves retain their Linux runners.

The passing Lean job contains 122 tests in 919.79 seconds. Fresh-replay forgery alone accounts for 343.61 seconds of call time, 97.40 seconds of setup, and 5.07 seconds of teardown. The `lean-replay` leaf owns that one case; `lean-core` owns the other 121, including the weaker-statement comparison. The local `lean` aggregate preserves their union. The 446.08-second replay portion and approximately 473.71-second remainder support an expected 9–13 wall minutes per leaf, allowing approximately two minutes for job setup and additional timing variation. This partition addresses the earlier 20-minute cancellation; the estimates do not prove independent-job durations or savings. The complete layout has 19 leaf jobs and six local aggregate selections.

Expected planning ranges per run are 7–11 wall minutes each for `m0-lineage`, `m0-replay`, and `m0-transcript`, and 9–13 for `m0-boundaries`. These include approximately one minute of setup on top of the projected test durations. Expected library ranges are 12–16 wall minutes for `solution-library-dlp`, 10–16 for `solution-library-finite-point`, and 4–6 for `solution-library-binding`. DLP uses the two observed 615/759-second case durations plus approximately two minutes of setup. The [peer library log](lane-partition/raw/lib-gate.log.gz) records call times of 269.24 seconds for DLP, 243.38 for finite-point, and 35.16 for binding. Finite-point's planning range applies the approximate two-to-three-times CI/local factor plus setup; its complete CI duration remains unmeasured. Binding uses its peer duration and the conservative measured DLP preparation interval of approximately 118 seconds plus setup; its own complete CI duration is unmeasured. Every leaf retains the 20-minute job ceiling. These ranges estimate runner occupancy, not cost or demonstrated savings.

`gh repo view --json visibility,nameWithOwner` reports `jwross24/cairn` as `PUBLIC`. [GitHub's billing policy](https://docs.github.com/en/billing/concepts/product-billing/github-actions) makes standard hosted runner usage free for public repositories. The ten-times billed-minute projections in commit `9f68240` therefore do not represent this repository's runner cost. Nineteen leaves consume concurrent runner slots and can increase queue time even when each job completes within its ceiling. The policy and repository visibility were checked on 2026-09-29; this observation makes no claim about separately metered storage.

The [run metadata](lane-partition/raw/ci-36608535105-terminal.json.gz), [M0 log](lane-partition/raw/ci-109543708095-m0.log.gz), [library log](lane-partition/raw/ci-109543708066-library.log.gz), [DLP trace](lane-partition/raw/ci-109543708066-dlp.jsonl.gz), [finite-point trace](lane-partition/raw/ci-109543708066-finite-point.jsonl.gz), and [Lean log](lane-partition/raw/ci-109543708027-lean.log.gz) retain the observations. The [baseline collection](lane-partition/raw/afternoon-baseline-collection.log.gz) records the 20 M0/library IDs at `6bd16aa` before the partition.

Parent verification used an isolated `6bd16aa` snapshot with only the M0 timeout metadata overlaid. All function bodies are AST-identical. Collection retains the exact 17 IDs, with 13 full-plan cases at 600 seconds and four early/certification cases at 180. Removing the lineage marker in a scratch copy makes verification refuse with `effective timeout 180, expected 600`. The real lineage and same-seed replay cases passed in 115.65 seconds total under the heavy-run lock and 6 GiB memcap; peak footprint was 0.13 GiB. Their call times were 39.79 and 75.33 seconds. The run emitted 2,101 pytest cleanup warnings, all from attempts to remove preexisting protected scratch directories in the shared system temp root. No warning is counted as test evidence; subsequent checks use a dedicated temp root. These local passes do not replace pushed CI.

## Parent partition verification

The verified snapshot is `88e8d4fbf233fbc9e29a707e3e733a8a59c562e5` with the nine owned source/doc files listed in [the source receipt](lane-partition/raw/afternoon-verified-source.json.gz). The parent reviewed every changed line. The three contract modules passed 451 tests in 70.58 seconds. Six additional aggregate-selection refusal parameters passed in a focused 69-test invocation, which overlaps 63 of the 451 cases. These are 457 unique validated contract cases, not 520. Both runs have no skips. The implementer's independent final invocation also passed all 457 cases.

Real collection across the nine affected leaves preserves all 142 baseline IDs exactly once: M0 4/2/3/8, Lean 121/1, and library 1/1/1. A scratch mutation removing one lineage owner fails the ownership contract with `assert 3 == 4`. Unknown library items cause `UsageError` in all five supported selections; the five outer refusal tests pass. The scoped fast check passes all five gates. These contracts establish dispatch and setup behavior; they do not establish complete execution of the heavy leaves or a green pushed workflow.

The [contract log](lane-partition/raw/afternoon-parent-contracts-final.log.gz), [aggregate refusals](lane-partition/raw/afternoon-parent-alias-refusals.log.gz), [partition receipt](lane-partition/raw/afternoon-parent-partition.json.gz), [wrong-owner refusal](lane-partition/raw/afternoon-parent-wrong-owner-final.log.gz), [unknown-item refusals](lane-partition/raw/afternoon-parent-unknown-item.log.gz), and [fast checks](lane-partition/raw/afternoon-parent-fast.log.gz) retain the parent results.

## Raw evidence

The [terminal run metadata](lane-partition/raw/partition-ci-current.json.gz) records all 13 job outcomes at `6953d46`. Lean job `109530014204` started at 17:34:52 UTC and completed at 17:55:25 UTC. Its [annotations](lane-partition/raw/partition-lean-annotations.json.gz) explicitly report that the job exceeded the maximum execution time of 20m0s. The [Lean job log](lane-partition/raw/partition-lean-job.log.gz) records cancellation at 17:55:08 UTC, after gates started at 17:37:11 UTC, without a session-timeout marker. The weaker-statement case passed at 17:45:36 UTC and the fresh-replay forgery case passed at 17:54:31 UTC; the lane reached 44% and has no complete pytest result. These partial passes do not establish a passing lane or a `PROVEN` result. PearlWolf's stale-index test correction is committed at `2e31531`; this run does not verify that correction.

Peer-run stdout, JUnit XML, final-tree metadata, and baseline collection output are preserved losslessly as gzip files under [`lane-partition/raw/`](lane-partition/raw/). [`lane-partition/raw/manifest.json`](lane-partition/raw/manifest.json) records each original and archive byte length and SHA-256 digest. The parent inspected these inputs; the parent did not run the measured heavy tests.
