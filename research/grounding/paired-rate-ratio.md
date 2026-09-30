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

## Measurement, `macos-host` arm, 2026-09-30

The pre-registration section is carried by commit `13ab293`, pushed ahead of the run. The run
is [paired-rate-ratio-macos-2026-09-30.json](paired-rate-ratio-macos-2026-09-30.json), 36207
bytes, SHA-256 `680d5fd9ecd6c466d23bd6e6c139eec8be3cb7fb301245b6f63c6e20d8bdcfc8`, taken at
15:39:06 through 15:39:07 UTC under the heavy lock and the 6 GiB cap (peak footprint 0.03 GiB):

```text
lockf -k /tmp/cairn-heavy.lock uv run --no-project python <orders>/memcap.py 6 \
  uv run python research/grounding/probe_paired_rate.py --compiler /usr/bin/clang \
  --arm macos-host --out <scratch>/paired-rate-ratio-macos-2026-09-30.json
```

| | |
|---|---|
| Compiler | `/usr/bin/clang`, Apple clang version 21.0.0 (clang-2100.3.34.2), `-O2 -std=c11 -Wall` |
| Host | macOS 26.6, kernel 25.6.0, arm64, Python 3.14.7 |
| Counted source, binary | `acaaa26e24b4acabc683871483d88e784a2d0993fa30d36798de1fc84e4f2a51`, `6076929c04bc516f1856a7fb543e3a1ae1de23acf67417600169e0355bda69dd` |
| Reference text, binary | `4fced42e85e8e533ff21d24e8e8d558870fff98650e0ff88868aeffb4f17ac3e`, `25322a466385bcc9ccb95a3aa8a74988a25d48b8b75745dfe0486fbd313a8ce9` |
| Load, 1-minute | 5.39 ahead of the pairs and 5.39 after |
| `kern.num_files` | 17212 ahead, 17200 after |
| Free 16 KiB pages | 4909 ahead, 46159 after; both below the 65536 quiet-host threshold in `cairn-mns5`, which the paired design does not gate on |
| Correctness prelude | 20 counted checks and 4 malformed refusals as in `counted-process-cost.md`; the reference agrees with the oracle at 0, 1, 2, 3 and 10000 operations |
| Orders drawn | 18 pairs counted-first, 13 reference-first |

Per-pair ratios over 31 pairs at 10000 operations per call:

| Kind | Min | Median | Max | Sample SD | Spread | Bound | Verdict |
|---|---:|---:|---:|---:|---:|---:|---|
| `cpu` | 0.888 | 0.990 | 1.138 | 0.058 | 0.252 | 0.30 | within bound |
| `wall` | 0.853 | 1.014 | 1.408 | 0.116 | 0.547 | 0.50 | exceeded |
| `deployed` | 1.879 | 2.376 | 3.996 | 0.363 | 0.891 | 0.50 | exceeded |
| null `cpu` | 0.718 | 1.001 | 1.344 | 0.101 | 0.625 | median in 0.90 through 1.10 | within bound |
| null `wall` | 0.763 | 0.958 | 1.569 | 0.178 | 0.842 | none pre-registered | reported |

Per-arm absolute costs over the same 31 pairs, medians with min, max and sample SD:

| Arm and clock | Median | Min | Max | SD |
|---|---:|---:|---:|---:|
| Reference child CPU | 153.5 ns/group op | 152.4 | 170.4 | 5.8 |
| Counted child CPU | 152.7 ns/group op | 151.2 | 173.5 | 6.0 |
| Reference parent wall | 356.8 ns/group op | 327.4 | 474.3 | 34.1 |
| Counted parent wall | 363.5 ns/group op | 320.2 | 627.8 | 55.6 |

The child CPU clock on this host reports whole microseconds, so at roughly 1.5 ms per call the
per-call resolution is about 0.07 percent.

What the rows say:

- The `cpu` ratio's median is 0.990: the counted chain costs what the reference chain costs,
  within the window's noise. The counter is one volatile increment per wrapper call. The null
  control's spread, 0.625 with the same binary on both sides of every pair, is wider than the
  `cpu` spread of 0.252, so the `cpu` spread is not distinguishable from the method's own noise
  in this window; the median is the figure, and it met its pre-registered bound. The null
  extremes are single calls at 2.139 ms (pair 1, first call) and 2.071 ms (pair 19, second
  call) against a 1.52 ms typical call.
