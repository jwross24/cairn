# The interpreted 60-bit hold-out rung does not fit the Tier-1 budget

Operator decision 2 funds a compiled rho/BSGS baseline only if an interpreted one cannot
finish a ladder rung inside the tier budget. Two rungs feed that call. This record settles
the 60-bit half and states the arithmetic; the <= 50-bit half is bead `cairn-m1-cqt.1.7`'s
and is absent here, because L7 is blocked on L4 and L4 on this bead.

**Status: proposed, pending operator ratification.** The numbers below are measurements and
arithmetic over them. Funding is the operator's decision, not this file's.

## Inputs, each read rather than recalled

| input | value | source |
|---|---|---|
| 60-bit interpreted rate | 688598.1 to 1294801.6 group ops per second | `research/grounding/m0-stack-facts.md` rho60 table, runs A to C |
| 60-bit expected work | 1166326476 group ops (birthday bound for the instance's order) | same table |
| 60-bit wall per trial | 1693.8 s (A), 996.0 s (B), 900.8 s (C) | same table, `expected ops / measured ops/s` |
| hold-out trial count | `hold_out_m = 10` | `bundle/ladder_plan.json` |
| 60-bit rung shape | `bits 60, role hold_out, trials 10` | `bundle/ladder_plan.json` |
| arms at the hold-out rung | the claimant's method only, no baseline and no A/A | PLAN.md 818-828 |
| Tier-1 ceiling | `max_core_s = 3600` | `bundle/tiers.json` boundary table, tier 1 |

## The arithmetic

One arm times ten trials times the per-trial wall:

    slowest measured rate   10 * 1693.8 s = 16938 s   =  4.71 * the 3600 s ceiling
    run B                   10 *  996.0 s =  9960 s   =  2.77 * the ceiling
    fastest measured rate   10 *  900.8 s =  9008 s   =  2.50 * the ceiling

The rung exceeds the ceiling at every rate measured, by a factor between 2.50 and 4.71.
The margin is not close enough for the spread to decide it: even at the fastest rate the
budget covers 3 of the 10 hold-out trials (2702.4 s), and 4 trials (3603.2 s) already
exceed it; at the slowest rate it covers 2.

## Verdict on the 60-bit half

**The interpreted 60-bit hold-out rung cannot finish inside the Tier-1 budget, so the
funding trigger fires on this half.** The decision stands on the 60-bit half alone. Bead
`cairn-m1-cqt.1.7` completes the record with the <= 50-bit half, which PLAN section 6(2)
prices at the sized trial count across three arms and expects to be the larger figure; a
funding call already triggered by the smaller figure is not weakened by the larger one.

## What this does not establish

The per-trial wall is CONJECTURE and carries that tag at its source: it assumes a rate
measured over the first 10^8 ops of one walk on one seed holds for the remaining ~1.07x10^9,
and that the walk's expected length equals its birthday bound. A completed 60-bit
interpreted walk exists nowhere in this tree.

Exceeding `max_core_s` for tier 1 is a statement about the tier-1 budget, not about
feasibility: tier 2 carries `max_core_s = 3600000`, which 16938 s sits well inside. The
trigger the operator decision names is the Tier-1 one, and that is the one this file
evaluates.

The rates are single-core cypari2 figures on one Apple M4 host. A compiled baseline's own
rate is measured nowhere here; `research/grounding/clock-reference-cost.md` measures a C
reference against cypari2 on a 60-bit curve at roughly 3.5 times faster per group
operation, which is an arithmetic-primitive comparison on that host and not a projection
of a compiled rho's end-to-end rate.
