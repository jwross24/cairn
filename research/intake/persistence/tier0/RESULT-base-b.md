# Baker chain in bases 6, 8, 9, 12 (and 10), and an exact closest-vector routine for rank ≤ 3

*2026-10-20, scout `baker`, second task. Code: `/home/claude/scouts/baker/baker_chain.py`
(`baker_upper_bound_base(b, k, bounded_exps_max)`; the base-10 API `baker_upper_bound(k, a)` and its table are
unchanged) and `/home/claude/scouts/baker/cvp_small.py` (`exact_nearest(v, U)`). Logs: `run.log` (chain),
`cvp_small.py` self-test output below. Everything is light CPU (4 s and 23 s). Same calibration as
BAKER-CHAIN.md: ordinary mathematical proof resting on Matveev's theorem (BMS Thm 9.4, quoted there), numerics
certified by interval arithmetic, nothing machine-checked.*

## 1. Setting (base b ≥ 3)

Let b ≥ 3, P := {primes p < b}, D := {p ∈ P : p | b}, F := P \ D. Let y′ be an integer with exactly n base-b
digits of the form

    y′ = R_n^{(b)} + Σ_{j=1}^{k} (d_j − 1) b^{E_j},   R_n^{(b)} = (b^n − 1)/(b − 1),   d_j ∈ {2, …, b−1},   n > E_1 > … > E_k ≥ 0,

(all digits 1 except the k digits d_j; k = 0 is the repunit), and suppose y′ = ∏_{p∈P} p^{e_p} with
e_p ≤ a_p for p ∈ D (a_p = `bounded_exps_max[p]`, the analogue of a; the exponents of p ∈ F are free).
With c_j := (b−1)(d_j − 1) ∈ [b−1, (b−1)(b−2)] and M := (b−1)y′,

    M + 1 = b^n + Σ_j c_j b^{E_j},        M = ∏_{p∈P} p^{e_p + v_p(b−1)}                                         (1.1)

(every prime factor of b−1 is < b, so M is again a P-unit). Facts used (same proofs as in base 10):
b^{n−1} ≤ y′ ≤ (b−1)R_n^{(b)} = b^n − 1 < b^n; hence e_p < n log b/log p for p ∈ F, and
e_p + v_p(b−1) < (n log b + log(b−1))/log 2 for every p ∈ P.

Gaps g₀ = n − E₁ ≥ 1, g_j = E_j − E_{j+1} ≥ 1, and N_j := b^{n−E_j} + Σ_{i≤j} c_i b^{E_i−E_j} (1 ≤ j ≤ k), so that
M + 1 = N_j b^{E_j} + Σ_{i>j} c_i b^{E_i} and

    b^{n−E_j} ≤ N_j ≤ b^{n−E_j} + (b−2) b^{E_1+1−E_j} ≤ (b−1) b^{n−E_j}                                          (1.2)

(Σ_{i≤j} c_i b^{E_i−E_j} ≤ (b−1)(b−2) b^{E_1−E_j}·b/(b−1) = (b−2) b^{E_1−E_j+1} and E_1 ≤ n−1).

## 2. Forms, non-vanishing, size (U := (b−2)b, V := b−1)

- Λ₀ := M b^{−n} − 1 = (Σ_j c_j b^{E_j} − 1)/b^n. For k ≥ 1: numerator ≥ (b−1) − 1 ≥ 1 and ≤ (b−2) b^{E_1+1}, so
  0 < Λ₀ ≤ U·b^{−g₀}. For k = 0: Λ₀ = −b^{−n}.
- Λ_j := M b^{−E_j} N_j^{−1} − 1 = (Σ_{i>j} c_i b^{E_i} − 1)/(N_j b^{E_j}). For 1 ≤ j < k the numerator is ≥ b−2 ≥ 1
  and ≤ (b−2) b^{E_{j+1}+1}, so 0 < Λ_j ≤ U·b^{−g_j}/N_j. For j = k: Λ_k = −1/(M+1), |Λ_k| < b^{−n}.

