# Archimedean (LLL / Baker–Davenport) height bound for the 4 surviving level-96 patterns

*2026-10-20, scout `lll`. Code: `/home/claude/scouts/lll/lll_bound.py` (exact-integer LLL via sympy's
`DomainMatrix.lll`, re-verified exactly; exact closest-vector enumeration; mpmath at 800 digits).
Logs: `run-D1.log`, `run-D2.log`; machine-readable: `results-D1.json`, `results-D2.json`.
Input: `survivors.json` (the 4 patterns with `closed_at_96 = false`; the fifth is closed and ignored).
Calibration: the lemma used is elementary and is proved below; every numerical step is exact
(integers / Fractions) except the logarithms, which are computed at 800 digits and whose error is
absorbed into the rounding allowance. No blind re-implementation yet.*

## 0. Setting and notation

Base 10, y′ = 2^a 3^{b′} 7^{c′}. A pattern is (a, ν, {(d_j, e_j)}_{j=1..k}) with a lattice coset
(b′, c′) ∈ (b, c) + Λ_96, Λ_96 = Z u1 + Z u2 (basis from the json, λ_1(Λ_96) = 7.8502·10^27 by exact
Gauss reduction, det = 2.8100·10^56). A **candidate** is an integer y′ in the coset with n digits,
n ≡ ν (mod 96), whose digits are all 1 except the listed digits d_j at pairwise distinct positions
E_j ≡ e_j (mod 96), 0 ≤ E_j < n (positions counted from the right, 0-indexed). Write

    (b′, c′) = (b, c) + x·u1 + y·u2  (x, y ∈ Z, unique),   n = ν + 96 m  (m ∈ Z).

| pattern (s, M) | a | anchor y | (b, c) | ν | (d_j, e_j) | k |
|---|---|---|---|---|---|---|
| 14336, 227888 | 0 | 78121827 = 3^13·7^2 | (13, 2) | 7 | (7,0) (2,1) (8,2) (2,4) (8,6) (8,7) | 6 |
| 28672, 2227888 | 0 | 78121827 | (13, 2) | 6 | (7,0) (2,1) (8,2) (2,4) (2,6) (8,6) (8,7) | 7 |
| 28672, 2244788 | 0 | 78121827 | (13, 2) | 8 | (7,0) (2,1) (8,2) (2,4) (8,6) (4,7) (4,7) | 7 |
| 42336, 22334677 | 1 | 3281116734 = 2·3^14·7^3 | (14, 3) | 10 | (4,0) (3,1) (7,2) (6,3) (2,7) (7,7) (2,8) (3,9) | 8 |

(The improper feature is a digit above the top in the first two — e_max = 7 ≥ ν — and a repeated
position 7 in the last two.)

## 1. The leading-ones inequality, stated precisely (and a correction)

For a candidate put g_j := n − 1 − E_j ≥ 0 (depth of the j-th listed digit below the top digit).
From n ≡ ν and E_j ≡ e_j (mod 96),

    g_j ≡ ν − 1 − e_j (mod 96);   write r_j := (ν − 1 − e_j) mod 96 ∈ [0, 95],  g_j = r_j + 96 t_j,  t_j ∈ Z≥0.   (1)

For a digit with e_j ≥ ν (and e_j − ν ≤ 94) this gives r_j = 95 − (e_j − ν), i.e. **that** digit sits at
least 95 − (e_j − ν) places below the top — this is the inequality in the task statement, and it is
correct *for the digit with e_j ≥ ν*. But the number of leading 1s of the candidate is min_j g_j, and
digits with e_j < ν have r_j = ν − 1 − e_j, which is small:

| pattern | r_j for the listed digits (same order as above) | min_j r_j | task's W = 95 − (e_max − ν) |
|---|---|---|---|
| 14336 | 6, 5, 4, 2, 0, 95 | **0** | 95 |
| 28672 / 2227888 | 5, 4, 3, 1, 95, 95, 94 | **1** | 94 |
| 28672 / 2244788 | 7, 6, 5, 3, 1, 0, 0 | **0** | 96 |
| 42336 | 9, 8, 7, 6, 2, 2, 1, 0 | **0** | 96 |

