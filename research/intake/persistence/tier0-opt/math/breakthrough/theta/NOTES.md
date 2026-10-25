# Theta lane: can a per-gap bound g <= C h^theta (theta < 1) be proved for the Tier C family?

Working notes, lane theta, 2026-10-20 night. Scripts and raw outputs sit beside this file (theta_0N_*.py, out_0N*.txt).
Labels: PROVEN-ON-PAPER (argument written here, not Lean-checked, so not PROVEN), HEURISTIC, CONJECTURE,
STRONG-EMPIRICAL. No step rests on abc, Lang-Waldschmidt, Schanuel or a Hasse principle. Matveev's theorem (BMS 9.4) and the
B3 constants for Bugeaud-Kaneko/Yu are taken as in BAKER-CHAIN.md and b3-archimedean/REPORT.md, not re-derived.

## 0. Verdict

No theta < 1 was obtained. Every argument examined returns theta = 1, and for each one the exact point of failure is
identified and, where a number is involved, measured. The reasons are structural rather than a matter of constants:

1. A bound g <= C h^theta with theta < 1 is equivalent (T1) to g <= eps h + A eps^(-beta), beta = theta/(1-theta): a
   Roth-type inequality with an effective constant polynomial in 1/eps. A uniform version would force every S-unit with n
   digits to have at least n^(1-theta)/C non-1 digits (T2); the recorded lower bound is c log n / log log n (LIT2 1.1, 1.3).
2. Linear dependence on the height of the approximant is sharp for the class of all rationals (T3a, Liouville), and for
   the sparse prefixes of this family any single rational approximant of the required precision has height at least
   min(s_j, g_j) log 10 - log 160 (T3b, Lemma H). The family-specific escape would have to be a statement that no S-unit has a
   sparse prefix followed by a long zero run, which is the original problem (T8).
3. Lattice coordinates make the Baker product of heights larger by 10^56.6 and shrink log B by a factor below 1.1 (T4).
4. The p-adic side is height-free in truth (true constant about 1.74 log B against an allowance 10^15 larger) but a
   gap needs v_5(M/T_j - 1) with T_j outside the group; an anchor inside the group exists only for E <= 4.3 log B (T5).
5. Any argument whose only inputs are archimedean prefix inequalities and 2/5-adic suffix inequalities of the Baker
   type has optimum min_m [K0 (1+K)^(m-1) + Z0 (1+Y)^(k-m)] (T6, explicit witness, exact arithmetic).

