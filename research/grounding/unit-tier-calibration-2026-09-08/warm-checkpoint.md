# Collection warm checkpoint

Status: unverified against the 60-second unit-command target. No bead close.
Exact hold: `--unit under-60 close run needs a quiet box: no other pytest, 1-minute load under 10`.

`tests/conftest.py` warms the shared bead store at collection finish when a selected
module consumes it, except for collect-only. Its elapsed time is logged and remains
inside pytest and command wall time. The consumer inventory is checked against
direct imports under `tests/`. An unavailable store fails the session loudly.

The real cold/cached probe exits 0: 16.569622540999262 seconds cold and
0.0000053340045269578695 seconds cached, one miss and one hit, same workspace.
The explicit command and raw result are in `warm-checkpoint-evidence.tar.gz`.
This demonstrates an order-dependent cache cost; it is not controlled attribution
of the 15.75-second call in the earlier unit command. Session-scoped fixtures
remain inside the first item's setup timing, so collection finish owns the warm.

## Command result and exclusions

Every path below is a member of `warm-checkpoint-evidence.tar.gz`.

- `unit-resume-full-cr1n5td8`: `scripts/check.sh --unit` exits 0 in
  145.40027104099863 seconds. Raw pytest: 1,989 passed, 265 deselected in 135.60
  seconds. Outside-pytest command time is 9.80027104099863 seconds; collection
  and import are inside pytest wall and are not separately established here.
  The command misses 60 seconds. Starting disk availability was 72 GiB.
- `unit-current-calibration-qy4sbm01/run-1`: exits 0 in 424.6427815000061 seconds
  of wrapper time. No required before/after load captures, so no median vote.
  The during-run capture at approximately 03:57 UTC shows this lane's pytest
  only; load was 27.93/40.04/31.58. A during-run observation proves neither endpoint.
- `unit-current-calibration-qy4sbm01/run-2`: deliberately interrupted, pytest
  exit 2, wrapper time 118.91035470800125 seconds. No passing-result claim.
- `unit-load-captured-virv5zoz/run-1`: one failure, 2,309 passes in 374.53
  seconds; wrapper 384.885459582998 seconds, exit 1. The API guard rejects extra
  `inputs_for_attempt`; CopperRidge 1252 assigns that guard to C2. Before capture
  at 04:04 UTC has no pytest process and load 40.12/40.65/34.91. After capture at
  04:10 UTC contains peer full-suite PID 20323, solution-forgery and collection
  runs; load 25.95/30.28/31.83. Excluded for failure and contention. Run 2 is
  interrupted; its wrapper exits 143 before saving result metadata.
- `unit-load-captured-p55o17id/run-1`: interrupted after a warm-test failure.
  The nested importer collision is reproduced and corrected in the tests.
  Initial load capture is unavailable after interruption. No median vote.
- `unit-load-captured-d98huiib/run-1`: interrupted and flagged contended by
  CopperRidge 1304 at 04:33 UTC. The 04:38–04:44 UTC monitor retains full-suite
  PID 3350 and later integration PID 13268. No median vote. CopperRidge 1329
  closes the window at 04:44 UTC and reports load 87 on 10 cores; that figure is
  coordinator-reported, not an independent measurement by this lane.

Qualifying fresh reports: zero. `calibration.json` retains its historical reports
and threshold; it does not count any attempt above. Quiet-window monitoring scripts
are included for reproducibility. Interrupted reports lack complete end metadata.

## Verification

```bash
UV_CACHE_DIR=/tmp/cairn-runtimemoth.U7GUPL/uv-cache uv run --no-sync pytest -q tests/unit/test_br_lookup.py tests/unit/test_check_unit_tier.py --basetemp=/tmp/cairn-runtimemoth.U7GUPL/warm-mixed-fixed-x26vrnh2/pytest
UV_CACHE_DIR=/tmp/cairn-runtimemoth.U7GUPL/uv-cache uv run --no-sync pytest -q tests/unit/test_check_unit_tier.py --basetemp=/tmp/cairn-runtimemoth.U7GUPL/warm-final-tests-mtf0rmxc/pytest
UV_CACHE_DIR=/tmp/cairn-runtimemoth.U7GUPL/uv-cache scripts/check.sh --fast --paths tests/conftest.py tests/unit/test_check_unit_tier.py
```

Fresh temporary basetemps are named in the raw logs' containing directories.
Mixed selection: 32 passed in 26.89 seconds, exit 0. Final named file: 20 passed
in 6.72 seconds, exit 0. Scoped fast gates pass. The fresh read-only audit's
same-name import finding has an exit-0 wrapper reproduction: inner pytest runs
12 real tests instead of one synthetic test, outer pytest exits 1. The synthetic
consumer has a separate namespace; the positive test retains the real-module
import premise and asserts a numeric warm-duration line.

UBS scans byte-equal copies of both changed Python files, exit 0: two files,
zero critical findings, four warnings. Two warnings duplicate the fixture's
intentional JSON error propagation; the open-call regex counts the
`GuardedPopen` class declaration; the deprecated-import regex matches the
`import importlib` prefix. The raw scan and root's byte/hash and rule probes
are included. No warning warrants a source change on that evidence.

Checkpoint `3c47511317cacd34edb1934ad9859b17c480950e` has CI 34292069355 success:
3,627 passed, five skipped, one xfailed in 690.14 seconds. That CI result precedes
this collection-warm checkpoint and does not validate its changes.

No-Claim: under-60 unit completion, fresh uncontended calibration, a causal
full-suite speedup, timing portability, or passes for skipped/unrun work.
