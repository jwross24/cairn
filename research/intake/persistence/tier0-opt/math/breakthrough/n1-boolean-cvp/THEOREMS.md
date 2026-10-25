# N1: Boolean lattice reduction in place of copy-choice enumeration. Statements and proofs

Calibration key (RULE 2): PROVEN-ON-PAPER = an ordinary proof is written below and every numeric instance used was
re-checked by exact integer arithmetic; STRONG-EMPIRICAL = exact computation agrees with an independent oracle on a
finite set, no proof; HEURISTIC = a counting argument; CONJECTURE = neither. Nothing here is Lean-checked, so nothing
is PROVEN. The three inputs inherited from the existing program are used as black boxes and keep their own labels:
Lemma C (DEEPCUT.md, STRONG-EMPIRICAL, two blind implementations, Lean for its arithmetic core), Theorem U
(BAKER-CHAIN.md, ordinary proof resting on Matveev; b3 REPORT for the two-ended k = 31, 44 values), and the
saturation statement of codex-deep-attempt.md Theorem 3 (PROVED ON PAPER there).

## 0. Setting

Fix an open pattern: exponent a, anchor coset C0 = p0 + L96 in Z^2 (b, c), digit multiset with types (d, e) of
multiplicity c(d,e), classes e in [0, 96). A candidate y' = 2^a 3^b 7^c (b, c >= 0, (b,c) in C0, y' != anchor)
has n >= 10^27 digits. Write K = 96 D. By Lemma C, y' = L(t) (mod 10^K) with

    L(t) = R_K + sum_j (d_j - 1) 10^(e_j + 96 t_j),     t_j in {0, ..., D-1} or "beyond",  positions pairwise distinct,

(R_K = (10^K - 1)/9). The sandwich closes the pattern at depth D when every sub-coset of {(b, c) in C0 :
2^a 3^b 7^c = L(t) mod 10^K, t admissible} has nearest point of squared norm > rho2(U), where
rho2(U) = floor(2 U^2 10^20 / 4771212547^2): a candidate with n <= U digits has max(b,c) log10(3) <= n, so
||(b,c)||^2 <= 2 max(b,c)^2 <= 2 U^2/log10(3)^2 < 2 U^2 10^20/4771212547^2 + 1 (the integer test is the C port's
`sandwich_closes`). Enumeration costs prod over blocks of the number of block fillings; this is the cost to beat.

Let E <= D and s = 96 E. Split each placement t into the part with t_j < E (the BASE; enumerated exactly as
deepcut.deep_cut does, with its cuts) and the part with E <= t_j <= D-1 (the HIGH variables). A base is a depth-E
sub-coset v0 + Z u1 + Z u2 together with Tbase = R_K + sum over base digits.

## 1. Exact linearization of the high blocks (PROVEN-ON-PAPER)

Lemma 1 (binomial). Let p be a prime, sigma >= 1, p^sigma | t. For every integer z (negative allowed),
(1+t)^z = 1 + z t (mod p^(2 sigma)). Proof: for z >= 0, (1+t)^z = sum_k C(z,k) t^k and C(z,k) in Z, v_p(t^k) >=
k sigma >= 2 sigma for k >= 2. For z < 0, (1+t)^(-1) = 1 - t + t^2 - ... = 1 - t (mod p^(2 sigma)) and the case z >= 0 gives
(1+t)^(-n) = (1 - t)^n = 1 - n t. Products: (1 + z1 tu)(1 + z2 tv) = 1 + z1 tu + z2 tv (mod p^(2 sigma)). QED.

Theorem 1 (block lift). Let a < s, K <= 2 s - a. Let (u1, u2) satisfy g(u_i) = 3^(u_i[0]) 7^(u_i[1]) = 1 (mod 2^(s-a))
and (mod 5^s), and let v0 satisfy 2^a g(v0) = Tbase (mod 10^s) (a depth-E base). Put G0 = g(v0), tu_i = g(u_i) - 1.
For a placement of the high variables x in {0,1}^m (variable i = (d_i, e_i, t_i), position pos_i = e_i + 96 t_i in
[s, K)), write w_i = (d_i - 1) 10^(pos_i) and T(x) = Tbase + sum x_i w_i. For every (z1, z2) in Z^2 and
(b, c) = v0 + z1 u1 + z2 u2:

    2^a 3^b 7^c = T(x) (mod 10^K)   <=>   alpha1 z1 + alpha2 z2 + sum_i om_i x_i = beta   (mod 10^(K-s)),