- The `wall` and `deployed` spreads exceeded their bounds on the spawn term: pair 31's counted
  call took 6.28 ms of parent wall against a 3.4 ms typical call, and one such stall doubles a
  sample. Their medians, 1.014 and 2.376, are recorded and not qualified; the pre-registration
  says a missed bound is that result and is not rerun.
- The `deployed` median of 2.376 is the spawned counted object at 10000 operations per call
  over the child-CPU reference: at this batch size the spawn term is about 1.4 times the
  arithmetic. It moves with the batch size, so a pin derived from it names the batch size.
- The reference arm under Apple clang 21 costs 153.5 ns per group operation against the
  bundle's 217.1 ns under Apple clang 17 on 2026-09-08. The bundle figure keeps its own
  provenance; whether `clock.reference_cost` moves to the current compiler is a bundle change
  and belongs to `cairn-m1-cqt.1.4` under its checker.

### The reference text and the feature macro

The reference text this run compiled, `4fced42e…`, carries no `_POSIX_C_SOURCE` definition,
and under `-std=c11` glibc then declares neither `clock_gettime` nor
`CLOCK_PROCESS_CPUTIME_ID`; Debian clang 14.0.6 in the Linux container refused it with `use of
undeclared identifier 'CLOCK_PROCESS_CPUTIME_ID'`. Apple's headers declare both regardless.
Commit `61b7996` adds `#define _POSIX_C_SOURCE 200809L` as the text's first line, which
`counted_process.c` already carries; the text with the macro hashes to
`ee9ac45dcc1801a265b0438f552905ff3f55428a4f9acf061dd98bceeec0006b`. On macOS the binary built
from the text with the macro is byte-identical to the binary this run executed,
`25322a46…` in both cases, checked by building both texts under the same file name with the
same compiler and flags. This run is therefore a run of the current text's binary, and the
Linux arm builds the same current text.

## Measurement, `linux-container` arm, 2026-09-30

The run is [paired-rate-ratio-linux-2026-09-30.json](paired-rate-ratio-linux-2026-09-30.json),
36255 bytes, SHA-256 `f29180a1f718d7852cd1efb78c7bbc9edc1e80c882fbfc7a9a7bc2e3eb9745ff`, taken
at 15:50:22 UTC in a disposable container under the heavy lock and the 6 GiB cap (peak footprint
0.01 GiB), with the checkout at commit `61b7996` mounted read-only:

```text
lockf -k /tmp/cairn-heavy.lock uv run --no-project python <orders>/memcap.py 6 \
  docker run --rm --network none --memory=6g \
    -v /Users/jwross/Documents/cairn:/work:ro -v <scratch>:/out \
    -e PYTHONPATH=/work/src:/work -e PYTHONDONTWRITEBYTECODE=1 -w /work \
    cairn-paired-rate:bookworm-clang \
    python3 research/grounding/probe_paired_rate.py --compiler /usr/bin/clang \
    --arm linux-container --out /out/paired-rate-ratio-linux-2026-09-30.json
```

| | |
|---|---|
| Image | `cairn-paired-rate:bookworm-clang`, id `sha256:b343793d99b02b029ac5426aab12a7cad53e3a4240bfa20a8a6a01c4b4211c06`, built from `debian:bookworm-slim` at `sha256:3783cc01769c7b2b1b83a5c5ad96c815348e28ed7da68e2e3687004faa906251` plus `apt-get install clang python3` |
| Compiler | `/usr/bin/clang`, Debian clang version 14.0.6, `-O2 -std=c11 -Wall` |
| Kernel, libc, Python | `7.0.14-orbstack`, glibc 2.36, Python 3.11.2, `linux/arm64`, 10 CPUs |
| Counted source, binary | `acaaa26e…` as on macOS, `0bc2f6d4f559c146348fb5b3ef3d88cc834dd14125fe22825ae60fcc8751aa65` |
| Reference text, binary | `ee9ac45d…` (the text with the macro), `453a6e69f5881984b4c1a4c2caaa3c0a78c872cd047dcbe959c323056aeb812f` |
| Load, 1-minute, inside the container | 0.95 ahead of the pairs and 0.95 after |
| `MemFree` | 12216696 kB ahead, 12207280 kB after |
| `file-nr` | 337 ahead, 346 after |
| Correctness prelude | 20 counted checks and 4 malformed refusals; the reference agrees with the oracle at 0, 1, 2, 3 and 10000 operations |
| Orders drawn | 18 pairs counted-first, 13 reference-first, the same sequence as macOS by construction |

Per-pair ratios over 31 pairs at 10000 operations per call:

