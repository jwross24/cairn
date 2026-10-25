# Tier C rank census and closure verdicts: vertex 3416267673274176 = 2^6 * 3^27 * 7

Everything under `P/tier0-opt/tierc-rank/` (P = `/Users/jwross/Documents/cairn/research/intake/persistence`). Nothing under `P/tier0/` or the other `P/tier0-opt/` subdirectories is edited; they are read only. Scripts and raw outputs sit beside this file.

Vertex choice: FRONTIER.md Tier C table, row `C | A_6 | 3416267673274176 | 2^6*3^27*7 | 1.72e+19 level-12 patterns | k_max 34 | 306 multisets`. It is the Tier C vertex with the fewest patterns.

Labels used: "closed by the cut" (Lemma C depth 1, a congruence cut), "closed by the sandwich (U'')" (Baker ceiling below a lattice floor), "open". Nothing here is PROVEN.

## 0. Verdicts in one table

| rank (MAP.md) | share of the open@96 anchored patterns, 95% interval | what closes it | label on the sample | what is left |
|---|---|---|---|---|
| 0 (3 and 7 do not divide y; y = 2^a) | 2.02% [1.84, 2.23] (exact count 4,168,580,093) | M0: discrete log of the pattern value base 2 modulo R_96, then one explicit integer 2^x0 | closed by the cut, 300/300 sampled (95% lower bound 0.988 per pattern) and by an argument that covers every rank-0 pattern | nothing |
| 1 (exactly one of 3, 7 divides y) | 28.4% [25.4, 31.7] | rank-aware depth-1 cut (moduli 5^9*2^(a+10) or 5^10*2^(a+12)), then Matveev with one logarithm fewer, Mignotte-Voutier three-log constants, one-dimensional first-gap reduction | closed by the cut: 15,000/15,000 sampled (10,000 wrap 0, 5,000 wrap > 0). The production rank-2 cut leaves 14 of the 10,000 wrap-0 patterns open; the rank-aware cut closes all 14 | no survivor observed; 95% upper bound 6.7e-4 per pattern, 3.9e7 patterns. The bound improvement of Section 4.2 is computed; no rank-1 certificate machine exists to use it |
| 2 (3 and 7 both divide y) | 69.6% [66.1, 72.6] | depth-1 cut (moduli 5^5*2^(a+9)), then sandwich | 14,918/14,918 sampled with wrap > 0 and 25,077/25,082 sampled with wrap 0 closed by the cut | 7.2e6 depth-1 survivors [1.4e6, 1.5e7]; at the measured per-survivor node costs a bill of 1.5e7 core-days [2.1e5, 4.7e7] = 4.0e4 core-years: a wall for the hardware at hand, a finite bill in principle |

The 57% / 38% / 5% split of MAP.md describes the level-12 patterns (Section 2.1: 57.14% / 38.10% / 4.76%, exact). The open@96 set follows the supply of S-units that can serve as anchors (Section 2.2): 2.0% / 28.4% / 69.6%. A rank dispatch removes the 2% and trims the 28%; the 70% is rank 2.

## 1. Rank, exactly as MAP.md defines it

MAP.md section 2.3 item L4 and section 3 item P3: a level-12 (or level-96) pattern fixes n mod 96 and the digit positions mod 96, hence y mod 3 (digit sum n + m) and y mod 7 (period 6 divides 12). Every candidate y' of the pattern has the same residues, because 3 and 7 divide R_96. Then:

- rank 0: 3 does not divide y and 7 does not divide y, so b = c = 0 and y' = 2^a;
- rank 1: exactly one of them divides y, so one of (b, c) is forced to 0;
- rank 2: both divide y.

MAP.md section 6 (last bullet) asks that the fractions be measured per vertex before use. Section 2 does that, on two populations.

## 2. Census

### 2.1 Layer A: all level-12 patterns, exact

`census_l12.py` enumerates the 306 multisets of digits {2,3,4,6,7,8,9} with product s and counts level-12 patterns (12 * prod_d C(11 + m_d, m_d)) by (y mod 3, y mod 7) with an exact residue convolution. Total 17,240,008,221,052,531,200 (equals the FRONTIER.md figure 1.72e19; k_max = 34).

| rank | patterns | share |
|---|---|---|
| 0 | 9,851,433,269,172,876,336 | 57.1429% |
| 1 | 6,567,622,179,448,581,024 | 38.0952% |
| 2 | 820,952,772,431,073,840 | 4.7619% |

The uniform-residue model of MAP.md (4/7, 8/21, 1/21) holds to 15 digits on this layer. No interval is needed: the counts are exact.

### 2.2 Layer B: the open@96 set, as anchored patterns

Definition (RESULT-anchorfirst.md section 1): a level-96 pattern (nu, {(d_j, e_j)}) is anchored on the S-unit y = 2^a 3^b 7^c below 10^98 (a <= 60) if y + k R_96 = R_nu + sum (d_j - 1) 10^(e_j) for an integer wrap k. A pattern anchored on y has the rank of y. The anchored set is the hypothesis-level open set; accidents (open patterns with no anchor) are not counted (Seams).

