# Owner-directed test-lane partition evidence

This record inventories the three dedicated lanes `m0`, `gateplan`, and `solution-library` within the 13-lane layout. Local ownership checks and planted refusals pass; pushed CI verification remains pending.

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

The planted wrong-owner run moved `m0` to `python`. Its collection command returned pytest exit 5 with no tests collected, and the lane ownership contract failed as expected. A planted `solution-library` exclusion also exited 1 at the exact-condition assertion. The final local fast check passed on the recorded final tree. An AST-equivalence check passed for the earlier formatting-only edits to three test files; the later assertion strengthening has its separate focused test receipt. The final tree receipt is headed at `822498a3beca1eefcba55c3a25fd45eb68bd4f78`. CI remains pending, so this report does not claim CI green.

The listed counts come from the full 48-node baseline collection; this partition report does not establish that tests elsewhere were never deleted, skipped, or sampled. The 1080-second session limit and 20-minute job limit are unchanged. Historical ten-lane profiles remain historical evidence. The separate Lean runtime observation is recorded in [timeout-evidence.md](timeout-evidence.md).

The verified 82.857811-second Lean receipt is CI run `36596493998` at `2de797830071146bc4433983e8ff8e5d3f90bebe`. The attribution to `90401ee` in the body of commit `822498a` does not identify that receipt. The corresponding 177.537110-second receipt is run `36598858989` at `0e9b47018c788df4904b836865deab755b814429`.

## Raw evidence

Peer-run stdout, JUnit XML, final-tree metadata, and baseline collection output are preserved losslessly as gzip files under [`lane-partition/raw/`](lane-partition/raw/). [`lane-partition/raw/manifest.json`](lane-partition/raw/manifest.json) records each original and archive byte length and SHA-256 digest. The parent inspected these inputs; the parent did not run the measured heavy tests.
