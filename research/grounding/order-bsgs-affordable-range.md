# Affordable range of the gmpy2 Hasse-interval order search

The toy-curve skill declares an independent range for each cross-check axis. This record
measures the per-curve cost of the gmpy2 implementation axis
(`src/cairn/skills/order_bsgs_gmpy2.py`) so the declared range for that axis rests on a
measurement rather than on arithmetic about the interval width.

## Host and toolchain

- Apple M4, arm64, macOS 26.6, 10 cores.
- Python 3.14.0 under uv; gmpy2 2.3.1 against GMP 6.3.0.
- libpari is reached only to draw the curves. The search itself imports gmpy2 and nothing
  else, which `tests/unit/test_order_bsgs_gmpy2.py` asserts against `sys.modules` in a
  subprocess.

## Method

`research/grounding/probe_order_bsgs_range.py --sizes 30,40,50,60 --curves 50`.

For each size and each seed 1..50 the probe draws a curve with
`cairn.skills.toy_curve.run(bits, seed)`, then times
`order_bsgs_gmpy2.orders_in_hasse(p, a, b, P)` on the drawn point and compares the recovered
order against the PARI-counted `n` the same call returns. The probe exits 1 without a table
if any curve disagrees.

**CPU time is the reported figure.** The host was shared while this ran: the one-minute load
average was 23.16 at the start and 24.23 at the end, on 10 cores. A wall figure taken under
that load measures the load, so the wall median is recorded beside the CPU figures as
context and is not the basis of any conclusion below.

## Measured

50 curves per size, 200 curves in total, seconds of CPU per curve. `table` is the number of
baby-step points the search stores; `ambig` counts curves where more than one order in the
Hasse interval annihilates the drawn point.

| bits | curves | table | ambig | cpu min | cpu median | cpu max | cpu sd | wall median |
|---|---|---|---|---|---|---|---|---|
| 30 | 50 | 338 | 0 | 0.000385 | 0.000474 | 0.000979 | 0.000160 | 0.000491 |
| 40 | 50 | 1986 | 0 | 0.002222 | 0.002868 | 0.004517 | 0.000612 | 0.003115 |
| 50 | 50 | 10360 | 0 | 0.014225 | 0.018908 | 0.026557 | 0.003058 | 0.025086 |
| 60 | 50 | 63119 | 0 | 0.086226 | 0.120636 | 0.144540 | 0.014628 | 0.142288 |

Every one of the 200 curves recovered exactly the order PARI counted, and on every one the
recovered order was the only order in the Hasse interval that annihilated the point, so a
single drawn point settled the group order without a second one.

Total elapsed for the run, curve generation included: 98.6 s.

## Verdict

The measured range is **30 to 60 bits inclusive**, at a median of 0.12 s of CPU per curve at
the top of it. That is affordable inside a toy-curve run whose own production cost at 60 bits
is 0.88 s of wall per curve (`COST_PROFILE` in `src/cairn/skills/toy_curve.py`), so the
cross-check adds roughly one seventh to the cost of drawing the curve.

The cost rises by a factor of about 6.3 per 10 bits, which is the `p^(1/4)` the interval
width predicts, and the stored table rises with it: 63119 points at 60 bits.

## Limits

- **Sizes above 60 bits are not measured.** The factor above extrapolates to roughly 0.75 s
  at 70 bits and 4.7 s at 80, and the table to about 2 million points at 80 bits, where
  memory rather than time becomes the binding constraint. None of that is measured here and
  none of it belongs in a declared range.
- **The sample is prime-order curves as `toy_curve` draws them.** `toy_curve` searches until
  the order is prime, so the drawn point generates the whole group and one point always
  suffices. The `ambig` column being zero is a property of that population, not of the
  algorithm: a curve whose group is not of prime order can leave several candidate orders,
  which `orders_in_hasse` returns and `group_order` refuses to guess between.
  `tests/unit/test_order_bsgs_gmpy2.py` covers that case on a tiny curve.
- **The figures are CPU seconds on a loaded box.** CPU time is far less sensitive to
  contention than wall time, but it is not immune: cache pressure from the other lanes
  inflates it by an unmeasured amount. The verdict has roughly a factor of seven of headroom
  at 60 bits, so it does not turn on the exact figure.
