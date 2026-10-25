# Lift ideation round: pre-registered predictions

Registered 2026-10-21 2026-10-21 15:19 EDT, before any measurement of any candidate in this directory.
Inputs read before registering (not measurements of these candidates): tierb-lift/{lvlJ.c,model.py,PREDICTIONS.md,logs/},
tier0/lvlN.c, gpu/ Metal lvl12 note (COORDINATION 2026-10-20 15:40: 1.3e10 patterns/s kernel on this M5), published NVIDIA
H100 whitepaper table (INT32 33.5 TOPS counting an IMAD as 2 ops, i.e. 16.7e12 IMAD/s, SXM5, 1980 MHz), RunPod/Vast rates
(Community H100 SXM 2.69 USD/h, Vast marketplace median 2.07, Lambda 8x 3.99; page dated 2026-10-18).
A prediction is never edited after a measurement; a miss is recorded as a miss in RESULT.md.

Structural fact used throughout (derived on paper, checked in P-D): every new prime p of 10^Lnew-1 divides 10^Lold+1, so
10^Lold = -1 mod p and a child with lifted-slot counts k_s has residue y = y0 - 2*S (mod p), S = sum k_s (d_s-1) 10^{r_s}
(integer). All child residues lie on one line parametrized by S.

Verdict words: HELD (inside window), MISSED (outside window, candidate still stands), KILLED (kill test fires).
Machine: Apple M5, 10 cores, load average ~15 from other jobs. CPU timings are rusage CPU seconds at nice 10, so load
inflates wall but not (much) CPU; cache contention may inflate CPU by up to 1.3x and is a stated seam.

## (a) join48 made correct and gated  (levels 48 only; lvlJ.c copied unchanged except mutant set)
Population: every equation directory under the scratchpad h12/ whose parents48.txt is non-empty and whose lvlN level-48
CPU time is <= 90 s. Count N48 unknown; Prediction A0: N48 >= 60.
A1 differential: lvlJ48 output identical to lvlN (sha256 of sorted lines) and tail-dead/open/exact counters equal on 100%
   of N48. Kill: any single mismatch (join48 then not correct).
A2 non-vacuity: >= 15 equations with open+exact >= 1 and >= 40 with tail-dead+open+exact >= 8. Kill: fewer than 5
   equations with open+exact >= 1 (then survivors cannot gate a join at 48 from this corpus).
A3 mutants. M1 = original (drop K index j%8==3); M1' = drop odd K indices (defined for every K >= 2); M2 = 2^a replaced by 1.
   Catch = sha256 or any of tail-dead/open/exact differs from lvlN. Denominator = equations with reference
   tail-dead+open+exact >= 8 ("non-vacuous"). Predict: M1' caught on 100% of non-vacuous, M2 caught on 100%, M1 caught on
   fewer than 100% (K=2 sets make j%8==3 empty). Kill (of "gated"): any non-vacuous equation where M1' or M2 is not caught.
