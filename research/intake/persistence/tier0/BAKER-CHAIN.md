# A certified Baker-type upper bound on the number of digits of an S-unit with k non-1 digits

*2026-10-20, scout `baker`; revised after the Codex review (hygiene fixes (a)–(c) of SANDWICH.md §"Independent
review": controls outside the lemma's domain restated as absolute-value variants, endpoints reported as the
certified grid values, and the returned integer certified by interval arithmetic). Code:
`/home/claude/scouts/baker/baker_chain.py` (pure Python + mpmath; runs in 4 s; log in `run.log`). This note is a
proof in the ordinary mathematical sense: it relies on Matveev's theorem on linear forms in logarithms (quoted in
§2 in the explicit form of Bugeaud–Mignotte–Siksek) and on elementary inequalities proved here; it is **not**
machine-checked (no Lean). The numerical resolution of the final inequality is done with mpmath at 60 digits,
the returned integer bound is then certified with mpmath **interval arithmetic** at 256 bits (§5.1), and the
whole thing is cross-checked by an independent closed-form lemma (§5.2). Every constant is rounded in the
direction that makes the bound larger. The generalisation to bases 6, 8, 9, 12 is in `RESULT-base-b.md`.*

## 0. Statement

Throughout, y′ is a positive integer with exactly n decimal digits of the form

    y′ = R_n + Σ_{j=1}^{k} (d_j − 1)·10^{E_j},    R_n = (10^n − 1)/9,    d_j ∈ {2, …, 9},    n > E_1 > E_2 > … > E_k ≥ 0,   (0.1)

i.e. all digits of y′ are 1 except the k digits d_j at the positions E_j (counted from the right, 0-indexed);
k = 0 means y′ = R_n. Equivalently, with c_j := 9(d_j − 1) ∈ {9, 18, …, 72},

    9y′ + 1 = 10^n + Σ_{j=1}^{k} c_j 10^{E_j}.                                                        (0.2)

Suppose moreover that y′ is a {2, 3, 7}-unit:

    y′ = 2^a 3^b 7^c,   a, b, c ∈ Z_{≥0}.                                                              (0.3)

