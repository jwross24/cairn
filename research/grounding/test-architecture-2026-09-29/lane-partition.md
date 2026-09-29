# Owner-directed test-lane partition evidence

This record inventories the three dedicated lanes `m0`, `gateplan`, and `solution-library` within the 13-lane layout. Local ownership checks pass. Pushed CI run `36604519180` is a terminal failure: nine jobs passed, M0 and Python failed, and solution-library and Lean were canceled. The partial observations below describe the evidence gathered while that run was active.

## Ownership and measured runs

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

The passing Lean job contains 122 tests in 919.79 seconds. Fresh-replay forgery alone accounts for 343.61 seconds of call time, 97.40 seconds of setup, and 5.07 seconds of teardown. The `lean-replay` leaf owns that one case; `lean-core` owns the other 121, including the weaker-statement comparison. The local `lean` aggregate preserves their union. The 446.08-second replay portion and approximately 473.71-second remainder support an expected 90–130 billed macOS minutes per leaf, allowing approximately two minutes for job setup and additional timing variation. This partition addresses the earlier 20-minute cancellation; the estimates do not prove independent-job durations or savings. The complete layout has 19 leaf jobs and six local aggregate selections.

At the owner's ten-times macOS billing multiplier, expected planning ranges per run are 70–110 billed minutes each for `m0-lineage`, `m0-replay`, and `m0-transcript`, and 90–130 for `m0-boundaries`. These include approximately one minute of setup on top of the projected test durations. Expected library ranges are 120–160 billed minutes for `solution-library-dlp`, 100–160 for `solution-library-finite-point`, and 40–60 for `solution-library-binding`. DLP uses the two observed 615/759-second case durations plus approximately two minutes of setup. The [peer library log](lane-partition/raw/lib-gate.log.gz) records call times of 269.24 seconds for DLP, 243.38 for finite-point, and 35.16 for binding. Finite-point's planning range applies the approximate two-to-three-times CI/local factor plus setup; its complete CI duration remains unmeasured. Binding uses its peer duration and the conservative measured DLP preparation interval of approximately 118 seconds plus setup; its own complete CI duration is unmeasured. Every leaf retains the 200-billed-minute job ceiling. These ranges are estimates for capacity and cost, not demonstrated savings.

The [run metadata](lane-partition/raw/ci-36608535105-terminal.json.gz), [M0 log](lane-partition/raw/ci-109543708095-m0.log.gz), [library log](lane-partition/raw/ci-109543708066-library.log.gz), [DLP trace](lane-partition/raw/ci-109543708066-dlp.jsonl.gz), [finite-point trace](lane-partition/raw/ci-109543708066-finite-point.jsonl.gz), and [Lean log](lane-partition/raw/ci-109543708027-lean.log.gz) retain the observations. The [baseline collection](lane-partition/raw/afternoon-baseline-collection.log.gz) records the 20 M0/library IDs at `6bd16aa` before the partition.

Parent verification used an isolated `6bd16aa` snapshot with only the M0 timeout metadata overlaid. All function bodies are AST-identical. Collection retains the exact 17 IDs, with 13 full-plan cases at 600 seconds and four early/certification cases at 180. Removing the lineage marker in a scratch copy makes verification refuse with `effective timeout 180, expected 600`. The real lineage and same-seed replay cases passed in 115.65 seconds total under the heavy-run lock and 6 GiB memcap; peak footprint was 0.13 GiB. Their call times were 39.79 and 75.33 seconds. The run emitted 2,101 pytest cleanup warnings, all from attempts to remove preexisting protected scratch directories in the shared system temp root. No warning is counted as test evidence; subsequent checks use a dedicated temp root. These local passes do not replace pushed CI.

## Parent partition verification

The verified snapshot is `88e8d4fbf233fbc9e29a707e3e733a8a59c562e5` with the nine owned source/doc files listed in [the source receipt](lane-partition/raw/afternoon-verified-source.json.gz). The parent reviewed every changed line. The three contract modules passed 451 tests in 70.58 seconds. Six additional aggregate-selection refusal parameters passed in a focused 69-test invocation, which overlaps 63 of the 451 cases. These are 457 unique validated contract cases, not 520. Both runs have no skips. The implementer's independent final invocation also passed all 457 cases.

Real collection across the nine affected leaves preserves all 142 baseline IDs exactly once: M0 4/2/3/8, Lean 121/1, and library 1/1/1. A scratch mutation removing one lineage owner fails the ownership contract with `assert 3 == 4`. Unknown library items cause `UsageError` in all five supported selections; the five outer refusal tests pass. The scoped fast check passes all five gates. These contracts establish dispatch and setup behavior; they do not establish complete execution of the heavy leaves or a green pushed workflow.

The [contract log](lane-partition/raw/afternoon-parent-contracts-final.log.gz), [aggregate refusals](lane-partition/raw/afternoon-parent-alias-refusals.log.gz), [partition receipt](lane-partition/raw/afternoon-parent-partition.json.gz), [wrong-owner refusal](lane-partition/raw/afternoon-parent-wrong-owner-final.log.gz), [unknown-item refusals](lane-partition/raw/afternoon-parent-unknown-item.log.gz), and [fast checks](lane-partition/raw/afternoon-parent-fast.log.gz) retain the parent results.

## Raw evidence

The [terminal run metadata](lane-partition/raw/partition-ci-current.json.gz) records all 13 job outcomes at `6953d46`. Lean job `109530014204` started at 17:34:52 UTC and completed at 17:55:25 UTC. Its [annotations](lane-partition/raw/partition-lean-annotations.json.gz) explicitly report that the job exceeded the maximum execution time of 20m0s. The [Lean job log](lane-partition/raw/partition-lean-job.log.gz) records cancellation at 17:55:08 UTC, after gates started at 17:37:11 UTC, without a session-timeout marker. The weaker-statement case passed at 17:45:36 UTC and the fresh-replay forgery case passed at 17:54:31 UTC; the lane reached 44% and has no complete pytest result. These partial passes do not establish a passing lane or a `PROVEN` result. PearlWolf's stale-index test correction is committed at `2e31531`; this run does not verify that correction.

Peer-run stdout, JUnit XML, final-tree metadata, and baseline collection output are preserved losslessly as gzip files under [`lane-partition/raw/`](lane-partition/raw/). [`lane-partition/raw/manifest.json`](lane-partition/raw/manifest.json) records each original and archive byte length and SHA-256 digest. The parent inspected these inputs; the parent did not run the measured heavy tests.
