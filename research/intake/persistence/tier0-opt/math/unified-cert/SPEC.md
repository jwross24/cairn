# Unified sandwich certificate: statement, two methods, and the independence contract

Calibration (RULE 2): a node certified by this package is "closed by the sandwich (U'')" at most. Every claim is
conditional on Lemma C (DEEPCUT.md), on the Baker ceiling U'' (Matveev, Yu 2007 Theorem II, `cport/NOTES-u2.md`), on the
representation list, and on the binomial lemma of section 3. Nothing here is Lean-checked, so nothing is PROVEN.

Code: `unified.py` (CLI), `ucert/` (package). Logs: `logs/*.jsonl`. Oracle copies: `oracle-u2/`, `oracle-uprime/`.

## 1. Objects

Fix an anchor y = 2^a 3^b 7^c with its coset C0 = (b, c) + L96 in Z^2, and one representation (nu, De) of its pattern,
De a list of special digits (d, e), e in [0, 96). Lemma C: every candidate y' != y has at least 10^27 digits, so for every
K = 96 D its lowest K digits are y' = L(W) (mod 10^K), where W places each special digit at one copy t (position
e + 96 t, positions pairwise distinct) or leaves it beyond K, and L(W) = R_K + sum over W of (d - 1) 10^(e + 96 t),
R_n = (10^n - 1)/9.

**Node.** A node is the data

    nu = (a, E, Y, C, R, D, N2)

- a: the 2-exponent, E >= 1 the depth of the node, s = 96 E;
- Y = R_s + sum over placed digits of (d - 1) 10^pos, the known tail (placements at copies t < E), with 5 not dividing Y and v2(Y) = a;
- C = { (b, c) in C0 : 2^a 3^b 7^c = Y (mod 10^s) }, a coset v0 + Z u1 + Z u2 (so g(u_i) = 3^(u_i[0]) 7^(u_i[1]) satisfies
  g(u_i) = 1 mod 2^(s-a) and mod 5^s);
- R: the multiset of special digits not yet placed;
- D >= E with K = 96 D <= 2 s - a (the exactness range, section 3), N2 a nonnegative integer.

An **admissible placement** W of nu is a set of triples (d, e, t), E <= t < D, whose (d, e) multiset lies in R and whose
positions e + 96 t are pairwise distinct. Put

    L(W) = Y + 10^s R_(K-s) + sum over W of (d - 1) 10^(e + 96 t).

**Statement Cert(nu).** There is no (b, c) in C and no admissible W with 2^a 3^b 7^c = L(W) (mod 10^K) and b^2 + c^2 <= N2.

**How patterns reduce to nodes.** For a representation and a depth D, let E = E(D, a) be the least E with 2 * 96 E - a >= 96 D.
The depth-E survivors of the deep cut (all placements of digits at copies below E whose cut coset is nonempty) are the
nodes; their number is the node count. A representation is closed at depth D when it has no nodes (closed by the cut) or
Cert holds for every node, with N2 = rho2(U) = floor(2 U^2 10^20 / 4771212547^2). That integer satisfies: a candidate with at
most U digits has max(b, c) log10(3) <= n <= U, hence b^2 + c^2 <= 2 U^2 / log10(3)^2 < rho2(U) + 1, so b^2 + c^2 <= rho2(U).

**Theorem 0 (pattern closure).** If every representation of a pattern is closed at some depth, then the pattern has no
candidate other than its anchor with at most U digits. With the Baker ceiling U it has none at all. Proof: a candidate
lies in a depth-E node (Lemma C, its low s digits) and in an admissible W of that node (its digits at copies E..D-1), and
(b, c) lies in the disc of squared radius rho2(U). That is a violation of Cert. QED (given Lemma C and U).

## 2. Shared preprocessing

Both certifiers consume the same problem statement. These items are shared and trusted by both:

| item | where | what it is |
|---|---|---|
| anchor and L96 | `inputs/patterns-u2.jsonl`, `inputs/lam96.json` | (b, c) from the factorization of y; L96 = { (db, dc) : 3^db 7^dc = 1 mod p for every prime p dividing 10^96 - 1, p != 3 } from `deepcut.kernel_lattice` |
| representation list | `ucert/prep.py` | `deepcut.all_representations(M, y)` filtered by the recorded (nu, eps) |
| ceiling | `inputs/utable_u2.txt`, `inputs/utable_uprime.txt` | U(k, a); rho2(U) by the integer formula above |
| coset primitive | `tier0/descent.py` `cut_coset`, `tier0/lattice.py` | the exact coset of (b, c) with 2^a 3^b 7^c = Y (mod 10^m) (Pohlig-Hellman); B calls it below 12 digits |
| depth rule | `ucert/env.py` `exact_E` | E(D, a) |