So the claim "the candidate begins with W = 95 − (e_max − ν) leading 1s" is **false as stated**: in
pattern 14336 the digit (8, 6) may sit at E = n − 1 (n − 1 ≡ 6 since n ≡ 7), and the candidate
n = 7 + 96m digits with E = n−1 (8), n−3 (2), n−5 (8), n−6 (2), n−7 (7), n−96 (8) starts with
8121827 11…1 8 … — the anchor's digits "wrapped" with the top 7 pushed down a period. The
unconditional guarantee is only min_j r_j ∈ {0, 1} leading 1s. What is true, and what the reduction
below uses, is the case-split version, which is in fact stronger (W_eff = 96·D for every pattern):

**Lemma A (top-window cases).** Fix D ≥ 1. For a candidate define its case τ = (t_j if t_j < D,
else "≥ D")_j, so the placed digits (t_j < D) have (r_j, t_j) pairwise distinct (positions are
distinct). Then, with θ_τ := Σ_{t_j < D} 9 (d_j − 1) 10^{−1 − r_j − 96 t_j} (an explicit rational that
depends only on τ) and ε_τ^+ := Σ_{t_j ≥ D} 9 (d_j − 1) 10^{−1 − r_j − 96 D},

    9 y′ / 10^n = 1 + θ_τ + ε,     −10^{−n} ≤ ε ≤ ε_τ^+ .                                   (2)

*Proof.* 9y′ = 9R_n + 9Σ(d_j − 1)10^{E_j} = 10^n − 1 + Σ 9(d_j−1)10^{n−1−g_j}; divide by 10^n and
split the sum according to t_j < D or t_j ≥ D (for t_j ≥ D, 10^{−1−g_j} ≤ 10^{−1−r_j−96D}). ∎

The candidate's top 96D digits are thus one of finitely many explicit blocks (the "1 + θ_τ" block),
and it agrees with that block to 96D places: this is the sense in which every candidate has
"W = 96D leading known digits". The number of cases is Π over residue classes of the admissible
t-assignments: D = 1: 64, 96, 96, 192; D = 2: 729, 1701, 1701, 5103.

**Lemma B (the linear form).** Let n ≥ 96D + 11 (every candidate has n ≥ 2.6·10^27: any coset point
other than (b, c) has max(b′, c′) ≥ λ_1/√2 − 14 = 5.55·10^27, and (b, c) itself is not a candidate —
for 14336/2227888 its 8 digits are ≢ ν, for 2244788 and 42336 it would need two distinct positions
≡ 7 below n = ν; independently of the lattice, n ≥ 97 for every candidate of an improper pattern,
since n ≤ 96 forces E_j = e_j and n = ν, contradicting e_j ≥ ν or a repeated e_j). Then

    Λ_τ := a log 2 + b′ log 3 + c′ log 7 + log 9 − n log 10 − log(1 + θ_τ)  satisfies  |Λ_τ| ≤ δ_τ := 2(ε_τ^+ + 10^{−(96D+10)}).

*Proof.* Λ_τ = log(1 + ε/(1+θ_τ)); |ε| ≤ ε_τ^+ + 10^{−n} ≤ 1/2 and |log(1+t)| ≤ 2|t| for |t| ≤ 1/2. ∎

Dividing by 96 log 10 and substituting (b′, c′) = (b, c) + x u1 + y u2, n = ν + 96 m:

    Λ′_τ = β_τ + α_1 x + α_2 y − m,    |Λ′_τ| < δ′_τ := δ_τ / (96 log 10)  (a rational upper bound is used),
    α_1 = (u11 log 3 + u12 log 7)/(96 log 10),  α_2 = (u21 log 3 + u22 log 7)/(96 log 10),
    β_τ = (a log 2 + b log 3 + c log 7 + log 9 − ν log 10 − log(1 + θ_τ))/(96 log 10).

m is the "integer variable" of the Baker–Davenport setting: it needs no bound.

## 2. The lemma used

**Lemma C (inhomogeneous LLL reduction; de Weger, *Algorithms for Diophantine equations*, CWI Tract
65, 1989, Lemma 3.5, in the form of Bugeaud–Mignotte–Siksek, Ann. Math. 163 (2006), §5 — stated here
with the exact lattice distance, which is what the code computes; de Weger's printed lower bound is
the corollary (ii)).** Let α_1, α_2, β ∈ R, δ′ > 0, X_1, X_2 ≥ 1, C ∈ Z_{>0}, and let A_i, B_0 be
integers with |A_i − Cα_i| ≤ ρ, |B_0 − Cβ| ≤ ρ. Let L ⊂ Z³ be the lattice with basis
b_1 = (1, 0, A_1), b_2 = (0, 1, A_2), b_3 = (0, 0, C) and w = (0, 0, −B_0). Put

    Q := X_1² + X_2² + (C δ′ + (X_1 + X_2 + 1) ρ)².

