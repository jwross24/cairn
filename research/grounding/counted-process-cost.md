# Counted process prototype and timing hold

`counted_process.c` is a separate process over the 60-bit curve and alternating double/add chain used by `probe_clock_reference_cost.py`. It uses `/usr/bin/clang -O2 -std=c11 -Wall`. The fixed curve constants keep arithmetic inputs within the bounds of the C integer operations.

The count is one requested primitive group-operation wrapper call. A `double` wrapper increments once, and an `add` wrapper increments once. If the add implementation reaches its internal doubling formula, that call goes directly to the uncounted implementation and does not increment again. The count says nothing about field multiplications, inversions, or arbitrary claimant code.

The process supports four modes:

| Mode | Work and output |
|---|---|
| `raw` | Runs the arithmetic chain without a call counter; `count` is null. |
| `counted` | Runs the same chain and counts wrapper calls in a volatile process counter. |
| `count-only` | Runs the same volatile counter increment without curve arithmetic. It reports seconds per counter increment, not seconds per group operation. This is a counter control, not a standalone estimate of counting cost. |
| `zero-work` | Runs no group operation. The requested operation count identifies the batch size used when amortizing one process call. |

Timed runs use 10,000 requested operations per process call and seven repetitions by default, matching the reference probe. The C process reports CPU time around its selected work. The Python parent measures wall time around process launch and completion, before output parsing. Each repetition launches one child, so process-call overhead is visible in parent wall time and is amortized across the requested batch size. The zero-work child CPU time mostly reflects clock-read overhead; parent wall time carries process startup and response costs, amortized across requested batch slots. The report provides per-repetition nanoseconds and min, median, max, and sample standard deviation in seconds per group operation, counter increment, or process call as appropriate. It does not estimate counter cost by subtracting raw from counted timings.

`--correctness-only` omits both child CPU-clock reads and parent wall-clock reads. It checks operation counts 0, 1, 2, 3, and 10,000, plus the requested `--ops` value, in every mode. The point oracle derives a scalar for the alternating chain and checks `cairn.ec.mul`, rather than repeating the chain in the oracle. The validator checks the exact JSON fields, count, point, and timing type before accepting any timed repetition. Child calls use a 30-second subprocess timeout after process creation; process creation itself can be uninterruptible. Decimal requests are limited to 0 through 1,000,000; negative, overflow, out-of-range, and non-digit input is rejected by the executable.

Correctness evidence from 2026-09-29:

```text
command: uv run python research/grounding/probe_counted_process.py --correctness-only
result: exit 0
checks: raw, counted, count-only, and zero-work at 0, 1, 2, 3, and 10000 operations
10000 counted: count 10000, point (476377072802646283, 562446501424608226)
malformed requests refused: -1, 3junk, 1000001, 18446744073709551616
compiler: Apple clang 21.0.0 (clang-2100.3.34.2)
flags: -O2 -std=c11 -Wall
source SHA-256: acaaa26e24b4acabc683871483d88e784a2d0993fa30d36798de1fc84e4f2a51
binary SHA-256: 6076929c04bc516f1856a7fb543e3a1ae1de23acf67417600169e0355bda69dd
platform: macOS 26.6, arm64
timing status: not taken
```

A scratch copy with the increment removed from `counted_double` compiled successfully and the real-process probe refused its one-operation result with `counted count was 0, expected 1`. The unit validator also refuses wrong counts, wrong points, malformed or duplicate-key output, boolean counters or coordinates, invalid timing values, and missing or extra protocol fields. Missing compiler and binary paths fail with explicit errors.

The probe records the source path and SHA-256 for its own compiler invocation. For an externally supplied binary, it reports source provenance as unknown unless `--source` names an artifact; that supplied source remains explicitly unverified against the binary.

The 06:43 UTC host observation had a 1-minute load average of 34.91 against the bead's threshold of 8 and 4,479 free 16-KiB pages against the 65,536-page minimum. Timing was held for that observation.

A quiet-host run was recorded around 14:2x EDT on 2026-09-29 with OrbStack paused. The owner reported 539,282 free 16-KiB pages and `kern.num_files` 25,557. The JSON records a 1-minute load average of 5.45458984375, which is also below the bead's threshold of 8. The quiet-host prerequisites are load at or below 8, `kern.num_files` at or below 60,000, and at least 65,536 free 16-KiB pages; each reported value meets its threshold. The timestamp, OrbStack state, free pages, and file count came from MagentaSparrow's assignment (agent-mail message 316); the JSON itself contains only the load value among those prerequisite readings.

The raw run record is [mns5-quiet-2026-09-29.json](mns5-quiet-2026-09-29.json). It contains 28 timed samples: seven repetitions in each of `raw`, `counted`, `count-only`, and `zero-work`, with one process call and 10,000 requested operations per repetition. Every row records its mode, repetition, process-call count, requested operation count, child CPU nanoseconds, parent wall nanoseconds, and reported count. The JSON retains `timing_status: PROVISIONAL`.

The medians, ranges, and sample standard deviations below are independently recomputable from those rows. Parent wall time covers process launch through completion before output parsing; therefore its per-operation and per-increment values include the amortized process-call cost. The count-only row is a counter control, not a standalone estimate of counting cost.

| Mode and component | Median | Min–max | Sample SD |
|---|---:|---:|---:|
| Raw child CPU | 150.100 ns/group op | 145.100–160.100 ns/group op | 6.721 ns/group op |
| Raw parent wall | 301.446 ns/group op | 288.021–314.667 ns/group op | 9.982 ns/group op |
| Counted child CPU | 140.300 ns/group op | 138.900–146.500 ns/group op | 2.617 ns/group op |
| Counted parent wall | 281.171 ns/group op | 276.725–304.442 ns/group op | 10.492 ns/group op |
| Count-only child CPU | 0.400 ns/increment | 0.300–1.000 ns/increment | 0.346 ns/increment |
| Count-only parent wall | 138.825 ns/increment | 130.467–142.225 ns/increment | 4.895 ns/increment |
| Zero-work child CPU | 1.000 µs/process call | 0–2.000 µs/process call | 0.690 µs/process call |
| Zero-work parent wall | 1.333042 ms/process call | 1.245083–1.492583 ms/process call | 0.092573 ms/process call |
| Zero-work parent wall, amortized | 133.304 ns/requested operation slot | 124.508–149.258 ns/requested operation slot | 9.257 ns/requested operation slot |

The JSON records Apple clang 21.0.0 with `-O2 -std=c11 -Wall`, Python 3.14.7, macOS 26.6 arm64, source SHA-256 `acaaa26e24b4acabc683871483d88e784a2d0993fa30d36798de1fc84e4f2a51`, and binary SHA-256 `6076929c04bc516f1856a7fb543e3a1ae1de23acf67417600169e0355bda69dd`. The historical `c_reference` used Apple clang 17.0.0 and measures an in-process chain, so it is not a calibrated comparison for this clang 21 process measurement. The evidence does not justify a derived `rate_ratio`; `clock.rate_ratio` retains its seeded provenance.

No Linux arm was measured, and no Docker daemon was accessed. This prototype does not establish production admission, sandbox safety, counting of arbitrary claimant code, a production rate, or Linux costs.