Pair list. `sunits.py` reproduces the scout's inputs: 609,796 S-units (61 of rank 0, 17,735 of rank 1, 592,000 of rank 2) and 1,109,618 (y, k) pairs that pass the mass filter (1,718 / 104,651 / 1,003,249 by rank). Both totals equal the numbers recorded in RESULT-anchorfirst.md.

Counting. `anchor_dp.c` counts, for a pair (y, k) and each nu in [0, 96), the exact number of patterns by a carry DP over the 96 positions with state (carry, exponent vector of the placed digits) and the target exponent vector (6, 27, 1). It matches brute-force enumeration on 3,840 cells for the vertex 12 (`dp_test.py`).

| rank | pairs | anchored pairs, 95% interval | anchored patterns, 95% interval | share, 95% interval | how obtained |
|---|---|---|---|---|---|
| 0 | 1,718 | 792 | 4,168,580,093 (exact) | 2.02% [1.84, 2.23] | every pair run |
| 1 | 104,651 | 18,147 [17,696, 18,605] | 5.87e10 [5.40e10, 6.34e10] | 28.4% [25.4, 31.7] | first 6,204 pairs run exactly (8,589,306,552 patterns, 1,899 anchored pairs); 25,000 uniform pairs of the other 98,447; bootstrap on the sample |
| 2 | 1,003,249 | 63,957 [61,574, 66,404] | 1.437e11 [1.248e11, 1.638e11] | 69.6% [66.1, 72.6] | 40,000 uniform pairs (2,550 anchored); Clopper-Pearson on the anchored fraction (6.375%), bootstrap on the pattern total |
| all | 1,109,618 | 82,896 | 2.07e11 [1.87e11, 2.27e11] | | |

Agreement with earlier work: RESULT-anchorfirst.md predicts 8.7e4 anchored pairs and 1.9e11 patterns for this vertex; FRONTIER.md forecasts 2e11 (interval x0.1 to x30). The rank-2 anchored fraction 6.4% is in line with the scout's 7.9 +- 0.5% over all ranks (the per-rank fractions are 46.1% for rank 0, 17.3% for rank 1, 6.4% for rank 2).

Why Layer B differs from Layer A: an anchor is a small S-unit. Of 609,796 candidates 97.1% are divisible by both 3 and 7, so a pattern anchored on a rank-0 or rank-1 S-unit needs one of only 61 pure powers of 2 or 17,735 two-prime S-units. The measured H11 result agrees: the branch-split lane found that only the class 3 | y and 7 | y keeps nearly everything through levels 24 to 96 (r1-branch-split/REPORT.md: "the other three keep under 0.3%", production versus split 1.0 to 1.3x at levels 24 to 96).

## 3. Rank 0: the finite check M0

Statement. Let P be a rank-0 pattern with value V = R_nu + sum (d_j - 1) 10^(e_j) (positions mod 96). A candidate is y' = 2^(a'), and y' = V (mod R_96).

1. R_96 is factored as the product of the cyclotomic values Phi_d(10), d | 96, d > 1 (product checked equal to R_96). `znlog` in PARI solves 2^x = V modulo each prime power and a CRT combines the solutions. No solution: closed by the cut.
2. The solutions form x0 + t L, with L = ord_{R_96}(2) = 10372778469215462708202978013645376100000000 (1.037e43).
3. Every candidate has a' <= A, where A is the larger of two 2-adic bounds for the pattern's digit multiset: the digit-by-digit chain T7 (theta/NOTES.md, re-derived without error in h3-h4/REPORT.md section "Audit", item 6) and Fonga Corollary 3.2 (arXiv:2608.27802, read in `n4-literature/raw/2608.27802.txt`; v_2(x) <= rho c^q + (c^q - 1)/(c - 1) log_2 B). Across the 300 sampled patterns A lies between 10^11.29 and 10^18.05. Since L > A by 24 orders of magnitude, a' = x0 is the only candidate exponent. If x0 > A the pattern is closed. Otherwise the single integer 2^x0 is compared with the pattern: exactly (x0 <= 3000) or by its 400 low digits having at most k non-1 digits.
4. The argument uses the exponent bound A, not a Baker ceiling, so it stands in the family "closed by the cut" (a congruence cut plus a finite check).

Sample. 300 patterns drawn uniformly from the 4,168,580,093 rank-0 anchored patterns (`draw.py`, the C sampler in `sample` mode, `verify_pat.py`: 300/300 satisfy the anchor identity and the product 2^6 3^27 7). Result (`r0_m0.out`): 300/300 closed by the cut; in every case x0 equals the anchor exponent (300/300), and 2^x0 is the anchor itself, which has the wrong digits. 95% Clopper-Pearson lower bound on the closure rate: 0.988. Do not retry a larger sample: the argument above does not depend on the sample.

Planted negatives (`m0_run.py`, `m0_controls.py`):

- Inflated bound: the same 300 patterns with A set to 10^400 (above L): 300/300 refused ("open", reason "ord2 not above a-bound").
- Known survivors: the 17 genuine powers of 2 whose digits are all in {1,2,3,4,6,7,8,9} (the five recorded children 16, 32, 64, 128, 8192 from `runall_final.jsonl`, `trees_c.jsonl`, `trees_mac.jsonl`, plus 12 more up to 2^400): 17/17 reported open ("2^x0 is a genuine candidate"); each with one position shifted: 16 closed by the cut, 1 outside rank 0 (not testable), 0 left open.

