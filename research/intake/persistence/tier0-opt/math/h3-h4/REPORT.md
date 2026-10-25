# H3 / H4 lane report

## Registered predictions (written 2026-10-20 20:58 EDT, before any new bound was computed)

H3, as stated (Laurent two-log, Bugeaud-Laurent p-adic, three-log kit replacing Matveev where a form has two or
three logarithms):
- The archimedean chain of BAKER-CHAIN.md has no two-log form. Its top form has 3 logs (a = 0) or 4 logs (a >= 1),
  every middle form and the bottom form has 4 or 5 logs. The one two-log form is the 5-adic form at the bottom
  (v_5 of M + 1, a = 0 only).
- Because the top constant K0 enters G only additively-multiplicatively once (Phi ~ K0 K1^k / log 10), a sharper
  three-log constant for the top form lowers log10 G by at most about log10(K0 / K0') <= 14. Prediction: this alone
  moves 0 of the 43 survivors by a depth level (a depth step is 48 digits).
- The hypothesis text predicts "at least one depth earlier on most". Prediction: false for Laurent and the three-log
  kit as such.

H3, a different use of the same theory that I expect to matter more: the last factor K1 of the chain (the form
Lambda_k) is removable. For a >= 1, y' is even, so its last digit is even and not 1, so E_k = 0 and n = S_k with no
final form. For a = 0, E_k <= v_5(M + 1) and Bugeaud-Laurent bounds that by a polylog in n. Either way
n <= S_k + E_k and one factor K1 (1.6e16 for a = 0, 1.6e18 for a >= 1) disappears from G.
Prediction: log10 G drops by about 16.3 (a = 0) and 18.2 (a >= 1); depth changes by one level on about 11 of the 43
(rough count: patterns whose old log10 U lies within that drop above the previous depth's lower bound of about 72,
120 or 168).

H4: prediction that the representation technique does not apply: the target would be a coset of an index-40
subgroup of (Z/P)^*, the survival test is multiplicative in V mod P, and a split of the digit multiset gives two
additive halves whose sums must be tested for membership in a multiplicative set of density 1/40; the density is
the obstruction (no exponential gain, only 40x), and the representation count is 1 per pattern, not exponential.

## Files

h3_sharp.py (old bound re-implemented and cross-checked, 99 of 99 integers equal to baker_chain.baker_upper_bound; new modes), h3_depths.py
(recomputes the lower bound of Lemma C at every depth below the recorded closing depth, imports tier0 read-only, output depths.jsonl),
h3_analyze.py (depth before/after, output analyze_out.txt), h3_meet.py (Codex two-ended chain, replica), h3_fold.py (B3 chain, independent
re-typing), h4_model.py (H4 cost model). Tables: h3_sharp_out.txt.

## H3 results

Where the chain has few logarithms (a = 0 / a >= 1): top form Lambda_0 3 / 4 logs; middle forms 4 / 5; bottom archimedean form 4 / 5; no archimedean
two-log form exists. The bottom 5-adic form v_5(M + 1) has 3 logs (3, 7, -1) and reduces to 2 logs (3 and 1/7, after squaring to remove the sign)
for a = 0; for a >= 1 it is empty (E_k = 0, M + 1 odd).

Sources. Read: Laurent Acta Arith. 133 (2008) Cor. 2 via the IMPAN-hosted text: log|L| >= -C2 D^4 (max{log b0 + 0.38, m/D, 1})^2 log A1 log A2, C2(10) = 25.2,
needs alpha_i, log alpha_i real positive, multiplicatively independent, log A_i >= max{h, |log alpha_i|/D, 1/D}. Not applicable: no two-log archimedean form. Read (preprint, not the
published Mignotte-Voutier, Math. Comp. 93 (2024)): Mignotte kit Prop. 5.2, log|L| > -790.95 Omega D^2 log^2 B in the non-degenerate branch (three
coprime positive b_i, a_i >= max{4, 5.296 l_i - log a + 2 D h}, Omega >= 100), else a degenerate alternative; so it is not an unconditional bound as stated. Used for illustration only.
Read as quoted by Bugeaud (Acta Arith. 80 and Proc. AMS 1997): Bugeaud-Laurent Thm 4 (mu,nu) = (10,5): v_p <= 24 p (p^f - 1)/((p-1) (log p)^4) D^4 max{log b + log log p + 0.4, 10 log p / D, 5}^2 log A1 log A2,
and Thm 3 with p^g (Bennett-Bugeaud 2012, Miyazaki 2014). Original BL not read. Used for E_k, a = 0: cap about 10^6.6 (larger of the two forms).

Registered prediction vs result (43 survivors; "before" depths 2/3/4 on 7/26/10 patterns, matches the recorded run):
- Laurent / three-log as stated: predicted 0 moves. Kit constant on the top form: log10 G(k,0) drops 3.6 (111.7 to 108.1 at k = 6); 0 of 43 move. Even with K0 set to zero (no theorem can do better): 7 move one level. Prediction held (0 for real constants).
- Drop of the last factor K1 (a >= 1 by parity E_k = 0, a = 0 by BL): predicted about 11 moves of one level; observed 11 (6 at 3 to 2, 5 at 4 to 3). Drop in log10 G is 16.7 (a = 0) and 18.5 (a >= 1).
- Two-ended chain with the 2^a fold (B3, independently retyped): 24 move one level and 19 move two (4 to 2: 10; 3 to 1: 9; 3 to 2: 17; 2 to 1: 7); none stays.
- Control: Lemma C bound at the recorded depth recomputed on 7 patterns, 6 match to 0.01, one differs by 0.044 (119.986 vs 120.03; run predates the deep_cut fix noted in SANDWICH.md); no depth depends on it. Bounds at lower depths never exceeded the old U.

## Audit of the two-ended chain (Codex idea 1, B3, theta T7)

Verified by me: (1) BK Thm 2.1 (2.2), read in arXiv 1704.00432: v_p < (16e)^(2(n+1)) n^(5/2) (log 2n)^2 p/(log p)^2 log A1...log An log B, n >= 2, product != 1, A_i >= max{|x_i|,|y_i|,e}, B = max{3,|b_i|}; the factor is p/(log p)^2 (checked in raw text). No unit or independence hypothesis printed.
(2) Against Yu as quoted by others (Berczes-Evertse-Gyory 2009 Thm B; Bugeaud-Evertse 2017 Thm 3.2; Cai 2019 Thm 3.3; Yu's own paper NOT read): for D = 1 the quoted Yu bound is c n^(3/2) log(2n) log 2 p/(log p)^2 prod h_i log(M/delta), log M = log B + (n+1)(6n+5)+O(1);
BK's is larger whenever n log(2n)/log 2 * log B >= log B + (n+1)(6n+5), i.e. log B >= 15 (n = 3), 14 (n = 4): true here (log B about 600). So BK (2.2) is a safe weakening of Yu as quoted; remaining assumption is the correctness of those quotations.
(3) Hypotheses: T_j is a 5-adic unit: T_k = -1; for j<k, E_k >= 1 gives T_j = -1 mod 5; E_k = 0 gives T_j = c_k - 1 mod 5 in {8,17,26,44,53,62,71}, which is 0 only for digit 5 (c - 1 = 35), excluded (digit product is {2,3,7}-smooth). M - T_j = N_j 10^(E_j) > 0, so M/T_j - 1 != 0 and v_5 >= E_j. Heights: log A >= 1 (A_i >= e; T_j >= 8). Ordering condition on b_n: the folded rational has exponent 1, minimal 5-adic order. Chain: E_j < Y (E_{j+1} log 10 + log 80 [+ a log 2 if folded]). Meeting: n = (n - E_j) + E_j <= X_j + Z_j. Monotonicity: both are polynomials with nonnegative coefficients in logs of an increasing argument, so (X+Z)/nu decreases beyond e^(k+1) (same lemma as BAKER-CHAIN 5.1); I certified integer endpoints in interval arithmetic.
(4) Numbers: Codex replica reproduces 10^236.7, 10^331.2, 10^464.5 (k = 22, 31, 44, a >= 1; j = 13, 18, 25) vs baker_chain 10^426.3, 10^598.7, 10^849.7. My re-typed B3 chain (fold) gives log10 G' = 281.50 / 279.23 / 280.06 (k = 31; a = 0, 1, 40) and 402.11 / 393.93 / 394.75 (k = 44), matching B3 to 0.01. Without the fold: 331.2 / 464.5 for every a. Fold, a = 100, 130, 160: 280.4, 280.5, 280.6 (k = 31) and 395.1, 395.2, 395.3 (k = 44). The fold only adds the constant a log 2 to a height, so it is valid for any FIXED a with a << n (the sandwich fixes a = the anchor's exponent, and candidates in the coset have that same a); "a <= 40" is not a limit of the method, and it is lost only if a grows with n.
(5) Combination with my results: B3 already contains the parity fact E_k = 0 for a >= 1. Adding the BL two-log cap for E_k at a = 0 changes nothing (281.50 / 402.11 unchanged), because the optimal meeting index (17, 24) is below k. Laurent / three-log top form: moves G by about 3.6 orders at most; the two-ended chain is where the gain is. They do not add.
(6) T7 (theta lane, 2-adic chain), re-derived: M = S_m mod 2^(p_(m+1)) holds since M + 1 = S_m + 1 + (terms divisible by 10^(p_(m+1))); if p_(m+1) <= a then 2^(p_(m+1)) | S_m, 0 < S_m < 80 * 10^(p_m), so p_(m+1) < 6.32 + 3.32 p_m; if p_(m+1) > a then v_2(S_m) = a, so a < 6.32 + 3.32 p_(m0). I found no error. It does not make a <= 6: a is bounded only as a function of the case index m0 (a <= 26.8, 95.2, 323, ... for m0 = 2, 3, 4), and the worst case G' (279.5 / 394.2) is at m0 = 1, a <= 6; larger a means larger m0 and a smaller G' (theta table: a in (95, 323] gives 249.2 / 369.5, so a = 160 gets that). The case m0 = k puts all of the configuration below 10^16 / 10^23 and is excluded by n >= 10^27 (sandwich premise), as the lane says. T7 removes the a <= 40 limit uniformly in a but is not needed for fixed a. Not independently re-run: their 728,256-case exhaustive check.
(7) Conflict with A >= 100-160 (two_adic_bound): none found. T7 allows a up to 323 at m0 = 4 and 1.1e3 at m0 = 5 (p_m <= 0, 6.1, 26.8, 95.2, 322.5, 1078); A = 118-144 sits at m0 = 4. They bound different things (A: max v_2 over modular tail configurations of a multiset; T7: necessary growth of positions given the 2-adic valuation). Not a proof the two agree beyond this consistency.
Not verified: Yu's original statement; the BL originals; Matveev (taken from BMS as in BAKER-CHAIN); T7's script.
Which (k, a) the figures cover: 281.5 / 402.1 are a = 0, k = 31 / 44; 279.2-280.6 and 393.9-395.3 are fixed a = 1..160; all have k = 31 / 44 only, with the optimal meeting index 16-17 / 23-24. Other k: use h3_fold.best(k, a).

## H4: verdict and cost model

Verdict: the representation technique does not apply, and no technique can gain more than a factor 49.5 on the level-12 listing.
Dictionary. Group Z/P, P = 5,291,005,291 (about 2^32.3). Weights: w_j u_e with w_j = d_j - 1 in 1..8 and u_e = 10^e mod P, e in Z/12 (a 12-ary variable per digit, multiset symmetry within a digit value). Target: not an element but T_nu = S - R_nu, S the index-40 subgroup of units generated by 2, 3, 7 (density 1/49.5 of Z/P once zero divisors are counted; 1.07e8 elements). Representations: a split of the digits into two halves gives exactly one per pattern; BCJ-style overlapping halves give C(k, k/2) (705,432 at k = 22; 10,400,600 at k = 26) but only against a single target of density 1/|G|.
Why not: (a) BCJ/HGJ solve a needle problem, 2^n about |G|, one solution. Here N_M/P is 1.5e3 (vertex 71663616) to 6.6e4 (1783627776) per multiset, and a fraction 1/49.5 of all patterns are solutions: the task is to list 6.3e13 / 3.2e15 survivors, so any algorithm costs at least that, and representations only reduce redundancy, which is already 1. (b) The target is a multiplicative coset with no additive structure; dpcount 1.2's argument stands: chi(a + b) does not factor; joins on a modulus Q only help by the density of the target mod Q (index 2 for the four small primes, so at most 2x; all of the 40-fold selectivity needs 9901 and the others jointly, a bitmap lookup per pair, which is the current test). (c) The Dimitrov-Howe MITM works because the multiplicative side is tiny relative to p; IDEAS.md measured 5.6e-2 against a needed 1e-6.
Cost model (counts exact from the multiset enumeration, which reproduces FRONTIER's 406 / 449 multisets, k_max 22 / 26 and 3.13e15 / 1.57e17 patterns; unit costs read from tier0-opt/costmodel/costmodel.py, not re-measured; survival 1/49.5 from dpcount MC):
| | 71663616 = 2^15 3^7 | 1783627776 = 2^20 3^5 7 |
| level-12 enumeration at 10 ns / 46 ns | 362 / 1,666 core-days | 18,135 / 83,420 |
| perfect output-bound listing (survivors x 10 ns) | 7.3 core-days | 366 |
| descent at 25 us per survivor | 1.8e4 core-days | 9.2e5 |
| level-24 children, expectation 2 prod(j+1) (unfiltered upper bound) at 6.1 us | 4.1e18 children, 2.9e8 core-days | 9.1e20, 6.5e10 |
| enumeration share of enumeration + descent | 1.9% | 1.9% |
A representation-technique speedup is capped at 49.5x on the first row, which moves total cost by under 2%; the lift and descent dominate by 10^2 to 10^6. Assumptions marked: the 25 us applies to every level-12 survivor (the engine's descent may see only the (a,pattern) subset), and 2 prod(j+1) ignores the 2-adic and a-split filters, so the lift row is an upper bound; the 1.9% share depends only on the first assumption. Nothing was implemented.
