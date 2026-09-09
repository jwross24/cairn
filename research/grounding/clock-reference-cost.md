# The clock reference is a cost in seconds per group operation

`uv run python research/grounding/probe_clock_reference_cost.py` (2026-09-08, build
machine, defaults: 10000 group operations per arm per rep, 7 reps).

Operator decision 12 asks what the fastest arithmetic a method could carry costs, so the
ladder's clock check has a floor to divide by. `ladderplan.ClockBound` holds when
`clock_tolerance * rate_ratio < 2 * design_radius`, and `rate_ratio` is the counted
object's per-operation cost over this figure. A throughput stored in this field inverts
the bound while leaving every type check satisfied, which is why
`bundle/ladder_plan.json` names the field `cost_s_per_group_op` and `ladderplan`
refuses a value at or above `MAX_GROUP_OP_COST_S` (one second): a group operation that
costs a whole second is a rate wearing a cost's name.

## Machine and toolchain

| | |
|---|---|
| Host | Apple M4, arm64, macOS 26.6 |
| Compiler | `/usr/bin/clang`, Apple clang version 17.0.0 (clang-1700.4.4.1) |
| C flags | `-O2 -std=c11 -Wall` |
| Build directory | a fresh `tempfile.mkdtemp` outside the checkout |
| Python | 3.14.0 under `uv` |
| gmpy2 | 2.3.1 against GMP 6.3.0 |
| PARI | 2.17.2 through `cypari2`, one thread (`cairn.pari` pins `nbthreads=1`) |

The compiler is reached by absolute path because an interactive shell on this machine
aliases `cc` to something that is not a compiler.

## Method

The curve is `tests/vectors/curve60_seed1.json`, a 60-bit prime-order toy curve, inlined
in the probe so it stands alone: `p = 866004983247663323`, `n = 866004982950395713`.

Four arms compute the same deterministic chain over that curve, a doubling on each even
step and an addition of the base point on each odd one:

- `python_int` — `cairn.ec`, the pure-Python affine arithmetic the harness ships.
- `gmpy2` — the same chain over `gmpy2.mpz`.
- `cypari2` — `pari.ellinit` on the same curve, with `pari.elladd(curve, v, v)` as the
  doubling, since PARI's addition law covers it.
- `c_reference` — an embedded C translation using `unsigned __int128` for mulmod and an
  extended-Euclid `invmod`, compiled into the scratch directory and timed on
  `CLOCK_PROCESS_CPUTIME_ID`.

Every arm reports its final point and the probe exits 1 without printing a table if the
four disagree, so a faster arm that is computing something else cannot become the
reference. Each arm runs 7 reps; the recorded figure is the median of the per-rep costs,
and the min, max and standard deviation travel with it so the spread is visible in the
bundle rather than hidden behind a single number.

## Measurement

All four arms agree on `(476377072802646283, 562446501424608226)`.

    arm                          min            median               max                sd
    python_int        0.000002458600    0.000002767600    0.000003137800    0.000000236166
    gmpy2             0.000000647500    0.000000676500    0.000000937100    0.000000101126
    cypari2           0.000000603800    0.000000767900    0.000000884800    0.000000117044
    c_reference       0.000000184900    0.000000217100    0.000000243700    0.000000017965

    fastest: c_reference at 0.000000217100 seconds per group operation

`bundle/ladder_plan.json` stores every row above under `clock.reference_cost`, with
`arm = c_reference` and `cost_s_per_group_op = 0.000000217100`. `ladderplan` refuses a
plan whose named arm is absent from the table, whose stored figure is not that arm's own
median, or whose named arm is not the fastest median measured, so the bundle cannot name
a reference the table does not support.

## What the figure is and is not

It is a build-machine fact at measurement time, tagged `measured:` in the plan's
provenance, not a claim about elliptic-curve arithmetic in general. The arms sit within a
factor of 13 of each other on one host, one curve size and one operation mix; a different
host, a Montgomery or projective representation, or a batched inversion moves them.

The gap that matters for the bound is `c_reference` against `cypari2`, a factor of about
3.5 on these medians: an implementation that counts PARI operations and reports them as
if they were the floor understates its own cost by roughly that much.

`clock.rate_ratio` is a separate field with its own provenance and is not set from this
measurement; it belongs to the counted object, and pinning it against this reference is
`cairn-m1-cqt.2.5`'s successor work, not this file's.