Positive control against recorded Tier A verdicts: the recorded depth-1 list `DEEPCUT-run-final-d1.txt` holds no rank-0 row (rank 0: 0; rank 1: 185 closed and 1 open; rank 2: 452 closed and 42 open). The recorded children are rank 0 in 5 of 169 cases and all 5 are reported open, as recorded.

## 4. Rank 1

### 4.1 The rank-aware depth-1 cut

For rank 2 the depth-1 test of Lemma C reduces to: a case (which digit, if any, of each low class e < a + 9 sits at the copy inside the 96-window) survives iff T = R_96 + sum_inside (d - 1) 10^e is congruent to y modulo 5^5 * 2^(a+9). This holds because both basis vectors of Lambda_96 are congruent to 1 modulo 5^5 and 2^9 (valuations 5 and 9, 5 and 10, theta/NOTES.md T4; saturation in codex-deep-attempt T3).

For rank 1 the lattice is one-dimensional, generated by g = 3^L3 (or 7^L7), with L3 = ord of 3 modulo R_96/3 and L7 = ord of 7 modulo R_96/7. `sat_check.py` computes v_5(g - 1) and v_2(g - 1): (9, 10) for base 3 (L3 = 4.51e41) and (10, 12) for base 7 (L7 = 2.96e42). Every candidate y' = y g^t is congruent to y modulo 5^9 * 2^(a+10) (respectively 5^10 * 2^(a+12)). The rank-1 cut uses these moduli. It is a necessary condition for a candidate, so it never closes a pattern that has one, and it is at least as strong as the rank-2 cut.

Control: the one recorded rank-1 survivor of the production (rank-2) cut, y = 19131876 = 2^2 * 3^14 (`patterns-u2.jsonl`, SANDWICH-run row s=42336 M=2336778, recorded closed by the sandwich at depth 3), is closed by the rank-1 cut (`r1_ctrl.out`).

Samples. 15,000 patterns are drawn from the rank-1 anchored population (cells with probability proportional to their counts: the exact prefix plus the suffix sample scaled by 98,447 / 25,000; wrap 0 is 18.2% [15.5, 21.0] of the rank-1 patterns): 10,000 from wrap 0 and 5,000 from wrap > 0. `verify_pat.py`: 0 invalid. Under the production (rank-2) cut 14 of the 10,000 wrap-0 patterns survive (0.14%, 95% interval [0.077%, 0.23%]) and 0 of the 5,000 others (upper 7.4e-4). Under the rank-1 cut 0 of 10,000 (upper 3.7e-4) and 0 of 5,000 survive, so all 14 are closed. The stratified 95% upper bound on the survival rate is 6.7e-4 (0.182 * 3.7e-4 + 0.818 * 7.4e-4), at most 3.9e7 of the 5.87e10 [5.41e10, 6.35e10] rank-1 patterns; the observed count is 0 (`survival_r1w0_prod.out`, `survival_r1w0_r1cut.out`, `survival_r1other_prod.out`, `costmodel4_r1.out`).

### 4.2 Bound improvement on rank-1 patterns (three-log reduction)

Chain values. `chainrank.py` reimplements `baker_chain.py` (Matveev, BMS Theorem 9.4, C(t) = 1.4 * 30^(t+3) * t^4.5) with gmpy2 and takes the logarithm sets as parameters. It reproduces all 99 cells of the BAKER-CHAIN.md table (k = 0..32; a = 0, 1, 40) within 0.0005, and the two-ended chain (b3 chain, `chain2_control.py`) reproduces the six recorded values 281.50 / 279.23 / 280.06 (k = 31) and 402.11 / 393.93 / 394.75 (k = 44) within 0.006, with the optimal meeting indices 17, 16, 16, 24, 23, 23.

Three-log constants. `kitmv.py` evaluates Theorem 2.1 of Mignotte-Voutier (arXiv:2205.08899, `raw/2205.08899.txt`) with the parameter recipe of its section 5.2 and the log b estimate of its Lemma 3.5(b). Calibration (`kit_control.out`): for Example 1, step 3 (D = 2, rho = 10, m = 6, chi = 0.75) the minimal L is 167, K = 221,944 log y, log b = 54.588 and K L log rho = 8.5345e7 log y; the paper prints L = 167, K = 221,945 log y, log b' < 54.58 and 8.535e7 log y. For the gap forms of the chain (alpha_1 = 10 with coefficient E_j, alpha_2 = N_j / 2^a with coefficient 1 and height (S_j ln 10 + 1), alpha_3 = 3 or 7 with coefficient b + 2 or c) the kit gives a per-gap multiplier K_1 = 10^10.6 (prime 3) or 10^10.9 (prime 7) at n = 10^400 (`k1_values.out`). The Matveev multipliers at the same n are 10^18.6 for baker_chain.py (rank 2), 10^16.4 for rank 1 with the logarithms of 2, 3, 10, and 10^14.5 for rank 1 with 2^a folded into the varying rational (the form the kit treats). The like-for-like gain of the kit is 10^3.9 per gap. Only the non-degenerate branch is used (Seams).