(i) If (x, y, m) ∈ Z³ satisfies |x| ≤ X_1, |y| ≤ X_2 and |β + α_1 x + α_2 y − m| < δ′, then
v := x b_1 + y b_2 − m b_3 ∈ L has |v − w|² ≤ Q. Hence **if dist(w, L)² > Q there is no such (x, y, m).**
(ii) If c_1, c_2, c_3 is an LLL-reduced basis of L (δ = 3/4), w = Σ s_i c_i with s_i ∈ Q, and i_0 is the
largest index with s_{i_0} ∉ Z, then dist(w, L)² ≥ min(‖s_{i_0}‖² |c_{i_0}*|², min_{i>i_0} |c_i*|²)
≥ 2^{−2} ‖s_{i_0}‖² |c_1|², where ‖·‖ is the distance to the nearest integer and c_i* the
Gram–Schmidt vectors. (If w ∈ L the bound is void.)

*Proof.* (i) v − w = (x, y, xA_1 + yA_2 − mC + B_0) and the last coordinate equals
C(β + α_1x + α_2y − m) + x(A_1 − Cα_1) + y(A_2 − Cα_2) + (B_0 − Cβ), of absolute value
≤ Cδ′ + (|x| + |y| + 1)ρ. (ii) For any t ∈ Z³ let i_1 be the largest index with t_{i_1} ≠ s_{i_1}
(i_1 ≥ i_0 exists); the Gram–Schmidt coefficient of c_{i_1}* in Σ(t_i − s_i)c_i is t_{i_1} − s_{i_1},
which is a nonzero integer if i_1 > i_0 and has absolute value ≥ ‖s_{i_0}‖ if i_1 = i_0; LLL with
δ = 3/4 gives |c_i*|² ≥ 2^{−(i−1)}|c_1|². ∎

Implementation (`lll_bound.py`): ρ = 1/2 + 10^{−100} (nearest-integer rounding of 800-digit values of
Cα_i, Cβ with C ≤ 10^{320}; the rounded integers were checked to be identical at 1100 digits);
LLL by `sympy.polys.matrices.DomainMatrix.lll(delta=3/4)`, then **exactly verified**: size-reduced,
Lovász with δ = 3/4, and unimodular w.r.t. the input basis (all in `Fraction` arithmetic);
dist(w, L) computed **exactly** by Schnorr–Euchner enumeration on the reduced basis (starting radius =
Babai's nearest-plane vector; all arithmetic in `Fraction`, enumeration ranges with a safe mpmath
margin), and asserted ≥ the de Weger bound (ii). The comparison dist² > Q is exact (δ′ is replaced by a
rational upper bound). For each case the code tries C = (κX)³, κ ∈ {10, 5, 20, 3, 7, 14}, and X on
the grid 10^{j/2}; the search goes up until three consecutive half-decades fail, then takes the last
success; later cases start from the running minimum and only move it down. Since "dist² > Q at X"
implies the conclusion for every smaller X, the running minimum X_min is certified for every case
(the *test* is not monotone in X for fixed C — a lattice point that is unusually close at one C can
spoil a single X — but the *conclusion* is).

**Conversion to a height bound.** If no candidate has |x|, |y| ≤ X, every candidate has
max(|x|, |y|) ≥ X + 1. With U = [u1 u2] (columns), (x, y)ᵀ = U^{−1}(b′ − b, c′ − c)ᵀ, so
max(|x|,|y|) ≤ ‖U^{−1}‖_∞ · ‖(b′−b, c′−c)‖_∞, where ‖U^{−1}‖_∞ = max row sum of adj(U)/|det U|
= 1.8012·10^{−28} (exact rational in the code). Since b′, c′ ≥ 0,

    max(b′, c′) = ‖(b′, c′)‖_∞ ≥ (X + 1)/‖U^{−1}‖_∞ − max(b, c) =: B_cert,    n ≥ 1 + B_cert · log_10 3.

