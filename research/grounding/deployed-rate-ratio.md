# Deployed rate ratio: what a method pays per counted operation, by protocol shape

`cairn-m1-cqt.1.4` records `clock.rate_ratio` with the deployed meaning, settled by the
orchestrator on the bead: the counted object's per-operation cost as a method actually pays it,
spawn and protocol included, at the batch size the gate itself uses. The `cpu` meaning in
`paired-rate-ratio.md` never carries the pin: a method doing real arithmetic uncounted and
issuing dummy counted calls hides work in proportion to deployed cost over fastest cost, and the
`cpu` figure understates that by 2.4 times on the host and 3.4 times in the container, which
shows the bound satisfied when it is not.

`ladderplan.ClockBound` holds while `clock_tolerance * rate_ratio < 2 * design_radius`. With
the plan's `clock_tolerance` 0.10 and `design_radius` 0.1216 the largest admissible ratio is
2.432, and a plan whose ratio meets or exceeds it refuses to load. This record measures the
ratio at the protocol shapes a process-kind counted object can take, so the pin, or its
refusal, rests on a number about the shape the gate would deploy.

## The batch size the gate uses is a protocol decision, and the walk decides it

No method routes its arithmetic through a process-kind object in the shipped tree: `rho_dp`
and `bsgs` call `cairn.ec` in-process, `ladder.run` accepts an `ops_counter` hook that nothing
on a production path supplies, and every trial's `gate_ops` is `OPS_UNKNOWN`. The batch size is
therefore not observable from the gate; it follows from how a method's operations reach the
object. A rho walk is sequential: each step's input is the previous step's output, so a method
that keeps the walk in its own process can send the object one operation at a time and no
more. A method whose walk runs inside the object sends one program per trial. The two shapes
are measured here as `ipc` and `batch`:

| Arm | What runs | What the parent times |
|---|---|---|
| `reference` | the `c_reference` chain in-process, 10000 operations | wall around one spawn; child CPU on `CLOCK_PROCESS_CPUTIME_ID` |
| `batch` | `counted_process counted 10000`, the chain inside the object, about the shortest observed 30-bit trial | wall around one spawn |
| `trial_batch` | `counted_process counted 37396`, the mean 30-bit trial's operation count inside the object | wall around one spawn |
| `ipc` | `counted_process serve 10000`: a Python client sends one `d x y` or `a x y gx gy` request per operation over a pipe and reads the point back, then `q` | wall around spawn, 10000 round trips and exit |

The `serve` mode of `counted_process.c` counts one wrapper call per request, refuses a
malformed request, a coordinate at or above `p`, a request beyond `OPS`, or input that ends
without `q`, and prints the same closed JSON summary as the other modes with `point` null. The
client validates every response as a field point and the final point against the scalar
oracle, and the summary's count against the request count. `trial_ops` 37396 is
`rho_dp.COST_PROFILE.production.per_size[30].mean_tries`, the smallest rung's mean group
operations per trial, so `trial_batch` is the batch shape at a mean 30-bit trial. Trials at
that rung span 9701 through 73522 operations over the ten measured seeds
(`m1-dlp-skill-costs.md` §1), and the spawn term per operation scales with one over the trial's
count, so the `batch` arm at 10000 operations stands in for the shortest observed trial, where
spawn amortizes least, and the two batch arms bracket the batch shape at the smallest rung.

## Pre-registration

Fixed in `probe_deployed_rate.py` as `PREREGISTERED`; any other value needs `--exploratory` and
labels the report `deployed_rate_exploratory`, which is not evidence. The commit carrying this
section precedes every timed run recorded below.

| Setting | Value |
|---|---|
| Pairs | 15 |
| Operations per call, `reference`, `batch`, `ipc` | 10000, the alternating double/add chain on `curve60_seed1` |
| Operations per call, `trial_batch` | 37396 |
| Order within a pair | the four arms sorted by a hash of seed 20260930, the pair index and the arm name |
| Warm-up | one call per arm, retained under `warmup`, excluded from the pairs |
| Ratios per pair | `deployed_batch`, `deployed_trial_batch`, `deployed_ipc`: the arm's parent wall per operation over the reference child CPU per operation |
| Spread | `(max - min) / median` over the per-pair ratios |
| Spread bound | 0.50 for each kind |
| Figure rule | the median when the spread is within bound; the maximum observed ratio when it is exceeded; never the `cpu` kind |
| Bound evaluation | `0.10 * figure < 0.2432`, computed by the probe from `bundle/ladder_plan.json` and reported per kind |
| Host observations | as in `paired-rate-ratio.md`, taken directly ahead of and after the pairs |

