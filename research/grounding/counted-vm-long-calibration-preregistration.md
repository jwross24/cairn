# Counted VM long-sample calibration: pre-registration

Bead `cairn-m1-cqt.1.4`, stage S4. Harness: `research/grounding/probe_counted_vm_long_calibration.py`
(its `PREREGISTERED` dictionary is the machine-readable copy of the table below; the harness refuses
a confirmatory run whose source or this document differs from the digests the operator supplies).
This document and the harness are committed before the run, and the run executes only from that
commit.

## Authority

- Owner ruling 2026-10-19, decision 3.3 (bead comment of that date): method as written in
  `fleet-infra/data/cairn-path-20261013/DECISIONS.md` section 2; one calibration; samples of at least
  10^7 operations; cost per operation as a two-point difference; the 0.50 bound unchanged; host load
  under 2 checked before any timing, otherwise no run is consumed; host load recorded beside every
  figure; a long-sample failure on an idle host leaves the ladder INCONCLUSIVE by its own rule and the
  bound never loosens.
- Owner ruling 2026-10-17 and 2026-10-19, decision 3.1: the ladder baseline is the plain
  distinguished-point program; the sign instruction stays behind `signed/1`. The harness reads
  `bundle/ladder_plan.json` and refuses unless `baseline.method_identity.params.variant` is `plain`.
- Coordinator rulings on the owner's delegation: the rung sizes come from the ladder plan and the
  loop bounds are the pre-registered constants in the table below; the plan supplies no operation
  counts. An exceeded cell has no figure and the bound never loosens.
- Arm scope: this pre-registration covers the `dev-macos` arm only, and "one calibration" means that
  arm. The Linux container arm is out of scope. A later Linux arm needs its own pre-registration and
  is not a retry of this one. The harness refuses a confirmatory run of any other arm.
- This document is a pre-registration under RULE 2. It sets no pin; the conversion to
  `clock.rate_ratio` is the rule below, and the pin itself is set from the retained report at the S4
  pin review.

## What is measured

The process-tree CPU cost per counted group operation of the gate-owned counted VM, divided by the
inner CPU cost per operation of the native reference (`probe_clock_reference_cost.C_SOURCE`, the
same text the earlier 10,000-operation pre-registration used), for each of six program kinds, at each
rung field size, on each arm. A counted operation is one group operation under
`countedvm.COUNTING_CONVENTION`.

| Kind | Loop body | Counted ops per iteration |
|---|---|---:|
| `chain` | `dblp`, `addp` | 2 |
| `add` | `addp p0 p0 p1` | 1 |
| `double` | `dblp p0 p0` | 1 |
| `identity` | `addp p0 p2 p1` with `p2` the identity | 1 |
| `inverse` | `addp p0 p1 p3` with `p3 = -p1` | 1 |
| `scalar_mul` | `mulp p0 p1 s0`, scalar 7 | 4 |

## Fixed before any curve is drawn

The rung field sizes come from `bundle/ladder_plan.json` (`rungs[].bits`) and must equal 30, 40, 50
and 60; the harness refuses otherwise. Every program, its SHA-256 and its exact executed-instruction
count are computed from these values and the parameters below before the first curve is generated,
and are written to the report as `bounds_fixed_before_any_curve`. A program text contains no curve
field: it depends on the kind, the operation count and the inner counter only.

| Parameter | Value |
|---|---|
| Rung sizes | 30, 40, 50, 60 bits (from the plan) |
| Low point | 10,000,000 counted operations |
| High point | 20,000,000 counted operations |
| Loop structure | outer counter in `i1`, inner counter `i0` of 500,000 iterations; both below the VM index cap 1,048,575 |
| Instruction budget | 200,000,000 (the largest program executes about 60,000,000) |
| Pairs per rung | 15 |
| Warm-up | one run per arm at the low point, retained, outside the statistic |
| Arm order | seeded hash order per pair, seed 20261020 |
| Instance | `toy_curve.run(bits, 1)`; every result checked against an independent GP computation |
| Wall cap | 300 s per process |
| Bound | 0.50, unchanged from the earlier pre-registration |
| Load limit | 2 |

## Sample design

For each pair and each arm, the harness runs the low point and then the high point back to back.
The cost per operation is the two-point difference

    cost = (CPU_high - CPU_low) / (ops_high - ops_low)

so process start, sandbox setup and any fixed allocation cancel. The VM figure is user plus system
CPU over the process tree from the runner receipt; the native figure is the inner
`CLOCK_PROCESS_CPUTIME_ID` interval its own output reports. The payload of one difference is
10,000,000 counted operations. Each run's counted operations, executed instructions and result point
must equal the expected values or the run is refused. A non-positive difference marks the pair
invalid; an invalid pair makes its cell INCONCLUSIVE and is never dropped or replaced.

Per pair the ratio for a kind is the VM cost per operation over the native cost per operation. This
ratio feeds the 0.50 spread statistic only; the conversion below uses the medians of the costs.

## Statistic and bound

Per kind and rung: spread = (max - min) / median over the 15 ratios. The cell is within the bound
when spread is at most 0.50, and INCONCLUSIVE when it is above. A cell above the bound has no
figure; no maximum rule, no trimmed rule and no extra pairs rescue it. Only the six kind cells per
rung gate. The harness recomputes every cell from the retained per-pair costs; it never trusts a
stored or caller-supplied status.

## Load precondition

Before the build and before any timing the harness reads `os.getloadavg()` and refuses unless the
one-minute average is strictly below 2. A refusal prints a record with `run_consumed: false` and the
observed averages to the `--out` path and to standard output, and builds nothing, so it consumes no
run. The one-, five- and fifteen-minute averages are recorded before and after every timed process,
warm-ups included, beside its CPU figure. A clean status requires every one of those recorded
one-minute readings to be strictly below 2.