(Note: the task's "(b′, c′) is within X(|u1| + |u2|) of (b, c)" is the upper-bound direction; the lower
bound needs ‖U^{−1}‖, as above. Also no bound on m is needed, which is why the reduction reaches
X ≈ δ′^{−1/2} rather than δ′^{−1/3}.)

## 3. Results

### D = 1 (top 96 digits; `run-D1.log`)

| pattern | cases | X certified (all cases) | search stopped at | worst case τ (t_j; "–" = below window), δ′_τ | **B_cert = min max(b′,c′)** | digits ≥ |
|---|---|---|---|---|---|---|
| 14336 | 64 | 10^47 | 10^47.5 | (0,0,–,–,–,0), 5.71·10^{−98} | **5.552·10^74** | 2.65·10^74 |
| 28672 / 2227888 | 96 | 10^48 | 10^48.5 | (0,0,–,–,0,–,0), 8.71·10^{−100} | **5.552·10^75** | 2.65·10^75 |
| 28672 / 2244788 | 96 | 10^47 | 10^47.5 | (0,0,–,0,0,0,–), 2.44·10^{−98} | **5.552·10^74** | 2.65·10^74 |
| 42336 | 192 | 10^46.5 | 10^47 | (0,0,–,–,0,–,–,–), 1.76·10^{−98} | **1.756·10^74** | 8.38·10^73 |

Run time ≈ 50 s for the four patterns (single core). Between 60 % and 80 % of the cases are already
certified by de Weger's printed bound (ii); the rest need the exact distance (‖s_{i_0}‖ happens to be
small, or an unusually close lattice point at that C — e.g. pattern 14336, τ = (–,0,–,0,–,0),
X = 10^{20.5}: a point with |x|,|y| ≈ 3·10^20 and |Λ′| ≈ 10^{−44}, 100× closer than generic; it is not a
solution and the reduction recovers from X = 10^21 on).

### D = 2 (top 192 digits; `run-D2.log`)

| pattern | cases | X certified (all cases) | search stopped at | worst case τ, δ′_τ | **B_cert = min max(b′,c′)** | digits ≥ |
|---|---|---|---|---|---|---|
| 14336 | 729 | 10^94.5 | 10^95 | (0,1,1,–,–,0), 5.71·10^{−194} | **1.756·10^122** | 8.38·10^121 |
| 28672 / 2227888 | 1701 | 10^94 | 10^94.5 | (0,–,0,–,0,1,–), 8.15·10^{−196} | **5.552·10^121** | 2.65·10^121 |
| 28672 / 2244788 | 1701 | 10^94.5 | 10^95 | (0,1,0,–,1,–,–), 4.89·10^{−194} | **1.756·10^122** | 8.38·10^121 |
| 42336 | 5103 | 10^94 | 10^94.5 | (1,0,0,–,1,0,1,–), 1.63·10^{−194} | **5.552·10^121** | 2.65·10^121 |

Run time ≈ 15 min (single core, 2-core machine shared with another job; C up to ≈ 10^{290}).
A first D = 2 run with a cruder search (lower X on the first failure, no retry at larger X) gave
10^{93.5}, 10^{93}, 10^{94.5}, 10^{85.5}: a failure at one X is usually a single unusually close lattice
point at that scale (≈ 0.1–1 % of the cases at each X), which a larger X cures; the retry at up to
four larger half-decades recovers the natural limit X ≈ 0.03·δ′^{−1/2} ≈ 10^{95}.

### Comparison with the other bounds

For every pattern the certified statement is: *no candidate y′ ≠ y with max(b′, c′) < B_cert*, i.e.
every impersonator has at least B_cert·log_10 3 digits.

| source of the bound | max(b′, c′) ≥ | digits ≥ |
|---|---|---|
| Λ_96 alone (λ_1/√2 − 14) | 5.55·10^27 | 2.65·10^27 |
| depth-1 10-adic cut (`bound_digits_after_cut` in the json = 2.08·10^72; the task text quotes it as ~10^66) | — | 2.08·10^72 |
| this note, D = 1 (W_eff = 96) | 1.8·10^74 – 5.6·10^75 | 0.8·10^74 – 2.6·10^75 |
| this note, D = 2 (W_eff = 192) | 5.6·10^121 – 1.8·10^122 | 2.6·10^121 – 8.4·10^121 |