The spread bound of 0.50 is the `deployed` bound of `paired-rate-ratio.md`, where the same
kind exceeded it on both arms on the spawn term; the figure rule is the orchestrator's
conservative rule for that case. A figure that makes the bound false is a finding to report,
not a value to tune the tolerance or the batch size around.

### Arms

The `macos-host` arm and the `linux-container` arm are as in `paired-rate-ratio.md`: Apple
clang 21 on the build machine; Debian clang 14.0.6 in the disposable
`cairn-paired-rate:bookworm-clang` image.

### The gold arm's compiler

The orchestrator's preference for the gold arm is Lean's bundled clang already in
`cairn-gate:b7a0f1bcf5e5d33c`, so that `bundle/Containerfile` does not move. Checked
2026-09-30 in that image: `/home/cairn/lean/bin/clang` is `clang version 22.1.4`, and the image
holds no C standard headers anywhere (`find / -name inttypes.h` returns nothing; `dpkg-query`
reports no `libc6-dev`, `gcc` or `clang` package), so it refuses a one-line `#include <stdio.h>`
program with `fatal error: 'stdio.h' file not found`, with or without `-I/home/cairn/lean/include`.
Lean's clang links Lean's own runtime and carries no libc development headers. A counted object
on the gold arm therefore needs the Containerfile alternative: `libc6-dev` under the image's apt
snapshot lets the bundled clang build it, or a distro `clang` package does both. Either moves
`bundle/Containerfile`, an identity-bearing file, and is a `.1.4` bundle change under its
checker.

## Measurement, both arms, 2026-09-30

The pre-registration is carried by commit `ac4dc15`, pushed ahead of the runs. Each run took the
heavy lock and the 6 GiB cap.

| | `macos-host` | `linux-container` |
|---|---|---|
| Raw JSON | [deployed-rate-ratio-macos-2026-09-30.json](deployed-rate-ratio-macos-2026-09-30.json), 26712 bytes, SHA-256 `171f47bf0f7b50e4eef0f1309de26b9424cf40664b130bee0dc553b7f2d9cd0c` | [deployed-rate-ratio-linux-2026-09-30.json](deployed-rate-ratio-linux-2026-09-30.json), 26759 bytes, SHA-256 `bf0736321116ae4ec09129e3dabc2cf0ffb0ad6b8b4afc7c03f2c32c3a5e5e2c` |
| Taken at | 17:23:13 through 17:23:16 UTC | 17:23:18 through 17:23:20 UTC |
| Compiler | Apple clang 21.0.0, `-O2 -std=c11 -Wall` | Debian clang 14.0.6, `-O2 -std=c11 -Wall`, kernel `7.0.14-orbstack` |
| Counted source, binary | `5fd61f282e77a9ed…` (the text with the serve mode), `9059d68af3db123e…` | the same text, `c52bf5a73c375168…` |
| Reference text, binary | `ee9ac45dcc1801a2…`, `25322a466385bcc9…` | the same text, `453a6e69f5881984…` |
| Load, 1-minute | 17.39 ahead of the pairs, 16.88 after | 0.40 ahead and after, inside the container |
| Memory | 14195 free 16 KiB pages ahead, 4184 after | `MemFree` 14945404 kB ahead, 14931524 kB after |
| Open files | `kern.num_files` 23741 ahead, 23726 after | `file-nr` 328 ahead, 340 after |
| Correctness prelude | 20 counted checks, 4 malformed refusals, serve sessions of 1, 2, 3 and 31 requests counted exactly | the same |

Per-pair ratios over 15 pairs, each arm's parent wall per operation over the reference child CPU
per operation, with the pre-registered figure rule applied:

| Arm, kind | Min | Median | Max | Sample SD | Spread | Verdict | Figure (rule) | `0.10 × figure` | Bound holds |
|---|---:|---:|---:|---:|---:|---|---:|---:|---|
| macOS, `deployed_batch` (10000 ops) | 1.631 | 2.836 | 4.624 | 0.824 | 1.055 | exceeded | 4.624 (max) | 0.4624 | no |
| macOS, `deployed_trial_batch` (37396 ops) | 0.954 | 1.503 | 2.167 | 0.306 | 0.807 | exceeded | 2.167 (max) | 0.2167 | yes |
| macOS, `deployed_ipc` (10000 round trips) | 31.14 | 53.97 | 88.26 | 12.92 | 1.058 | exceeded | 88.26 (max) | 8.826 | no |
| Linux, `deployed_batch` (10000 ops) | 1.600 | 3.548 | 5.102 | 1.123 | 0.987 | exceeded | 5.102 (max) | 0.5102 | no |
| Linux, `deployed_trial_batch` (37396 ops) | 0.543 | 1.425 | 2.602 | 0.470 | 1.445 | exceeded | 2.602 (max) | 0.2602 | no |
| Linux, `deployed_ipc` (10000 round trips) | 11.27 | 26.54 | 63.33 | 11.53 | 1.961 | exceeded | 63.33 (max) | 6.333 | no |

The keep-band excess is 0.2432 and the largest admissible ratio 2.432 on both arms. Per-arm
absolute medians, with min and max, in nanoseconds per group operation:

| Arm | macOS child CPU | macOS parent wall | Linux child CPU | Linux parent wall |
|---|---:|---:|---:|---:|
| `reference` | 155.9 (152.9, 223.4) | 446.9 (393.7, 706.3) | 169.9 (144.5, 354.3) | 599.0 (287.7, 882.3) |
| `batch` | 157.4 (152.0, 180.2) | 453.9 (364.4, 720.9) | 159.3 (145.6, 607.1) | 667.2 (366.2, 1113.7) |
| `trial_batch` | 154.6 (152.6, 172.1) | 236.8 (206.8, 337.8) | 173.5 (145.8, 347.3) | 261.6 (187.6, 493.8) |
| `ipc` | 2759.5 (2518.4, 3477.7) | 8435.2 (6957.4, 13759.5) | 1162.6 (1049.4, 5696.7) | 4564.3 (3572.4, 19974.6) |

What the rows say:

- Every spread exceeded its 0.50 bound, on the host under a 1-minute load of 17 from the other
  lanes' suites and in the container on its bimodal spawn, so the pre-registered rule takes the
  maximum observed ratio for every kind. The medians are reported beside them and are not the
  figures.
- The `ipc` shape fails the bound by more than an order of magnitude on both arms at the
  median (54 on the host, 27 in the container), never mind the maximum. The failure is
  structural, not a load artifact: the child's own CPU per request, 2.76 µs on the host and
  1.16 µs in the container, is already 7 to 18 times the reference before the client's side of
  the round trip is counted. A method that keeps its walk in its own process and sends the
  object one operation at a time cannot sit under this bound at the plan's tolerance of 0.10;
  a tolerance small enough to admit these maxima, 0.002 or below, is not evaluated here.
- The `batch` shapes fail on the spawn term at the shortest 30-bit trial on both arms, at the
  median (2.84, 3.55) as well as at the maximum (4.62, 5.10). At the mean 30-bit trial the
  maximum holds on the host (2.17) and fails in the container (2.60), with medians of 1.50 and
  1.42. The batch shape satisfies the bound only where a trial is long enough to amortize one
  spawn. The median spawn term per call, parent wall less child CPU, is 2.91 ms and 2.94 ms
  on the host for the two batch arms and 5.12 ms and 3.08 ms in the container; spread over
  the 40-bit rung's floor count of 1171749 operations at each arm's median child CPU per
  operation, that is 1.6 percent of the arithmetic on the host and 1.5 to 2.7 percent in the
  container, and the short trials of the 30-bit rung are where it does not hold.
