# Paired rate ratio: the counted process over `c_reference`, interleaved in one window

`clock.rate_ratio` in `bundle/ladder_plan.json` is the counted object's per-operation cost over
the reference cost, and `ladderplan.ClockBound` holds while `clock_tolerance * rate_ratio <
2 * design_radius`. The figure is a cost over a cost, so the owner chose a paired design over a
quiet-host precondition: the reference arm and the counted arm run interleaved in the same time
window, on the same curve, chain and operation count, and the ratio is taken per pair. Host load
lands on both arms of a pair, so the ratio is steadier than either absolute cost. The absolute
costs still carry the load and are reported beside the host observations, never as quiet-host
figures.

The probe is `research/grounding/probe_paired_rate.py`. It reuses the counted binary, its
validators and its correctness prelude from `probe_counted_process.py`, and compiles the
reference from the C text embedded in `probe_clock_reference_cost.py`, so the reference arm is
the same source as the 2026-09-08 `c_reference` row in `clock-reference-cost.md` under the
compiler of the day. `cairn-mns5` holds the open question this record answers.

## The two arms

| Arm | Source | Timing inside the child | Timing in the parent |
|---|---|---|---|
| `reference` | `C_SOURCE` from `probe_clock_reference_cost.py`, unchanged | `CLOCK_PROCESS_CPUTIME_ID` around the chain, printed as `cpu_s` | wall time around one spawn |
| `counted` | `counted_process.c` in `counted` mode | `CLOCK_PROCESS_CPUTIME_ID` around the chain, printed as `child_cpu_ns` | wall time around one spawn |

Both arms are compiled by the same compiler with `-O2 -std=c11 -Wall` into one scratch directory
outside the checkout, and both are spawned as a fresh process per call. The parent validates
every returned point against the scalar oracle in `probe_counted_process.expected_point`, and
the counted arm's count against the requested operation count, ahead of accepting any timing
row; a wrong point or count is a refusal, not a sample. The correctness prelude runs both arms
untimed at 0, 1, 2, 3 and 10000 operations against that oracle, so an arm that walks a different
chain cannot enter a pair.

## Pre-registration

These settings are fixed in the probe as `PREREGISTERED` and the probe refuses any other value
unless `--exploratory` is passed, in which case the report is labeled
`paired_rate_exploratory` and is not evidence. The commit that carries this section precedes
every timed run recorded below; the results section names that commit.

| Setting | Value |
|---|---|
| Pairs | 31 |
| Operations per call per arm | 10000, the alternating double/add chain on `curve60_seed1` |
| Order within a pair | decided per pair from seed 20260930, so both orders occur and the sequence is reproducible |
| Warm-up | one call per arm, validated and retained under `warmup`, excluded from the pairs |
| Ratios per pair | `cpu`, `wall`, `deployed`, defined below |
| Spread | `(max - min) / median` over the 31 per-pair ratios |
| Acceptance spread bound | `cpu` 0.30, `wall` 0.50, `deployed` 0.50 |
| Null control | 31 reference-versus-reference pairs in the same window, same settings |
| Null-control bound | median `cpu` null ratio within 0.90 through 1.10 |
| Host observations | 1-minute load, free pages or `MemFree`, open-file count, taken directly ahead of and directly after the pairs, recorded either way |

The ratio kinds:

- `cpu`: counted child CPU per group operation over reference child CPU per group operation.
  Both clocks are `CLOCK_PROCESS_CPUTIME_ID` read inside the child around the chain, so this is
  arithmetic plus counting over arithmetic, independent of spawn.
- `wall`: counted parent wall per group operation over reference parent wall per group
  operation. Both include one spawn per call, so this is the process-kind object over a
  process-kind reference at this batch size.
- `deployed`: counted parent wall per group operation over reference child CPU per group
  operation. This is the spawned counted object at 10000 operations per call over the clock
  the bundle's `reference_cost` is stated in. It depends on the batch size through spawn
  amortization, so a pin derived from it names the batch size.

The bounds are chosen thresholds with a stated basis, not measured breakpoints. The quiet-host
rows of 2026-09-29 in `counted-process-cost.md` put the counted child CPU range at 5.5 percent
of its median, the raw child CPU range at 10 percent, and the zero-work parent wall range at 20
percent. A ratio of two such arms spans roughly the sum of their ranges, so the `cpu` bound is
twice the quiet-host sum and the `wall` and `deployed` bounds allow the spawn term twice its
quiet-host range on each side. The null control has no counting term, so its median is expected
at 1.0; a median outside 0.90 through 1.10 says the window could not hold even a same-binary
ratio steady, and the paired result of that window is recorded as unqualified.

A run whose spread misses a bound is recorded as that result with its verdict `exceeded`. It is
not rerun until it passes, and the rate provenance stays held on it. A run whose spread is
within bound is a measured ratio for its arm and its batch size; it is a candidate for the
`rate_ratio` pin, and the pin itself moves only under `cairn-m1-cqt.1.4` with its checker.

### Arms

| Arm label | Host | Compiler | Execution |
|---|---|---|---|
| `macos-host` | the build machine, Apple M4, macOS 26.6, arm64 | `/usr/bin/clang`, Apple clang 21 | under the machine-wide heavy lock with a 6 GiB memory cap |
| `linux-container` | a disposable container on the same machine through OrbStack, `linux/arm64` | Debian clang 14.0.6 from `debian:bookworm-slim`, Python 3.11.2 | `docker run --rm --network none --memory=6g`, checkout mounted read-only, under the heavy lock and the same cap |

The Linux image is built from `debian:bookworm-slim` with `apt-get install clang python3` and
nothing else. It is a research image, not the gate image: `cairn-gate` carries Lean's bundled
clang and no Python, and pinning a compiler into the gate bundle is `.1.4`'s work. The two arms
therefore differ in compiler as well as kernel, and each arm's ratio is internal to its own
compiler. The pre-registered settings are identical for both arms.

### The reference of record

The historical `c_reference` median of `0.000000217100` s per group operation was taken under
Apple clang 17 on 2026-09-08. The reference arm here is the same C text under the compiler that
built the counted object, so the per-pair ratio compares like with like. The reference arm's
absolute cost under load is reported but does not replace `clock.reference_cost`, which keeps
its own provenance.
