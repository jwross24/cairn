# Constant-work counted operations: the D2 requirement and its probe

This record is retained as research. Design v2 of `cairn-m1-cqt.1.4`
(`c14-design-v2-2026-09-30.md`, after the adversarial review of v1) withdraws the
exact-equality requirement below in favor of a conservative lower bound on the CPU of any
counted opcode (its B2), executed inside a gate-owned VM; no timed run of this probe is taken
under v2, and the step and the division finding stand as evidence that bound will need.

Design item D2 of v1 (orchestrator ruling 468): every counted call costs the same CPU
regardless of input, within a pre-registered spread, so that
`clock_tolerance * rate_ratio < 2 * design_radius` bounds hidden work with the cheapest
counted call equal to the generic one. The bound assumes every counted call costs at
least the per-operation allowance; a call that early-returns on a degenerate input, or an
inversion whose running time depends on its operand, lets a method buy allowance it does not
spend. This record carries the change to `counted_process.c`, the reason its first form was not
enough, the probe that measures every counted kind against the generic addition in paired
runs, and the two planted builds that must fail it.

## The counted step

`counted_add` and `counted_double` route every call through one `ct_step(left, right)`:

- One affine formula serves addition and doubling. The chord slope `(y2 - y1) / (x2 - x1)`
  and the tangent slope `(3 x1^2 + a) / (2 y1)` are both computed, and the one the inputs
  call for is selected by a mask, never by a branch; `x3 = lam^2 - x1 - x2` and
  `y3 = lam (x1 - x3) - y1` are the same expression in both cases.
- The degenerate cases (an infinity operand, the inverse pair `P + (-P)`, the `y = 0`
  doubling, and `P + P` through the addition path) are detected as masks, the full formula
  is computed on whatever the operands are, and the output is selected by mask: the other
  operand, the point at infinity, or the computed point.
- The field inversion is a fixed-exponent Fermat ladder, `x^(p-2)`, over all sixty bits of the
  exponent: sixty squarings and sixty multiplications every call, with the multiply's result
  selected by the exponent bit through a mask. The extended-Euclid `invmod` remains in the
  file for the `raw` mode, which is the variable-time reference chain, and for the planted
  build below.
- Every multiplication in the step is a Montgomery multiplication (`mont_mul`, REDC with a
  64-bit word, constants `-p^-1 mod 2^64`, `2^128 mod p` and `2^64 mod p`), with a masked
  conditional subtraction. Operands enter Montgomery form on the way in and leave it on the
  way out. The `raw` mode keeps the `u128 % p` multiplication it always had.

The step's semantics on curve points are those of the previous implementation: the `counted`
chain lands on the same point as the `raw` chain and the scalar oracle at every count the
correctness prelude checks.

### Why the division had to go

The first constant-work form kept `u128 % p` as the multiplication and only replaced the
inversion and the early returns. Under it the counted chain cost 1475 ns per operation and the
generic addition 1475 ns, but the inverse pair cost 284 ns, the `y = 0` doubling 286 ns and
the unit-`x`-difference chord 289 ns (exploratory single runs on the host, 10000 operations
each). The work was constant at the algorithm's level and the time was not: the masked-out
paths multiply by zero, and the compiler's 128-by-64-bit division returns early on a small
dividend, so a call whose inputs make the intermediate values small runs five times faster.
Montgomery multiplication has no division, and under it the same kinds cost within a few
percent of the generic addition.

### What "constant work" claims here

The claim is that the algorithm performs the same sequence of arithmetic operations for every
input, with no data-dependent branch and no data-dependent division at the source level. It is
not a claim about the hardware, and it is established for one target: multiplier latency on
the build machine is not measured here, and the compiler decides the branches. Apple clang 21
at `-O2` emits the masked subtraction in `mont_redc` as a select on arm64 and as an
operand-dependent conditional branch on x86-64 (four `jb` sites inside the inversion loop of
`ct_step` under `-arch x86_64`), so the branch-free property of the counted path holds for the
arm64 build and not for an x86-64 one. Cache and branch-predictor effects of the surrounding
loop are handled by giving every measured kind the same loop-carried dependency (the previous
result feeds a volatile carry into the next inputs), so that no kind gains instruction overlap
the others lack.