- Under the deployed meaning and the pre-registered rule, no measured shape yields a
  `rate_ratio` below 2.432 on both arms. One table figure loads: the host's mean-trial batch
  at 2.167 gives a product of 0.2167 and `ladderplan.LadderPlan.load` accepts it, while the
  same shape's figure in the container, 2.602, and every other figure in the table make it
  refuse the shipped bundle with `clock-bound-violated`. A plan carries one ratio and loads
  the same on every arm, so a pin at the host's 2.167 would be accepted by the loader while
  the container's own measurement of the same shape sits above the admissible 2.432: the
  loader would not see the arm on which the bound fails. That refusal, and that gap, are the
  finding this record reports. Neither the clock tolerance nor the batch size is tuned here,
  and the `cpu` kind is not offered.

## Where this leaves `clock.rate_ratio`

The pin stays `1.0` with provenance `seeded:cairn-m1-cqt.1.4`, and this record is the stated
reason it cannot move: the deployed cost of a process-kind counted object depends on a protocol
shape the tree does not yet fix, and the shapes measured here either fail the bound outright or
fail it at the smallest rung's short trials. Two decisions are the owner's, under RULE 2, and
neither is shown here to satisfy the bound at the 30-bit rung. A counted object that runs the
walk itself makes the batch the whole trial; on these figures the spawn term is 1.5 to 2.7
percent of the arithmetic at the 40-bit floor count and smaller above it, while at the 30-bit
mean trial the maximum still fails in the container (2.602) and at the shortest 30-bit trials it
fails on both arms. A ratio carried per rung would let the rungs at 40 bits and above carry a
figure near their own amortized cost, and leaves the 30-bit rung with the failures measured
here. Spawn stays inside the deployed rate in either case. Until the owner takes one and a run
under it holds, `ladderplan` keeps refusing a ratio at or above 2.432, which is the gate
failing closed on a number it cannot yet support.

## The wall figures overstate the predicate's quantity

The orchestrator's correction on the bead (agent-mail message 464, 2026-09-30 17:42 UTC) sets
the quantity the deployed ratio must be measured in. The clock predicate in
`laddertable._clock` compares a trial's process-tree CPU seconds, user plus system from the
execution receipt, against counted operations at the reference rate, so the budget a method
can hide uncounted work inside is process-tree CPU, and the ratio that sizes that room is
process-tree CPU per counted operation in the deployed shape, the method process's protocol
CPU plus the spawn's CPU plus the child's CPU, over the reference child CPU per operation.
The tables above use parent wall per operation as the numerator. Wall includes the exec and
scheduling waits of each spawn, about 2.9 ms per call on the host and 3.1 to 5.1 ms in the
container on the batch arms' medians (parent wall less child CPU), and wall is not the
quantity `_clock` bounds; the wall figures therefore overstate the predicate's quantity, and
the numbers above stand as the record of the wall measurement, not as the figures the pin is
judged by. `laddertable._wall` bounds elapsed time relative to reported CPU: it fires when
wall exceeds CPU by more than its tolerance, so it limits idle waiting but does not by itself
close a computation channel, since added CPU under a fixed wall makes it easier to pass. The
CPU-deployed measurement is pre-registered below.

The checker's review of this reasoning (gpt-6-astra, logged as findings on the bead) holds
the CPU unit and the reference child CPU denominator and names two premises the bound rests on
that this record does not establish. First, complete accounting: the receipt is `wait4` on the
trial's direct child, which rolls up descendants only as they are reaped, and the runner's own
CPU sits outside it; `laddertable._measurement_scope` refuses a trial whose scope is weaker
than `tree`, and that predicate, not this ratio, is what excludes unaccounted execution.
Second, a compulsory-cost floor: `clock_tolerance * rate_ratio < 2 * design_radius` bounds the
hidden work only if every counted call costs at least the allowance per operation. The
prototype counts a call before its arithmetic, and `ec_add_impl` returns early for an
inverse-point addition, so a session of 10000 `a P (-P)` requests is accepted and counted with
the field arithmetic skipped. In the serve shape that session still costs 433 ns of child CPU
per request, above the 171.6 ns allowance at the plan's tolerance, because the pipe round trip
dominates, so the serve shape does not demonstrate the hole; in a batch shape the skipped
arithmetic is the whole per-operation cost, about 156 ns against the same allowance, and a
counted object with that code path would count a near-free call. A counted object that fills
the slot must charge every counted call at least the reference cost or refuse to count a
short-circuited one; that is a requirement on item 1 of `cairn-m1-cqt.1.4`, and the live
allowance in `ladder.py` still comes from the method's declared profile until item 4 lands.