Every attempt's output (refused, `LOAD_NOT_CLEAN`, or complete) is retained unedited, and the close
of the bead lists all of them. The criterion that decides whether an attempt consumed the
calibration is the mechanical recorded load and the status below, never a judgment.

## Outcomes

`status` in the report is one of the following, evaluated in the order listed under "Precedence".
`WITHIN_BOUND` and `EXCEEDED_ON_IDLE_HOST` each consume the one calibration; a refusal,
`LOAD_NOT_CLEAN` and `INVALID_SAMPLE` do not, and the report records `run_consumed` accordingly. An
exploratory (non-preregistered) run never consumes the calibration, never sets `run_consumed`, and
never produces a `rate_ratio` candidate; its status is informational only.

- `WITHIN_BOUND`: every cell on the arm is within 0.50 and no recorded one-minute average reached 2.
  The long samples pass the bound on this arm. It leaves the startup allocation, margin and emulation
  floor of design v2 unsupported. Consumes the calibration.
- `EXCEEDED_ON_IDLE_HOST`: some cell is above 0.50 and every recorded one-minute average stayed below
  2. By DECISIONS.md section 2 the CPU clock cannot support the design on this machine; the ladder
  stays INCONCLUSIVE here by its own rule, the bound does not move, and a dedicated host is the
  remaining route. This is a finding. Consumes the calibration.
- `LOAD_NOT_CLEAN`: some recorded one-minute average, a warm-up reading included, reached 2 during
  the run. The run says nothing about the idle host in either direction, and no pin is set from it.
  It does not consume the calibration: a rerun is allowed on a new output path, and this attempt's
  report stays retained and listed.
- `INVALID_SAMPLE`: the host stayed idle, no valid cell exceeded 0.50, and at least one pair has a
  non-positive or ill-posed two-point difference, so its cell is INCONCLUSIVE. This is not a
  measurement of the bound. It does not consume the calibration, the same retention rule as
  `LOAD_NOT_CLEAN` applies, and no pin is set from it.

Precedence: `LOAD_NOT_CLEAN` first; then `EXCEEDED_ON_IDLE_HOST` when any fully valid cell is above
0.50, so an invalid pair elsewhere never converts an idle-host failure into a retry; then
`INVALID_SAMPLE`; then `WITHIN_BOUND`.

## Conversion to `clock.rate_ratio`

Defined by `src/cairn/ladderplan.py`: `ReferenceCost` is the fastest per-operation cost on the build
machine, `ClockBound.rate_ratio` is the counted object's per-operation cost divided by it, and the
plan holds only when `clock_tolerance * rate_ratio < 2 * design_radius` (tolerance 0.10 and design
radius 0.1216 in the plan give a ceiling of 2.432 on the ratio). The plan also refuses a ratio below 1.

- Counted object: the VM, all six kinds, each a counted opcode the gate attributes to a method.
- Reference binding (coordinator decision, following `ladderplan.py` exactly): the scalar
  `ReferenceCost.cost_s_per_group_op` for the pin is set from this run as the smallest native
  two-point per-operation median, taken over the native medians of the four rungs (the native arm is
  one cost per rung, shared by that rung's six kind cells, so the 24 cells carry four distinct native
  medians). It is a cost in seconds per group operation, never a rate. The stored bundle value
  `2.17100E-7` is not used in the conversion; the pin review replaces both the scalar and the ratio
  from this same run. No claim is made that no faster arithmetic exists.
- Statistic: for each rung and kind, the median over the pairs of the two-point VM cost per
  operation, in seconds. It is not a per-cell paired ratio: a paired ratio divides by that rung's own
  native cost and so understates the ratio against the single reference scalar, which errs loose.
- Conversion: only from a report whose status, recomputed from the cells, is `WITHIN_BOUND`, and only
  with all four rungs and all six kinds present; anything else is refused. The unrounded ratio is
  the largest VM median over all 24 cells divided by the reference scalar. The unrounded ratio is
  checked against the below-1 refusal first. It is then rounded up (toward positive infinity) to
  three significant digits, and the plan inequality is applied to the rounded candidate. The largest
  ratio makes the tolerance `min(plan value, 2 * radius / ratio)` and the load check err tight.
- The harness reports `rate_ratio` with `reference_cost_s_per_group_op`, `slowest_vm_cost_s_per_op`,
  `unrounded_ratio`, `candidate`, the product with `tolerances.clock`, `2 * design_radius` from
  `bundle/ladder_plan.json`, and whether the plan inequality holds. No other statistic, kind subset
  or rung subset is used.
- If the candidate product reaches 2 * design_radius, the plan refuses the pin
  (`clock-bound-violated`), the ladder stays INCONCLUSIVE, and nothing loosens: not the tolerance, not
  the design radius, not the rounding, not the kind set. If the unrounded ratio is below 1, no
  candidate is produced (the benchmark and the object do not measure the same operation) and the
  ladder stays INCONCLUSIVE. From any status other than `WITHIN_BOUND` no candidate is produced.
- Scope of the figure: it is the marginal (two-point) ratio. Process start, sandbox setup and fixed
  allocation cancel in it by design and are not in the figure. They belong to the B2 startup terms,
  which this run leaves unsupported (see below). The pin review states how those terms enter before
  any pin is set; this conversion rule does not change.

## Not established by this run

The measured figures are of this native reference, these field sizes, this operation mix, this machine
and this session. The run does not evaluate B2/B3 sufficiency, supply a rung A/A radius, support a
startup allocation or margin, or bound the cheapest VM-emulated group operation. No KEEP, no PROVEN and no claim about the 254-bit curve follows
from a green harness or a passing run.