## The per-kind modes

`counted_process kind-<name> OPS timed|untimed` runs `OPS` counted calls of one kind and prints
the closed JSON summary with the count and the last result:

| Mode | Call | Expected result after `OPS` calls |
|---|---|---|
| `kind-add` | `acc + G`, `acc` from `G` | `(OPS + 1) G` |
| `kind-double` | `acc + acc` through the same step | `2^OPS G` |
| `kind-inverse` | `G + (-G)` | infinity |
| `kind-identity` | `O + G` | `G` |
| `kind-torsion` | `(gx, 0) + (gx, 0)` as a doubling | infinity |
| `kind-adjacent` | `(gx, gy) + (gx + 1, gy)` | the chord with slope 0 |

The chained kinds carry their own dependency; the fixed-input kinds read their operands through
volatile loads XORed with a volatile-carried zero derived from the previous result, so the loop
cannot be hoisted or overlapped. The probe validates every kind's count and final point against
its own arithmetic (`cairn.ec` for the curve kinds, the chord formula for `kind-adjacent`).

Two compile-time flags restore the defects for the planted builds and are otherwise absent:
`-DCAIRN_EARLY_RETURN` returns the other operand or infinity ahead of the formula on the
degenerate inputs; `-DCAIRN_VARIABLE_INVERSION` inverts with the extended Euclid.

## Pre-registration

`probe_constant_work.py` fixes these in `PREREGISTERED`; any other value needs `--exploratory`
and labels the report `constant_work_exploratory`, which is not evidence. The commit carrying
this section precedes every timed run recorded below.

| Setting | Value |
|---|---|
| Kinds | `counted` (the alternating chain), `kind-add`, `kind-double`, `kind-inverse`, `kind-identity`, `kind-torsion`, `kind-adjacent` |
| Generic | `kind-add` |
| Pairs | 15, each running all seven kinds in an order drawn from seed 20260930 and the pair index |
| Operations per call | 10000 |
| Warm-up | one call per kind, retained, excluded from the pairs |
| Quantity | child CPU per operation on `CLOCK_PROCESS_CPUTIME_ID` inside the object; the spawn is the same for every kind and cancels in the ratio; process-tree CPU is recorded beside it |
| Ratio per pair | each kind's child CPU per operation over the generic addition's in the same pair |
| Constant-work band | a kind is constant work when the median of its ratio is at least 0.90; below the band it is cheaper and the requirement fails |
| Spread | `(max - min) / median` over the per-pair ratios, bound 0.50, reported per kind |
| Planted builds | `--planted early-return` must show `kind-inverse`, `kind-identity` and `kind-torsion` cheaper; `--planted variable-inversion` must show `kind-adjacent` cheaper, and the kinds whose denominator is zero come out cheaper under it as well, since the extended Euclid on zero exits at once; a planted run whose expected kinds are not all cheaper exits 1 |

The 0.90 band is the null-control band of `paired-rate-ratio.md`, applied one-sided: a kind may
cost more than the generic addition and still meet this requirement. That one-sidedness is
safe only when the rate the deployed ratio uses is the minimum per-operation CPU over every
counted kind; the deployed probes of `deployed-rate-ratio.md` calibrate on the alternating
chain alone, so a dearer chain beside a cheaper kind would let a method buy the cheaper call
against the dearer calibration. Under v2 that minimum is B2's `c_floor`, taken as a lower bound
with a margin, and the per-kind medians here are the evidence it draws on, not the calibration
itself. The requirement holds only when every kind is within the band and within the spread
bound; an exceeded spread refuses the requirement rather than passing on the median.