Non-vanishing in base b: every numerator is ≡ −1 (mod b−1) (all c_i are multiples of b−1), hence ≠ 0 for
b ≥ 3 (and positivity for j < k as shown). The p-adic argument (p | b, p ∤ M) gives the same. In base 8 the
numerators are ≡ −1 (mod 7), in base 12 ≡ −1 (mod 11), etc.

## 3. Which logarithms (the count t and Matveev's B)

Matveev's theorem (BMS Thm 9.4, real case, D = 1): log|Λ| > −C(t)(1 + log B) A₁⋯A_t with
C(t) = 1.4·30^{t+3} t^{4.5} and A(α) = log α for a positive integer α ≥ 2. There is no independence hypothesis,
so both of the following are valid applications; the code evaluates both chains and takes the smaller bound.

**Option (i) — only prime logarithms.** α's = P, since b^{−n} = ∏_{p∈D} p^{−n v_p(b)}:
Λ₀ = ∏_{p∈F} p^{e_p + v_p(b−1)} · ∏_{p∈D} p^{e_p − n v_p(b)} − 1, t₀ = |P|; the inner forms add α = N_j (exponent −1),
t = |P| + 1. This is the "primitive logs with coefficient 3n on log 2" prescription for b = 8 = 2³ (and 2n on
log 3 for b = 9), and it is also what the code picks for b = 6, 10, 12, because the product of the heights
Π log p is smaller than with log b as a separate α, and t is never larger.

**Option (ii) — b as a separate α.** α's = F ∪ {b} ∪ D⁺, D⁺ := {p ∈ D : a_p ≥ 1} (for p ∈ D \ D⁺ the exponent is 0 and
the α is dropped), t₀ = |F| + 1 + |D⁺|. This is the base-10 choice of BAKER-CHAIN.md ((3, 7, 10) for a = 0,
(2, 3, 7, 10) for a ≥ 1), and it wins only when D⁺ is small (base 10 with a = 0: t₀ = 3 against 4).

**B.** In both options every |b_i| ≤ σn + τ with

    σ := log b/log 2 (rounded up to 6 decimals),   τ := log(b−1)/log 2 (rounded up) + max_{p∈D} a_p,

because for p ∈ F: 0 ≤ e_p + v_p(b−1) < (n log b + log(b−1))/log 2; for p ∈ D in option (i):
|e_p − n v_p(b)| ≤ max(a_p, n v_p(b)) ≤ n log b/log 2 + a_p; in option (ii): e_p ≤ a_p and the exponent of b is −n ≤ σn;
and the exponent of N_j is −1. σ ≥ 1 for b ≥ 2, which is what the monotonicity lemma needs (§4).

For the bases requested:

| b | P | D | option used | t₀ (top) / t (inner) | PA = Π log α | σ | τ (with a_p as below) |
|---|---|---|---|---|---|---|---|
| 6 | 2,3,5 | 2,3 (a₂,a₃ ≤ 2) | (i) α = 2,3,5 | 3 / 4 | 1.2256 | 2.584963 | 4.321929 |
| 8 | 2,3,5,7 | 2 (a₂ ≤ 2) | (i) α = 2,3,5,7 | 4 / 5 | 2.3849 | 3.000001 | 4.807356 |
| 9 | 2,3,5,7 | 3 (a₃ ≤ 2) | (i) α = 2,3,5,7 | 4 / 5 | 2.3849 | 3.169927 | 5.000001 |
| 10 | 2,3,5,7 | 2,5 (a₂ ≤ 40, a₅ = 0) | (i) for a₂ ≥ 1; (ii) α = 3,7,10 for a₂ = 0 | 4 / 5 (3 / 4) | 2.3849 (4.9225) | 3.321930 | 43.169927 |
| 12 | 2,3,5,7,11 | 2,3 (a₂,a₃ ≤ 2) | (i) α = 2,3,5,7,11 | 5 / 6 | 5.7187 | 3.584963 | 5.459433 |