A4 speedup (CPU seconds lvlN / lvlJ48), median over equations with >= 1e6 children: 2.0, window [1.3, 4.0].
A5 model correction: lvlN level-48 cost per child, median over equations with >= 1e6 children: 150 ns, window
   [80, 300] ns. (model.py assumes 1000 ns; if A5 holds, the model's lift48 term is >= 3x too high.)

## (b) three-way join, meet cost ~ 2^{(k+1)/3}
Setup: C = 2^{k+1}-scale children per parent split into three lists of ~C^{1/3}; the constraint y in T*K couples all three
sums, so for every pair (a,b) one must probe K (or the cyclic structure of K); implemented as JOIN_WAY=3 in lvlJ3.c with
the same candidate verification, counting probes+table builds+candidate checks ("ops") exactly.
B1: candidate sets equal to the 2-way join's (same key set): 100% of parents (correctness of the construction).
B2: best-3-way ops / best-2-way ops, median over level-24 parents with C >= 1e4: 3.0, window [1.2, 10]. i.e. the three-way
    join is NOT cheaper. Kill of the owner's hypothesis (meet cost 2^{(k+1)/3}): fitted slope d log(ops)/d log(C) for
    3-way <= 0.45 on parents with C from 1e3 to 1e6; I predict the slope is in [0.5, 0.75] (2-way ~0.5 at fixed |K|).
B3: if B2 holds, three-way is KILLED; no timing run is claimed beyond ops count plus one CPU timing on 5 equations.

## (c) the lift on this Mac's GPU (Metal)
Design: GPU prefilter only. Per parent, the two halves HA (nA x np) and HB (nB x np) are formed on the CPU as in lvlJ; the
GPU evaluates for every (ia, ib, dn) the necessary condition y mod p0 in T0*K0 and y mod p1 in T1*K1 (bitmap membership
after multiplying by T^{-1}) for the two cheapest key primes (< 2^31), emits candidate indices, the CPU runs the
unchanged process_child on candidates. Sound by construction (necessary conditions only); correctness is checked by
sha256 vs lvlN.
C1 throughput: kernel children/s on a parent with C >= 1e6 children: 3e9/s, window [1e9, 1e10].
C2 end-to-end, level 24, equations with >= 5e6 children: speedup over lvlN (1 core CPU) 40x, window [10, 200].
C3 end-to-end, level 24, over lvlJ (CPU join): 2.5x, window [0.7, 8]. Kill ("GPU lift worth building next"): C3 <= 1.0.
C4 end-to-end, level 48, over lvlN: 60x, window [10, 400]; over lvlJ48: 8x, window [1, 40].
C5 differential: byte-identical on 100% of equations tested (>= 20 at 24, >= 20 at 48), one planted mutant (bitmap bit
    cleared for a K element) caught on every non-vacuous equation.

## (d) rank-0 / rank-1 fast paths that decide a parent without lifting
Definitions (from the line structure above). rank-0: all slot weights vanish mod the key prime (children residues a single
point). rank-1: children residues are a subset-sum line y0 - 2S; the parent is decided dead without enumerating children
iff the reachable residue set R_p = {y0 - 2S mod p} (a bitset DP, O(slots * p) instead of O(C)) misses T*K_p for some
prime p of the new modulus with p < 2^22.
D0: rank-0 parents: exactly 0 (p does not divide 2(d-1)10^r for d in 2..9 and p >= 17). Kill: any parent found.
D1: fraction of parents with C >= 2^10 decided dead by the bitset DP: <= 1% (window [0, 1%]); saturation: the DP
    residue set covers Z/p for p <= 1e4 once C >> p ln p. Kill of the fast path: <= 1% at Tier B scale (that is the
    prediction); the candidate SURVIVES only if >= 10% of C >= 2^10 parents are decided dead.
D2: share of level-24 and level-48 children belonging to parents with C <= 2^6: < 0.1%.
D3 proof obligation test: every parent decided dead has zero OPEN/EXACT lines and zero tail-dead in lvlN on the same parent
    (differential over all parents of >= 30 equations at each level); mutant: declare dead when R_p misses T*K_p shifted
    by one residue, must be caught.

## (e) adversarial lane
E1: across logged multisets with npat >= 1e7 and equal k (h12 logs, k = 13..21), the max/median ratio of lift24 children
    per level-12 pattern is >= 3 (window [3, 30]). Kill of "the fitted law is adequate": max/median <= 1.5.
E2: the all-2s-type multiset at the largest k of each vertex has per-pattern lift cost >= 4x the fitted law
    (survivors-per-pattern uplift 5x-15x already recorded at k = 20-21).
E3: with that uplift the single most expensive multiset (found by exhaustive scan of all multisets of all 13 vertices under
    the fitted law times the empirical uplift class) costs >= 15% of its vertex's total, and the adversarial vertex total
    exceeds the law-based estimate by >= 3x. Stated budget used for "cannot finish": 8 GPUs x 168 h = 1344 GPU-h
    (an assumption: the owner gave none). Existence is shown by construction in the model plus measured uplift at k <= 21;
    no vertex at k >= 25 is run, so the adversary at Tier B scale is MODELED, not measured.

## (f) CUDA port of level 12 + lift on 8 rented GPUs, all 13 Tier B vertices (modeled)
GPU class H100 SXM5 80 GB, 16.7e12 IMAD/s peak (published), rate 2.69 USD/GPU-h (RunPod Community; Vast median 2.07,
Lambda 8x 3.99 as band). Throughput basis: this M5's measured peak INT32 IMAD rate (microbenchmark) and the measured
Metal kernel rates (lvl12 1.3e10 patterns/s per Cairn's note; prefilter C1), scaled by published peak ratio with an
efficiency factor 0.6 relative to the M5 kernel's efficiency (H100 occupancy/memory behavior unmeasured).
F1: total GPU-hours, all 13 vertices, brute-force CUDA level 12 + CUDA join/prefilter lift: 1,500, window [500, 10,000]
    (band is the model uncertainty, not a confidence interval). At 2.69 USD/h: 4,000 USD, window [1,300, 27,000].
F2: level 12 is >= 50% of the GPU-hours in that configuration. Replacing it with dual12 (CPU, cost independent of N12;
    tierb-lift model 28 core-days) lowers the total by >= 2x. Kill of F2: level 12 < 30%.
F3: wall clock on 8 GPUs = total/8: window [60, 1,300] hours.
F4: host side (candidate verification at ~100 ns per candidate at 24, ~2 us at 48) needs <= 1,000 CPU-core-days; PCIe and
    memory terms <= 5% of GPU-hours.
F5: porting plus validation effort: 5-10 engineer-days for CUDA lvl12 (kernel exists in Metal; gate v2 exists) plus
    10-20 for the lift prefilter, host orchestration and the differential gates (an estimate, not measured).

## Surfaced by the skills (scored by expected value / cost)
G1 (idea-wizard): the model's lift48 term at 1 us per child is the largest term of the mixed plan (8.4e3 of 1.06e4
   core-days); A5 tests it first because it is free and moves every other number.
G2: dual12 + join24 + GPU prefilter at 48 is the combination to build; join48 on CPU (x2) is the fallback.
G3: p5 persistence of the 3-prime key at 48 (17, 5882353): evaluate which key sets lvlJ actually selects at 48 and the
    resulting candidate rates; no separate prediction beyond A4.