Put t₀ := 3 and P₀ := log 3 · log 7 · log 10 if a = 0, and t₀ := 4, P₀ := log 2 · log 3 · log 7 · log 10 if
a ≥ 1; C(t) := 1.4 · 30^{t+3} · t^{4.5} (Matveev's constant); and, for a real variable ν ≥ 1,

    T(ν) := 1 + log(2.1 ν + 2 + a),     K₀(ν) := C(t₀) P₀ T(ν),     K₁(ν) := C(t₀+1) P₀ T(ν),

    Φ_{k,a}(ν) :=  K₀(ν)/log 10                                                        if k = 0,
                   K₁(ν)·(S_k log 10 + log 9)/log 10                                   if k ≥ 1, where
    G₀ := (K₀(ν) + log 80)/log 10,  S₁ := G₀,  G_j := (log 80 + K₁(ν)(S_j log 10 + log 9))/log 10,  S_{j+1} := S_j + G_j  (1 ≤ j ≤ k−1).

**Theorem.** If y′ satisfies (0.1)–(0.3), then n ≤ Φ_{k,a}(n). Consequently n < G(k, a), where G(k, a) is any
number N ≥ e^k with Φ_{k,a}(N) < N; `baker_upper_bound(k, a)` returns such an integer N (certified by interval
arithmetic, §5.1),
and log₁₀ G(k, a) is tabulated in §6. Numerically

    log₁₀ G(k, 0) ≈ 11.49 + log₁₀ T + k (13.89 + log₁₀ T),    log₁₀ G(k, a≥1) ≈ 13.37 + log₁₀ T + k (15.64 + log₁₀ T),

with T = 1 + log(2.1 G + 2 + a) (T ≈ 259 for k = 6, a = 0; ≈ 374 for k = 8, a = 1), i.e. G ≈ C₀·Cᵏ with
C = C(t₀+1) P₀ T ≈ 2.0·10¹⁶ (a = 0, k ≈ 6) and ≈ 1.6·10¹⁸ (a ≥ 1, k ≈ 8). In particular

| k | a | log₁₀ G(k, a) |
|---|---|---|
| 6 | 0 | 111.704 |
| 7 | 0 | 128.488 |
| 8 | 0 | 145.328 |
| 8 | 1 | 161.654 |

The bound depends on a only through t₀ (a = 0 vs a ≥ 1) and through the harmless term "+ a" inside T; for a ≤ 40
the values for a = 1 and a = 40 agree to all printed digits.

**Assumptions (complete list).**
(A1) Matveev's theorem in the form of Bugeaud–Mignotte–Siksek, Theorem 9.4 (quoted verbatim in §2), is correct as
printed. (A2) The quantities in §1–§4 are as defined there; in particular y′ has digits in {1, …, 9} only (digit 0
is excluded by (0.1); see Remark 3.4 for what changes if it is allowed). (A3) mpmath's logarithms and powers at
60 decimal digits are correct to far better than the 10⁻⁶ relative slack used in the *search*, and mpmath's
interval arithmetic (`mpmath.iv`: log, exp, sqrt, powers, ring operations with outward rounding) is correct —
the *certificate* (§5.1) uses only the latter.
(A4) Nothing else: no lattice, no pattern data, no LLL output, no 10-adic cut enters this note.

## 1. Setting and elementary facts

Let M := 9y′ = 2^a 3^{b+2} 7^c. By (0.2), M + 1 = 10^n + Σ_j c_j 10^{E_j}.

**Lemma 1.1 (digit count, exponent sizes).** 10^{n−1} ≤ y′ < 10^n. Hence 3^b ≤ y′ < 10^n gives
b < n log 10/log 3 < 2.096 n, and similarly c < n log 10/log 7 < 1.184 n. In particular

    max(a, b + 2, c, n, 1) ≤ 2.1 n + 2 + a =: B_max(n).                                              (1.1)

*Proof.* y′ ≥ R_n ≥ 10^{n−1}; y′ ≤ R_n + 8·Σ_{i=0}^{n−1} 10^i = R_n + 8R_n = 10^n − 1 < 10^n. ∎

**Gaps.** g₀ := n − E₁ ≥ 1, g_j := E_j − E_{j+1} ≥ 1 (1 ≤ j ≤ k−1), and E_k ≥ 0. Then n − E_j = g₀ + … + g_{j−1}.

**Partial sums.** For 1 ≤ j ≤ k put

    N_j := 10^{n−E_j} + Σ_{i=1}^{j} c_i 10^{E_i − E_j}   (a positive integer, since E_i ≥ E_j for i ≤ j),       (1.2)

so that M + 1 = N_j 10^{E_j} + Σ_{i>j} c_i 10^{E_i}, i.e. N_j is the integer formed by the top j+1 "blocks" of
M + 1. Clearly

    10^{n−E_j} ≤ N_j ≤ 10^{n−E_j} + 80·10^{E_1−E_j} ≤ 9·10^{n−E_j},   hence   (n − E_j) log 10 ≤ log N_j ≤ (n − E_j) log 10 + log 9,   (1.3)

using Σ_{i≤j} c_i 10^{E_i−E_j} ≤ 72·10^{E_1−E_j}(1 + 10⁻¹ + 10⁻² + …) = 80·10^{E_1−E_j} and E_1 ≤ n − 1.

## 2. Matveev's theorem (the explicit form used)

Quoted from Y. Bugeaud, M. Mignotte, S. Siksek, *Classical and modular approaches to exponential Diophantine
equations I. Fibonacci and Lucas perfect powers*, Ann. of Math. (2) 163 (2006), 969–1018, §9.1, Theorem 9.4
(fetched from arXiv:math/0403046v1 and from the authors' final version at
warwick.ac.uk/~maseap/papers/fibannalsfinal.pdf; the two agree). Their n is our t.

> Let L be a number field of degree D, let α₁, …, α_n be non-zero elements of L and let b₁, …, b_n be rational
> integers. Set B = max{|b₁|, …, |b_n|}, and Λ = α₁^{b₁} ⋯ α_n^{b_n} − 1. Let h denote the absolute logarithmic
> height and let A₁, …, A_n be real numbers with
>     A_j ≥ h′(α_j) := max{D h(α_j), |log α_j|, 0.16},   1 ≤ j ≤ n.
> We call h′ the modified height (with respect to the field L).
>
> **Theorem 9.4 (Matveev).** Assume that Λ is non-zero. We then have
>     log|Λ| > −3·30^{n+4} (n+1)^{5.5} D² (1 + log D)(1 + log nB) A₁ ⋯ A_n.
> Furthermore, if L is real, we have
>     log|Λ| > −1.4·30^{n+3} n^{4.5} D² (1 + log D)(1 + log B) A₁ ⋯ A_n.

They attribute this to E. M. Matveev, *An explicit lower bound for a homogeneous rational linear form in
logarithms of algebraic numbers. II*, Izv. Ross. Akad. Nauk Ser. Mat. 64 (2000), 125–180 (English transl. Izv.
Math. 64 (2000), 1217–1269). Matveev's own Corollary (as quoted e.g. in arXiv:1604.04720, Thm 3) reads
log|Λ| ≥ −C(n, 1) D² A₁⋯A_n log(eD) log(eB′) with C(n, 1) = min{(en/2)·30^{n+3} n^{3.5}, 2^{6n+20}} for real L;
since e/2 = 1.359… ≤ 1.4 and log(eB) = 1 + log B, the BMS form is a (slightly weakened) restatement. Remarks:
there is **no** hypothesis of multiplicative independence of the α_j and no restriction on the b_j (some may
be 0); the only hypothesis is Λ ≠ 0.

**How it is used here.** L = Q, D = 1 (real), so D²(1 + log D) = 1, and the real-case bound reads

    log|Λ| > −C(t) (1 + log B) A₁ ⋯ A_t,    C(t) := 1.4·30^{t+3} t^{4.5},                            (2.1)

    C(3) ≤ 1.4319·10¹¹,   C(4) ≤ 1.5677·10¹³,   C(5) ≤ 1.2838·10¹⁵.

For a positive integer m ≥ 2, h(m) = log m = |log m| > 0.16, so A = log m is admissible: A(2) = log 2,
A(3) = log 3, A(7) = log 7, A(10) = log 10, A(N_j) = log N_j (N_j ≥ 10 by (1.3)). Finally, since the right side of
(2.1) is decreasing in B, B may be replaced by any upper bound for max|b_i|; we always use B := B_max(n) from (1.1).

## 3. The linear forms, their non-vanishing and their size

**Step 0 (top gap).** Λ₀ := M·10^{−n} − 1 = 2^a 3^{b+2} 7^c 10^{−n} − 1.

**Lemma 3.1.** (i) If k ≥ 1 then 0 < Λ₀ ≤ 80·10^{−g₀}. (ii) If k = 0 then Λ₀ = −10^{−n}. In both cases Λ₀ ≠ 0.

*Proof.* M·10^{−n} − 1 = (Σ_j c_j 10^{E_j} − 1)/10^n. For k ≥ 1 the numerator is ≥ 9 − 1 > 0 and
≤ 72·10^{E_1}(1 + 10⁻¹ + …) = 80·10^{E_1} = 80·10^{n−g₀}. For k = 0, M = 10^n − 1. ∎

(The 5-adic argument gives the same: 5 ∤ M while 5 | 10^n, so M ≠ 10^n.)

**Step j, 1 ≤ j ≤ k.** Λ_j := M·10^{−E_j}·N_j^{−1} − 1 = 2^a 3^{b+2} 7^c · 10^{−E_j} · N_j^{−1} − 1.

**Lemma 3.2.** (i) For 1 ≤ j ≤ k − 1:  0 < Λ_j ≤ 80·10^{−g_j}/N_j, so log Λ_j ≤ log 80 − g_j log 10 − log N_j.
(ii) For j = k: Λ_k = −1/(M + 1), so log|Λ_k| = −log(M + 1) < −n log 10. In all cases Λ_j ≠ 0.

*Proof.* By (1.2), M = N_j 10^{E_j} + (Σ_{i>j} c_i 10^{E_i} − 1), so Λ_j = (Σ_{i>j} c_i 10^{E_i} − 1)/(N_j 10^{E_j}).
For j < k the numerator is ≥ 9·10^{E_{j+1}} − 1 ≥ 8 > 0 and ≤ 72·10^{E_{j+1}}·10/9 = 80·10^{E_{j+1}} = 80·10^{E_j − g_j}.
For j = k the numerator is −1 and N_k 10^{E_k} = M + 1 > 10^n. ∎

(Again 5-adically: for j < k the numerator is ≡ −1 (mod 10^{E_k}) and in any case ≡ −1 (mod 9), so it is not 0.)

**Lemma 3.3 (data for Matveev).** Step 0 is Λ₀ = α₁^{b₁}⋯α_t^{b_t} − 1 with (α; b) = (3, 7, 10; b+2, c, −n) if a = 0
(t = 3) and (2, 3, 7, 10; a, b+2, c, −n) if a ≥ 1 (t = 4); A₁⋯A_t = P₀. Step j (1 ≤ j ≤ k) has the additional
factor α = N_j with exponent −1: t = t₀ + 1 and A₁⋯A_t = P₀ log N_j. In every step max|b_i| ≤ max(a, b+2, c, n, 1)
≤ B_max(n) by (1.1) (E_j < n). All α_i are positive rationals, L = Q, D = 1.

**Remark 3.4 (digit 0).** If d_j = 0 were allowed (c_j = −9), every form would still be non-zero, because the
numerators Σ_{i>j} c_i 10^{E_i} − 1 are ≡ −1 (mod 9); the constants 80 and the lower bound on N_j would change
slightly (81 and 0.88·10^{n−E_j}). The theorem is stated and proved for d_j ∈ {2, …, 9} only, which is what the
application needs; the positive controls in the code (genuine S-units, which do contain zeros) check the
inequalities of Lemmas 3.1–3.2 with the constants as written, which happen to hold there with large margin.

## 4. The chain

**Proposition 4.1.** With K₀ := C(t₀) P₀ (1 + log B_max(n)) and K₁ := C(t₀+1) P₀ (1 + log B_max(n)):

    (a) if k = 0:  n log 10 < K₀,  i.e.  n < K₀/log 10;
    (b) if k ≥ 1:  g₀ < (K₀ + log 80)/log 10;
    (c) for 1 ≤ j ≤ k−1:  g_j < (log 80 + K₁ log N_j)/log 10 ≤ (log 80 + K₁((n − E_j) log 10 + log 9))/log 10;
    (d) n log 10 < K₁ log N_k ≤ K₁((n − E_k) log 10 + log 9)   if E_k ≥ 1,   and n = n − E_k if E_k = 0.

*Proof.* (a) Lemma 3.1(ii) and (2.1) with Lemma 3.3: −n log 10 = log|Λ₀| > −K₀.
(b) Lemma 3.1(i): log 80 − g₀ log 10 ≥ log Λ₀ > −K₀.
(c) Lemma 3.2(i) and (2.1) with t = t₀+1, A-product P₀ log N_j: log 80 − g_j log 10 − log N_j ≥ log Λ_j > −K₁ log N_j,
so g_j log 10 < log 80 + (K₁ − 1) log N_j < log 80 + K₁ log N_j; then (1.3).
(d) Lemma 3.2(ii): −n log 10 > log|Λ_k| > −K₁ log N_k; then (1.3). If E_k = 0 there is nothing to prove. ∎

**Proof of the Theorem (n ≤ Φ_{k,a}(n)).** For k = 0 this is (a). For k ≥ 1, define S_j := g₀ + … + g_{j−1} = n − E_j.
By (b), S₁ = g₀ ≤ G₀. Inductively, if S_j ≤ S_j^{bound} (the quantity called S_j in §0), then by (c)
g_j ≤ (log 80 + K₁(S_j^{bound} log 10 + log 9))/log 10 = G_j, hence S_{j+1} ≤ S_{j+1}^{bound}. Finally by (d),
either E_k ≥ 1 and n < K₁(S_k log 10 + log 9)/log 10 ≤ Φ(n), or E_k = 0 and n = S_k ≤ S_k^{bound} ≤ Φ(n), the last
inequality because K₁ ≥ 1. (All quantities G_j, S_j, Φ are increasing in n through T(n) = 1 + log B_max(n).) ∎

Note the structure: Φ_{k,a}(n) is a polynomial in T = T(n) of degree k + 1 with non-negative coefficients
(`chain_poly_coeffs` in the code computes them and the code checks that this agrees with the recursion), and
its leading behaviour is Φ ≈ (K₀/log 10)·K₁^k: each gap multiplies the admissible size by K₁ ≈ 2·10¹⁶ (a = 0)
resp. ≈ 1.6·10¹⁸ (a ≥ 1).

## 5. Resolving the self-reference n ≤ Φ_{k,a}(n)

### 5.1 Monotonicity lemma (what the code certifies)

**Lemma 5.1.** Φ_{k,a}(ν)/ν is strictly decreasing on [e^k, ∞). Consequently, if N ≥ e^k and Φ_{k,a}(N) < N, then
every solution of n ≤ Φ_{k,a}(n) satisfies n < N.

*Proof.* Φ(ν) = Σ_{i=0}^{k+1} α_i T(ν)^i with α_i ≥ 0 and T(ν) = 1 + log(2.1ν + 2 + a). The term α₀/ν is decreasing.
For i ≥ 1, d/dν [T^i/ν] = (T^{i−1}/ν²)·(i·ν T′(ν) − T) with ν T′(ν) = 2.1ν/(2.1ν + 2 + a) < 1, so the derivative is
negative as soon as T ≥ i; and T(ν) ≥ 1 + log ν ≥ i for ν ≥ e^{i−1}. Since i ≤ k + 1, all terms are decreasing
for ν ≥ e^k, and the sum is strictly decreasing (α_{k+1} > 0). If n ≥ N then Φ(n)/n ≤ Φ(N)/N < 1, contradicting
n ≤ Φ(n). ∎

`baker_upper_bound(k, a)` (via `solve_chain`) finds a grid point x (step 0.001 in log₁₀) by iterating ν ← Φ(ν)
(which increases towards the largest fixed point) and then stepping up until the floating test
Φ(10^x)(1 + 10⁻⁶) < 10^x passes; this only locates the candidate. It then forms the **exact integer**
N := m·10^{⌊x⌋−6} with m = ⌈10^{frac(x)}·10⁶⌉ + 1 < 10⁷ (so N ≥ 10^x, and N is represented exactly), and
**certifies** it in mpmath interval arithmetic at 256 bits (`_certify`): with N_iv = [m]·[10]^e (m exact, the
power enclosed), it asserts  lower(N_iv) > upper(exp(k))  and  upper(Φ_iv(N_iv)) < lower(N_iv), where Φ_iv is
the same recursion evaluated with interval log/power/products (C(t) = 1.4·30^{t+3}·t^{4.5} as an interval, T as an
interval, etc.). Both inequalities are between rigorous endpoints, so the certified statement is: *every y′
satisfying (0.1)–(0.3) has n < baker_upper_bound(k, a)* (the returned Python int). If the certificate fails the
search continues at the next grid point (it never failed in the tables below).

### 5.2 Independent closed-form cross-check (Pethő–de Weger)

The lemma of A. Pethő and B. M. M. de Weger (Math. Comp. 47 (1986), 713–727; in the form of Lemma 6 of
arXiv:2010.11670, proof in N. Smart, *The Algorithmic Resolution of Diophantine Equations*, LMS Student Texts 41,
App. B): *if u, v ≥ 0, h ≥ 1 and x is the largest real solution of x = u + v(log x)^h, then
x < max{2^h(u^{1/h} + v^{1/h} log(h^h v))^h, 2^h(u^{1/h} + 2e²)^h}*. With x := e(2.1n + 2 + a) we have T = log x, and
since T ≥ 1, n ≤ Φ(n) ≤ α₀ + (Σ_{i≥1} α_i) T^{k+1}, i.e. x ≤ u + v (log x)^{k+1} with u = e(2 + a + 2.1α₀),
v = 2.1e Σ_{i≥1} α_i; any such x is ≤ the largest root. `baker_upper_bound_closed_form` evaluates this. It is
weaker than §5.1 by a factor 10^{0.3} (k = 0) to 10^{8.5} (k = 32) and the code asserts that it is ≥ G(k, a)
for every table entry — an independent check of the fixed-point computation (I have seen this lemma only in the
secondary source quoted; it is not used for the certified bound).

### 5.3 Numerical hygiene

Constants: in the floating search C(t) is multiplied by (1 + 10⁻³⁰); log 10/log 3 = 2.0959… is replaced by 2.1;
the "+2" and "+a" in B_max are kept. The certificate itself (§5.1) is pure interval arithmetic with the exact
integer N, so no floating-point rounding enters the final statement. Reported endpoints: the table in §6 gives
log₁₀ N for the certified integer N, truncated to 3 decimals — e.g. "111.704" means the certified N satisfies
log₁₀ N ∈ [111.704, 111.705); quoting "10^{111.70}" would be *below* the certified point, so all abbreviated
values in this note are rounded **up** (5.1·10¹¹¹ > 10^{111.705}, etc.). The code is single-threaded and takes 4 s.

## 6. Table: log₁₀ G(k, a) (certified: n < G)

Columns: the certified bound from §5.1, and [PdW] the closed-form cross-check of §5.2. The a = 1 and a = 40
columns coincide to the printed precision (a enters only through t₀ and the "+a" inside a logarithm).

```
 k    a=0    [PdW]     a=1    [PdW]     a=40   [PdW]
 0    12.987   13.237    14.925   15.179    14.925   15.179
 1    29.047   29.554    32.784   33.299    32.784   33.299
 2    45.339   46.103    50.875   51.650    50.875   51.650
 3    61.783   62.804    69.118   70.153    69.118   70.153
 4    78.338   79.617    87.472   88.769    87.472   88.769
 5    94.984   96.520   105.916  107.473   105.916  107.473
 6   111.704  113.498   124.434  126.253   124.434  126.253
 7   128.488  130.540   143.016  145.096   143.016  145.096
 8   145.328  147.638   161.654  163.995   161.654  163.995
 9   162.217  164.785   180.342  182.944   180.342  182.944
10   179.151  181.977   199.073  201.937   199.073  201.937
11   196.126  199.210   217.846  220.971   217.846  220.971
12   213.137  216.480   236.655  240.042   236.655  240.042
13   230.183  233.785   255.499  259.147   255.499  259.147
14   247.261  251.121   274.374  278.284   274.374  278.284
15   264.369  268.487   293.279  297.450   293.279  297.450
16   281.504  285.881   312.212  316.645   312.212  316.645
17   298.666  303.302   331.171  335.866   331.171  335.866
18   315.853  320.747   350.154  355.111   350.154  355.111
19   333.063  338.216   369.161  374.380   369.161  374.380
20   350.295  355.707   388.191  393.671   388.191  393.671
21   367.548  373.219   407.241  412.984   407.241  412.984
22   384.822  390.751   426.312  432.316   426.312  432.316
23   402.115  408.303   445.402  451.668   445.402  451.668
24   419.427  425.874   464.510  471.039   464.510  471.039
25   436.756  443.462   483.637  490.427   483.637  490.427
26   454.103  461.068   502.780  509.832   502.780  509.832
27   471.466  478.690   521.940  529.254   521.940  529.254
28   488.845  496.328   541.115  548.692   541.115  548.692
29   506.239  513.981   560.307  568.145   560.307  568.145
30   523.648  531.650   579.512  587.613   579.512  587.613
31   541.072  549.332   598.733  607.096   598.733  607.096
32   558.509  567.029   617.967  626.592   617.967  626.592
```

Per-gap detail for k = 6, a = 0 at the certified integer N = 5.0574…·10¹¹¹ (log₁₀ N = 111.7039…): T = 258.95,
K₀ = 1.825·10¹⁴, K₁ = 1.998·10¹⁶; the gap bounds are log₁₀ G_j = 13.90, 30.20, 46.50, 62.80, 79.10, 95.40
(j = 0..5), Φ(N)/N = 0.9978. The sketch in `/home/claude/scouts/lll/RESULT-lll.md` §6 (≈ 5·10¹¹¹ for k = 6,
≈ 10¹²⁸ for k = 7, ≈ 10¹⁶¹ for k = 8 with a = 1) is confirmed: certified log₁₀ N = 111.704, 128.488, 161.654,
i.e. n < 5.1·10¹¹¹, n < 3.1·10¹²⁸, n < 4.6·10¹⁶¹ (safe roundings up).

**Consequence for the four open patterns** (not part of this note's certification; it combines this note with
the *lower* bounds of RESULT-lll.md, which rest on their own assumptions): pattern 14336 (k = 6, a = 0) has
every candidate with n < 5.1·10¹¹¹ digits, while RESULT-lll.md certifies ≥ 8.4·10¹²¹ digits at D = 2 — the two
are incompatible, so (granting both) the pattern has no candidate. The two 28672 patterns (k = 7, a = 0,
n < 3.1·10¹²⁸) and 42336 (k = 8, a = 1, n < 4.6·10¹⁶¹) need the D = 3 lower bound (≈ 10¹⁷⁰ according to
RESULT-lll.md §6; since run: SANDWICH.md reports all four closed, at D = 2, 3, 3, 3).

## 7. The p-adic alternative (Yu's theorem) — structure, and why it is not used

The same identity read 5-adically (or 2-adically) gives an independent, bottom-up chain. Put
T_j := Σ_{i>j} c_i 10^{E_i} − 1 for 0 ≤ j ≤ k (so T_k = −1). Then M − T_j = N_j 10^{E_j} (with N₀ := 1, E₀ := n), so

    v₅(M·T_j^{−1} − 1) ≥ E_j   whenever 5 ∤ T_j,   and   v₅(M·T₀^{−1} − 1) = n   (j = 0).

(5 ∤ T_j holds for every j if E_k ≥ 1, since then T_j ≡ −1 (mod 5); if E_k = 0 one may have 5 | T_j, e.g.
c_k − 1 = 35, and one would use v₂ instead or shift the bottom block.) Each form α₁^{b₁}⋯ − 1 has α's 2, 3, 7, T_j
with |T_j| ≤ 80·10^{E_{j+1}}, so h(T_j) ≤ E_{j+1} log 10 + log 80 — the *lower* part enters, and the chain runs from
E_k upward: E_k ≤ c_p·(floor height)·log B, E_j ≤ c_p·(E_{j+1} log 10 + log 80)·log B, …, n ≤ c_p·(E_1 log 10 + …)·log B.
The shape is the same, n ≲ C₀·(c_p log B)^{k+1}.

I could not fetch a fully explicit, verifiable statement of Yu's theorem (K. Yu, *p-adic logarithmic forms and
group varieties III*, Forum Math. 19 (2007), 187–280, or *p-adic logarithmic forms and a problem of Erdős*, Acta
Math. 211 (2013), 315–382) in this session: the sources reached either state it with an unspecified
"effectively computable c₂(D)" (arXiv:2503.22084, Thm 2.2) or in Stewart's simplified form (arXiv:2108.09857,
Thm 3.1), which requires the α_i to be *multiplicatively independent* p-adic units — a hypothesis that is not
automatic for {2, 3, 7, T_j} (T_j could itself be a {2,3,7}-unit) — and whose constant, as reported there,
is ≈ 10⁵·30^t·t^{5/2}·log*t·Ω·Πh(α_i)·log*B with Ω = max{(5/δ)(t/log 5)^t, e^t log 5} ≈ 2·10² at p = 5, t = 4,
i.e. ≈ 7·10¹⁴ per gap against Matveev's 1.6·10¹³: **worse by a factor ≈ 45 per gap** even if applicable. The
Bugeaud–Laurent explicit theorem (J. Number Theory 61 (1996)) covers only two logarithms. The p-adic route is
therefore reported as a structural alternative only; the archimedean chain of §3–§5 is the certified one and
suffices.

