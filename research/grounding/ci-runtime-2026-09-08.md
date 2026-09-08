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

Run `34255029635` at `7fa7ec59112654375a18b51cf58dc6b6fbfac62b` reports 8 failed,
3366 passed, 5 skipped, and 1 xfailed in 848.24 seconds. Setup before Gates is 32 seconds;
the entire job takes 889 seconds. Remaining margins are 231.76 seconds to the session
deadline and 311 seconds to the job ceiling. All eight failures occur in
`tests/integration/test_ladder_allowlist_enforcement.py`, where Python's `posix_spawn`
reports `Undefined error: 0` for the Homebrew Python.app executable. The sandbox methods
do not reach their expected behavior. This failed run is neither green nor a paired
whole-suite speedup measurement. Its complete log and job metadata carry the run id
in their filenames.

```bash
gh run view 34255029635 --log
gh run view 34255029635 --json headSha,jobs,conclusion
```

### Remaining costs in run 34255029635

Confidence: HIGH for the reported durations and the source-level execution requirements.
Verified: 2026-09-08 by reading the complete log and the functions cited here. The top
25 rows sum to 425.46 seconds, 50.16% of the 848.24-second run. The smallest listed row
is 4.52 seconds; module subtotals below are lower bounds, not complete module profiles.
The other 422.78 seconds combine unlisted test phases and pytest overhead; this log
does not separate them.

- The three leading calls take 97.19 seconds for the axiom matrix, 72.22 seconds for
  the twenty fresh BSGS instances, and 53.33 seconds for Lean build plus fresh replay.
  Together they take 222.74 seconds, 26.26% of this run. A separate missing-theorem
  refusal takes 4.76 seconds. Their independent positive and negative executions remain
  necessary; the earlier CI observations above describe their coverage.
- Five hasher stability pairs take 68.16 seconds: fresh 30.92, comment 11.76, definition
  9.43, unused 9.04, and hypothesis 7.01. Each pair builds both its baseline and its
  comparison in separate directories (`tests/integration/test_hasher_stability.py:37`).
  Each hash call checks pins, builds the gate-owned tool, builds the target, and executes
  the hasher (`src/cairn/lean.py:215`). Sharing those builds would change the tested fresh
  execution path. No behavior-identical caching opportunity is established.
- Eight M0 calls in the list sum to 43.66 seconds. Their function-scoped deployment
  creates a bundle, pin, attestation, and certification (`tests/e2e/test_m0_slice.py:60`).
  Tests inspect distinct database state, cold-versus-cached service, altered paths, and
  CLI refusal behavior. For example, the operator test requires `served_from_cache` to
  be false, while the cache test deliberately executes the first, repeated, different-seed,
  and cache-bypassed cases (`tests/e2e/test_m0_slice.py:103,221`). Sharing a mutable deployed
  database would change those premises; no safe fixture-scope change is identified.
- The 24.41-second conformance setup belongs to the sweep of all six subjects and every
  clause, although pytest attributes it to `toy_curve-S2-01`. Harness, sweep, and verdicts
  already have module scope (`tests/conformance/test_skill_contract.py:49,68,84`), and
  certification is cached per subject/context (`tests/conformance/skill_contract.py:90`).
  The same-seed replay and independent double-transcript checks execute distinct runs
  (`tests/conformance/skill_contract.py:235,311`); reusing their outputs would remove evidence.
- Three deadline calls total 29.04 seconds. The 19.32-second GIL-starvation test uses the
  real four-second deadline plus the production fifteen-second backstop grace
  (`tests/integration/test_session_deadline.py:165`, `tests/_session_deadline.py:23,77`).
  The 5.16-second cancellation test includes an explicit five-second survival wait beyond
  a one-plus-two-second backstop; the 4.56-second hanging test asserts a four-second
  timeout and its thread profile. Shortening these waits changes the timing coverage.
- Two stateful substrate calls total 17.28 seconds. Their settings explicitly require
  200 examples and 50 state-machine steps (`tests/integration/test_substrate_stateful.py:16`).
  No redundant execution is established. The 9.13-second GC conflict test holds a real
  second connection's write transaction (`tests/integration/test_gc.py:182`); the substrate
  configures a 5000-ms busy timeout (`src/cairn/substrate.py:17,212,218`). A lock wait is
  consistent with part of the observed cost, but this log does not time that phase.
  The 6.28-second toy-curve idempotency call requires two real certifications and asserts
  one inserted row followed by the same present certificate
  (`tests/integration/test_toy_curve_selftest.py:137`).

The bounded source review identifies no additional verified, behavior-identical optimization
within this lane's file ownership. It does not prove that the remaining workload is optimal.

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

## Collection boundary evidence

CI run `34253574475` at `c299761273f77b16179e5fd3e5318ce726e957d7` fails during collection:
the snapshot test's direct `conftest` import resolves `tests/planted/conftest.py`, which
does not export `_snapshot`. Its complete log is `34253574475.log.gz`; no suite runtime
can be measured from this run. Targeted unit collection does not expose this collision.