| Kind | Min | Median | Max | Sample SD | Spread | Bound | Verdict |
|---|---:|---:|---:|---:|---:|---:|---|
| `cpu` | 0.928 | 1.016 | 1.143 | 0.047 | 0.212 | 0.30 | within bound |
| `wall` | 0.418 | 1.004 | 2.470 | 0.626 | 2.043 | 0.50 | exceeded |
| `deployed` | 1.823 | 3.445 | 4.677 | 0.956 | 0.829 | 0.50 | exceeded |
| null `cpu` | 0.909 | 1.000 | 1.208 | 0.055 | 0.299 | median in 0.90 through 1.10 | within bound |
| null `wall` | 0.418 | 1.005 | 2.439 | 0.545 | 2.011 | none pre-registered | reported |

Per-arm absolute costs over the same 31 pairs:

| Arm and clock | Median | Min | Max | SD |
|---|---:|---:|---:|---:|
| Reference child CPU | 179.1 ns/group op | 145.1 | 207.1 | 23.0 |
| Counted child CPU | 178.1 ns/group op | 145.2 | 229.3 | 26.3 |
| Reference parent wall | 588.9 ns/group op | 278.1 | 707.8 | 187.2 |
| Counted parent wall | 675.9 ns/group op | 278.7 | 711.1 | 156.3 |

What the rows say:

- The `cpu` ratio's median is 1.016 with the null control at 1.000, so on this arm too the
  counted chain costs what the reference chain costs within the window's noise, and the
  pre-registered bound was met. The `cpu` spread of 0.212 sits inside the null control's 0.299.
- The child CPU cost is bimodal inside the container: calls near 2.0 ms and calls near 1.45 ms
  for both arms alike, which is why the per-arm SD is four times the macOS value while the
  per-pair ratio stays tight. The pairing removes what a single-arm measurement cannot.
- Parent wall is bimodal the same way, near 6.8 ms and near 2.8 ms per call, and the null
  control's `wall` spread of 2.011 matches the paired `wall` spread of 2.043: a spawn in this
  container lands in one of two modes, and pair 26 caught the reference in the fast mode and
  the counted object in the slow one. The `wall` and `deployed` verdicts are `exceeded` on the
  spawn term, as on macOS, and their medians, 1.004 and 3.445, are recorded and not qualified.
- At 10000 operations per call the spawn term inside the container is about 2.4 times the
  arithmetic on the `deployed` median, against about 1.4 times on the macOS host.

## The per-arm answer and the rate provenance

One build cannot serve both arms: the object is a Mach-O binary under Apple clang 21 on the
host and an ELF binary under a Linux clang in the container, and the gold gate image
(`cairn-gate:b7a0f1bcf5e5d33c`) carries no distro compiler at all, only Lean's bundled
`/home/cairn/lean/bin/clang`, `clang version 22.1.4`, so a counted object on the gold arm is
built by a third compiler unless the Containerfile gains a pinned one. The source is one text
with one hash on every arm; the binary digest is per arm; and the ratio is per arm. The plan
carries a value per arm.

| Arm | `cpu` median (spread, verdict) | `deployed` median at 10000 ops per call (spread, verdict) | Counted child CPU |
|---|---|---|---|
| `macos-host`, Apple clang 21 | 0.990 (0.252, within bound) | 2.376 (0.891, exceeded) | 152.7 ns/group op |
| `linux-container`, Debian clang 14 | 1.016 (0.212, within bound) | 3.445 (0.829, exceeded) | 178.1 ns/group op |

The seeded `clock.rate_ratio` of `1.0` describes the arithmetic-plus-counting term on both arms
to within the method's noise: the counted process-kind object's chain costs the reference
chain's cost, and the counter is not measurable above that noise. The same value understates
the spawned object by 2.4 times on the host and 3.4 times in the container at 10000 operations
per call, and by more at smaller batches.

The measured provenance this record offers for `clock.rate_ratio` is the `cpu` kind, per arm,
with its raw JSON, its pre-registered bound and its null control. The spawned-object kind is
recorded with an `exceeded` verdict on both arms and is not offered as a pin. Whether the
bound's `rate_ratio` means the arithmetic term or the spawned object at a named batch size is a
semantics decision of `ladderplan.ClockBound`, and the pin itself lives in
`bundle/ladder_plan.json`, an identity-bearing file: both belong to `cairn-m1-cqt.1.4` under its
checker. Until that bead moves it, `clock.rate_ratio` keeps `seeded:cairn-m1-cqt.1.4` as its
provenance, and this record is the reason the seed is the right number for one meaning and the
wrong number for the other.

No production source, bundle object, pin, golden or admission changed for this record.