## Pre-registration, CPU-deployed

`probe_deployed_cpu.py` reuses the four arms, the pair design, the order rule, the warm-up,
the spread definition, the 0.50 bound per kind and the figure rule of the wall probe, and
changes only the numerator: the parent takes `getrusage(RUSAGE_SELF)` and
`getrusage(RUSAGE_CHILDREN)` directly ahead of the spawn and again at the reap, before any
response is parsed or validated, with the garbage collector held off in between and the
serve mode's kill timer joined, and the arm's cost is the sum of the two user plus system
deltas, so the parent's protocol CPU, the spawn's CPU and the reaped child's CPU are inside it
and the probe's own oracle work is not. The denominator stays the reference child CPU per operation from the
reference binary's own clock. The kinds are `cpu_deployed_batch`, `cpu_deployed_trial_batch`
and `cpu_deployed_ipc`; the `cpu` kind of `paired-rate-ratio.md` is never used. The bound is
evaluated per shape and arm as `0.10 × figure < 0.2432`, and the commit carrying this section
precedes every timed run recorded below. `getrusage` reports whole microseconds, so at 10000
operations per call the resolution is one tenth of a nanosecond per operation.

## Measurement, CPU-deployed, both arms, 2026-09-30

The pre-registration is carried by commit `48b06ef`. Each run took the heavy lock and the 6 GiB
cap; the orchestrator confirmed on the bead that these runs stand as the pre-registered ones
(agent-mail 468 and its follow-up).

| | `macos-host` | `linux-container` |
|---|---|---|
| Raw JSON | [deployed-cpu-ratio-macos-2026-09-30.json](deployed-cpu-ratio-macos-2026-09-30.json), 36716 bytes, SHA-256 `4f04a8c5b7af8cf5ec981aaf961a0b1515ecd9bbe05f744be6c08688d953b9d1` | [deployed-cpu-ratio-linux-2026-09-30.json](deployed-cpu-ratio-linux-2026-09-30.json), 36670 bytes, SHA-256 `23c64e0f6e071767c88b3420ee81ad774eef361f4bba4a32ac901a80b7d16f34` |
| Taken at | 18:02:45 through 18:02:51 UTC | 18:02:55 through 18:02:56 UTC |
| Compiler | Apple clang 21.0.0, `-O2 -std=c11 -Wall` | Debian clang 14.0.6, `-O2 -std=c11 -Wall`, kernel `7.0.14-orbstack` |
| Counted binary, reference binary | `9059d68af3db123e…`, `25322a466385bcc9…` | `c52bf5a73c375168…`, `453a6e69f5881984…` |
| Load, 1-minute | 40.90 ahead of the pairs, 39.77 after | 0.07 ahead and after, inside the container |
| Memory | 3943 free 16 KiB pages ahead, 5366 after | `MemFree` 14933048 kB ahead, 14924052 kB after |
| Open files | `kern.num_files` 24335 ahead, 24726 after | `file-nr` 340 ahead and after |
| Correctness prelude | 20 counted checks, 4 malformed refusals, serve sessions of 1, 2, 3 and 31 requests counted exactly | the same |

Per-pair ratios over 15 pairs, each arm's process-tree CPU per operation over the reference
child CPU per operation, with the pre-registered figure rule applied:

| Arm, kind | Min | Median | Max | Sample SD | Spread | Verdict | Figure (rule) | `0.10 × figure` | Bound holds |
|---|---:|---:|---:|---:|---:|---|---:|---:|---|
| macOS, `cpu_deployed_batch` (10000 ops) | 2.343 | 2.782 | 3.611 | 0.353 | 0.456 | within bound | 2.782 (median) | 0.2782 | no |
| macOS, `cpu_deployed_trial_batch` (37396 ops) | 1.206 | 1.464 | 1.965 | 0.187 | 0.518 | exceeded | 1.965 (max) | 0.1965 | yes |
| macOS, `cpu_deployed_ipc` (10000 round trips) | 43.12 | 59.08 | 79.38 | 8.16 | 0.614 | exceeded | 79.38 (max) | 7.938 | no |
| Linux, `cpu_deployed_batch` (10000 ops) | 0.962 | 1.318 | 1.617 | 0.170 | 0.496 | within bound | 1.318 (median) | 0.1318 | yes |
| Linux, `cpu_deployed_trial_batch` (37396 ops) | 0.890 | 1.100 | 1.674 | 0.224 | 0.713 | exceeded | 1.674 (max) | 0.1674 | yes |
| Linux, `cpu_deployed_ipc` (10000 round trips) | 15.56 | 25.49 | 29.24 | 3.95 | 0.537 | exceeded | 29.24 (max) | 2.924 | no |

