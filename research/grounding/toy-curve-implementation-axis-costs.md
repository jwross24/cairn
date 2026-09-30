# Toy-curve and instance-maker implementation-axis costs

Calibration: STRONG-EMPIRICAL on the recorded samples. These measurements describe
runtime cost and recorded agreement on prime-order curves drawn by toy_curve. They
make no PROVEN mathematical claim and confer no calibration promotion.

## Scope and toolchain

The implementation axis covers bits [30,60]. The algorithm axis covers [0,50].
At 70 bits both axes report untested; that size supplies S2-12's outside probe.
Its measured 1.0578-second subprocess mean exceeds the gate bundle's one-second
Tier-0 boundary. A declared Tier-0 launch at 70 bits is refused with boundary-table;
a cost-profile row is not an admission or an independent-coverage declaration.

Host: macOS 26.6, Darwin 25.6.0, arm64. Python 3.14.7; GP 2.17.4; cypari2 2.2.4;
libpari 2.17.2 with nbthreads=1; gmpy2 2.3.1; GMP 6.3.0; blake3 1.0.9.
The host is shared. Wall measurements include host contention and are sample means,
not throughput guarantees or isolated CPU measurements.

## Commands and source binding

Both commands run under the machine-wide heavy lock and a 6-GiB process-group cap:

```bash
lockf -k /tmp/cairn-heavy.lock uv run --no-project python /Users/jwross/.local/share/cairn-agent-mail/orders/memcap.py 6 uv run cairn measure toy-curve-tries --sizes 30,40,50,60,70 --seeds 50 --json
lockf -k /tmp/cairn-heavy.lock uv run --no-project python /Users/jwross/.local/share/cairn-agent-mail/orders/memcap.py 6 uv run cairn measure dlp --skill instance-maker --sizes 28,30,40,50,60 --seeds 10 --json
```

Sample date: 2026-09-30. Base commit: a15cc8dde6c202bf6a3677255885b310ef85d84c.
Measured feature sources have these SHA256 digests:

| Source | SHA256 |
|---|---|
| src/cairn/skills/toy_curve.py | 3b93fbaeaf0b9731df651abd5bbc1c32dc88cc988c886e1f6d8c91956194b74c |
| src/cairn/skills/instance_maker.py | d59dff358def69ec5cbaef2b078014ccf78d16eae964255120ededf6a04f430b |
| src/cairn/skills/order_bsgs_gmpy2.py | 9d978b61ae7a4148207eac892ba0ded32da14536383727163844c4cc1b355708 |

The measured toy-curve implementation revision is
7604e43c08ea93588791a94ba6923ca0420332750e7f3a8a624876254e733b07;
the measured maker revision is
ce362055ccc57e1e612669e8f499f45427b1f10755bac50c6b1d30150c574bb7.
Cost-profile constants, primary SEAM metadata, and declaration type annotations are
outside the measured computation. The profile tests bind the recorded rows to the
declared constants.

## Toy-curve sample

Raw stdout: [toy-curve-implementation-axis-costs.json](toy-curve-implementation-axis-costs.json).
Each seed 1..50 runs in-process and in a subprocess. The measurement checks equality
of p, a, b, n, P, tries, and status between those runs. Subprocess wall time includes
interpreter startup. Per-try time divides the entire in-process run by its tries;
it includes postconditions and cross-checks rather than timing only the search loop.

| bits | seeds | mean tries | sd tries | min | max | per-try ms | in-process mean wall s | subprocess mean wall s |
|---|---|---|---|---|---|---|---|---|
| 30 | 50 | 39.48 | 29.83 | 4 | 148 | 0.654 | 0.0258 | 0.1009 |
| 40 | 50 | 50.60 | 46.22 | 1 | 260 | 0.841 | 0.0426 | 0.1154 |
| 50 | 50 | 63.82 | 60.56 | 1 | 232 | 2.164 | 0.1381 | 0.2107 |
| 60 | 50 | 68.72 | 59.09 | 7 | 259 | 7.681 | 0.5278 | 0.6095 |
| 70 | 50 | 118.98 | 107.89 | 1 | 406 | 8.466 | 1.0072 | 1.0578 |

The retained stderr has 250 in-process toy-curve run events, all OK: 200 implementation
agree events at 30..60 and 50 implementation untested events at 70. Algorithm agrees
on the 150 events at 30..50 and is untested on the 100 events at 60..70.
The command exits 0; the memory cap records a peak footprint of 0.15 GiB.

## Instance-maker sample

Raw stdout: [instance-maker-implementation-axis-costs.json](instance-maker-implementation-axis-costs.json).
Seeds 1..10 run in-process at each size. The measured work includes toy_curve,
instance construction, postconditions, and the maker's own eligible BSGS cross-check.

| bits | seeds | mean tries | sd tries | per-try us | mean wall s |
|---|---|---|---|---|---|
| 28 | 10 | 49.70 | 37.67 | 745.0959 | 0.0370 |
| 30 | 10 | 45.00 | 46.70 | 559.9244 | 0.0252 |
| 40 | 10 | 55.50 | 38.86 | 816.0001 | 0.0453 |
| 50 | 10 | 79.20 | 69.22 | 1909.1165 | 0.1512 |
| 60 | 10 | 84.00 | 65.32 | 7150.9745 | 0.6007 |

The retained stderr has 50 maker run events and 50 nested toy-curve run events,
all OK. The nested implementation axis agrees on 40 events at 30..60 and reports
untested on 10 events at 28. The command exits 0; the cap records 0.08 GiB peak.

Retained stderr paths:
`/tmp/cairn-5d69-work.8cntpQ/toy-curve-measurement.stderr` and
`/tmp/cairn-5d69-work.8cntpQ/instance-maker-measurement.stderr`.