where, per prime, with sigma_2 = s - a, sigma_5 = s:
    alpha_i^(2) = G0 tu_i / 2^(s-a),  alpha_i^(5) = G0 tu_i / 5^s,
    om_i^(2) = - (w_i / 2^a) / 2^(s-a),  om_i^(5) = - (w_i 2^(-a)) / 5^s,
    beta^(2) = -(G0 - Tbase/2^a)/2^(s-a),  beta^(5) = -(G0 - Tbase 2^(-a))/5^s,
and the two congruences (moduli 2^(K-s), 5^(K-s)) are combined by the Chinese remainder theorem into one modulus 10^(K-s).
Proof. 2^a G = T mod 10^K iff G = T/2^a mod 2^(K-a) and G = T 2^(-a) mod 5^K (2^a divides Tbase and every w_i since
pos_i >= s > a). G = G0 g(u1)^z1 g(u2)^z2. By Lemma 1 with sigma = s - a at p = 2 and sigma = s at p = 5, and
K - a <= 2(s - a), K <= 2 s: G = G0 (1 + z1 tu1 + z2 tu2) modulo 2^(K-a) and 5^K. The base condition gives
G0 - Tbase/2^a = 0 mod 2^(s-a) and G0 - Tbase 2^(-a) = 0 mod 5^s; every term of
G0 tu1 z1 + G0 tu2 z2 - (T(x) - Tbase)/2^a + (G0 - Tbase/2^a) is divisible by 2^(s-a) (w_i/2^a is, since pos_i >= s),
and likewise by 5^s, so dividing by 2^(s-a), resp. 5^s, turns "= 0 mod 2^(K-a)", resp. "mod 5^K" into the stated
congruences mod 2^(K-s), resp. 5^(K-s), with no loss and no gain. QED.

Corollary 1.1 (what E must be). K <= 2 s - a with K = 96 D, s = 96 E is the exact-linearization range, i.e.
E >= (D + a/96)/2. For smaller E, Lemma 1 still holds modulo the smaller moduli m2 = min(K - a, 2 (s - a)) at p = 2 and
m5 = min(K, 2 s) at p = 5, so the same formulas read with moduli 2^(m2 - (s - a)) and 5^(m5 - s) give a congruence that is
NECESSARY for a solution: the relaxed system's solution set contains the exact one. The prototype re-checks every
candidate it accepts by exact modular exponentiation, so relaxed mode returns exact minima and only costs more nodes
(n1neg.py measures this).

Proposition 1.2 (E < D/2 cannot be exact; why enumeration of the low half is unavoidable for this method; PROVEN-ON-PAPER).
Take two free digits at positions p, q >= s with 5 not dividing (d_p - 1)(d_q - 1), and any unit T0. Let ell be the 5-adic
logarithm of the principal-unit part. The second difference over the four placements {0, w_p, w_q, w_p + w_q} is
ell(T0 + w_p + w_q) - ell(T0 + w_p) - ell(T0 + w_q) + ell(T0) = log( 1 - w_p w_q / (T0 + w_p)(T0 + w_q) ), which has 5-adic
valuation exactly p + q. The fiber map x -> (coset of z in Z^2 / Lambda) is the image of ell(T(x)) under the (injective, by
saturation) map z -> alpha z, so it is affine in x modulo 5^m exactly when that second difference vanishes modulo 5^m, i.e. only
for m <= p + q. Hence no family of congruences affine in x describes the fibers beyond precision p + q; for variables at
positions >= s the best exact affine modulus is 5^(2s), i.e. D_eff = 2E. (For p = 2 the valuation is p + q - 1.)

Theorem 2 (the lattice formulation reproduces the enumerated sub-cosets). For a fixed placement x the solution set
{(b,c)} of Theorem 1 is exactly the depth-D sub-coset deep_cut computes for (base, x). Hence
min over placements and lattice points of ||(b,c)||^2 equals min over sub-cosets of nearest_norm, and the number of
admissible placements (weighted by label multiplicities) equals deep_cut's survivor count when every sub-coset is
nonempty. Nonemptiness (saturation) is codex-deep-attempt.md Theorem 3: the image of L96 in
(Z/2^(K-a))^* x (Z/5^K)^* is (1 + 2^9 Z) x (1 + 5^5 Z), so every unit that is 1 modulo (2^(s-a), 5^s) is hit. QED (given Theorem 3).

## 2. The certificate (PROVEN-ON-PAPER)

Setting: the system of Theorem 1, modulus M = 10^(K-s) (or the relaxed modulus), unknowns z in a box
Z1 x Z2 = [zlo1, zhi1] x [zlo2, zhi2] containing {z : ||v0 + U z||^2 <= rho2} and x in {0,1}^m, with the variables
partitioned into position groups G_(e,t) (all variables whose position is e + 96 t; at most one digit sits at a
position, so sum_{i in G} x_i <= 1).