The archimedean bound at D = 1 is roughly the depth-1 10-adic bound times 10²–10³; each further
96-digit window multiplies it by ≈ 10^48 (X ∝ δ′^{−1/2}), at a cost of ×(D+1)/D per digit in the
number of cases (4^6 = 4096 cases for 14336 at D = 3, 5^6·13 ≈ 2·10^5 for 42336 at D = 4). The two
constraints are independent and would multiply: with the 10-adic sub-coset basis in place of Λ_96
(depth 1: λ_1 ≈ 10^{72}; depth 2: λ_1 ≈ 10^{120.6} per DEEPCUT.md — neither basis is in the json, not
attempted), the conversion factor 1/‖U^{−1}‖_∞ would be ≈ 10^{72} resp. 10^{120} instead of 5.6·10^27,
giving ≈ 10^{119} resp. 10^{167} at D = 1 and ≈ 10^{167} resp. 10^{215} at D = 2 from the same reductions.

## 4. Sanity control (genuine S-unit; `run-D1.log`, section CONTROL)

y″ = 2^3·3^401·7^141, n = 312 digits, ν = n mod 96 = 24, 282 non-1 digits (so "W" in the task's
sense is 0: the leading digit is not 1). Its own pattern is {(digit, position mod 96)} over all non-1
digits; with D = 1 the actual positions give the case τ: 89 digits in the top 96 positions (t_j = 0),
193 below. To exercise x, y ≠ 0, a fake small lattice u1 = (5, 3), u2 = (2, −7) and anchor
(b, c) = (397, 114) were used, so (x, y, m) = (2, −3, 3) (the inequality chain does not depend on the
lattice). Numbers:

- (2): ε = 9y″/10^n − 1 − θ_τ = 2.391097·10^{−96}, ε_τ^+ = 8.274421·10^{−96}; −10^{−n} ≤ ε ≤ ε_τ^+ ✓.
- Lemma B: |Λ_τ| = 1.0884735·10^{−96} ≤ 2|ε| = 4.7821933·10^{−96} ✓.
- Λ′ = β_τ + α_1·2 + α_2·(−3) − 3 = 4.9241461·10^{−99} = Λ_τ/(96 log 10) (agree to 10^{−700}) ✓; δ′_τ = 7.487·10^{−98}; |Λ′| < δ′ ✓.
- Lemma C(i) at X = 3, C = (κ·3)³ for κ = 3, 5, 10, 30: |v − w|² = 13, 14, 14, 13 ≤ Q = 30.25 ✓, and the
  reduction correctly **refuses** to certify (exact dist² = 4.9, 7.0, 8.8, 0.13 ≤ Q) — a genuine
  solution is never excluded.
- Negative control: the same data with θ_τ perturbed by 9·10^{−6} (a different top block, so y″ is no
  longer a solution): the reduction certifies "no solution with |x|,|y| ≤ 10^6" ✓.

(Also, in DEEPCUT's spirit: the candidate's top-96-digit block 1 + θ_τ recovers y″'s top 96 digits
exactly — that is what (2) says.)

## 5. What this does and does not achieve

This is a **height bound, not a closure**. For each of the four patterns it is now certified that any
impersonator y′ = 2^a 3^{b′} 7^{c′} ≠ y realizing the pattern has max(b′, c′) ≥ B_cert (≈ 10^{75} at
D = 1, ≈ 10^{122} at D = 2), i.e. astronomically many digits — but the method is a fixed-precision
archimedean statement (the candidate's top 96D digits are known), and no amount of lattice reduction
can turn "|Λ| < 10^{−96D}" into an upper bound: Baker-type lower bounds |Λ| > B^{−K} only say
B > 10^{96D/K}, which is trivial. What the LLL step gains per window (×10^48) it pays in cases
(×(D+1)/D per digit), so pushing D up is cheap for a few more windows and then exponential.

Caveats on what *is* certified: the arithmetic rests on (a) the coset statement
(b′, c′) ∈ (b, c) + Λ_96 with the json basis (taken as input), (b) mpmath's logarithms being correct to
far better than 10^{−400} (checked by recomputation at 1100 digits), (c) sympy's LLL output, which is
independently verified to be a reduced basis of the same lattice, and (d) my own enumeration code for
the exact distance, which is cross-checked against de Weger's lower bound in every call and against the
genuine-solution control. There is no Lean and no second implementation.

## 6. Not certified: why the archimedean side may nevertheless close these patterns

The parent's framing ("a height bound, not a closure") is the honest status of what is proved above.
But the candidate also satisfies the (k+3)-term S-unit identity

    10^n − 9·2^a 3^{b′} 7^{c′} = 1 − Σ_j 9(d_j − 1)·10^{E_j},

i.e. 9y′ + 1 has only k + 1 "nonzero digits" (coefficients 9(d_j−1) ∈ [9, 72]) in base 10, with k ≤ 8 fixed.
For *that* kind of statement Baker's method is effective (this is the iterated-gap argument behind
Stewart's and Bugeaud's results on integers with few nonzero digits and bounded prime factors), and
the resulting *upper* bound looks small enough to be beaten by the LLL *lower* bound above. Sketch,
for a = 0 (9y′ = 3^{b′+2} 7^{c′}), with E_(1) > E_(2) > … > E_(k) the listed positions in decreasing order
and N_j := 10^{n−E_(j)} + Σ_{i≤j} 9(d_(i)−1) 10^{E_(i)−E_(j)} (integers, log N_j ≤ (n − E_(j)) log 10 + log(1+7.2k)):

