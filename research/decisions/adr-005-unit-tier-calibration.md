# ADR 005: Measured unit-tier selection

Status: accepted

## Decision

The optional `scripts/check.sh --unit` tier selects unit tests using two complete,
passing duration reports from the same source revision. Each report includes every
unit node and all three pytest phases. A node's duration is the median of its summed
setup, call and teardown times. Unknown nodes remain included.

The personal-MBP phase budget is 45 seconds. The threshold is the largest observed
median for which the retained population fits that budget. The remaining 15 seconds
of the 60-second command target covers measured startup and fast-gate overhead plus
variation. A timed command under 60 seconds is required independently of the sum.

The resulting threshold is 1.075 seconds across 2,432 measured nodes. Ten nodes are
slow-marked and 2,422 remain selected. Every node with a median above five seconds
is included in the slow-marked set. Marker selection affects only the optional unit
tier; pre-commit uses `--fast`, and full checks and CI execute marked tests too.

## Evidence

`research/grounding/unit-tier-calibration-2026-09-08/mbp-verification.md` records
the commands, source revision, load observations, report digests, actual command
timing and planted refusal. `tests/unit/test_check_unit_tier.py` checks report
completeness, strict threshold arithmetic and a deliberately missing marker.

## Alternatives and limits

A fixed five-second threshold does not account for aggregate command time.
Omitting arbitrary modules or reducing Hypothesis examples would discard coverage
without measured selection. Neither is part of this policy.

This is a local feedback tier, not a substitute for a full passing gate. Timing
portability, full-suite speedup and mathematical claims are outside its evidence.