Theorem 3 (dual-multiplier certificate). For any integer mu, let r_i = [mu alpha_i]_M and tau_j = [mu om_j]_M
(centered residues), b = mu beta mod M, and
    Fmin = sum_i min(r_i zlo_i, r_i zhi_i) + sum_G min(0, min_(j in G) tau_j),
    Fmax = sum_i max(r_i zlo_i, r_i zhi_i) + sum_G max(0, max_(j in G) tau_j).
If no integer k has Fmin <= b + k M <= Fmax, then no (z, x) with z in the box and x admissible solves the system.
Proof. A solution gives F = r1 z1 + r2 z2 + sum_j tau_j x_j = mu(alpha z + om x) = mu beta (mod M), and F lies in
[Fmin, Fmax] (for each group at most one x_j is 1, so the group's contribution is 0 or one tau_j). QED.

Soundness of the sandwich verdict (Theorem 4). Suppose every depth-E base of the pattern, at every representation,
has a multiplier satisfying Theorem 3 for U = the Baker bound of (k, a), box from rho2(U). Then the pattern has no
candidate other than the anchor with at most U digits; with Theorem U it has none at all. Proof: a candidate has
y' = L(t) mod 10^K (Lemma C); its base is a survivor deepcut enumerates, so it is one of the bases examined; its
(b,c) = v0 + z U lies in the disc of radius^2 rho2, hence z in the box; its high placement is admissible, so (z, x)
solves the system (Theorem 1 / Corollary 1.1); this contradicts Theorem 3. QED. The certificate is a one-way gate:
it can fail to certify, never wrongly certify; a pattern with a genuine solution inside the disc is never certified
(P3 below tests exactly this).

Why polynomial in q per base. Finding mu is an SVP-type problem in the lattice generated by (1, w1 alpha1, w2 alpha2,
tau-coordinates) and M w e_j, of dimension m + 3 with m = (number of types) x (D - E): one LLL, polynomial in m and the bit
length K - s. No (D+1)^q term appears. What stays exponential is the number of depth-E bases (section 4).

## 3. Existence of a certificate (HEURISTIC, with the arithmetic that predicts it)

A multiplier mu works iff roughly |r_i| Z_i <= M/(2 n') and |tau_j| <= M/(2 n') for all coordinates (n' the number of
coordinates). Heuristic count of good mu: M x prod_i (1/(n' Z_i)) x prod_G (1/n'). With M = 10^(96 (D-E)) and
Z = 10^(log10 rho - log10 |Lambda_E|), |Lambda_E| = 10^(72 + 48 (E-1)) (the shortest vector of the sub-lattice; confirmed:
log10 Z = 113.3 at E = 3 and 185.9 at E = 4 for log10 U = 281.51 and 402.12):

    slack = log10 M - 2 log10 Z - (g + 2) log10(g + 2)     (g = number of position groups)

At D = 2E: log10 M = 96 E and log10 Z = log10 rho - 24 - 48 E, so slack = 192 E + 48 - 2 log10 rho - (g + 2) log10(g + 2).
The count is conservative: the one-sided group hulls and the L1 shape of
the body make a certificate appear down to slack of about -50 (grid in NOTES.md: found at -49.5 in 62 coordinates, not found
at -102 or below). It is a prediction, tested in NOTES.md, not a theorem.

Theorem 5 (incremental lift; PROVEN-ON-PAPER, checked on 144 children). Theorem 1 applied with a fixed filling x refines a
depth-e coset to depth e+1 (K = 96 (e+1) <= 2 (96 e) - a, i.e. e >= 2, or e = 1 when a = 0) by solving ONE congruence
alpha1 z1 + alpha2 z2 = beta mod 10^96 in two integer unknowns (Coset.intersect), with no discrete logarithm. The result is
the same coset as cut_coset (equality of the cosets is the content of the theorem; n1full.py liftcheck found 144 of 144 equal).
The depth-e bases of the Tier-C pattern are therefore generated in about 8 ms each instead of 1.2 to 2.6 s.

## 4. Cost of the whole procedure (PROVEN-ON-PAPER as counting, HEURISTIC as a time estimate)

cost = N_E x t_LLL(m + 3, K - s) where N_E is the number of depth-E bases (a product of per-block filling counts,
computed exactly by a class-wise dynamic program in n1tier.count_blocks, and verified against the C-port survivor
counts on the 43 patterns). t_LLL is polynomial. Compared with (D+1)^q-type enumeration (N_D), the exponent is cut
from D blocks to E = ceil(D/2) blocks (+1 when a > 0 and D is even). It is not polynomial in q.