First-gap reduction. `bd_first_gap` in `m1lib.py` applies Baker-Davenport (Dujella-Pethő form: convergent denominator q > 6B, epsilon = ||mu q|| - B ||gamma q|| > 0) to the top form |b' gamma - n + mu| < (80 / ln 10) 10^(-g_0), gamma = ln p / ln 10, mu = a ln 2 / ln 10, B = 2.1 n + 2. It replaces the first-gap bound 10^15 by about log10 n + 2 digits. Later gaps depend on the prefix and cannot be reduced without enumerating prefixes (theta/NOTES.md T8; MAP.md B4), so the gain is one gap out of k.

Results on 5,500 sampled rank-1 patterns (1,000 from the wrap-0 sample and 4,500 from the wrap > 0 sample, matching the 18:82 split; 610 distinct (k, a, prime) triples; k = 19 to 34 with median 26, a median 6; `m1_final_summary.out`). The sandwich depth is D = ceil((log10 G - 72)/48) + 1, from the floor 10^(24 + 48 D) digits (DEEPCUT.md; SANDWICH.md).

| digit bound G | median log10 G | range | D, median [range] | share with D <= 6 |
|---|---|---|---|---|
| baker_chain.py, rank 2 (reference) | 502.8 | 333.1 to 656.5 | 10 [7, 14] | 0% |
| Matveev, rank 1 (one logarithm fewer) | 441.7 | 290.0 to 586.2 | 9 [6, 12] | 0% |
| Matveev rank 1 plus first-gap Baker-Davenport | 430.0 | 280.2 to 574.3 | 9 [6, 12] | 0.3% |
| Matveev rank 1 with 2^a folded into the varying rational (the kit's form; `m1_fold.out`) | 398.3 | 287.1 to 520.5 | 8 [6, 11] | 0.4% |
| three-log kit (non-degenerate branch) | 289.7 | 205.0 to 382.3 | 6 [4, 8] | 78.5% |
| three-log kit plus first-gap Baker-Davenport | 277.2 | 192.6 to 369.8 | 6 [4, 8] | 91.8% |
| two-ended, rank 2 (Matveev plus Bugeaud-Kaneko 5-adic) | 240.5 | 166.1 to 300.6 | 5 [3, 6] | 100% |
| two-ended, rank 1 | 196.4 | 140.2 to 248.0 | 4 [3, 5] | 100% |

Median gains in orders of magnitude: rank 1 against rank 2 with Matveev 58.8; folding 2^a 50.3; kit against folded Matveev rank 1 108.9 (against unfolded 158.9); kit against baker_chain.py 213.1; first-gap reduction 11.7. Depth saved by rank 1 in the two-ended chain: 0 levels for 986 patterns (17.9%), 1 for 4,331 (78.7%), 2 for 183 (3.3%). Depth saved by the kit against baker_chain.py: 3 to 5 levels for 5,467 of 5,500 patterns. Two-ended with the kit on the archimedean half (`m1_t2.out`): k = 34, a = 6: 205.0 (D = 4); k = 31, a = 0: 191.9 (D = 4); k = 26, a = 6: 155.8 (D = 3).

Reading. The three-log constants lower the one-ended bound by about 109 orders of magnitude against Matveev on the same folded form (159 against the unfolded one), and bring the one-ended depth into the range D <= 6 that Method A has run (k = 31, 200/200 nodes at D = 6). The pipeline's own ceiling family is two-ended; there the rank-1 logarithm count alone saves one depth level for 79% of the sampled patterns (median D 5 to 4), and the kit on the archimedean half saves a second (k = 34, a = 6: 300.6 for rank 2, 243.8 for rank 1, 205.0 with the kit; D 6, 5, 4). A lower D can lower the explicit-digit depth E of Method A (exact_E: D = 6 and a > 0 need E = 4, D <= 5 need E = 3), which cuts the node count by a factor of 77 on the recorded k = 31 pattern (33,882,112 nodes at E = 4 against 440,640 at E = 3). This changes the cost per survivor, not the count of survivors.

Verdict for rank 1: "open" for the survivors of the rank-aware cut. The bound improvement is real and measured, it does not by itself close a pattern, and no rank-1 certificate machine exists to run the closure.

Planted negative and control for the closure rule (`m1_control.py`): the 43 recorded sandwich patterns (42 of rank 2, 1 of rank 1): my rank-2 chain reproduces the recorded log10 G on 43/43 (max difference 0.0044), the recorded depth rule on 43/43, and closure at the recorded depth (min-bound above G) on 43/43; with G set to 10^400 the rule refuses 43/43. The rank-1 row has G = 124.8 against 143.02 for rank 2 and still needs depth 3, as recorded.

## 5. Rank 2: cost model of the residue

Unit costs. The recorded k = 31 Method A run (COORDINATION.md lines on "Method A"; `k31run/summary.out`): 440,640 depth-3 nodes, 440,640/440,640 certified, mean 0.02320 s per node to certify and 0.02167 s to verify, 5.49 core-hours for certify plus verify (2.84 core-hours certify only).

Node counts. The depth-E nodes of that run are digit-ordered placements with at most one special digit per position, so for a pattern the count is: sum over the depth-1 surviving cases of the product over classes of the number of completions in the remaining E - 1 copies, times the product over high classes of all completions. `depth1c.py` computes it. On the recorded k = 31 pattern (`TIERC_CLASSES`, y = 3^3 7^10) it returns 2 surviving depth-1 cases and 3,072 / 440,640 / 33,882,112 nodes at E = 2 / 3 / 4: the E = 3 value equals the recorded N_3 = 440,640 exactly (`depth1c_k31.out`). The depth D of a pattern with k digits and exponent a comes from the U'' table (`cport-shadow/logs/utable_u2_k29.log` for k <= 29, `utable_u2_k31.txt` for (31, 0), linear extrapolation in k beyond), E from `exact_E(D, a)`.

Depth-1 survival. The same DP counts surviving cases exactly for any explicit pattern. Controls (`depth1_control.py`, `s1_bruteforce.py`): the 43 recorded depth-1 survivors are all reported as survivors (43/43; 47 of their 88 representations survive); 600 random small patterns agree with direct enumeration of all cases (599 with at least one surviving case, 183 with more than one, 0 count mismatches); 1,319 of 1,760 single-digit perturbations of the recorded survivors are closed.

Samples. Patterns are drawn uniformly from the rank-2 anchored population (cells chosen with probability proportional to their exact pattern counts, then a uniform pattern inside the cell by a backward-count sampler; `verify_pat.py` checks the anchor identity and the digit product on every pattern: 0 invalid in 41,200). Survivors cluster on wrap 0 (y itself equals R_nu plus a sparse tail; 25.2% [20.1, 30.4] of the rank-2 patterns), so the wrap-0 stratum has its own sample.

| stratum | patterns sampled | depth-1 survivors | rate, 95% interval | survivor node counts (E = 3) |
|---|---|---|---|---|
| wrap 0 (25.2% of rank 2) | 25,082 | 5 | 2.0e-4 [6.5e-5, 4.7e-4] | 24,912; 301,056; 445,952; 652,800; 18,186,240 |
| wrap > 0 (74.8%) | 14,918 | 0 | 0 [0, 2.5e-4] | |

Independent random cases predict far more survivors than the exact count. On the first 1,200 sampled patterns, a per-case probability of 1/640,000 gives 44,471 expected surviving cases and the per-case probability 1/(3125 * 2^(a+9)) gives 3,829; the exact number of surviving patterns is 0 (`nc_stats.py`, `nc_stats2.py`). The cases of one pattern are strongly dependent (bit constraints chain through the classes), so that model is not used.

Totals for the 1.437e11 rank-2 patterns [1.248e11, 1.638e11]:

| quantity | central | 95% interval |
|---|---|---|
| depth-1 survivors | 7.2e6 | [1.4e6, 1.5e7] |
| core-days, certify plus verify at 0.0449 s per node | 1.47e7 | [2.1e5, 4.7e7] |
| core-years | 4.0e4 | [590, 1.3e5] |

The largest survivor (18.2 million nodes, 227 core-hours) carries 93% of the node sum of the five survivors, so the interval reflects a heavy tail; the other four average 4.4 core-hours, which gives a central total of 1.3e6 core-days (3.6e3 core-years). A fixed 32 s per survivor, the cost of the level-480 closure of the k = 31 pattern (`cport-shadow480/RESULT.md`), would give 2.7e3 core-days [5.3e2, 5.5e3]; that route was run on one pattern and its child space (2.4e16 per word at k = 31) grows with k, so it is a sensitivity, not an estimate.

Verdict for rank 2: a finite bill that is a wall on this hardware. On 10 cores the central figure is about 4,000 years and the lower edge of the box about 59 years. It becomes a bill only if a per-survivor route about 10^3 times cheaper than Method A generalizes beyond the one pattern where it was run.

Rank 1 adds no cost estimate. No survivor of the rank-aware cut appears in 15,000 sampled patterns, so no node count exists, and no rank-1 certificate machine exists. The 95% upper bound for rank 1 (3.9e7 patterns) lies above the rank-2 central count (7.2e6), so the upper limit of the whole residue is set by the rank-1 sample size, not by the rank-2 measurement: about 6e4 sampled rank-1 patterns with wrap > 0 and none surviving (with the wrap-0 sample unchanged) would bring that bound to the rank-2 count.

Rank 0 contributes nothing (Section 3).

## 6. Controls and planted negatives in one place

| item | control | result |
|---|---|---|
| anchor pair list | scout totals | 609,796 S-units and 1,109,618 pairs: equal |
| anchor DP | brute force on vertex 12 (all positions, all nu) | 3,840/3,840 cells equal, zero cells included |
| rank-2 chain | BAKER-CHAIN.md table | 99/99 cells within 0.0005 |
| two-ended chain | recorded 281.50 .. 394.75 | 6/6 within 0.006 |
| three-log kit | Mignotte-Voutier Example 1 step 3 | L = 167, K, log b, K L log rho reproduced |
| depth-1 test | 43 recorded survivors | 43/43 survive; 1,319/1,760 perturbed copies closed |
| depth-1 test | direct enumeration | 600/600 counts equal |
| node model | recorded k = 31 N_3 | 440,640 = 440,640 |
| closure rule | 43 recorded sandwich rows | G, depth and closure reproduced 43/43; G = 10^400 refused 43/43 |
| M0 | 17 genuine powers of 2 | 17/17 open; 16/16 shifted copies closed |
| M0 | A = 10^400 | 300/300 refused |

## 7. Commands and md5

All commands run from `P/tier0-opt/tierc-rank`, each prefixed `PYTHONDONTWRITEBYTECODE=1 nice -n 10`; `PY` stands for `uv run --no-project python -I`. One compute process ran at a time (the exact rank-1 run was suspended with SIGSTOP and resumed with SIGCONT around the short jobs, see Seams).

| step | command |
|---|---|
| build | `cc -O2 -o anchor_dp anchor_dp.c`; `cc -O2 -o anchor_dp2 anchor_dp.c` (anchor_dp2 accepts `y k nu m` lines in `sample` mode) |
| Layer A | `PY census_l12.py > census_l12.out` |
| pair list | `PY sunits.py > sunits.out` (writes `pairs_filtered.jsonl`) |
| DP control | `PY dp_test.py > dp_test.out` |
| chain and kit controls | `PY chain_control.py > chain_control.out`; `PY chain2_control.py > chain2_control.out`; `PY kit_control.py > kit_control.out`; `PY m1_control.py > m1_control.out` |
| rank 0 census | `PY mk_sample.py 0 100000 1 r0_all.txt`; `./anchor_dp 6 27 1 count < r0_all.txt > r0_all.out` |
| rank 2 census | `PY mk_sample.py 2 40000 31 s2_40k.txt`; `./anchor_dp 6 27 1 count < s2_40k.txt > s2_40k.out` |
| rank 1 census | `PY mk_sample.py 1 1000000 1 r1_all.txt`; `./anchor_dp 6 27 1 count < r1_all.txt > r1_all.out` (stopped after 6,204 lines); `head -6204 r1_all.out > r1_prefix.out`; `PY mk_suffix.py r1_all.txt 6204 25000 5 r1_suffix_sample.txt`; `./anchor_dp2 6 27 1 count < r1_suffix_sample.txt > r1_suffix_sample.out` |
| census table | `PY census_stats2.py spec_final.json > census_final.out` |
| pattern samples, rank 0 | `PY draw.py r0_all.out 300 5 r0_draw.txt`; `./anchor_dp 6 27 1 sample 5 1 < r0_draw.txt > r0_samp.out`; `PY parse_samples.py r0_samp.out r0_pat.jsonl`; `PY verify_pat.py r0_pat.jsonl` |
| pattern samples, rank 2 | `PY draw.py s2_40k.out 1200 9 r2_draw.txt` with `./anchor_dp ... sample 9 1`; `PY draw_grouped.py s2_40k.out 20000 77 r2g_draw.txt` with `./anchor_dp2 ... sample 77 1`; `PY draw_wrap.py s2_40k.out 20000 91 r2w0_draw.txt w0` with `./anchor_dp2 ... sample 91 1`; then `parse_samples.py`, `verify_pat.py`, `filt_wrap.py r2g_pat.jsonl r2other_pat.jsonl other`, `filt_wrap.py r2g_pat.jsonl r2uni_w0_pat.jsonl w0`, `cat r2w0_pat.jsonl r2uni_w0_pat.jsonl > r2w0_pooled_pat.jsonl` |
| pattern samples, rank 1 | `PY draw_hybrid.py r1_prefix.out r1_suffix_sample.out 98447 10000 61 r1w0_draw.txt w0` with `./anchor_dp2 6 27 1 sample 61 1`; `PY draw_hybrid.py ... 5000 62 r1other_draw.txt other` with `sample 62 1`; `parse_samples.py`, `verify_pat.py` |
| M0 | `PY m0_controls.py > m0_controls.out`; `PY m0_run.py r0_pat.jsonl r0_m0.jsonl > r0_m0.out`; `PY m0_run.py r0_pat.jsonl r0_m0_inflated.jsonl 400 > r0_m0_inflated.out`; `PY scan_children.py > scan_children.out` |
| depth-1 cut | `PY survival.py r2g_pat.jsonl 2 r2g_survivors.jsonl > survival_r2g.out`; `PY survival.py r1w0_pat.jsonl 2 r1w0_surv_prod.jsonl > survival_r1w0_prod.out`; `PY survival.py r1w0_pat.jsonl auto r1w0_surv_r1cut.jsonl > survival_r1w0_r1cut.out`; `PY survival.py r1other_pat.jsonl 2 ... > survival_r1other_prod.out`; `PY depth1_control.py > depth1_control.out`; `PY s1_bruteforce.py > s1_bruteforce.out`; `PY depth1c_k31.py > depth1c_k31.out`; `PY sat_check.py > sat_check.out`; `PY r1_ctrl.py > r1_ctrl.out`; `PY scan_d1rows.py > scan_d1rows.out` |
| cost | `PY costmodel3.py cfg_r2_pooled.json > costmodel3_r2_pooled.out`; `PY costmodel4.py cfg_r1.json > costmodel4_r1.out` |
| rank 1 bounds | `head -1000 r1w0_pat.jsonl > r1mix_pat.jsonl`; `head -4500 r1other_pat.jsonl >> r1mix_pat.jsonl`; `PY m1_run.py r1mix_pat.jsonl m1_final.jsonl > m1_final.out`; `PY m1_summary.py m1_final.jsonl > m1_final_summary.out`; `PY m1_t2.py > m1_t2.out`; `PY k1_values.py > k1_values.out`; `PY m1_fold.py m1_final.jsonl > m1_fold.out` |

md5 (full lists taken with `md5 -r`: `md5_outputs.txt` for the 173 files present before the last two scripts, `md5_outputs_late.txt` for `k1_values.*` and `m1_fold.*`, `md5_inputs.txt` for the 23 inputs read):

| file | md5 |
|---|---|
| `anchor_dp.c` | 9c43abda29fbe74143c07c21d45a0131 |
| `anchor_dp` / `anchor_dp2` (binaries) | 35a97500cfffee1ee1cf57f1891e9f63 / 3176a5a6233d4f584dde0c4bb3bbd2e7 |
| `census_l12.out` | 52f8843d8e997035528f2aae6ff618f4 |
| `sunits.out` | 2141b6184466245b84dbf52d718d6230 |
| `pairs_filtered.jsonl` | 7901d499d51a595c4d1c1ac8b8fee49b |
| `r0_all.out` | bd6377d85fb01fb4c68292563b95e172 |
| `s2_40k.out` | 9ff7ed35d06aee451d74725e629a8011 |
| `r1_prefix.out` | 720e886aa43c691b6a7686092992a74e |
| `r1_suffix_sample.out` | a6544dd69c63950ec08d46187309a6b8 |
| `census_final.out` | 9ca6cf32d1230506fe739be3046adedb |
| `chain_control.out` / `chain2_control.out` / `kit_control.out` | fbaf0bac1e940185cbd73cdf3b12ada6 / ab737ea530846aa56f3bc7aa2041d258 / bffe928dd937976421a71bfe54c667a4 |
| `dp_test.out` | 781b8aca98b7b6779054708c403bd709 |
| `m0_controls.out` / `r0_m0.out` / `r0_m0_inflated.out` | 4ed7b9d9decb94891ebd55a769515454 / 903fe52c37af069486aff310ace47017 / 2e31a367aab1dd6cab1f2dd20364b1e8 |
| `depth1_control.out` / `s1_bruteforce.out` / `depth1c_k31.out` | 3baa2f7047181e3955132589404632e5 / a7186eec0a9935017c38ac9f86233d1a / 5c6a6f9c9ba03f1b82c0c0e4a2ec00a6 |
| `survival_r2g.out` / `survival_r1w0_prod.out` / `survival_r1w0_r1cut.out` / `survival_r1other_prod.out` | f7df71260f19e277a81df57d3709111e / 214d137a41dc154c000c1ca447a9d819 / bd7b1eff092d1ce711f0d6d2509f0096 / 0c487a51a1a18cbefb6bf90579eff421 |
| `costmodel3_r2_pooled.out` / `costmodel4_r1.out` | 0c4317b3d70bf0ae1c8c0ddf0a95ca0e / 85bd580a72203cbf613c92fd880df101 |
| `m1_final_summary.out` / `m1_final.jsonl` / `m1_control.out` | 279582028eed0365680bab13ab7dc699 / f3959fd4ffcff2a0c606b8daef244b88 / 9e84d91c6d6e88d8fbc6bd9a64e3e0ce |
| `sat_check.out` / `r1_ctrl.out` / `scan_d1rows.out` / `scan_children.out` | be798a32a9181117f3456dff26e2e192 / 3192c3546c2f19ace57eb7842f9ca29d / 0d9ba32f22b84e90ce3e13580725d202 / 1dbf2815f93bb97645b235a3c4006dcb |
| inputs: `FRONTIER.md` / `MAP.md` / `baker_chain.py` | 968d650bb8be3d04efb43feb0cc1fd95 / fbf453940b715fad6509aada929c18e8 / 5bb85b4af979c4da911483efcd60ab55 |

Files named `costmodel.py`, `costmodel2.py`, `depth1.py`, `depth1w.py`, `qprime.py`, `percase.py`, `cost_dist.py`, `m1_prelim*`, `s1_300.*`, `s2_200.*`, `r1_*prelim*` and their outputs belong to earlier, superseded models and small trial samples. The 14 patterns the production cut leaves open among the rank-1 wrap-0 sample are in `r1w0_surv_prod.jsonl`.

## 8. Seams

1. Population. Layer B counts anchored patterns. Open patterns with no anchor are not counted and cannot be bounded with the tools at hand (n2-accidents: no rigorous "accidents < 1"). The S-unit range (a <= 60, y < 10^98) is the scout's; the sampled anchors reach a = 49, so the cutoff does not bind in the samples. A pattern anchored on several (y, k) cells is counted once per cell; the overlap is not measured.
2. Estimates. Rank 0 is exact. Rank 1 is an exact prefix (6,204 of 104,651 pairs, a <= 2, 8.59e9 patterns) plus a uniform sample of 25,000 of the remaining 98,447 pairs. Rank 2 is a uniform sample of 40,000 of 1,003,249 pairs. Pattern totals are heavy tailed (the three largest cells carry 5.1% of the rank-2 sample total), so the bootstrap intervals are indicative.
3. Pattern samples. Cells are drawn with probability proportional to exact cell counts taken from the pair samples; the pattern inside a cell is exactly uniform. Survivors cluster in wrap 0, so wrap 0 and wrap > 0 have separate samples with weights from the same pair samples. The rank-2 wrap-0 estimate pools two independent samples (5,082 and 20,000 patterns); their survivor rates (3/5,082 and 2/20,000) differ by Poisson noise only.
4. Depth-1 cut. The rank-2 test is the reduction stated in RESULT-anchorfirst.md (the verdict depends only on the target modulo 5^5 * 2^(a+9)), with a = v_2 of the anchor, so a candidate is assumed to share the anchor's 2-adic exponent, which is the anchored hypothesis. The rank-1 moduli come from my computation of orders and valuations (`sat_check.out`); soundness needs only g = 1 modulo 5^9 * 2^10 (5^10 * 2^12), which the valuations give. No closure claim uses saturation.
5. Node counts and costs. The node model is inferred from `cert_cvp.expand_nodes` and reproduces one recorded count. The per-node times (0.0232 s certify, 0.0217 s verify) are the means of the k = 31, D = 5 run. For a pattern with k > 29 digits the depth D uses a linear extrapolation of the U'' table in k (D = 3 to 5 across the rank-2 sample). The five survivors cost 1.1e3 to 8.2e5 core-seconds, so the totals have a heavy-tail uncertainty that the 95% box reflects only partly.
6. M0. The argument uses a 2-adic exponent bound (T7 of the theta lane, PROVEN-ON-PAPER and re-derived in the H3 audit; Fonga Corollary 3.2, arXiv only, read in the raw file) and the order L = 1.037e43 from PARI `znorder` over the factorization of R_96 (product checked). Neither is a Baker ceiling.
7. Three-log kit. Only the conclusion Lambda' > rho^(-KL) of Theorem 2.1 (non-degenerate branch) is evaluated. The alternatives (2.14) and (2.15) are not excluded, and the paper's two-logarithm treatment of the degenerate case is not run. Parameters are real valued; the integer rounding of K, R_i, S_i, T_i (relative size below 10^-300) is ignored; (2.9) to (2.13) follow from the section 5.2 recipe and are not rechecked. The form assignment (alpha_2 = N_j / 2^a with coefficient 1) needs N_j > 2^a, true after the first few gaps. The kit is applied to the archimedean forms; the 5-adic half keeps the Yu constants. K_1 is taken at the largest prefix height, an upper bound for every gap.
8. Chain code. `chainrank.py` and `mvchain.py` use 320-bit gmpy2 floats and a scan step of 0.001 in log10; they do not reproduce the interval-arithmetic integer certificates of `baker_chain.py`.
9. The 32 s level-480 closure is one pattern (k = 31, a = 0); its cost at other patterns is unknown.
10. Process. Two `python3 - <<EOF` invocations occurred outside the `uv run --no-project python -I <file>` rule (one patched `anchor_dp.c`; one was empty and ran nothing). One read-only `git status --short` was run at the end, against the no-git rule. One denied `rm` attempt left an empty file `m1lib_patch.txt` here. The exact rank-1 run was suspended around short jobs; two short overlaps with a running job occurred (one `parse_samples.py`, one `r1_analysis.py` on the rank-0 file). Python bytecode directories appeared in this directory. `trees_mac.jsonl` changed after the earlier recorded md5 in `SANDWICH-run.txt`; `md5_inputs.txt` holds the md5 at read time.
11. Every closure rate is a sample rate with its Clopper-Pearson bound; "closed by the cut" for the population means "closed except for the measured survivor fraction".

## 9. Do not retry without new data

- The 57% / 38% / 5% split as a size of the Tier C residue: the anchored open set is 2.0% / 28.4% / 69.6% (Section 2.2). Do not retry a rank-based reduction of the residue without a different supply of anchors.
- Independent-case survival models for the depth-1 cut (probability 1/640,000 or 1/(3125 * 2^(a+9)) per case): they predict thousands of surviving cases in a 1,200-pattern sample in which no pattern survives. Use the exact case DP (`depth1d.py`).
- A larger rank-0 sample: the argument covers every rank-0 pattern as long as L exceeds A.
- Rank-1 closure by the three-log kit alone: the kit lowers D by three to five levels in the one-ended chain but not the dependence on the digit count, its degenerate branch is open, and no rank-1 certificate machine exists. Do not retry without both.
- A full exact rank-2 anchored count: the rank-2 total is within 14% (95%) from 40,000 pairs, and the exact run is a job of many core-hours (the 40,000-pair sample took about 30 minutes under load).
- Method A cost from the single recorded k = 31 pattern: survivors range from 2.5e4 to 1.8e7 nodes; use the node model per pattern.
- Anchored counts for the other five Tier C vertices from this vertex's shares: the S-unit supply is the same, the anchors per vertex are not.

## 10. No-Claim

No-Claim: nothing here is PROVEN or Lean-checked; verdicts are conditional on Lemma C, Matveev, Yu 2007 Thm II, any three-log constants used, and the pattern list.

Additional conditions of the rank-0 argument: the 2-adic bound A (theta T7 and Fonga Corollary 3.2); of the node model: the enumerator's structure as inferred from `cert_cvp.expand_nodes` and its agreement with one recorded count.