(The coordinator fixed a₂ ≤ 2 for base 8 and left the bounds for bases 6 and 12 open; I used 2. The bound depends
on max a_p only through τ inside 1 + log(σn + τ), so it is insensitive: with a_p = 40 instead of 2 the k = 8
values change by < 0.001 in log₁₀ — verified for b = 6, 8, 12.)

## 4. Chain and certificate (identical in structure to BAKER-CHAIN.md §4–§5)

With T := 1 + log(σn + τ), K₀ := C(t₀)·PA·T, K₁ := C(t₀+1)·PA·T, L := log b:

    k = 0:   n L < K₀;
    k ≥ 1:   g₀ < (K₀ + log U)/L =: G₀,  S₁ := G₀,  G_j := (log U + K₁(S_j L + log V))/L,  S_{j+1} := S_j + G_j  (1 ≤ j ≤ k−1),
             n ≤ Φ(n) := K₁(S_k L + log V)/L     (if E_k ≥ 1 from Λ_k; if E_k = 0 then n = S_k ≤ Φ(n)).

Proof: as Proposition 4.1 of BAKER-CHAIN.md with 10 → b, 80 → U = (b−2)b, 9 → V = b−1, (1.3) → (1.2). The
resolution of n ≤ Φ(n) is Lemma 5.1 there, verbatim: Φ(ν) is a polynomial in T(ν) = 1 + log(σν + τ) with
non-negative coefficients, ν T′(ν) = σν/(σν + τ) < 1 and T(ν) ≥ 1 + log ν (as σ ≥ 1), so Φ(ν)/ν is strictly
decreasing on [e^k, ∞), and any integer N ≥ e^k with Φ(N) < N bounds every solution: n < N. The code finds N on a
grid, represents it exactly as m·10^e (m < 10⁷), and certifies lower(N) > upper(e^k) and upper(Φ_iv(N)) < lower(N)
in mpmath interval arithmetic at 256 bits (`_certify`). The reported value is log₁₀ N truncated to 3 decimals
(so the printed number is ≤ the certified one).

Approximate closed form (leading behaviour Φ ≈ (K₀/L)·K₁^k):

    log₁₀ G(b, k) ≈ log₁₀(C(t₀) PA / ln b) + log₁₀ T + k·(log₁₀(C(t₀+1) PA) + log₁₀ T),   T = 1 + ln(σG + τ),

with log₁₀(C(t₀)PA/ln b), log₁₀(C(t₀+1)PA) = (10.99, 13.28) for b = 6; (13.26, 15.49) for b = 8; (13.23, 15.49)
for b = 9; (13.21, 15.49) for b = 10 (a₂ ≥ 1); (15.47, 17.70) for b = 12. Per gap the admissible size multiplies by
K₁ ≈ 10^{13.28}·T ≈ 5·10¹⁵ (b = 6), ≈ 10^{15.49}·T ≈ 10^{18} (b = 8, 9, 10), ≈ 10^{17.70}·T ≈ 2·10^{20} (b = 12).

## 5. Table: log₁₀ N for N = `baker_upper_bound_base(b, k, bounded_exps_max)` (certified: n < N), k ≤ 16

Bounded exponents: b = 6: {2: 2, 3: 2}; b = 8: {2: 2}; b = 9: {3: 2}; b = 10: {2: 40, 5: 0}; b = 12: {2: 2, 3: 2}.

```
 k   b=6        b=8        b=9        b=10       b=12
 0     12.479     14.815     14.791     14.770     17.091
 1     27.918     32.514     32.490     32.470     37.056
 2     43.589     50.446     50.422     50.402     57.252
 3     59.412     68.529     68.505     68.485     77.599
 4     75.347     86.724     86.700     86.680     98.059
 5     91.372    105.009    104.985    104.964    118.607
 6    107.472    123.368    123.344    123.323    139.230
 7    123.636    141.790    141.766    141.746    159.916
 8    139.855    160.269    160.245    160.225    180.658
 9    156.125    178.797    178.773    178.753    201.449
10    172.439    197.370    197.346    197.325    222.285
11    188.793    215.983    215.959    215.938    243.161
12    205.185    234.633    234.609    234.588    264.074
13    221.611    253.317    253.293    253.273    285.021
14    238.069    272.033    272.009    271.989    306.000
15    254.557    290.779    290.755    290.735    327.009
16    271.073    309.552    309.529    309.508    348.045
```