By-products that are positive: T7 (an elementary 2-adic chain with ratio log_2 10 = 3.32 below position a, which makes
B3's two-ended bounds unconditional in a), T9 (the per-gap constant that depth 1 needs: 10^1.3 at k = 44, one-ended).

## 1. Setting

9y + 1 = 10^n + sum_{i<=k} c_i 10^(E_i), c_i = 9(d_i - 1) in [9, 72], E_1 > ... > E_k >= 0, M = 9y = 2^a 3^(b+2) 7^c.
Prefix height s_j = n - E_j, N_j = 10^(s_j) + sum_{i<=j} c_i 10^(s_j - s_i), gap g_j = E_j - E_(j+1) = s_(j+1) - s_j.
Archimedean form Lambda_j = M 10^(-E_j) / N_j - 1, 0 < Lambda_j <= 80 10^(-g_j) / N_j. Matveev gives
g_j <= (log 80 + K1 (s_j log 10 + log 9)) / log 10, K1 = C(t) P T. The recursion S_(j+1) = (1 + K1) S_j + O(1) is the whole
exponential-in-k shape: theta = 1 with multiplier 10^16.7 (Matveev, a >= 1, folded) or 10^18.2 (p-adic Yu chain).

## 2. Results

### T1. theta < 1 is equivalent to a polynomial-epsilon Roth form. PROVEN-ON-PAPER
(a) For theta in [0,1), C > 0, eps > 0, h >= 0: C h^theta <= eps h + c eps^(-theta/(1-theta)), c = (1-theta) theta^(theta/(1-theta)) C^(1/(1-theta)).
Proof: maximize C h^theta - eps h; the maximizer is h* = (C theta / eps)^(1/(1-theta)).
(b) If g <= eps h + A eps^(-beta) for all eps in (0,1] and h >= A, then g <= 2 A^(1/(1+beta)) h^(beta/(1+beta)); take eps = (A/h)^(1/(1+beta)).
With beta = theta/(1-theta) the exponent is theta.
(c) Recursion: S_(j+1) <= S_j + C S_j^theta gives S_k <= (S_1^(1-theta) + (1-theta) C (k-1))^(1/(1-theta)) (concavity of x^(1-theta)).
Checked (theta_01): 16 closed-form comparisons against the iteration, 2000 random Young draws, planted negative refused.
Consequence for the b3_theta table: theta = 0.75 corresponds to eps-form constants c(eps) = 10^64 at eps = 1; the required
object is a Roth-type theorem with a 10^64-sized, polynomially growing constant. Nothing of that kind exists effectively.

### T2. A uniform theta < 1 would be a different theorem class. PROVEN-ON-PAPER (implication), literature statement read from LIT2
If g_j <= C s_j^theta held for every S-unit with k non-1 digits, for all k, then by T1(c) n <= (S_1^(1-theta) + (1-theta) C k)^(1/(1-theta))
(+ the 5-adic height-free E_k), i.e. k >= n^(1-theta)/(C (1-theta)) - O((log n)^(1-theta)). The effective results recorded in
LIT2 (Stewart 1980; Bugeaud-Kaneko 2018 Thm 1.2, Cor 1.5) give k >= c log n / log log n. The fixed-k Tier C statement is not
the uniform one, but any proof technique that is uniform in k inherits this. Not a contradiction with anything known.

### T3a. Linear dependence on h(beta) is optimal for the class of all rationals beta. PROVEN-ON-PAPER
For U in <2,3,7,10> of bounded exponents and beta = U (1 + 10^(-m)): h(beta) = m log 10 + O(h(U)) and
Lambda = U/beta - 1 = -10^(-m)/(1 + 10^(-m)), so -log|Lambda| = h(beta) - O(h(U)). Hence no lower bound valid for all rationals beta
can have exponent of h(beta) below 1 with constant below 1. Checked (theta_02): ratio -log|Lambda| / h(beta) = 0.692, 0.900, 0.973,
0.993, 0.998 at m = 10, 40, 160, 640, 2560.

### T3b. Lemma H (a single rational approximant of a sparse prefix is tall). PROVEN-ON-PAPER
Let x = 1 + sum_(i<=j+1) c_i 10^(-s_i), 1 <= c_i <= 80 integers, s_1 < ... < s_(j+1), x_j = N_j / 10^(s_j) the j-term truncation,
delta_j = gcd(N_j, 10^(s_j)). If p/q satisfies |x - p/q| <= 80 * 10^(-s_(j+1)), then q >= min(10^(s_j) / delta_j, 10^(g_j) / 160).
Proof: |x - x_j| < 80 * 10^(-s_(j+1)). If p/q = x_j then q = 10^(s_j)/gcd-adjusted >= 10^(s_j)/delta_j. Otherwise
|N_j q - p 10^(s_j)| >= 1 gives |x_j - p/q| >= 1/(q 10^(s_j)), and the triangle inequality gives 1/(q 10^(s_j)) <= 160 * 10^(-s_(j+1)).
(delta_j <= 8 when g_(j-1) >= 4, since N_j = c_j mod 10^(g_(j-1)) and 5 does not divide c_j.)
Consequence: a Baker-type form built on one rational beta and delta-precision 10^(-s_(j+1)) has h(beta) >= min(s_j, g_j) log 10 - log 160;
when g_j >= s_j (the only regime in which a gap bound has content) the linear form carries the full height of the prefix.
Checked (theta_02): 0 violations in 4000 random sparse prefixes, 1459 within a factor 50 of the bound; planted negative
(tolerance widened by 10^12) violates the bound in 746 of 4000 trials.

### T4. Lattice coordinates multiply the Baker product by 10^56.6. PROVEN-ON-PAPER (arithmetic on the recorded basis)
Writing the exponent vector as x_0 + z_1 u + z_2 v with the recorded Lambda_96 basis (norms 5.8e27 and 2.6e28, |det| = 2.81e56,
both verified to satisfy 3^u1 7^u2 = 1 mod R_96 with the factors 3, 7 removed) makes the logarithms g_u = 3^u1 7^u2, g_v of height
10^28.22 and 10^28.71. Matveev's A-product grows from log 3 log 7 = 2.14 to h(g_u) h(g_v): a factor 10^56.6. The coefficients z_i are
about n/10^28, and log B drops from 1958 to 1894 at n = 10^850: a factor 1.03. Net loss 10^56.6. Coefficients bounded by the
lattice do not help because B enters Baker only through 1 + log B; the heights of the generators enter linearly.
Also v_5(g_u - 1) = 5, v_2 = 9; v_5(g_v - 1) = 5, v_2 = 10 (theta_03): the raw Lambda_96 vectors carry only 5-9 digits of 10-adic precision,
the deeper precision comes from the 10-adic cosets, whose generators are larger still.

### T5. The p-adic side is height-free in truth, and that does not reach a gap. PROVEN-ON-PAPER (counting) + STRONG-EMPIRICAL
(a) Measured (theta_04): the lattice {2^a 3^b 7^c = 1 mod 5^L} has lambda_1 = 10^22.25 at L = 96 and 10^29.57 at L = 128, i.e.
3 log_10(lambda_1) / (L log_10 5) = 0.99. So the largest 5-adic valuation of 2^a 3^b 7^c - 1 over the box B is about 1.74 log B. The
allowance used by B3's p-adic chain (CY(3) log2 log3 log7 log B) exceeds it by 10^15.0 at every tested B (10^3 ... 10^48). The 10-adic rank-2
lattice {3^b 7^c = 1 mod 10^L} has lambda_1 = 10^47.34 at L = 96 (L/log10 lambda_1 = 2.03), the sqrt-det law.
(b) A gap needs v_5(M/T_j - 1) >= E_j where T_j = sum_(i>j) c_i 10^(E_i) - 1 is outside the group, of height E_(j+1) log 10. To make
it homogeneous replace T_j by an S-unit M_a congruent to it mod 5^(E_j). The box {|x| <= B} has about B^3 points and maps to
at most B^3 of the 5^(E_j) residues, so for E_j > 3 log_5 B + O(1) a generic T_j has no such M_a in the box, and M_a of size
5^(E/3) gives Yu's bound E <= C log(5^(E/3)) which is void for C > 3/log 5. For E_j <= 4.3 log B nothing beyond Yu with
three tiny-height logarithms is needed. Between these the p-adic bound is C h(T_j) log B: theta = 1 with the Yu multiplier.
(c) The same counting shows why homogeneous forms in two candidates are height-free (T10) but cannot produce a bound on one candidate.

### T6. No-go for the class of one-sided Baker inequalities. PROVEN-ON-PAPER (explicit witness, exact rational arithmetic)
Constraints: g_0 <= K0, E_k <= Z0, and for 1 <= j <= k-1: g_j <= K S_j and g_j <= Y E_(j+1), n = S_k + E_k. For every m,
S_m <= K0 (1+K)^(m-1) and E_m <= Z0 (1+Y)^(k-m), so n <= F(m) = K0 (1+K)^(m-1) + Z0 (1+Y)^(k-m). Take m* minimizing F and set
S_j = K0 (1+K)^(j-1) (j <= m*), E_j = Z0 (1+Y)^(k-j) (j >= m*), n* = S_(m*) + E_(m*), the remaining S_j, E_j from n*. Then g_j = K S_j for j < m*,
g_(m*) = Y E_(m*+1), g_j = Y E_(j+1) for j > m*; the two cross constraints at j = m*-1 and j = m* are exactly F(m*) <= F(m*-1) and F(m*) <= F(m*+1).
So n* = min_m F(m) is attained, and no argument that uses only these inequalities can bound n below it. Checked (theta_06): the
construction is feasible with n = min F in 300 of 300 random parameter sets (exact Fractions), the LP optimum equals min F to 1e-15 on 60 sets,
a planted inflated gap is refused. At k = 44: K = 10^16.7, Y = 10^18.2, K0 = Z0 = 10^14.7 gives 10^396.9; even K = Y = 10^3 gives 10^80.7, which is above the 10^72 that
depth 1 needs. Interior information beyond the two ends is what theta < 1 needs, and the inequalities that exist are all of this form.

### T7. Elementary 2-adic chain; B3 is unconditional in a. PROVEN-ON-PAPER (identities exhaustively checked on small cases)
Let a = v_2(M) >= 1, positions p_1 < ... < p_k (p_m = E_(k+1-m)), coefficients gamma_m, S_m = sum_(i<=m) gamma_i 10^(p_i) - 1.
(i) M + 1 odd forces p_1 = 0 and gamma_1 odd. (ii) M = S_m mod 2^(p_(m+1)) for 0 <= m < k. (iii) 0 < S_m < 80 * 10^(p_m).
(iv) If p_(m+1) <= a then 2^(p_(m+1)) | S_m, so p_(m+1) < log_2 80 + (log_2 10) p_m = 6.322 + 3.3219 p_m (and p_2 <= log_2 71 = 6.15).
(v) If p_(m+1) > a then v_2(S_m) = a, so a < 6.322 + 3.3219 p_m. Let m0 be the least m with p_(m+1) > a (or k).
For m0 < k: p_m < 2.723 (3.3219^(m-1) - 1) for m <= m0 and a < 6.322 + 3.3219 p_(m0). For m0 = k the whole configuration sits in the lowest
2.723 * 3.3219^(k-1) positions (10^22.9 at k = 44, 10^16.1 at k = 31) and n = p_k + g_0 with g_0 <= 10^14.7 by the top Matveev form,
which is below the 10^27 the lattice forces, so m0 < k.
Hence every a >= 1 falls in one case m0 in [1, k-1] with a bounded by a_max(m0), the bottom m0 positions elementary (ratio 3.32, no Baker constant),
and the Yu chain only above them. B3's chain recomputed per case (theta_05): worst case is m0 = 1 (a <= 6): log10 G' = 279.47 at k = 31,
394.17 at k = 44 (B3: 279.23 / 393.93 at a = 1, 280.06 / 394.75 at a = 40); m0 = 2: 266.3 / 386.8; m0 = 10: 198.1 / 317.8. With a = 0 (281.50 / 402.11)
the bound over all a is 281.50 (k = 31) and 402.11 (k = 44): B3's "a <= 40" hypothesis is not needed. Checked (theta_05b): 728,256 candidates
(n <= 14, k <= 3), 95,860 with a >= 1, 0 violations of (i)-(v); with a shifted by 3 (planted) 2,021,244 violations.
Failure for theta: the argument needs M = 0 mod 2^a, i.e. vanishing of M in Z/2^(p_(m+1)). Above position a, M/2^a is a 2-adic unit of rank 2 and the form
3^(b+2) 7^c T^(-1) - 1 has three logarithms. Positions below a are at most 6.15, 26.8, 95.2, ... : too few to matter, and the adversary takes a <= 6.

### T8. Per-prefix reduction is theta = 0 with an exceptional set equal to the problem. PROVEN-ON-PAPER (dichotomy) + HEURISTIC (cost)
Fix a prefix N_j and a bound B >= 2.1 n + 2. Let eps_j(B) = min over integer vectors x with |x| <= B of |x . (log 2, log 3, log 7, log 10) - log N_j|
(computable by LLL/CVP in dimension 4-5). Any candidate with this prefix has |Lambda_j| >= eps_j(B)(1 - o(1)), hence g_j <= (log 80 - log eps_j(B))/log 10 + o(1).
If eps_j(B) >= c B^(-4) this is g_j <= 4 log_10 B + O(1): height-free. A prefix with eps_j < c B^(-4) is exactly a prefix that is a sparse leading block of an S-unit of
exponent size <= B followed by a zero run longer than 4 log_10 B. Thus a theta < 1 statement for all prefixes is equivalent to the absence of such S-units, the original
problem. The cost of using the first alternative is the number of prefixes: (3 log_10 B / 96 + k choose k) times pattern count (B1 section 2.2 B4). This is the trade B3 item 4 measured as worse than one more sandwich depth.

### T9. What depth 1 needs. HEURISTIC arithmetic (theta_01)
S_1 = 10^14.7, target 10^72, S_(j+1) = (1 + Y) S_j: Y <= 10^1.90 (k = 31) and 10^1.31 (k = 44) one-ended; two-ended Y <= 10^3.80 and 10^2.60. Matveev gives 10^16.7 and Yu 10^18.2:
a constant deficit of 10^14 to 10^16. Depth 2, 3, 4 at k = 44 one-ended: Y <= 10^2.45, 10^3.56, 10^4.68. A bound that is linear with a constant of 20 closes Tier C
as well as theta = 0.75 does; theta < 1 is not necessary, a 10^15-fold smaller constant is sufficient. On the 43 recorded SANDWICH-run patterns (k = 5..11) the theta model with theta = 0.75 would close every
one at depth 1 (recorded: 7 at depth 2, 26 at depth 3, 10 at depth 4); theta = 0.9 would close 39 at depth 2 and 4 at depth 3 (theta_08). The recorded log10 U implies per-gap multipliers 10^18.2 to 10^18.4.

### T10. Two candidates cannot share many leading digits. PROVEN-ON-PAPER (Matveev), height-free
If M != M' are in <2,3,7> with exponents <= B and |M'/M - 1| <= 10^(-G) then G log 10 <= C(3) log 2 log 3 log 7 (1 + log B), C(3) = 1.43e11, so G <= 10^10.97 (1 + log B). Distinct S-units therefore diverge
within about 10^11 (1 + log B) leading digits: a prefix agreeing with an S-unit in the box beyond that length belongs to at most one of them. This is the anchor idea (i) made precise:
the lattice minimum 10^27 enters only through log B. It bounds the multiplicity of a prefix, not the length of a gap of one candidate.

## 3. Candidate arguments and where each fails

| Candidate | What it would give | Failure point |
|---|---|---|
| (i) lattice coordinates z_1, z_2 as the coefficients | coefficients about n/10^28 | heights of g_u, g_v are 10^28: net 10^56.6 loss (T4) |
| (i') anchor and candidate, homogeneous form | height-free | covers two candidates, not one (T10); anchor in the box needs E <= 4.3 log B (T5b) |
| (ii) fixed part as S-unit plus sparse correction | smaller height than s_j | h(N_j) = s_j log 10 is forced (Lemma H); near-S-unit prefixes are exactly the exceptional set (T8) |
| (iii) 2-adic digit by digit | ratio 3.32 instead of 10^18 | needs M = 0 mod 2^p; valid only below a, adversary takes a <= 6 (T7) |
| (iii) 5-adic digit by digit | height-free p-adic bound | 2 is a primitive root mod 5^L so the group has no 5-adic constraint; the form has T_j outside the group (T5b) |
| p-adic valuation of u - 1 at 2 and 5 | gap linear in log h | true law is height-free (about 1.74 log B) but it bounds precision of cosets, i.e. a lower bound on n, not a gap |
| archimedean plus p-adic combined | theta < 1 | combined inequalities have optimum min_m F(m) (T6) |
| any single-rational Baker form | sublinear h | Liouville (T3a) and Lemma H (T3b) |
| per-prefix lattice reduction | theta = 0 | exceptional prefixes = near-S-units; cost (T8) |

## 4. Numerical checks (scripts, outputs)

- theta_01_recursion.py / out_01.txt: closed form vs iteration (16 cases), Young inequality (2000 draws), planted negative, required Y table.
- theta_02_height_barrier.py / out_02.txt: Lemma H (4000 trials, 0 violations; negative 746), Liouville ratio.
- theta_03_lattice_heights.py / out_03.txt: recorded Lambda_96 basis, valuations, height inflation 10^56.6.
- theta_04_padic_slack.py / out_04.txt: 5-adic and 10-adic lattices to L = 128 and 96, 10^15 slack.
- theta_05_two_adic_elementary.py / out_05.txt, theta_05b_two_adic_exhaustive.py / out_05b.txt: T7.
- theta_06_no_go_lp.py / out_06.txt: T6.
- theta_07_sunit_census.py / out_07_300.txt: all 37,375,388 S-units below 10^300: the minimum number of non-1 digits is about 0.8 n at n = 300 (k = 244 at n = 300); the largest
  n with k <= 12 is 20; the longest run of 1s anywhere is 8. STRONG-EMPIRICAL context: the family is empty far beyond where proofs reach, and observed gaps are logarithmic.
- theta_08_recorded_sandwich.py / out_08.txt: the 43 recorded patterns, depth rule reproduced 43 of 43.
- lat.py: small LLL and 2-D congruence lattice helpers.

## 5. What remains open

1. A constant 10^14 to 10^16 smaller than Matveev/Yu per gap (T9); B3 measured that a factor 10^-3 to 10^-6 is not enough for depth 1.
2. An effective Roth-type theorem with polynomial epsilon dependence for S-unit approximation by integers (T1, T2).
3. A structural reason that sparse prefixes are never near an S-unit (T8); the heuristic count says so, no proof route found.
