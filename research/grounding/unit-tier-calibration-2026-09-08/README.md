# Measured unit tier

The personal-MBP calibration and command verification are recorded in
`mbp-verification.md`. The operating condition is no competing pytest process
and a one-minute load below 10 at both measurement endpoints.

The unit tier marks tests whose measured median duration exceeds **1.075 seconds**.
The plugin reads `calibration.json`; a test absent from its slow-node list runs by
default. Full pytest and CI execute the marked tests. This is tier selection,
not a speedup of the full suite or a change to Hypothesis examples.

Two complete passing samples provide two observations for 2,432 nodes. Ten nodes
are marked slow; 2,422 retained nodes sum to 43.880 seconds in per-node medians.
The 45-second phase budget reserves 15 seconds of the command target for startup,
fast gates and variation. Full-unit command overhead outside the recorded phases
was 9.23 and 9.51 seconds; the unchanged unit command's non-pytest overhead was
2.42 seconds. The actual unit command, rather than that arithmetic, settles the
60-second target. No unit node is omitted from the measurement population.

## Historical source-machine evidence

`warm-checkpoint.md` and `warm-checkpoint-evidence.tar.gz` preserve the source-machine
attempts, exclusions, warm-hook verification and independent audit reproduction.
The paragraphs below describe those archived measurements, not `calibration.json`.

Two historical passing samples provide two observations for 2,156 nodes. Their 265 slow nodes
are all under `tests/unit/`; integration, end-to-end and other directories have
zero nodes in this marker list. The 1,891 measured retained nodes sum to 54.775
seconds in per-node medians, within a 55-second measurement budget. Their phase
totals in the two individual reports are 54.80 and 54.75 seconds. These quantities
exclude collection/session overhead and do not establish command wall time.
The source-machine checkpoint has no qualifying post-warm sample and uses
the 265-node selection described in its archived reports.

The largest observed threshold satisfying that budget is 0.11 seconds. Reports
print hundredths of a second; arithmetic uses `Decimal`, and a two-sample median
can have half-hundredth precision. The boundary concerns reported timings, not
unrounded elapsed time.

`calibration.json` records every observed node's sample count, exact slow IDs,
unmeasured IDs, report digests and budget arithmetic. Forty-four nodes have one
observation: 27 in `test_ladder_table.py`, 17 in `test_gate_scope.py`. They remain
unmeasured and included by default. Tests introduced outside these reports also
remain included. No measured module is excluded in its entirety.

The measurement commands and their wrapper results are in `measurements.json`.
`full-unit.log.gz` contains 2,200 passes in 258.64 seconds; `stable-unit.log.gz`
contains 2,156 passes in 296.54 seconds. The stable sample names explicit unit
file paths and omits the two files with in-flight peer edits. Those omissions
apply to measurement only. CopperRidge messages 1072 and 1098 authorize per-test medians
with at least two passing observations on the moving shared tree.

Rejected samples remain available: `rejected-ladder-api.log.gz` has two failures
and 2,198 passes in 380.15 seconds; `rejected-gate-scope.log.gz` has six failures
and 2,203 passes in 351.01 seconds. Neither contributes timing observations.

`unit-before-selection.log.gz` records the complete unit command at
`b9e6742cfb66f15094f8ab178cc5674f489a98fd`: 2,181 passes and two deselections in
307.45 seconds; command wall time 311.3909475830005 seconds, exit 0. The shared
tree's test population varies between samples, so the figures do not establish
a causal performance delta.

`checkpoint-validation.tar.gz` contains the fresh read-only audit and main-agent
reexecution from before the September 8 disk pause at 23:23 UTC, plus the live
single-file and fast-gate logs from 23:36 UTC under RESUME-LIMITED.

```bash
UV_CACHE_DIR=/tmp/cairn-runtimemoth.U7GUPL/uv-cache uv run pytest -q tests/unit/test_check_unit_tier.py
UV_CACHE_DIR=/tmp/cairn-runtimemoth.U7GUPL/uv-cache scripts/check.sh --fast
```

Both commands exit 0. The targeted result is 15 passed, 1,896 warnings in 1.01
seconds; the warnings concern pytest cleanup PermissionErrors in its shared
default scratch root. Every fast gate passes. UBS, compliance and the full unit
command are unrun under the coordinator's disk restriction. This is a checkpoint,
not closing evidence.

No-Claim: full-suite speedup, changed example budget, timing portability, an
irreducible runtime floor, or mathematical evidence.