Commit `d8968c90072a4cc837853eeda94c0e5765d20929` supplies the snapshot callable through
a root fixture. Full collection reports 3396 tests in 2.92 seconds, exit 0, in
`collection-after.log.gz`. The error-bearing report is `collection-before.log.gz`.
The assertion that the import error occurs exits 0 against the error-bearing report and
exits 1 against the successful report. `collection-fix-clean.log.gz` reports 19 passed
in 2.10 seconds with a fresh temporary directory.

```bash
uv run pytest --collect-only -q
scratch=$(mktemp -d)
uv run pytest -q tests/unit/test_isolation_snapshot.py tests/unit/test_golden_harness.py tests/unit/test_check_unit_tier.py --basetemp="$scratch/pytest"
```

The commit's four per-path checks, format, lint, spelling, and types, each exit 0.
Its whole-tree fast gate has a logged, CopperRidge-authorized bypass for PTH208 in
another lane's uncommitted `src/cairn/runner.py`. This is not whole-tree green.
UBS scans two files with zero critical findings and three warnings, exit 0; the JSON
warnings concern the fixture's intentional propagation of invalid-vector parse errors,
and the file-open warning identifies no unclosed handle.

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

Summing the recorded setup, call, and teardown rows in `unit-after.log.gz` yields
78.70 seconds, subject to the report's two-decimal rounding. The largest modules are
`test_justify_properties.py` at 19.96 seconds, `test_formal_statement_hasher.py` at
9.26 seconds, and `test_cli_contract.py` at 5.57 seconds. The justification module's
largest individual call is 1.46 seconds; its aggregate cost does not justify a slow
marker under the per-test five-second rule. These are observations, not evidence that
any property case or required sample is redundant.

No-Claim: runtime measurements provide no mathematical evidence, do not certify all tests
as passing, and do not establish a unit tier below sixty seconds.

## Unit gate contract and validation

`scripts/check.sh --unit` runs the five fast gates and
`uv run pytest tests/unit -q -m "not slow" --durations=10`. The registered `slow` marker
applies to the measured Lean canonicalization test through `tests/_unit_tier.py`.
The unrestricted suite retains that test. The pre-commit hook uses `--fast`; CI uses the
unrestricted gate. Neither the Hypothesis sample count nor a deadline depends on this tier.

The duration-budget test sums setup, call, and teardown, then uses the median of available
samples against a strict five-second threshold. It reads the archived baseline and repeat
reports. Updating those recorded reports is necessary to detect drift in the budget test;
this is not a live timing assertion on every unit execution. A report with skipped tests,
missing durations, or no passing summary refuses validation. Pytest 9.1.1 is the installed
version; Context7's pytest documentation and its upstream import-mode test establish the
scratch collection's `--import-mode=importlib` behavior.

`final-targeted.log` reports 31 passed in 1.57 seconds. Its marker test imports the actual
Lean test module before collecting the scratch module, then checks both one selected plus
one deselected test and two tests in the unrestricted scratch run. A normal import of the
same basename produces an import-file mismatch in the real unit collection; importlib mode
avoids that collision without changing which tests execute.

`planted-budget.log` records the deliberate negative: a 4.90-second call plus 0.11-second
setup is an unmarked 5.01-second test, and the assertion that no slow test exists fails.
`skipped-repro-after.log` records refusal of a real pytest report with one pass and one skip.
Neither negative is counted as a passing production test.

```bash
uv run pytest -q tests/unit/test_check_unit_tier.py tests/unit/test_check_gate_instruments.py tests/unit/test_golden_harness.py tests/unit/test_isolation_snapshot.py
uv run pytest -q tests/integration/test_axiom_computation.py tests/integration/test_bsgs_selftest.py tests/integration/test_lean_toolchain.py --durations=25
```

The three integration modules report 35 passed in 338.81 seconds (`top-three.log`).
`unit-gate.log.gz` reports 2 failed, 1986 passed, 1 deselected in 392.26 seconds, with
403.18 seconds of total command wall time. A concurrent full suite was active, so this is
not a valid idle timing measurement. The two failures are the scratch import collision
described above and `m0-run` refusing a receipt without `measurement_scope`, which belongs
to the receipt lane. The under-sixty-second acceptance criterion remains open.

At `cf04d1b85851ddc54f470b35781238f1c6b89dfa`, the receipt-producing runner supplies
`measurement_scope`; the isolated `m0-run` case reports one pass in 7.42 seconds.
The complete unit gate reports 2085 passed and one deselected in 237.98 seconds, with
247.243 seconds of total command wall time (`unit-idle-final.log.gz` and
`unit-idle-final.json`). No other pytest process was observed immediately before this run.
The shared checkout and machine are not an isolated benchmark environment.

```bash
PYTEST_ADDOPTS='--basetemp=/tmp/cairn-runtimemoth.U7GUPL/unit-idle-final' scripts/check.sh --unit
```

This passing measurement does not meet the sixty-second target. Three unmarked calls in
its top-ten report exceed five seconds: verifier fuzz at 11.34, runner fuzz at 8.20,
and the justification assumption relation at 5.41. Those single observations require
repeat measurements before establishing a median-based marker change. They do not
authorize reducing sample counts or excluding their whole modules.