Every point either certifier returns or relies on is re-verified by raw modular exponentiation (`pow(3, b, 10^K) * pow(7, c, 10^K) * 2^a`
against L(W)), which does not call `cut_coset`.

## 3. The linearization both methods rest on

**Lemma 1 (binomial).** p prime, sigma >= 1, p^sigma divides t. For every integer z, (1 + t)^z = 1 + z t (mod p^(2 sigma)).
For z >= 0 every term of index k >= 2 carries p^(k sigma) and the binomial coefficients are integers. For z < 0,
(1 + t)^(-1) = 1 - t (mod p^(2 sigma)) and (1 + t)^(-n) = (1 - t)^n = 1 - n t. Products of two factors 1 + z1 t1 and 1 + z2 t2
keep only the linear terms. QED.

**Theorem 1 (block lift; exact for K <= 2 s - a).** Let nu be a node with a < s and K <= 2 s - a, h = K - s, (b, c) = v0 + z1 u1 + z2 u2
with (v0, u1, u2) the coset of nu, y0 = 2^a 3^(v0[0]) 7^(v0[1]) mod 10^K, and t_i = g(u_i) - 1, so v2(t_i) >= s - a and v5(t_i) >= s.
For every integer z1, z2 and every admissible placement W,

    2^a 3^b 7^c = L(W) (mod 10^K)   <=>   A1 z1 + A2 z2 - sum over W of w_i = beta   (mod 10^h),

    A_i = (y0 t_i / 10^s) mod 10^h,   w_i = (d_i - 1) 10^(e_i + 96 t_i - s),   beta = ((Y + 10^s R_h - y0) mod 10^K) / 10^s mod 10^h.

Proof. 3^b 7^c = G0 g(u1)^z1 g(u2)^z2 with G0 = 3^(v0[0]) 7^(v0[1]). Lemma 1 with p = 2, sigma = s - a gives
g(u1)^z1 g(u2)^z2 = 1 + z1 t1 + z2 t2 modulo 2^(2 (s - a)), which contains 2^(K - a) because K - a <= 2 (s - a). Lemma 1 with
p = 5, sigma = s gives the same modulo 5^(2 s), which contains 5^K. Multiplying by 2^a G0 gives
2^a 3^b 7^c = y0 (1 + z1 t1 + z2 t2) modulo 10^K. Since v0 lies in C, y0 = Y (mod 10^s), and y0 t_i is divisible by 10^s
(v2 >= a + s - a, v5 >= s). Subtract y0, note that L(W) - y0 is divisible by 10^s, and divide by 10^s: the congruence modulo 10^K
becomes the stated congruence modulo 10^h with no loss. QED.

