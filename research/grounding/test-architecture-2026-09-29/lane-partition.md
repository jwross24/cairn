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

## Raw evidence

The [terminal run metadata](lane-partition/raw/partition-ci-current.json.gz) records all 13 job outcomes at `6953d46`. Lean job `109530014204` started at 17:34:52 UTC and completed at 17:55:25 UTC. Its [annotations](lane-partition/raw/partition-lean-annotations.json.gz) explicitly report that the job exceeded the maximum execution time of 20m0s. The [Lean job log](lane-partition/raw/partition-lean-job.log.gz) records cancellation at 17:55:08 UTC, after gates started at 17:37:11 UTC, without a session-timeout marker. The weaker-statement case passed at 17:45:36 UTC and the fresh-replay forgery case passed at 17:54:31 UTC; the lane reached 44% and has no complete pytest result. These partial passes do not establish a passing lane or a `PROVEN` result. PearlWolf's stale-index test correction is committed at `2e31531`; this run does not verify that correction.

Peer-run stdout, JUnit XML, final-tree metadata, and baseline collection output are preserved losslessly as gzip files under [`lane-partition/raw/`](lane-partition/raw/). [`lane-partition/raw/manifest.json`](lane-partition/raw/manifest.json) records each original and archive byte length and SHA-256 digest. The parent inspected these inputs; the parent did not run the measured heavy tests.