Requested rows:

| k | b = 6 | b = 8 | b = 9 | b = 10 | b = 12 |
|---|---|---|---|---|---|
| 6 | 107.472 | 123.368 | 123.344 | 123.323 | 139.230 |
| 8 | 139.855 | 160.269 | 160.245 | 160.225 | 180.658 |
| 10 | 172.439 | 197.370 | 197.346 | 197.325 | 222.285 |
| 12 | 205.185 | 234.633 | 234.609 | 234.588 | 264.074 |
| 16 | 271.073 | 309.552 | 309.529 | 309.508 | 348.045 |

Remarks. (1) Bases 8, 9, 10 have the same four primes, hence the same t and PA; they differ only through σ, τ
and log b, i.e. negligibly. (2) For base 10 the generic function with a₂ ≥ 1 uses option (i) (α = 2, 3, 5, 7,
PA = 2.38) and is slightly *better* than the base-10 table of BAKER-CHAIN.md (α = 2, 3, 7, 10, PA = 3.41):
160.225 vs 161.654 at k = 8; with a₂ = 0 it reproduces that table (145.333 vs 145.328; the 0.005 is the cruder
σ, τ). The base-10 API and table are left as they were, since SANDWICH.md was run with them. (3) Base 12 is
costlier because of the fifth prime (t = 6 inner logs, C(6) = 8.75·10¹⁶): ≈ 10^{20.8} per gap instead of 10^{18}.
(4) Base 6 is the cheapest (three primes, t₀ = 3): ≈ 10^{15.7} per gap.

## 6. Assumptions (complete)

(A1) BMS Theorem 9.4 as printed (quoted in BAKER-CHAIN.md §2), applied with L = Q, D = 1, real case, to
forms with α's ⊂ P ∪ {b} ∪ {N_j}; no independence hypothesis is needed and exponents may be 0.
(A2) y′ has base-b digits in {1, …, b−1} only (digit 0 excluded) with exactly k digits ≠ 1, all ≥ 2; y′ is a
P-unit with e_p ≤ a_p for p | b. The bound returned for given a_p is valid for all smaller exponents too
(option (i) does not depend on D⁺; option (ii) includes every p with a_p ≥ 1 and an exponent 0 is allowed).
(A3) mpmath's interval arithmetic (`mpmath.iv`) is correct; the 60-digit floating search only locates the
candidate.
(A4) Nothing from the sweep, the lattices or the 10-adic cuts enters.

Controls (`positive_control(b, exps)` in the code, exact rational arithmetic): in each base two small
in-domain S-units (5⁴ = 625 = 2521₆, n = 4, k = 3; 7⁴ = 2401 = 4541₈, k = 3; 7⁴ = 3257₉, k = 4; 11⁴ = 14641 = 8581₁₂, k = 3) satisfy
every inequality of §2 and §4 verbatim (both parameter options), and one large S-unit per base (≈ 60–130 digits,
containing zeros, outside the domain) satisfies the absolute-value variants (identity, non-vanishing mod b−1,
|numerator| ≤ U b^{E_{j+1}} + 1, N_j ≥ 1, the Matveev inequalities with A(N_j) = max(log N_j, 0.16)).

## 7. `cvp_small.py`: exact nearest coset point in rank ≤ 3

`exact_nearest(v, U)`: v an integer vector of length m, U a list of d ≤ m linearly independent integer row
vectors (entries of any size; tested up to 700 digits). Returns `(point, z, norm2)` with point = v + Σ z_i U[i]
of minimal Euclidean norm in the coset v + ZU, z ∈ Z^d, norm2 = |point|² (exact int). Method:

1. **Exact LLL** (`lll_exact`, Fractions, δ = 3/4, textbook size-reduction + Lovász swaps, Gram–Schmidt
   recomputed exactly after every change — fine for d ≤ 3), returning the reduced basis B and the unimodular T
   with B = T·U, verified exactly.
2. **Exact Fincke–Pohst / Schnorr–Euchner enumeration** (`closest_vector`) of all x ∈ Z^d with
   |xB − t|² ≤ R², t = −v: at level i the admissible interval for x_i is |x_i − c_i| ≤ sqrt((R² − partial)/|b_i*|²)
   with c_i = τ_i − Σ_{j>i} x_j μ_{j,i}; the square root is replaced by the exact rational over-estimate
   (isqrt(pq)+1)/q ≥ sqrt(p/q), the integer range [⌈c_i − w⌉, ⌊c_i + w⌋] is enumerated from the centre outward,
   and each partial norm is compared with R² exactly. R² starts at the Babai nearest-plane distance and shrinks
   on every strict improvement. Since the per-level bounds are exact over-estimates of the true admissible
   interval, every lattice point within the final radius is visited, so the returned point is a true minimiser.
3. The result is re-verified: point = v + Σ z_i U_i recomputed exactly and |point|² = norm2.

Also provided: `babai_with_neighbours(v, U)` (Babai on the LLL basis + the 3^d neighbours; not exact in general).

Self-test (`python3 cvp_small.py`, 23 s, seed 1):

```
test 1: 300/300 random small cosets (dims 1-3, ambient dims up to 4) agree with brute force
test 2: 200/200 skewed-diagonal lattices (dims 1-3) match the closed-form minimum
test 3: 30 large-entry cosets (300-700 digit entries, dims 1-3): exact minimum <= Babai+neighbours in all cases
test 4: in 3000 random 3-dim cosets plain Babai was suboptimal 194 times; Babai+neighbours was never suboptimal in this sample (so test 3 only shows '<=')
all tests passed in 23.0 s
```

- Test 1: random bases with entries in [−6, 6] (rank d, ambient dimension d or d+1), targets in [−25, 25]; brute
  force over the box |z|_∞ ≤ 1.1·2|v|/σ_min(U) + 2, which provably contains every z with |v + zU| ≤ |v|
  (near-singular bases with box > 40 (> 22 in dim 3) are skipped; the exact code itself handles them — one such
  case, v = (21, −7, −18), U = ((1,−2,−6), (0,2,4), (−5,−4,4)), has minimum norm² = 1 at z = (−111, −144, −18),
  which a naive box of 60 misses: this was a bug in my first test, not in the solver).
- Test 2: lattices diag(s)·Z^d presented by a random unimodular skewing (so LLL and the enumeration are
  exercised) with targets up to 10⁶; the exact minimum is Σ_j min(r_j, s_j − r_j)², r_j = v_j mod s_j — a closed
  form independent of the solver.
- Test 3: 300–700-digit entries (the regime of the sandwich lattices): exact ≤ Babai+neighbours always
  (as it must be); typical run time per instance well under a second.
- Test 4 (honesty check): on random small 3-dimensional instances Babai+neighbours happened to be optimal
  every time, so test 3 does not *demonstrate* that the exact routine beats it; plain Babai was suboptimal in
  6.5 % of the cases. The exactness claim rests on the algorithm (step 2), not on the comparison.

## 8. Doubts / caveats

1. The base-b statement inherits every caveat of BAKER-CHAIN.md (Matveev as printed; interval arithmetic
   trusted; not machine-checked).
2. The exponent bounds a_p for bases 6 and 12 were not specified; 2 was used, and the sensitivity is < 0.001
   in log₁₀ at a_p = 40.
3. In the CVP module the LLL step is exact but naive (full GSO recomputation per swap); for d = 3 and 700-digit
   entries it is fast enough (test 3), for larger ranks it would not be.
4. `exact_nearest` returns *a* minimiser; if several coset points share the minimal norm, which one is returned
   depends on the enumeration order.
