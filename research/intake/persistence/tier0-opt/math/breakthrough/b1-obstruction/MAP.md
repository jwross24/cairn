# B1 obstruction map: why every route costs at least f(k) at Tier C, and what the equations offer that the general theorems ignore

Lane B1, 2026-10-20. Inputs: the thirteen files named in the brief, plus `tier0/baker_chain.py` (read-only, copied to scratch to run). Computations are in `scripts/` (`run.py` needs `baker_chain.py` on its path; `heur.py`, `tails.py`, `more.py` are standalone). Nothing in `tier0/` or any existing file was edited.

Labels: PROVEN-ON-PAPER (argument written here, unchecked by anyone else; nothing is PROVEN without Lean plus a statement review), HEURISTIC (a model, with the model stated), STRONG-EMPIRICAL (measured by a documented computation), CONJECTURE. No step rests on abc, Lang-Waldschmidt, Schanuel or any other unproven conjecture; where a conclusion would need one, it is stated as conditional and not used.

## 0. The binding obstruction

To certify that a Tier-C pattern has no candidate, the sandwich must show that the exponent lattice of (b, c) has no point below the Baker bound G, and G is exponential in k. Three facts multiply:

1. **G is exponential in k with a large base.** Each non-1 digit multiplies the admissible length by about 10^17 to 10^19, because the Matveev form for gap j carries the rational N_j, whose height is the whole prefix length S_j, so S_{j+1} <= (1 + lambda) S_j with lambda ~ 10^18.6 (certified: log10 G(44, a>=1) = 849.7).
2. **A rank-2 lattice yields only sqrt(det).** The 10-adic window of K digits has index ~10^K, so it certifies n > ~10^(K/2). Beating 10^850 needs K ~ 1700 low digits pinned, that is depth D = 18 at k = 44.
3. **Every pinned digit window costs (D+1)^q copy choices** (which of the q digits lie inside the window). With D ~ 0.4 k this is (0.4 k)^k, superexponential: 10^56 per pattern at k = 44, on top of 10^(19-22) level-12 patterns and 10^(9-12) depth-1 survivors per vertex.

All three have one root: each of the k interior digit positions is treated as an independent unknown whose range is the full length scale, and information about an interior gap reaches us only through the two ends (the top digits through the archimedean form, the bottom digits through the 10-adic window or the 5-adic Yu form), each paying a multiplicative cost per digit crossed. The assumption a breakthrough must break is "interior positions are independent unknowns reached only from the ends".

Heuristically the truth is nowhere near: the expected number of solutions for the k = 44 multiset is 10^-31.6 at its peak length (n = 49) and 10^-234 summed over n >= 300 (section 1.4). The proof gap is log10 n: ~850 proven against ~2 expected.

## 1. The problem and the exact quantities

### 1.1 One Diophantine statement per vertex

Vertex s = 2^alpha 3^beta 7^gamma. A child with non-1 digit multiset M (|M| = k, product of M = s, digits in {2,3,4,6,7,8,9}) is a solution of

    2^a 3^b 7^c = y = R_n + sum_{j=1..k} (d_j - 1) 10^(e_j),   R_n = (10^n - 1)/9,   n > e_1 > ... > e_k >= 0,   (E)

equivalently 9y + 1 = 10^n + 9W with W = sum w_j 10^(e_j), w_j = d_j - 1, and the digit sum of W fixed at m = sum w_j. Unknowns: (a, b, c, n, e_1..e_k, the assignment of the multiset to positions). Three exponents plus k + 1 positions, one equation, and the multiset is part of the data, so the digit product of y is s by construction.

For the heaviest vertex, 727326941773824 = 2^39 3^3 7^2, the k = 44 multiset is forced: thirty-nine 2s, three 3s, two 7s, so w = 1 (coefficient 9) thirty-nine times, w = 2 (coefficient 18) three times, w = 6 (coefficient 54) twice, m = 57.