## 8. Sanity check k = 0 (repunits)

For k = 0 the Theorem gives n < K₀/log 10 = C(t₀) P₀ (1 + log(2.1n + 2 + a))/log 10, whose solution is
n < 10^{12.99} (a = 0) and n < 10^{14.93} (a ≤ 40): a repunit R_n that is a {2,3,7}-unit has fewer than 10¹⁵ digits.
This is consistent with (and of course much weaker than) the known fact that no R_n with n ≥ 2 is a
{2,3,7}-unit: R₂ = 11 is prime; in general 10^n − 1 has a primitive prime divisor p for every n ≥ 2 (Zsigmondy;
base 10 has no exceptional case), p ≡ 1 (mod n), p ≠ 2, 3, and p = 7 (primitive for n = 6) is accompanied by
11 | R₆ = 3·7·11·13·37. So the only repunit S-unit is R₁ = 1, within the bound.

Positive controls (code, `positive_control`), with exact rational arithmetic for the forms:
- **in-domain** (all digits in {1, …, 9}, so Lemmas 3.1–3.2 and Proposition 4.1 apply verbatim): the genuine
  S-units 3¹³·7² = 78121827 (n = 8, k = 6) and 2·3¹⁴·7³ = 3281116734 (n = 10, k = 7). Checked: identity (0.2);
  Λ₀, Λ_j > 0 for j < k and Λ_k = −1/(M+1); the bounds of Lemmas 3.1–3.2 and (1.3); the Matveev inequalities (2.1)
  themselves; and the gap bounds of Proposition 4.1.