- step 1: |3^{b′+2} 7^{c′} 10^{−n} − 1| ≤ 1.2·72k·10^{−(n−E_(1))}; Matveev (3 logs, D = 1,
  A = log 3, log 7, log 10, ΠA = 4.922, C(3) = 1.4·30^6·3^{4.5} = 1.43·10^{11}) gives
  (n − E_(1)) ≤ G_1 := C(3)·4.922·(1 + log B)/log 10 + O(1) ≈ 7.9·10^{13} (log B ≈ 258 for B ≈ 10^{112});
- step j ≥ 2: |3^{b′+2} 7^{c′} 10^{−E_(j−1)} N_{j−1}^{−1} − 1| ≤ 1.2·72k·10^{−(E_(j−1)−E_(j))}/N_{j−1}, nonzero
  since 5 ∤ 9y′ and E_(j−1) ≥ 1; Matveev with 4 logs (C(4) = 1.4·30^7·4^{4.5} = 1.57·10^{13},
  A_N = log N_{j−1} ≤ 2.31·Σ_{i<j} G_i) gives E_(j−1) − E_(j) ≤ G_j := C(4)·4.922·(1 + log B)·Σ_{i<j}G_i ≈ 2.0·10^{16}·G_{j−1};
- last: 9y′ + 1 = N_k 10^{E_(k)}; if E_(k) = 0 then n ≤ log_10 N_k ≤ Σ_{j≤k} G_j, otherwise the same
  linear form with |Λ| = 1/(N_k 10^{E_(k)}) ≈ 10^{−n} gives n ≤ G_{k+1}.

Hence n ≤ G_{k+1} ≈ 7.9·10^{13}·(2.0·10^{16})^k: **≈ 5·10^{111} digits for k = 6 (pattern 14336), ≈ 10^{128}
for k = 7 (the two 28672 patterns)**; for 42336 (a = 1, one more log, k = 8: C(4) and C(5) = 1.28·10^{15},
ΠA = 3.4) the same chain gives ≈ 10^{161}. Compare the certified lower bounds (digits): 8.4·10^{121} (14336, D = 2),
2.6·10^{121} and 8.4·10^{121} (28672, D = 2), 2.6·10^{121} (42336, D = 2), and ≈ 10^{170} at D = 3 for every pattern (4^6 = 4096 cases
for 14336 — minutes; 13312 for each 28672 pattern — about an hour each; 53248 for 42336 — hours;
`python3 lll_bound.py 3 --idx i`). The depth-2 10-adic sub-coset would do the same job at D = 1, and the depth-1 sub-coset at D = 2 (≈ 10^{167} either way).

If the Baker chain above survives a careful write-up (Matveev's constants as in Bugeaud–Mignotte–Siksek
Thm 9.4; the only delicate points are the non-vanishing of each form, which is the 5-adic argument, and
the bookkeeping of B and of the heights of the N_j), then pattern 14336 is already **closed** by this
file's D = 2 bound with ten orders of magnitude to spare, the two 28672 patterns need D = 3, and 42336
needs D = 3 with a thin margin (10^{161} vs 10^{170}) or D = 4. I have not done the Baker side rigorously
and I report it as the next step, not as a result; nothing in sections 1–4 depends on it.

