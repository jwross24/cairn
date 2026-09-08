# CI runtime and unit-tier measurements

Consumer: CopperRidge's acceptance of cairn-1s2 and cairn-sm1.3, requested by the operator
on 2026-09-08. These measurements retire when their source revisions cease to inform that decision.
Raw logs and run metadata live in `ci-runtime-2026-09-08/`; `.log.gz` files contain complete output.

## CI observations

Confidence: HIGH. Verified: 2026-09-08 through `gh run view <id> --log` and
`gh run view <id> --json headSha,jobs,conclusion`. The three runs report success, each with
3230 passed, 5 skipped, and 1 xfailed. Skips and expected failures are not passing tests.

| Run / source | Pytest seconds | Setup before Gates | Entire job | Pytest / job margin |
|---|---:|---:|---:|---:|
| 34217624693 / `5ba81debac9b3420a41febbf4243c7cfca1b19e4` | 805.77 | 47 | 866 | 274.23 / 334 |
| 34219024235 / `dda120bd5636d8ebcb4d6cca0f58835617e5160c` | 895.54 | 71 | 977 | 184.46 / 223 |
| 34220624975 / `d5c4939e776b124c22fe0846d478d91891e829b2` | 946.24 | 62 | 1021 | 133.76 / 179 |

Margins use the 1080-second session deadline and 1200-second job ceiling. Job duration includes
setup and cleanup; setup measures job start to the Gates step. The 15-second watchdog backstop
also consumes job headroom when the session deadline expires. These cache-hit runs do not bound
a cold Lean toolchain installation or a slower runner.

The top three test calls account for 191.45, 245.01, and 265.99 seconds respectively:

| Test | 34217624693 | 34219024235 | 34220624975 |
|---|---:|---:|---:|
| `test_real_axiom_matrix` | 67.06 | 101.58 | 115.58 |
| `test_twenty_fresh_forty_bit_instances_drawn_by_postcondition_are_recovered` | 71.24 | 72.63 | 88.07 |
| `test_hello_theorem_builds_and_leanchecker_replays_it_from_empty` | 53.15 | 70.80 | 62.34 |

These tests exercise seven axiom fixtures, twenty fresh 40-bit instances, and both normal and
fresh Lean replay. Their bodies contain required independent executions. They are outside this
lane's edit ownership; the timing observations alone do not authorize removing any execution.
The hasher fresh-build call varies from 7.65 to 33.58 seconds. Cross-run differences are not
paired optimization evidence because source and runner conditions differ.

## Shared isolation snapshot

Confidence: HIGH for the paired local measurement; CONJECTURE for CI savings.
Source baseline: `dfa4445886c03a15905640ab88b9cdd179ffdad3`, `tests/conftest.py`.
The snapshot checks every guarded file's size and modification timestamp before and after
each test. Its traversal uses `os.scandir`, lexical relative names, and fresh file stats;
directory links inside a guarded root are not traversed. Guarded roots themselves may be links.

Seven paired batches of 50 snapshots cover the same 161 files, asserting dictionary equality
on every call. Median time per snapshot is 4.510 ms for the baseline and 2.381 ms for the
candidate, a 47.2% reduction. The denominator is one snapshot; the countermetric is exact
equality of every path, size, and timestamp. No whole-suite or CI speedup is established.

```bash
scratch=$(mktemp -d)
git show dfa4445886c03a15905640ab88b9cdd179ffdad3:tests/conftest.py > "$scratch/conftest.py"
uv run python research/grounding/ci-runtime-2026-09-08/probe_snapshot.py --before "$scratch/conftest.py"
uv run pytest -q tests/unit/test_isolation_snapshot.py tests/unit/test_golden_harness.py --durations=0
```

The targeted result is 10 passed in 0.21 seconds. Coverage includes nested files, file and
directory links, broken links, link loops, FIFOs, missing roots, unreadable directories, and
observable file mutation. Existing planted writes under `deploy/` and forbidden subprocesses
still produce pytest errors/failures inside the guard tests. A snapshot is not an atomic
filesystem view; this measurement makes no concurrent-writer guarantee.

## Unit observations

Confidence: HIGH for the observed runs; attribution of their full difference is unverified.
The baseline command `uv run pytest tests/unit -q --durations=0` reports 1955 passed in
108.34 seconds, with 1331 temp-cleanup warnings. The candidate with a fresh `--basetemp`
reports 1961 passed in 87.52 seconds. Six additional cases exercise snapshot boundaries.
Different cleanup and machine-load conditions prevent assigning the full 20.82-second
difference to the traversal change.

The only unit call above five seconds in the baseline is
`tests/unit/test_formal_statement_hasher.py::test_lean_canonicalization_known_answer`:
9.36 seconds, with isolated repeats of 9.17 and 8.58 seconds. Median call time is 9.17 seconds.
The other unit tests individually fit five seconds but collectively exceed one minute.
No sample-count reduction, additional exclusion, deadline increase, or container operation
is part of these measurements.

No-Claim: runtime measurements provide no mathematical evidence, do not certify all tests
as passing, and do not establish a unit tier below sixty seconds.