- **absolute-value variants** (the S-units 2³·3⁴⁰¹·7¹⁴¹, n = 312, k = 282, and 3⁶⁰·7²⁰, n = 46, k = 39, contain
  digits 0, so they are *outside* the theorem's domain and some intermediate forms are negative; they test only
  the parts of the argument that do not use d_j ≥ 2): identity (0.2) with c_j = −9 for a digit 0; non-vanishing of
  every form (numerators ≡ −1 mod 9); |numerator_j| ≤ 80·10^{E_{j+1}} + 1; N_j ≥ 1 with A(N_j) = max(log N_j, 0.16);
  and the Matveev inequalities (2.1) with these A's. The in-domain inequalities of Lemma 3.2 are *not* asserted
  for them.
(The base-b generalisation runs the same two kinds of control in bases 6, 8, 9, 12; see RESULT-base-b.md.)

## 9. Points of residual uncertainty

1. The whole bound rests on BMS Theorem 9.4 as printed (two copies fetched and compared, §2). I did not
   re-derive it from Matveev's paper; Matveev's own constant, as quoted in a third source, is consistent.
2. B is bounded by 2.1n + 2 + a rather than computed; this is only ever inside 1 + log B. The "+ 1" exponent of
   N_j and all other |b_i| are ≤ n ≤ B_max(n).
3. The certificate is mpmath interval arithmetic (`mpmath.iv`) at 256 bits on an exactly represented integer;
   I rely on mpmath's interval implementation being correct (outward rounding of log/exp/pow). The closed-form
   cross-check (§5.2) agrees to within its expected looseness for all 99 table entries.
4. The p-adic comparison (§7) is structural only; the constant quoted there is from a secondary source and is
   not certified.
5. No part of this note is machine-checked. The statement is a theorem conditional on (A1)–(A3) in the
   ordinary mathematical sense.
