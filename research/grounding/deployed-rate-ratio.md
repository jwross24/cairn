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