Per-arm absolute medians in nanoseconds per group operation, with min and max; process-tree
CPU is the parent's delta plus the children's delta, and the children's delta covers the
child's chain plus its spawn:

| Arm | macOS child CPU | macOS tree CPU | Linux child CPU | Linux tree CPU |
|---|---:|---:|---:|---:|
| `reference` | 209.7 (157.1, 227.1) | 586.1 (450.9, 662.2) | 193.1 (148.6, 302.0) | 286.4 (198.5, 497.7) |
| `batch` | 206.3 (178.1, 233.1) | 576.4 (495.9, 678.3) | 182.4 (156.6, 278.0) | 247.3 (208.7, 445.9) |
| `trial_batch` | 203.2 (184.4, 221.4) | 296.2 (270.9, 327.1) | 193.3 (165.5, 282.4) | 209.1 (181.5, 338.4) |
| `ipc` | 4559 (3548, 5137) | 12095 (9719, 13513) | 1408 (1208, 1498) | 5045 (4338, 5531) |

The median spawn plus protocol CPU per call, tree CPU less the child's own clock, is 3.60 ms
and 3.48 ms on the host for the two batch arms under a load of 41, and 0.69 ms and 0.81 ms in
the container.

What the rows say:

- Under the CPU meaning the mean-trial batch shape holds the bound on both arms with the
  maximum observed ratio (1.965 on the host, 1.674 in the container), and the shortest-trial
  batch shape holds in the container at its median (1.318) and fails on the host at its median
  (2.782, a within-bound spread, so the median is the figure). The host run sat under a
  1-minute load of 41 from the other lanes' suites; its spawn plus protocol CPU is 3.6 ms per
  call against 0.7 ms in the container, and the two arms also differ in operating system,
  compiler, binaries and Python, so this record does not separate the load's share of that
  difference from the arm's. The pairing keeps the ratio a same-window figure on each arm and
  does not make either a quiet-host figure.
- Per-operation IPC fails on both arms by an order of magnitude, at the median as well as the
  maximum: the child's own CPU per request is 4.56 µs on the host and 1.41 µs in the
  container, 22 and 7 times the reference chain step, before the client's side is counted.
  The per-op round-trip shape cannot carry the pin at the plan's tolerance.
- The batch shape's figure is set by the spawn term over the trial's operation count. At the
  40-bit floor count of 1171749 operations the host's 3.6 ms of spawn CPU is 1.5 percent of
  the chain and the container's 0.7 ms is 0.3 percent; the 30-bit rung's short trials are
  where the shape fails on the host.

## Where this leaves `clock.rate_ratio` under the CPU meaning

The pin stays `1.0` with provenance `seeded:cairn-m1-cqt.1.4`. The measured figures the pin
would carry are, per shape and arm, in the table above: for the mean-trial batch shape 1.965
on the host and 1.674 in the container, which the loader accepts; for the shortest-trial
batch shape 2.782 on the host, which it refuses, and 1.318 in the container; for the per-op
shape 79.38 and 29.24, which it refuses. The orchestrator's rule is that the pin moves only
for the shape the gate deploys, with that shape named in the provenance, and the tree fixes no
shape: no method routes arithmetic through a process-kind object, `ladder.run`'s `ops_counter`
has no production supplier, and the counted object's own code path counts a degenerate call at
a fraction of a generic step (the compulsory-cost floor above). The shape decision goes to the
owner with both numbers: the batch shape whose walk runs inside the object holds the bound on
both arms at the mean 30-bit trial and fails on the host at the shortest 30-bit trials; the
per-op shape fails everywhere. Until the owner names the shape and item 1 builds an object
that charges constant work per counted call, `ladderplan` keeps the seeded value and refuses
any figure at or above 2.432.

No production source, bundle object, pin, golden or admission changed for this record.