For fixed placement the solution set of the congruence in (z1, z2) is the sub-coset of C that cutting by L(W) produces
(saturation of the image of L96, codex-deep-attempt.md Theorem 3, makes every such sub-coset nonempty; Method B does not
need that fact, Method A's exact-minimum mode does).

For K > 2 s - a the same formulas read modulo the smaller prime-wise precisions are necessary conditions. Method A
supports that relaxed mode (sound and weaker); Method B asserts h <= s - a and refuses to run outside the exact range.

**Why the low half is enumerated.** Two free digits at positions p, q >= s have a second difference of the 5-adic logarithm of
valuation exactly p + q, so no congruence affine in x is exact past precision 2 s. The depth-E bases (positions below s) are
enumerated; everything above is linear.

## 4. Method A: dual multiplier (N1, `ucert/cert_dual.py`)

Per node: build the system alpha1 z1 + alpha2 z2 + sum_i om_i x_i = beta (mod M), M = 2^(h2) 5^(h5), where the 2-part and the
5-part are derived separately,

    alpha_i^(2) = G0 t_i / 2^(s-a),   om_i^(2) = - (w_i / 2^a) / 2^(s-a),   beta^(2) = - (G0 - Tbase/2^a) / 2^(s-a)
    alpha_i^(5) = G0 t_i / 5^s,       om_i^(5) = - w_i 2^(-a) / 5^s,        beta^(5) = - (G0 - Tbase 2^(-a)) / 5^s

(G0 = g(v0), Tbase = Y + 10^s R_(K-s)), then combined by the Chinese remainder theorem. The unknowns: z in the integer box
Z1 x Z2 that contains { z : ||v0 + U z||^2 <= N2 } (exact Fraction arithmetic from the node's own basis), and x in {0,1}^m,
one variable per (type (d, e), copy t in [E, D)), with at most one active variable per position group (e, t).

**Theorem A (dual-multiplier certificate).** For an integer mu put r_i = [mu alpha_i]_M, tau_j = [mu om_j]_M (centered), b = mu beta mod M,

    Fmin = sum_i min(r_i zlo_i, r_i zhi_i) + sum_G min(0, min_(j in G) tau_j),
    Fmax = sum_i max(r_i zlo_i, r_i zhi_i) + sum_G max(0, max_(j in G) tau_j).

If no integer k has Fmin <= b + k M <= Fmax, no (z, x) in the box with admissible x solves the system. Branching on a position
group (choose none or one member; the chosen omega moves to the right-hand side; the group leaves the variable list) gives
a tree whose leaves each carry a multiplier. A tree whose every leaf passes the interval test is a certificate of Cert(nu).
Proof: a solution gives F = mu(alpha z + om x) = mu beta mod M with F in [Fmin, Fmax]. QED.

Finding mu is a short-vector problem in the lattice spanned by (1, w_j a_j) and M w_j e_j (fpylll LLL, floating point, used
only to propose mu). The verdict is the exact integer interval test; no float reaches it.

Properties: succinct (one integer per leaf, checked in O(m) big-integer operations by `cert_dual.verify_record`, which also
recomputes the system and the box from the node); sound (a pattern with a genuine point in the disc is never certified);
one-way (failure to certify is not a refutation: the relaxation drops the multiplicity bound of equal digits and the integrality
structure that Method B keeps).

Nodes with no variables (D = E) are certified by the exact nearest point of C, found by Babai rounding on the reduced basis with
a plus-or-minus 2 window (`DC.nearest_norm`); the record carries the point and the verifier checks membership and the norm.

## 5. Method B: per-anchor box-constrained CVP (`ucert/cert_cvp.py`)

Per node (h = K - s <= s - a): linearize by the unit expansion modulo 10^(s+h) directly,

    y0 = 2^a 3^b0 7^c0 mod 10^(s+h),   t_i = g(u_i) - 1,   A_i = (y0 t_i mod 10^(s+h)) / 10^s mod 10^h,
    beta = ((Y + (10^(s+h) - 10^s)/9 - y0) mod 10^(s+h)) / 10^s,

with the asserted valuations v5(t_i) >= s and v2(t_i) >= s - a (the hypothesis of Lemma 1). Boolean variables: one per
(remaining digit j, position p in [s, s+h) with p = e_j mod 96), weight w = (d_j - 1) 10^(p - s). Groups: all positions of one
digit j, and all digits at one position p (groups of size 1 add no constraint). The lattice

    K = { (z, x) in Z^(2+f) : A1 z1 + A2 z2 - sum w_i x_i = 0 (mod 10^h) }

has index 10^h / gcd(10^h, A1, A2, w) in Z^(2+f), and a unimodular column reduction gives a basis and a particular solution.

**Lemma B (exact box encoding).** Let lam = isqrt(N2) + 1, G the number of groups, and embed
E(z, x) = (2 (z1 u1 + z2 u2), 2 lam x_1, ..., 2 lam x_f, 2 lam (sum over group 1 of x), ..., 2 lam (sum over group G of x)),
target tau = (-2 v0, lam, ..., lam). Then ||E(z, x) - tau||^2 = 4 ||(b, c)||^2 + lam^2 sum_i (2 x_i - 1)^2 / 1 + lam^2 sum_g (2 s_g - 1)^2,
where s_g is the group sum. For admissible x every penalty term is lam^2, so the distance squared is 4 ||(b,c)||^2 + lam^2 (f + G).
For inadmissible x some integer penalty is at least 9 lam^2, so the distance squared is at least lam^2 (f + G) + 8 lam^2, which exceeds
R^2 = 4 N2 + lam^2 (f + G) because lam^2 > N2 / 2. Hence the lattice points of E(particular + K) within R of tau are exactly the
admissible points with ||(b, c)||^2 <= N2. QED.

**Theorem B.** Cert(nu) holds iff there is no lattice point within R of tau. The decision is exact: integral LLL (Cohen 2.6.7, delta 0.99, with the
coordinate rows carried and asserted equal to the reduced vectors' preimages) followed by Schnorr-Euchner enumeration over rational
Gram-Schmidt data (`gmpy2.mpq`). A found point is an explicit counterexample to Cert(nu): it is converted to (b, c) and the
digits it claims are checked by modular exponentiation.

The B back-end is therefore exact in both directions; the verdict "not certified" always arrives with a point (or the
enumeration reports it hit its node cap, which is reported as such). Method A can answer "not certified" with no point.

**Record and verifier.** The record carries the reduced basis, the carried coordinates, the particular solution, lam, R^2 and the target.
`verify_record` recomputes the coefficients from the node, checks every basis row against the congruence, checks that the
embedding of the carried rows equals the recorded vectors, checks |det(basis)| equals the lattice index (so the rows span the whole
congruence lattice), checks the particular solution, and replays the exact enumeration at R^2 expecting no point. The
check is a replay, not a succinct proof.

Nodes with no variables use the exact nearest point of C found by an LLL-reduced basis, four rounding candidates and exact
enumeration at that radius (`nearest2d`).

## 6. Where the methods share and diverge, and the independence contract

Shared preprocessing: section 2, and the lemma of section 3 (Lemma 1 and the equivalence of Theorem 1).

Diverging steps (each is a separate implementation, no common code):

| step | A (dual) | B (cvp) |
|---|---|---|
| depth-E node enumeration | block-wise deep cut: choose a copy-(E'-1) placement for every free digit set, cut once per 96 digits (`cert_dual.expand_nodes`) | digit-ordered depth-first search over positions, one cut at every branching position, equal digits merged, linear extension from 12 digits up (`cert_cvp.expand_nodes`) |
| coefficient derivation | per prime (2^h2 and 5^h5), combined by CRT | modulo 10^(s+h) directly from y0 t_i / 10^s |
| search space | dual multiplier mu in Z_M, interval test | primal lattice points of Z^(2+f) with penalty embedding |
| z domain | explicit box from the disc (Fractions) | none: the radius R bounds z through the lattice |
| multiplicity constraint | position groups only; equal digits are one type | digit groups and position groups |
| reduction | fpylll LLL (floating point, proposal only) | exact integral LLL in gmpy2 |
| decision | exact interval arithmetic | exact rational enumeration |
| nodes without variables | Babai plus-or-minus 2 (`DC.nearest_norm`) | exact enumeration (`nearest2d`) |
| exact minimum | shrinking-radius enumeration, float-guided, every leaf re-verified exactly | shrinking radius, rational |

**What an independent second certifier must not share with the first.** (i) The linear system: a second certifier that reads
alpha, omega, beta from the first inherits any error in them. (ii) The node enumeration: sharing the survivor list hides a lost or
spurious node in both. (iii) The reduction and enumeration code. (iv) The nearest-point routine on variable-free nodes.
(v) The box or radius derivation. This package separates all five. `run.py` stores a canonical digest of every node
(tail, remaining digits, Hermite normal form of the coset), and the two back-ends' digest lists are compared row by row.

**What both still trust (stated limits).** Lemma C and the representation list; L96; cut_coset (B calls it only for the first
11 digits and A at every block, each result is cross-checked by the other and by raw exponentiation of returned points);
Lemma 1 itself, whose consequence (the linear equation holds for every genuine point) is audited by `planted.py` against
sub-coset points computed by `cut_coset` (see the validation record).

## 7. Validation record

Command form: `PYTHONDONTWRITEBYTECODE=1 nice -n 10 uv run --no-project --with gmpy2 --with fpylll --with cysignals --with sympy python -I -u unified.py <run|compare|planted|tierc> ...` (`rt.sh`). Inputs: `inputs/patterns-u2.jsonl` (md5 1b704973), 43 patterns, 88 representations, rebuilt from the frozen snapshot behind `SANDWICH-full-U2.txt`; oracles: the C port's per-representation rows (`oracle-u2/cport-sandwich-u2.tsv`, 100 rows, utable_u2) and the earlier U' run (`oracle-uprime/`, 186 rows, depths 2 to 4).

**43 patterns under the U'' ceiling** (`logs/u2-dual-r2.jsonl`, `logs/u2-cvp-r2.jsonl`, `logs/compare-u2.json`). Each back-end ran with its own node enumeration, depth by depth to its first closing depth, with exact-minimum mode and the replay verifier on every certificate.

| quantity | Method A (dual) | Method B (cvp) |
|---|---|---|
| (representation, depth) rows with the oracle's status (open / CLOSED-sandwich / CLOSED-cut) | 100 / 100 | 100 / 100 |
| exact minimum squared norm equal to the C port's integer | 59 / 59 | 59 / 59 |
| labeled sub-coset count equal to the C port's | 59 / 59 | not computed (equal digits are merged) |
| patterns whose depth, sub-coset count and 2-decimal min-bound equal `SANDWICH-full-U2.txt` | 43 / 43 | 43 / 43 (depth, min-bound) |
| node certificates accepted by the replay verifier | 80 / 80 | 80 / 80 |
| node-set digests equal between A and B | 100 / 100 rows | 100 / 100 rows |

Of the 80 node certificates only 8 use the linear system (the a = 0 depth-2 nodes); 72 are variable-free nodes decided by the exact
nearest point. Under U'' the lattice machinery is therefore lightly exercised; the U' run below exercises it on several hundred more node problems (211 lattice-system records for k <= 9, 304 more for k >= 10 under Method B).

**Same 43 patterns under the earlier U' ceiling**, which closes at depths 2 to 4 (`logs/uprime-dual-all.jsonl`, `logs/uprime-cvp-all.jsonl`, `logs/compare-uprime.json`): 186 / 186 rows with the oracle's status for each back-end, 395 / 395 node certificates verified,
exact minimum equal to the oracle's integer on 134 / 134 rows (A) and 142 / 142 rows (B), labeled counts equal on 145 / 145 rows (A), A and B node digests equal on 186 / 186 rows. Method A's minimum mode was run at depths up to 3.
A re-run of Method A at depths up to 3 after its verifier was strengthened (`logs/uprime-dual-v2.jsonl`) verified 154 dual, 9 variable-free-with-digits-placed and 2 nearest certificates; its six reported mismatches are the three patterns that need depth 4 and were not run to depth 4.

**Disagreements between the back-ends or with an oracle: none.**

**Planted negatives** (`logs/planted.jsonl`, `logs/planted-genuine.jsonl`, `logs/tierc-planted.jsonl`):

- 68 planted sub-coset points (random admissible words and the empty word on 12 representation/depth pairs, radius = the word's exact nearest norm, computed by `cut_coset`, point re-verified by raw exponentiation): refused 68 / 68 by A, 68 / 68 by B; B returned a point inside the ball 68 / 68. Linear-system audit: the planted point satisfies A's congruence 68 / 68 and B's 68 / 68.
- 19 nodes at radius = the exact minimum over the union: refused 19 / 19 by both; the two minima equal 19 / 19. At radius = minimum - 1: B certifies 19 / 19, A certifies 3 / 19 (A is a one-way certificate; the branch cap was 60 nodes in this test).
- 18 genuine S-units 2^a 3^b 7^c (a up to 9, b about 900 to 1500, c about 500 to 900, 83 to 92 undetermined digits, depths 2 and 3, arbitrary digits including zeros) placed in the box at their own norm: refused 18 / 18 by both; B returned the point 18 / 18.
- k = 31 scale (E = 3, D = 5, K = 480): 8 planted words refused 8 / 8 by both.
- Mutants (`tests/mutants.py`, `logs/mutants3.out`): unmutated suite fails 0; an off-by-one interval test, a narrowed z box, ignored group terms (A) and a first-candidate-only enumerator, a quartered radius, a lattice missing the modulus row (B) are each refused by the suite (32, 22, 9, 4, 21, 39 failing checks). Before the exact-enumeration check was added to the suite, the first-candidate-only mutant was not caught (`logs/mutants2.out`).
- Tamper refusals (`tests/test_ucert.py`, 5 / 5 pass): a changed multiplier, a changed embedded vector, a changed basis row and a larger claimed radius are each rejected by the verifiers.

**Not run.** Method A with relaxed moduli (E below the exact range); depth 4 for the k = 10 and 11 patterns in exact-minimum mode for Method A (certification statuses were run); nothing was run in C; no Lean.
