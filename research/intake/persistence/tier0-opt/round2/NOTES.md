# lvl12 round 2 (untracked research code)

Deliverable: `lvl12_r2.c` (build: `cc -O3 -march=native -o lvl12 lvl12_r2.c`, Apple clang, NEON required), binary `lvl12_r2`, SHA256 in `SHA256`.
Baseline for every ratio: `tier0-opt/lvl12.c` (md5 8f60d984...) and the frozen reference (`tier0-opt/reference/lvl12.c`, md5 35528aab..., binary sha256 a28dc065...), which is byte-identical to the tier0/lvl12 used for the reference hashes.

## Fixed-shape guard
At startup the program derives the prefilter as a sum of per-prime table entries and proves it equal to the original subgroup test over every component index (512, 243, 3125, 11). The fast paths need np=5, nc=4, L=12, G=12, K=3 for every a, lam=100, q>3, A+12<64; otherwise the optimized-baseline code path runs unchanged (the fallbacks were not exercised at level 12).

## Levers (each source in levers/Ln.c, cumulative)
| id | lever | isomorphism note |
|---|---|---|
| L1 | last digit loop fused into one function, counters in locals, one modular reduction per prime | same enumeration order, same per-pattern predicate; counters added at end |
| L2 | prefilter as sum of u16 syndrome entries (one per prime, zero flag folded in) plus a 14-bit accept table; ENT/OKT only on survivors | accept set proven equal on the component index space at startup |
| L3 | doubled per-prime tables indexed by the unreduced sum (no compare/subtract), compact u16 residue table | table[v] = table[v mod p] |
| L4 | branch-light tail for K=3, lam=100: feasibility table of the 1000 residues Y plus allowed-digit masks for residues 0..2; any candidate is re-run through the original tail_test | exact case impossible when q>3 (Y has <=3 digits); a conservative "alive" falls back to the original code, so printed records and counters come from the original |
| L5 | survivor path on packed u32 component index and (v0 mod 1200, v1 mod 100, v2 mod 100) words | k mod 100 = (a0 - v0 mod 1200)/12 mod 100 |
| L6 | branchless leaf: survivors collected into a list, processed after the 12-residue loop | emission order unchanged |
| L7 | NEON: 12 residues at once, per-prefix table SV[p][b*12+r] (syndrome vectors), movemask for pass and zero lanes | pass mask applied only to r >= start |
| L8 | survivor queue (128 records, FIFO flushed per nu and when full) | survivors processed in enumeration order, so stdout is byte-identical |
| L9 | R folded into the prefix state | none |
PGO (llvm 23 -fprofile-instr-use): no gain over the same compiler without it; not used. Homebrew clang alone ~8-10% faster than Apple clang, within noise.
Not landed: early-abort prime ordering (coordinator's measurement: 10-25% slower; and the zero test must see all five primes to keep cnt_zero/cnt_pre identical, so ordering is not free); Gray-code walk (prefix cost is 0.7 of ~2.5 ns, not pursued); CRT-grouped tables.

## Findings
- Unpredictable branches cost about 25 ns each on this host: replacing the survivor branch with a branchless list gave L5 5.9 -> L6 3.8 ns.
- Prime 37 matters only as a zero test; the Z4/Z2 syndrome involves primes 11, 13, 9901 and the Z5 one 11, 101, 9901. H is the same for every multiset at level 12.
- Phase split of L7: enumeration 0.70 ns, vector filter 0.45, survivors 1.3 (before L8).

## Gate state (see logs/)
Gate (a) check_golden (9 files + c_oracle incl. stderr counters): L1, L2, L3, L4, L6 (queue), R2 final: all SAME.
Gate (b) difftest 72 and 10800: L1 IDENTICAL both; L2 only 72 (10800 not run, queue interrupted); L3 both; L4 72 only; R2 (final): both IDENTICAL (logs/R2_b.log).
Gate (c) vertex 14336 (16 equations, 503581 lines, 1.79e9 patterns, per-equation and overall sha plus stderr counters): L1, L3, R2 identical to the frozen reference (R2 3.7 s vs 55.8 s, 3 procs each).
L5, L6, L7, L8, L9 were not individually gated through (b)/(c); only the final R2 passed (a), (b) and (c). Raw stdout of R2 is byte-identical (unsorted) to the reference on 5 scratch equations.
Mutants (mutants/, 20 optimization-specific): quick differential (logs/quickmut.log) 19 of 20 differ from the reference on stdout or stderr counters in at least one of three equations; m12 (feasibility count permissive) is equivalent by design (falls back to the original tail); m05/m06 (valid mask) show only on equations whose last digit group repeats. Full gate (a) was completed for m01-m04 only (all DIFF in 5 files); the rest were interrupted. Gate v2 not run.