Bounds on the unknowns from the documents: a <= A(M) (2-adic, rigorous when computed; for Tier-C multisets the engine's search does not terminate and reports A >= 100-160, so a is not yet bounded); n < G(k, a) (Baker chain, section 2.2); (b, c) in a coset of a rank-2 lattice per pattern (section 2.3).

### 1.2 Tier-C table (from FRONTIER.md, RESULT-dpcount.md, RESULT-anchorfirst.md, and `scripts/run.py`)

D is the depth the sandwich needs: the lower bound is 10^(24 + 48 D) digits (documented 10^72, 10^120, 10^168 for D = 1, 2, 3), so D = ceil((log10 G - 72)/48) + 1. Check against SANDWICH.md: this rule reproduces D = 2, 3, 3, 3 for its four closed patterns and D = 7 for k = 22 (FRONTIER.md). Cases are the upper bound (D+1)^k from DEEPCUT.md (t_j in {0..D-1, >=D}); measured sub-coset growth for k <= 15 is x3-5 per depth (FRONTIER.md), which I could not reconcile with (D+1)^q/D^q from the documents, so treat the case column as an upper bound and the gap as an open accounting question.

| vertex s | 2^a 3^b 7^c | k_max | equations (multisets) | level-12 patterns | log10 G(k_max, a>=1) | D (one-ended Baker) | (D+1)^k | D (two-ended, interpolated) | (D+1)^k | open@96 forecast |
|---|---|---|---|---|---|---|---|---|---|---|
| 3416267673274176 | 2^6 3^27 7 | 34 | 306 | 1.7e19 | 656.5 | 14 | 10^40.0 | 8 | 10^32.4 | 2e11 |
| 128421199872 | 2^23 3^7 7 | 31 | 925 | 2.6e19 | 598.7 | 12 | 10^34.5 | 7 | 10^28 | 3e11 |
| 913217421312 | 2^29 3^5 7 | 35 | 911 | 8.6e19 | 675.7 | 14 | 10^41.2 | 8 | 10^33.4 | 9e11 |
| 727326941773824 | 2^39 3^3 7^2 | 44 | 834 | 5.5e21 | 849.7 | 18 | 10^56.3 | 10 | 10^45.8 | 6e13 |
| 112717121716224 | 2^34 3^8 | 42 | 2446 | 9.9e21 | 811.0 | 17 | 10^52.7 | 9 | 10^42 | 1e14 |
| 1438916737499136 | 2^24 3^6 7^6 | 36 | 829 | 1.4e22 | 695.0 | 14 | 10^42.3 | 8 | 10^34.4 | 1e14 |

Notes. The a = 0 bound is smaller (G(34, 0) ~ 10^593, D = 12), but a vertex's equations include a >= 1 patterns, so the closure depth is the a >= 1 depth. FRONTIER.md's last column (11-12 for all six) matches the a = 0 values; the a >= 1 values above are the ones that apply. The two-ended column scales the three values reported in codex-brainstorm.md (10^237, 10^332, 10^465 at k = 22, 31, 44, a > 0; reported, not re-derived here) linearly in k, about 10.3 orders per digit; the k = 31 and k = 44 entries reproduce Codex's depths 7 and 10.

Other exact quantities (all documented): Lambda_96 has index 2.81e56 and shortest vector 7.85e27; a depth-1 case survives with probability 1/640000 (image index 4*5^4 in (Z/5^96)^*, 2^8 in (Z/2^96)^*), and the verdict depends only on the target modulo 5^5 * 2^(a+9), so only classes e < a+9 matter; level-12 survival is 1/49.5 for every Tier-C vertex (derivable: index-40 subgroup, times the 19.2% non-zero-divisor fraction, 0.808/40); survivors 3.5e17 to 2.8e20 per vertex, level-24 lift inputs 1e24-1e28; anchored open@96 patterns 1.9e11 to 1.5e14 on ~10^5 anchors per vertex, depth-1 closure 90-99.99%, leaving 10^9-10^12 depth-1 survivors per vertex.

### 1.3 Per-digit price of Baker, read off the certified table

log10 G(k, a>=1) minus its k = 0 value (14.9), divided by k, is 18.2 at k = 6, 18.9 at k = 44. This is the per-digit multiplier lambda ~ 10^(18-19) in S_{j+1} <= (1 + lambda) S_j.

### 1.4 What the heuristic says the truth is (`scripts/heur.py`)

Model (HEURISTIC): about 4.1 n^2 S-units have n digits (volume of the rank-3 region); the number of n-digit numbers of the shape (E) with the fixed multiset is C(n, k) * k!/prod(m_d!); an n-digit number has probability that shape of that count over 9*10^(n-1). Expected solutions E(n): for 2^39 3^3 7^2 (k = 44), the maximum over n is 10^-31.6 at n = 49 (already negligible at the shortest possible length) and the sum over n >= 300 is 10^-234; for 2^23 3^7 7 (k = 31), 10^-18.7 at n = 34 and 10^-244 beyond 300. The model is not a theorem; it fixes the scale of the gap between what is believed (n of order 10^2) and what is proven (n < 10^850).

## 2. Each method class: the cost floor as a proposition

### 2.1 Modular ladder and local-global sieves

**M1 (anchored patterns are open at every level; no purely modular method terminates).** For every L and every S-unit y < R_L that has a representation as a pattern of the equation, that pattern passes every congruence modulo the primes of 10^L - 1, because every candidate satisfies y' = y (mod R_L). PROVEN-ON-PAPER (H1 report A2; the congruence core is the Lean lemma `candidate_modEq`). Consequence: the open set at every level contains the anchored patterns, so a ladder alone never reaches an empty set; an archimedean upper bound is logically required, and the ladder's role is only to raise the lower bound.

**M2 (sqrt-det barrier for any lattice lower bound).** Let Lambda be the rank-2 lattice of (b, c) allowed by a modulus of index det and p + Lambda a coset. The shortest nonzero vector satisfies lambda_1 lambda_2 <= (2/sqrt 3) det and the coset's nearest point lies within the covering radius, <= lambda_2 / sqrt 2 (Minkowski/Gauss reduction; PROVEN-ON-PAPER). For a balanced lattice lambda_2 ~ sqrt(det), so a modulus of index det certifies n above ~sqrt(det) and no more, while a point of norm below sqrt(det) can exist in the worst coset. For Lambda_96, sqrt(det) = 5.3e28 against the measured shortest vector 7.85e27 (ratio 0.15, balanced; STRONG-EMPIRICAL). To certify n > G needs det >= ~G^2. The 10-adic window gives det ~ 10^K for K digits (orders 4*5^(K-1) and 2^(K-2); PROVEN-ON-PAPER arithmetic), hence K >= 2 log10 G: 1700 digits for the heaviest vertex, D = 18.

**M3 (cost floor of any pattern-as-unit sieve).** Work is at least the size of the surviving pattern list at the widest stage. Measured/derived: N_12 = 12 * prod_d C(11 + m_d, m_d) patterns (exact combinatorics), survivors N_12/49.5 (derivation above; Monte Carlo confirms to 0.2%), lift inputs 1e24-1e28 per vertex. No exact count or join beats the pattern list (RESULT-dpcount.md section 1.2: the test is multiplicative, the pattern sum is additive; STRONG-EMPIRICAL plus an argument, not a lower-bound theorem over all algorithms). The cost is not exponential in k at fixed L (it is polynomial of degree 11 in each multiplicity), but L must grow with k for the sieve to bite: see M4.

**M4 (accidents bound the useful depth from below).** The H1 report exhibits a q = 100 pattern that passes all 20 level-96 congruences with no S-unit below 10^98 in its coset (PROVEN-ON-PAPER plus exact computation), so the Anchoring Lemma is false as stated and the open set is anchored patterns plus accidents. At Tier-C q (30-44) the accident count is unknown: the uniform-residue model predicts 2.3 (q = 30) to 1.35e11 (q = 44) per equation at level 96, but the same model overshot the q = 14, level-48 test by a factor of at least 29 (observed 0 accidents of 17 survivors, predicted ~42), so it is an upper bound from an invalid model, not a forecast. Extrapolating the measured log10 rho_96 = -37.3 (0.388 per level) against N_L for the k = 44 multiset, the product N_L rho_L crosses 1 near L ~ 128 (HEURISTIC; `scripts/more.py`). Only the Baker sandwich removes accidents at the q where they are plausible, so the sandwich is not optional at Tier C.

**M5 (depth-1 Lemma C kills by counting only up to q ~ 20).** A case survives with probability 1/640000, and the verdict depends on classes e < a+9, so expected survivors per pattern are about 2^(q (a+9)/96) / 640000. This exceeds 1 once q (a+9)/96 >= 19.3. For a >= 87 (possible at Tier C, where A >= 100-160) all q classes matter and depth 1 cannot kill by counting beyond q ~ 20. Depth 2 never kills (DEEPCUT.md: the depth-1 sublattice maps onto the kernel of G_192 -> G_96), so closure past depth 1 is by bound only.

### 2.2 Baker-Matveev chains (single-ended, Laurent, two-ended)

**B1 (single-ended chain; geometric by construction).** The form for gap j is Lambda_j = M 10^(-E_j) N_j^(-1) - 1 with N_j the top part. Matveev gives g_j log 10 + log N_j <= C(t) log B * h(N_j) * (other heights), and h(N_j) = S_j log 10 + O(1) because N_j ~ 10^(S_j). So S_{j+1} <= (1 + lambda) S_j with lambda = C(t) P_0 T log 10-scale ~ 10^(18.6) at k = 44, hence S_k >= (lambda)^k K_0 and n < G(k) with log10 G ~ 14.9 + 19 k at k = 44. Any bound of this form has log10 G >= k log10(1 + lambda): exponential in k whenever lambda > 1, and a polynomial-in-k bound needs lambda <= 1 + O(1/k). PROVEN-ON-PAPER (the recursion is arithmetic; the certified numbers are BAKER-CHAIN.md section 6 with a Codex re-derivation of Matveev's Theorem 9.4 application).

**B2 (the constant is not the issue).** To close the k = 44 sandwich at depth <= 3 needs log10 G' <= 168. Single-ended: lambda^43 <= 10^(168 - 14.9), lambda <= 10^3.6. Two-ended (B3): lambda^22 <= 10^153, lambda <= 10^7.0. The documented lambda is 10^18.6. Matveev's C(4) = 1.6e13 and C(5) = 1.3e15, multiplied by P_0 ~ 3.4 and T ~ 10^3 (T = 1 + log(2.1 n + 2 + a) at n ~ 10^850), give 10^18-19. Laurent's two-logarithm constants (about 25 (log B)^2 h_1 h_2) apply to forms in two logarithms only; Lambda_0 has at least three logarithms, and Lambda_j one more. H3 (LIT2.md): sharper bounds "do not change the exponential shape". Here that is quantified: a 10^9 to 10^15 improvement per digit is needed, which is not constant-polishing. HEURISTIC for the claim that no near-term explicit Baker constant reaches 10^7; the arithmetic of the requirement is exact.

**B3 (two-ended chain, H5).** The 5-adic Yu chain from the bottom, Z_{j+1} <= Y (Z_j log 10 + log 80), meets the Matveev chain from the top: n <= X_j + Z_{k-j}. Reported (Codex, not re-derived): 10^237, 10^332, 10^465. Structural limit (PROVEN-ON-PAPER as a statement about the recursion): a scheme in which an interior gap is bounded only by the prefix or the suffix above or below it gives bound ~ lambda^(min(j, k-j)), so the exponent cannot drop below (k/2) log10 lambda. It halves log G and leaves the shape. Yu's published explicit constants are about 45x worse per gap than Matveev's (BAKER-CHAIN.md section 7).

**B4 (reduction moves the exponential, it does not remove it; PROVEN-ON-PAPER for the counting, HEURISTIC for the pruning).** Given a bound B on the exponents, lattice reduction on the inhomogeneous form with target log(1 + delta'_j) gives g_j <= ~3 log10 B for every prefix (spacing B^-3 of the values x.l in a box of four integers with one relation). Iterating B -> 3(k+1) log10(2.1 n) converges in three rounds to n of order 4e2 for k = 44. The cost is the number of sparse prefixes to examine: gaps range over [1, 3 log10 B], so about C(3 log10 B, k) * (multiset arrangements): 10^102 for 3 log10 B = 2550 (log10 G = 850), 10^90.7 at 1400 (two-ended G), 10^70.7 at 504 (log10 G = 168). With the pattern's residues mod 96, gaps are fixed mod 96 and the count is C(3 log10 B / 96 + k, k) = 10^19.0, 10^13.0, 10^6.3 respectively (`scripts/more.py`), but then it is multiplied by the pattern count. The exponent is relocated from the size of the bound to the number of cases, and in this route it depends on log G polynomially to the power k: shrinking log G from 850 to 465 divides the cost by ~10^11.5.

### 2.3 The lattice sandwich

**L1 (depth).** D = ceil((log10 G - 72)/48) + 1; with log10 G ~ 19 k, D ~ 0.4 k (PROVEN-ON-PAPER given Lemma C's 10^48 per depth, which is M2's sqrt-det).

**L2 (case count).** At depth D the window has 96 D digits and each of the q digits is either inside it at one of D copies or outside, giving at most (D+1)^q cases (DEEPCUT.md; blind re-implementations agree on the depth-1 count 2^q - collisions). With D ~ 0.4 k the count is (0.4 k + 1)^k: superexponential in k. PROVEN-ON-PAPER as an upper bound; the true number of live sub-cosets was measured to grow x3-5 per depth for k <= 15, which would be far below (D+1)^q/D^q; unresolved.

**L3 (mirror at the top, and why one side is cheaper).** The archimedean strip of S top digits has relative width 10^-S, so it trades one-for-one with a bottom window digit in the count B^2 10^-S/det of lattice points in a strip (HEURISTIC counting; the CVP in dimension 3 decides it exactly per case). The top window has the same (D+1)^q case structure because the pattern fixes n - e_j mod 96. Since log(1 + x) + log(1 + y) > log(1 + x + y), splitting the pinned digits between the two ends costs more than pinning all on one side. No gain from balancing.

**L4 (the exponent-lattice rank is a lever, and no document uses it for bounds).** The pattern fixes n mod 96 and e_j mod 96, hence y mod 3 (digit sum n + m) and y mod 7 (period 6 divides 12). So each pattern determines whether b = 0 and whether c = 0. With y divisible by neither 3 nor 7 (probability about (2/3)(6/7) = 57% over uniform residues), y = 2^a and a <= A(M): no lattice, no Baker, a finite check once A(M) is known. With exactly one of b, c free (about 38%), the exponent lattice has rank 1: the least b in a coset b = b_0 (mod N_K) with N_K ~ 10^K/20 is typically ~N_K, not sqrt(N_K), so the bound is ~10^(96) per depth, not 10^48 (PROVEN-ON-PAPER arithmetic of orders; HEURISTIC that the coset representative is not unusually small, which for an anchored pattern is false and is handled by the exact nearest-point computation as before). Only the branch with both 3 | y and 7 | y (about 5%) keeps rank 2 and the full cost. H11 uses the branch only for survival rates (12.6x, 21x). Effect on the table: in the rank-1 branch D roughly halves (log10 G drops by a further 5-10% from one fewer logarithm, C(3) = 1.4e11 against C(4) = 1.6e13), so (D+1)^q falls from 10^56 to ~10^44 at k = 44. The 5% rank-2 branch is unchanged, and the vertex is closed only when every branch is, so the worst case is not reduced.

### 2.4 Anchor-first enumeration

**A1 (anchor-first is a forecast, not a certificate).** It replaces the 10^22 level-12 patterns with ~10^5 anchors per vertex carrying 10^11-10^14 level-96 patterns, matching FRONTIER.md's independent forecast within x0.9-1.7 for all six vertices (STRONG-EMPIRICAL). Two facts cap its value. (i) By M1 every anchored pattern is open at every level, so each of the 10^11-10^14 patterns still needs a closing argument; depth-1 Lemma C closes 90-99.99%, leaving 10^9-10^12 per vertex needing depth 7-18 over up to 2^q sub-cosets (RESULT-anchorfirst.md section 0). (ii) By M4 the accidents are not enumerated by anchors. So cost >= (anchored patterns) x (depth-1 survival) x (D+1)^q is the floor of the route, before the accident question.

**A2 (per-anchor closure, H2, is not yet a theorem and has no stated mechanism).** All patterns of an anchor y share the coset (b_y, c_y) + Lambda_96, so every non-anchor candidate is y times an S-unit in Lambda_96 \ {0} (n >= 10^27 digits, PROVEN-ON-PAPER from the shortest vector). The patterns differ only in their low-window words L(P, t), so a per-anchor decision would be a statement "no nonzero lattice point of norm < G has a digit window compatible with any pattern in the carried set". That set is large (representation multiplicities of 10^9 for a single eight-digit anchor), and I see no reason in the documents that the low words are correlated across patterns. Labeled CONJECTURE that a per-anchor collapse exists at all.

### 2.5 Subspace-theorem counts

**S1 (finiteness and counts, ineffective).** Evertse/Schlickewei give n - E_{j+1} <= eps n + C(eps) for every eps > 0 with ineffective C (LIT2.md section 1.7). Even an effective version at fixed eps is not polynomial-in-k unless eps <= 1/k, and any effective C(eps) known from the Subspace route is doubly exponential in the number of terms (Evertse-Schlickewei-Schmidt, exp((6N)^(3N)(r+1)); Amoroso-Viada (8N)^(4 N^4 (N+r+1))), N = k + 3, r = 4. So the Subspace route gives finiteness of the solution set and an astronomical count, never a size bound. PROVEN-ON-PAPER as a reading of the cited statements; the effective step is the missing theorem.

**S2 (what would be conditional).** A polynomial-in-k length bound follows from abc-strength input (LIT2.md: ~5e3 digits at k = 44). That is conditional and not admissible under RULE 2; it is recorded as the shape of the answer, not as a step.

### 2.6 Dimitrov-Howe style residue-class lifting (the literature's other complete method)

Cost x3.5 per extra term, 22-25 terms at 8.6 CPU-days (LIT2.md section 1.11). Extrapolation to k = 31-44 (HEURISTIC) matches FRONTIER.md's own estimate; it is the ladder of 2.1 under another name.

## 3. Structure in these equations that the general theorems do not use

Stewart 1980, Bugeaud-Kaneko 2018 and Dimitrov-Howe 2021 treat an S-unit with k nonzero digits, base b, with a free digit alphabet and a free group of rank s. Our equations add the following. For each: can it give a bound polynomial in k, or collapse the 2^q?

### P1. All but k digits equal 1: y - W = R_n, and 9y + 1 = 10^n + 9W

Used already: it is why the form has the shape Lambda_j = M 10^(-E_j) N_j^(-1) - 1 with a bounded numerator (80 * 10^(E_{j+1})). Unused: that R_n has an exact cyclotomic factorization. I checked the natural attempt, "R_n is n-rough for prime n, so y - W has no prime factor below 2n", and it is vacuous: the information is a statement about n alone, since y - W = R_n is an identity. Verdict: P1 contributes nothing beyond the chain; the extra constraints that look available are the same congruences the ladder already imposes.

### P2. Coefficients come from a tiny set (9 and 18 for the digits 2 and 3; 54 for 7)

The coefficient set affects only the constant 80 (a bound on the numerator, valid for any coefficients up to 72) and the count of arrangements. The height of N_j lives in the exponents, not in the coefficients, so the multiplicative step S_{j+1} ~ lambda S_j is unchanged. The multiset symmetry reduces the pattern count from 2^q-like to prod (j_{d,r} + 1) copy choices per class; with 39 twos in 96 classes the expected number of coinciding pairs is 39^2/192 ~ 8, so the saving is a factor ~2^8, not the exponent. Verdict: constant factors only; no polynomial bound, no collapse of the 2^q.

### P3. y is in a rank-3 group (and the pattern pins the rank, L4 above)

Counting: about 4.1 n^2 S-units have n digits against C(n, k) sparse shapes (section 1.4). That count is what makes the expected number of solutions 10^-234, and it is the reason the true bound is small, but turning it into a theorem requires equidistribution of a log 2 + b log 3 + c log 7 modulo log 10 at the scale 10^-S, which is an irrationality measure, i.e. Baker with its constants. What is used by no document is the per-pattern rank (L4): rank 0 (57%): finite check; rank 1 (38%): sqrt-det becomes det and one logarithm leaves the form, and for a = 0 the leading forms are two-logarithm forms decided exactly by continued fractions of log 3/log 10 and log 7/log 10, which is Laurent-strength with no constant; rank 2 (5%): unchanged. Worked example: pattern with y = 2^a 3^b (c = 0): window K = 96 gives N ~ 10^96/(5 * 2^(a+2)), so the typical least b exceeds 10^90 at a = 0 (against 10^27 for the rank-2 coset of the same level). Verdict: a constant-exponent improvement in the cheap branches and zero improvement in the rank-2 branch; cannot give a polynomial-in-k bound; does not collapse the 2^q. Best immediately usable item; it must not be mistaken for a breakthrough, because the sandwich is only as strong as its hardest branch.

### P4. The digit multiset is fixed, so the digit sum m and the 2-adic tail structure are fixed

Two consequences:

(a) **The 2-adic tail is forced, and the number of admissible tails is polynomial in the tail length, not exponential.** For y with v_2(y) = a, the low terms satisfy 9 sum_{e_j < a} w_j 10^(e_j) = 1 (mod 2^a). Order the terms by position; the partial sum r_j = 9 sum_{i<=j} w_i 10^(e_i) - 1 must have v_2(r_j) = e_{j+1} exactly (when e_{j+1} < a), so each next position is a function of the digits chosen so far, and only the weight of the next digit is free (parity of the running quotient forces the digit's parity, leaving 1, 3 or 7 on odd steps and 2 on even steps). Computed (`scripts/tails.py`) for the k = 44 multiset {2^39, 3^3, 7^2}: the number of admissible tails of length l divisible by 2^l is 1, 3, 5, 11, 19 (l = 1..5), 291 (l = 10), 7960 (l = 20), 63218 (l = 30), 286742 (l = 40), 924421 (l = 50), 2387368 (l = 60), growth ~l^5.2, against 2^l = 1.15e18 at l = 60. The exponent 5 is the number of non-2 digits. Consequence: the depth-1 enumeration over 2^(q (a+9)/96) copy choices can be replaced by this forced DFS and is polynomial for multisets dominated by one digit value; the Yu bottom chain below position a is replaced by an exact automaton with no Baker constant. Limits: (i) only positions below a are forced; positions in [a+9, 96 D) are 2-adically free, and 5-adically they are tied to the unknown (b, c), so depth >= 2 cases are not collapsed; (ii) for multisets with several comparable digit values (4s, 6s, 8s mixed) the tail count is not small; (iii) the same DFS decides A(M) exactly where its tree is finite, which is the item that stops the engine at k >= 36. Labels: the forcing statement is PROVEN-ON-PAPER (elementary 2-adic arithmetic); the growth rate is STRONG-EMPIRICAL to l = 60 (the search hit a state cap at l = 63).

(b) **Digit-sum and 3-adic structure.** 10 = 1 + 9, so 10^e is a 1-unit in Z_3, y = n + m + 9(C(n, 2) + sum w_j e_j) + ... (mod 3^j) and b = v_3(y) is a 3-adic function of (n, e_j). For b > log_3 n + 2 the congruences mod 3^(b-2) pin the actual integers n, e_j rather than their residues (they are below 3^(b-2)). I found no way to use this without a 3-adic linear-form theorem (Yu with p = 3, the same height-of-the-rest obstruction as for p = 5), so it is recorded as an untested direction. CONJECTURE that it supplies anything beyond the 3-adic part of the existing ladder.

Verdict for P4: (a) can collapse the 2^q at depth 1 for dominated multisets and eliminate the bottom Yu chain; it does not touch the top chain, depth >= 2, or the superexponential D; (b) is open.

### P5. The digit product of y must itself be the vertex

This is the definition of the multiset and enters through (E) only as a count. A vertex tree is graded (every child is a vertex of a lower or equal tree), but the grading does not constrain the position structure of one child. Verdict: no mechanism found.

### P6. Positions are only constrained residue-by-residue, and runs of adjacent digits are cheap

A run of r adjacent equal non-1 digits equals w (10^(e+r) - 10^e)/9, two terms of the group rather than r. The Baker chain bounds gaps without using adjacency (g_j >= 1 is the only requirement), so runs of non-1 digits are not seen by the chain, and its bound is attained only when all gaps are large. Observation, not a theorem: large gaps are exactly the case where the top-down chain is needed and the digits are independent; clustered digits are the case where the number of independent unknowns is smaller than k. A cluster decomposition (a chain over clusters separated by gaps above a threshold theta) would reduce the effective k in the exponent to the number of clusters. The worst case (all gaps above theta) has k clusters, so this cannot improve the worst-case bound; it could cut the case count for specific patterns. Verdict: no polynomial bound; no collapse of 2^q in the worst case.

### P7. Large-sieve/character-sum control of the number of open patterns

The open set at level L is sum over patterns of prod_p 1_{H_p}(V(pattern)), with 1_{H_p} a sum of multiplicative characters and V = f(zeta) a value of a short (l1-norm m) polynomial at a root of unity in F_p. A bound of the form (open count) <= N_L rho_L (1 + o(1)) would replace enumeration by an a-priori count, but it does not list the survivors, so the sandwich still has nothing to run on; and equidistribution of such sums with a sparse additive structure is the content of the character-sum problem for sumsets of 10^e, which the documents do not touch. Verdict: would bound the accident count (M4) rigorously if proven, which is publishable and useful, and does not by itself close anything.

## 4. The two shapes of a win

### W1. A length bound n < G'(k) with log G' polynomial in k, or small enough that the sandwich closes at depth <= 3 at k = 44

Exact requirement for depth <= 3: lower bound 10^168 at D = 3, so log10 G' <= 168 at k = 44 (cost then 4^44 = 10^26.5 cases per pattern worst case; D <= 2 needs log10 G' <= 120, 3^44 = 10^21). Compared with the certified 849.7 (single-ended) and ~465 (two-ended): a factor 5 and 2.8 in the exponent. In terms of the recursion: lambda <= 10^3.6 (single) or 10^7.0 (two-ended), against the documented 10^18.6. In terms of a Stewart-type shape n < (c log n)^k: c <= ~20 (c = 10 gives log10 n ~ 156; c = 100 gives ~208, D = 4).

Candidate mechanisms, ranked by what I can support:

1. **Cluster-aware chain plus forced 2-adic region (P6 + P4a).** Reduces the effective number of independent gaps for some patterns; worst case unchanged. Probability of delivering W1 for the worst case: very low. Cost to try: low.
2. **Rank-based branch bounds (L4/P3).** Gives log G drops of 5-10% in rank-1 branches and exact CF decisions for a = 0 two-logarithm forms. Does not reach 168 and leaves the rank-2 branch at 849.7. Cost: low; value: removes about 95% of the work, not the hardest 5%.
3. **An effective weakening of the Subspace ε-gap with ε = 1/k for this family** (S1): this is the real W1. It would be new mathematics: Evertse's bound (gap <= eps n + C(eps)) made effective with C(1/k) polynomial in k for the group <2,3,5,7> and coefficients bounded by 72. No existing technique in the documents gives it. Label CONJECTURE that it is within reach; if proven it is a theorem about all S-units with few non-1 digits, not just our vertices.
4. **A 3-adic linear-form argument for large b (P4b).** Untested; likely repeats the height-of-the-rest obstruction.
5. **Character-sum control (P7).** Not W1; bounds the number of accidents only.

### W2. A sandwich step whose cost is subexponential in q (given the present G)

Present cost per pattern at D = 18, q = 44: (D+1)^q = 10^56. A W2 would make it exp(o(q)) or polynomial in q.

1. **Forced-DFS pruning of copy choices (P4a).** Polynomial (~l^5) at depth 1 for dominated multisets. At depth >= 2 the positions in [a+9, 96D) are 5-adically constrained only through the unknown (b, c), so the collapse does not extend; the only route past that is a 5-adic analog of the forcing, which needs the target (the unknown coset) to be fixed, i.e. an enumeration over cosets rather than over cases. Probability of full W2: low-moderate; of a 10^10-10^20 saving at depth 1: high.
2. **Anchor-level closure that avoids enumerating copy choices** (A2). Needs a structural reason that low-window words are shared across patterns. None documented. CONJECTURE.
3. **Dual enumeration over the coset image instead of the case list** (H7, H13): enumerate S-unit residues in the image once and decode. Wins when the image size H is below the case count; H grows like 10^(0.4 L) and the case count like (D+1)^q, so the crossover is in the scale of the problem (HEURISTIC; the H13 estimate of ~40x at k = 29 is not a subexponential improvement).
4. **A meet-in-the-middle on the sum of the q digit contributions against the multiplicative image.** The documents state (dpcount section 1.2, and H4) that nothing factors because the test is multiplicative and the sum additive; no mechanism found.

## 5. What would be genuinely new

Publishable if proven (each is mathematics, not engineering):

- **N1.** An effective gap bound for S-units with k non-1 decimal digits in which the constant does not carry the height of the lower part (OPEN-PROBLEM.md's original question): e.g. g_j <= C(S) log n for all interior gaps, or the weaker S_{j+1} <= (1 + 1/k) S_j + poly. This is Stewart/Bugeaud-Kaneko made polynomial in k and would settle the even-target case. No route is documented; Subspace gives it ineffectively.
- **N2.** Effective version of Evertse's inequality for the specific group <2, 3, 5, 7> and bounded coefficients with eps = 1/k.
- **N3.** A rigorous equidistribution/character-sum bound for sparse sumsets {sum w_j 10^(e_j)} in cosets of the subgroup <2, 3, 7> mod primes of 10^L - 1, giving a proven upper bound on the number of open (accident) patterns. Useful for the whole program: it is the missing piece of H1/H10.
- **N4.** A 5-adic (or 10-adic) analog of the 2-adic forcing that fixes copy choices without knowing the coset, which would give a subexponential sandwich step (W2).

Only engineering (valuable, no new theorem):

- Per-pattern rank dispatch (L4): rank-0 finite check, rank-1 CF/det bound, rank-2 as now. Likely a 10-20x reduction in total sandwich work and the removal of the a = 0 two-logarithm case from Baker entirely.
- The forced 2-adic DFS in C (P4a), which also computes A(M) for the Tier-C multisets.
- Interval-arithmetic certification of the two-ended chain (H5, already in progress).
- Resolving the sub-coset accounting question (L2) by measuring live sub-coset counts at depths 1-4 on a k = 15-20 equation.
- GPU or large-memory counting jobs (dpcount): they produce the same survivor counts Monte Carlo gives to 0.2%.

## 6. Open items and seams

- G(k, a) for a >= 1 treats a as free (t_0 = 4). If A(M) is computed (P4a) and a <= A, each fixed a gives a form with 9*2^a as one constant of height <= (A + 2) log 2; I did not recompute G for that.
- The two-ended numbers are Codex's, scaled linearly in k; the three reported points are consistent with that slope, and the interpolated entries are marked as such. They need the independent audit H5 already assigns.
- Sub-coset growth versus (D+1)^q is unreconciled (L2).
- A(M) for the Tier-C multisets is not known (engine cannot terminate); the polynomial tail growth suggests it can be computed by a C DFS, but I did not run it past l = 63.
- The 57%/38%/5% rank split assumes uniform residues of n mod 3 and the pattern-determined residue of y mod 7; the real fractions per vertex should be measured before use.
