# A fully explicit conditional digit bound for the even trees: which abc-type conjecture, how explicit, how many digits

*2026-10-21, scout `conditional`. Inputs: BAKER-CHAIN.md §0–§3 (the setting, Lemmas 3.1–3.2), LIT2.md §3 (the
sketch this note makes rigorous), FRONTIER.md and TABLES.md Table A/D (the 19 Tier-B/C vertices and their k_max).
Statements of conjectures were fetched this session from the sources listed in §8; where a formula could only be
read through a garbled PDF extraction I say so. All derivations in §1–§2 are mine and are written out inequality by
inequality. Numbers come from `/home/claude/night/conditional/nk.py` (log in `nk.out`; pure Python, 1 minute); the
N(k) values are verified there by evaluating the master inequality at n = N(k) (holds) and n = N(k)+1 (fails).
No heavy computation was done.*

## 0. Verdict

**There is no explicitly stated conjecture in the literature that yields a usable digit bound.** The fully explicit
conjectures that exist either have an exponent too large for a chain of k+1 gaps (Granville–Tucker c < rad², and the
IUT-claimed effective abc with exponent 3 on |abc|) and give nothing, or — Baker's explicit abc, c < (6/5)·N·(log N)^ω/ω!
— give a finite but astronomical N(k) (≈ 10^{83} digits at k = 29, ≈ 10^{133} at k = 44; better than Matveev's
10^{506}, 10^{769}, still useless), because ω(abc) is unbounded in our triples. The conjectures with the right *shape*
(Masser–Oesterlé abc, Lang–Waldschmidt, the Browkin–Brzeziński n-conjecture, and the Robert–Stewart–Tenenbaum (RST)
refinement) all carry an unspecified constant (κ(ε), C(ε), K(n,ε), C₁).

**The weakest natural explicit instantiation is RST with its constant fixed: RST[C₁]** (§3.4): *for all coprime
positive integers a, b with c = a+b and N = rad(abc) ≥ 16,*
c < N·exp(4√(3 log N/log₂N)·(1 + log₃N/(2 log₂N) + C₁/log₂N)).
RST assert this with "there exists C₁"; their own model predicts the true constant is β = 1 + log 3 − (13/6)log 2 =
0.5968 (upper bound with any C₁ > β for large N, violated infinitely often with C₁ < β), so the honest explicit
choice is C₁ = 1 ("RST[1]"), and every C₁ ≥ 0 is consistent with all known abc triples (record merit 38.67 < 48).
Under RST[1], a zero-free {2,3,7}-unit with k non-1 digits has at most N(k) digits with

| k | 16 | 20 | 22 | 25 | 26 | 27 | 28 | 29 | 31 | 34 | 35 | 36 | 42 | 44 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| N(k), RST[1] | 1324 | 1881 | 2191 | 2694 | 2871 | 3054 | 3241 | 3433 | 3832 | 4466 | 4687 | 4912 | 6363 | 6883 |
| N(k), RST[β] (model value) | 1242 | 1766 | 2058 | 2532 | 2700 | 2872 | 3049 | 3230 | 3607 | 4206 | 4414 | 4627 | 5999 | 6491 |
| N(k), leading term only (4√3; expected FALSE by RST (1.6)) | 927 | 1320 | 1540 | 1897 | 2024 | 2154 | 2287 | 2424 | 2709 | 3163 | 3321 | 3483 | 4525 | 4900 |
| N(k), Baker explicit abc (log₁₀) | 42.6 | 54.7 | 60.8 | 70.3 | 73.5 | 76.7 | 79.9 | 83.1 | 89.6 | 99.5 | 102.8 | 106.1 | 126.4 | 133.3 |
| Matveev, Theorem U (log₁₀, BAKER-CHAIN/TABLES D) | 281.5 | 350.3 | 384.8 | 436.8 | 454.1 | 471.5 | 488.8 | 506.2 | 541.1 | 593.4 | 610.9 | 628.4 | 733.6 | 768.7 |

So under RST[1] **the 10^4000 corpus closes every vertex with k_max ≤ 31**: all 13 Tier-B vertices, all 15 Tier-A
vertices, the 5 closed-below-height vertices, and the Tier-C vertex 128421199872 (k_max = 31) — hence the whole of T_2
(max k_max 29) and T_4 (max k_max 31) — and the other five Tier-C vertices need the enumeration extended to
10^{4466}, 10^{4687}, 10^{4912} (T_6: 3416267673274176, 913217421312, 1438916737499136) and 10^{6363}, 10^{6883} (T_8:
112717121716224, 727326941773824). LIT2's "≈ 5·10³ digits at k = 44" is the leading-term value (4900); the honest
instantiation gives 6500–6900. No abc-type hypothesis that is consistent with the RST model closes k ≥ 42 with the
existing corpus (§4.3).

## 1. Setting and the three abc triples

Notation as in BAKER-CHAIN.md §0–§1. y′ = 2^a 3^b 7^c has n digits, all equal to 1 except the k ≥ 1 digits d_j ∈
{2,…,9} at positions n > E_1 > … > E_k ≥ 0; c_j := 9(d_j − 1) ∈ {9, …, 72}; M := 9y′ = 2^a 3^{b+2} 7^c;

    M + 1 = 10^n + Σ_{j=1}^k c_j 10^{E_j}.                                                          (1.1)

Gaps: g_0 := n − E_1, g_j := E_j − E_{j+1} (1 ≤ j ≤ k−1), so n = g_0 + g_1 + … + g_{k−1} + E_k. Blocks: N_j :=
10^{n−E_j} + Σ_{i≤j} c_i 10^{E_i−E_j} (the top j+1 blocks of M+1) and T_j := Σ_{i>j} c_i 10^{E_i} − 1 (the rest), so

    M = N_j 10^{E_j} + T_j   (0 ≤ j ≤ k; N_0 := 1, E_0 := n, T_k = −1).                              (1.2)

**Facts** (BAKER-CHAIN (1.3) and Lemmas 3.1–3.2): 10^{n−E_j} ≤ N_j ≤ 9·10^{n−E_j}; for j ≤ k−1, 0 < T_j ≤ 80·10^{E_{j+1}}
(T_0 ≤ 80·10^{E_1}). rad(m) denotes the product of the distinct primes of m.

**Lemma 1.1 (the three coprime triples and their radicals).** Put r := 210 = 2·3·5·7. (Notation: in this lemma the
letters a, b, c of the abc triples are local to each displayed triple; the exponent v₂(y′) is written α.)

(T) *Top gap* (needs k ≥ 1). Let α := v₂(y′) and m := min(α, n), so gcd(10^n, M) = 2^m = gcd(10^n, T_0). The integers
a := 10^n/2^m, b := T_0/2^m, c := M/2^m are positive, pairwise coprime, a + b = c, and
    a ≥ 5^n,   rad(abc) ≤ r·b ≤ r·80·10^{E_1}/2^m,   rad(abc) ≤ 16800·10^{E_1}.

(I) *Interior gap j, 1 ≤ j ≤ k−1.* Let d := gcd(N_j 10^{E_j}, M) = gcd(N_j 10^{E_j}, T_j). Then a := N_j 10^{E_j}/d,
b := T_j/d, c := M/d are positive, pairwise coprime, a + b = c, and
    c ≥ a ≥ 5^{E_j},   rad(abc) ≤ r·N_j·T_j/d,   rad(abc) ≤ 151200·10^{n−g_j}.

(B) *Bottom gap.* a := M, b := 1, c := M + 1 = N_k 10^{E_k} are pairwise coprime and
    c ≥ 10^n,   rad(abc) ≤ r·N_k ≤ 1890·10^{n−E_k}.

*Proof.* (T) 2^m | T_0 = M − 10^n, so b is an integer; after division 2 divides at most one of a, c (none if α = n),
5 | a only, 3 and 7 divide c only, and b is coprime to a and c since gcd(10^n, T_0) = gcd(10^n, M) = 2^m. Pairwise
coprime ⇒ rad(abc) = rad(a)rad(b)rad(c) = rad(ac)·rad(b) ≤ rad(10^n M)·b ≤ r·b (each of 2, 3, 5, 7 at most once), and
b ≤ T_0 ≤ 80·10^{E_1}. a = 10^n/2^m ≥ 10^n/2^n = 5^n. (I) d | T_j = M − N_j 10^{E_j}, so b is an integer; coprimality
of the three after division by the full gcd d is the usual fact (any prime dividing two of a, b, c divides the third,
hence d). rad(ac) | rad(N_j 10^{E_j} M) = rad(210·N_j) ≤ 210·N_j, and rad(b) ≤ b = T_j/d. For the lower bound on a: d
is composed of the primes 2, 3, 7 and d | N_j 10^{E_j}, so v_3(d) ≤ v_3(N_j), v_7(d) ≤ v_7(N_j), v_2(d) ≤ v_2(N_j) + E_j,
whence d ≤ N_j·2^{E_j} and a = N_j 10^{E_j}/d ≥ 5^{E_j}. The numerical bound: r·N_j·T_j ≤ 210·9·10^{n−E_j}·80·10^{E_{j+1}}
= 151200·10^{n−g_j}. (B) gcd(M, M+1) = 1; rad(M(M+1)) = rad(M·N_k·10^{E_k}) = rad(210·N_k) ≤ 210·N_k ≤ 1890·10^{n−E_k};
c = M + 1 ≥ 10^n by (1.1). ∎

In every case rad(abc) ≤ R_max(n) := 16800·10^n (the three bounds are 1680·10^n, 15120·10^n, 1890·10^n).

## 2. The master inequality

**Hypothesis ABC_f.** Let f: [1, ∞) → [1, ∞) be any function. ABC_f is the statement: *for all coprime positive
integers a, b, c with a + b = c, c ≤ rad(abc)·f(rad(abc)).* Put Φ_f(n) := sup{log f(N) : 1 ≤ N ≤ 16800·10^n}.

**Theorem A.** Assume ABC_f. If y′ is as in §1 with k ≥ 1 non-1 digits and n digits, then

    n ≤ (k+1)·( log₁₀ 16800 + Φ_f(n)/log 10 ) =: ρ_f(n)     (log₁₀ 16800 = 4.2253).                    (2.1)

Hence n ≤ N_f(k) := max{n ≥ 1 : n ≤ ρ_f(n)} whenever this maximum is finite (it is, as soon as Φ_f(n) = o(n)).

*Proof.* Apply ABC_f to the three triples of Lemma 1.1, writing R for the radical of the triple at hand, so that
log f(R) ≤ Φ_f(n) because R ≤ 16800·10^n.
(T): 10^n/2^m = a ≤ c ≤ R f(R) ≤ (210·T_0/2^m) f(R) ⇒ 10^n ≤ 210·T_0·f(R) ≤ 210·80·10^{E_1} f(R), i.e.
    g_0 = n − E_1 ≤ log₁₀ 16800 + log₁₀ f(R).
(I): N_j 10^{E_j}/d = a ≤ c ≤ R f(R) ≤ (210·N_j·T_j/d) f(R) ⇒ 10^{E_j} ≤ 210·T_j·f(R) ≤ 16800·10^{E_{j+1}} f(R), i.e.
    g_j = E_j − E_{j+1} ≤ log₁₀ 16800 + log₁₀ f(R)   (1 ≤ j ≤ k−1).
(B): N_k 10^{E_k} = c ≤ R f(R) ≤ 210·N_k·f(R) ⇒ 10^{E_k} ≤ 210 f(R), i.e. E_k ≤ log₁₀ 210 + log₁₀ f(R) ≤ log₁₀ 16800 +
    log₁₀ f(R).
Summing the k+1 bounds, n = g_0 + … + g_{k−1} + E_k ≤ (k+1)(log₁₀ 16800 + Φ_f(n)/log 10). ∎

Remarks. (i) Nothing about a = v_2(y′) enters; the chain is the same for a = 0 and a ≥ 1. (ii) The factor k+1 is
the number of gaps; each abc application pays for everything except one gap through the radical (rad(N_j) ≤ N_j is
the only place where the upper block enters, and it enters *additively* in the exponent — this is what Matveev's
multiplicative C·log N_j·log B does not give). (iii) For f(N) = K·N^ε (plain abc) Φ_f(n) = log K + ε log(16800·10^n)
and (2.1) solves to

    n ≤ N_abc(k; ε, K) := (k+1)·(4.2253·(1+ε) + log₁₀ K)/(1 − (k+1)ε)   if (k+1)ε < 1,  vacuous otherwise.   (2.2)

So any abc-type statement with exponent ≥ 1 + 1/(k+1) (c < rad², c ≤ rad^{3/2}, …) gives nothing for our k (§3.2,
§3.6): the gap bound becomes g_j ≤ n/2 + O(1) and the sum is vacuous for k ≥ 1.

**Lemma 2.1 (tiny radicals).** If a, b, c are coprime positive integers with a + b = c and rad(abc) ≤ 15, then c ≤ 9.
*Proof.* The prime set of abc has product ≤ 15, so it is {2}, {3}, {5}, {7}, {11}, {13}, {2,3}, {2,5}, {2,7} or {3,5},
and each prime divides exactly one of a, b, c. One prime: two of a, b, c equal 1, so 1 + 1 = 2. Two primes p < q:
one of a, b, c is 1 and the others are p^x, q^y. {2,3}: 1 + 2^x = 3^y has (x,y) = (1,1), (3,2) only (3^y − 1 = 2^x:
y odd ⇒ (3^y−1)/2 odd ⇒ y = 1; y even ⇒ 3^{y/2} ± 1 both powers of 2 ⇒ y = 2), 1 + 3^y = 2^x has (0,1), (1,2) only
(2^x − 1 ≡ 7 mod 8 for x ≥ 3); so c ≤ 9. {2,5}: 1 + 2^x = 5^y forces y = 1 (same factorisation argument), 1 + 5^y = 2^x
forces y = 0; c ≤ 5. {2,7}: 1 + 2^x = 7^y is impossible (3 | 7^y − 1), 1 + 7^y = 2^x forces y ∈ {0, 1}; c ≤ 8.
{3,5}: 3^x + 1 ≡ 2, 4 (mod 8) is never a power of 5 ≡ 1, 5 (mod 8), and 5^y + 1 is even; no solution. ∎
Consequently a hypothesis stated only for rad(abc) ≥ 16 implies ABC_f with f extended by f(N) := f(16) for N < 16,
provided f(16) ≥ 9 (then c ≤ 9 ≤ N·f(16)); in the chain a triple with radical ≤ 15 would in any case force n ≤ 1
(top), E_j ≤ 1 (interior) or 10^n ≤ 9 (bottom), so these triples never matter.

## 3. The conjectures, one by one

### 3.1 Masser–Oesterlé abc: c ≤ κ(ε)·rad(abc)^{1+ε}
Oesterlé 1988 / Masser 1990 (quoted in Chim–Nair–Shorey, HRJ 2019 [CNS]): "for any given ε > 0 there exists a
computable constant κ depending only on ε such that if a + b = c … c ≤ κ N^{1+ε}". **Not explicit** (κ(ε) unspecified).
Under abc(ε, K) the bound is (2.2). For the existing corpus (n ≤ 4000) to suffice at k with ε = 1/(2(k+1)) one needs
log₁₀ K ≤ 62.4 (k = 29), 58.2 (31), 49.8 (36), 42.2 (42), 40.2 (44); for 10^{8000}: 129, 121, 104, 89, 85
(`nk.out`). These are *stronger* than what RST-type conjectures predict: the leading-term RST bound implies abc(ε, K)
only with log₁₀ K = 58 at the optimal ε = 0.0095 for k = 44 (N = 4900 again), and RST[1] implies more. So "abc with
ε = 1/90 and K ≤ 10^{40}" is an admissible explicit hypothesis that closes k = 44 with the existing corpus, but it is
not implied by any conjecture in the literature and contradicts the RST model at N ≈ 10^{4000} (§4.3).

### 3.2 Granville–Tucker: c < rad(abc)²
Granville–Tucker, Notices AMS 49 (2002), as quoted by Laishram–Shorey [LS12] ((1.3): "c < N² for N ≥ 1") and by
Waldschmidt [Wal]. **Fully explicit.** Exponent 2 ⇒ ε = 1 in (2.2): vacuous for every k ≥ 1. Gives nothing. Same for
the Laishram–Shorey / Chim–Shorey–Sinha consequences of Baker's conjecture c < N^{7/4}, N^{1.72}, 32N^{1.6},
10N^{1.62991} (exponent ≥ 1.6).

### 3.3 Baker's explicit abc: c < (6/5)·N·(log N)^ω/ω!
Baker, *Experiments on the abc-conjecture*, Publ. Math. Debrecen 65 (2004) 253–260, as quoted in [LS12] Conj. 1.2 and
[CNS] (1.2): for coprime a + b = c, N = rad(abc), ω = ω(N) the number of distinct primes of N, c < (6/5) N (log N)^ω/ω!
(for N > 2). Baker's earlier 1996/98 form ("Logarithmic forms and the abc-conjecture", Eger 1996 proceedings, de
Gruyter 1998) is c ≤ κ ε^{−ω} N^{1+ε} with κ absolute and unspecified ([Wal]; Martin–Miao [MM] quote it as
c < ε^{−K₁ min{ω(ab),ω(ac),ω(bc)}} R^{1+ε}); that one is **not explicit**. The 2004 form **is fully explicit**.

What it gives. The obstruction is ω: in triples (T), (I) the middle term T_j/d is an arbitrary integer of size 10^{E_{j+1}},
so ω(abc) can be as large as ≈ log N/log log N and (log N)^ω/ω! is then N^{(1+o(1))/log log N}. The sharpest published
elimination of ω is Chim–Shorey–Sinha, *On Baker's explicit abc-conjecture*, Publ. Math. Debrecen 94 (2019) 435–453
[CSS], Theorem 1.3: Baker's conjecture implies, for N > 2,

    c < (6/5)·N^{1+G(N)},   G(N) := (1 + log A(N))/A(N),   A(N) := log₂N − log₃N,                          (3.1)

(and c < (6/5)N^{1+G₁(N)} for N ≥ 297856 with A₁ = A + log A − 1.076869; G is decreasing for N ≥ 16). The proof is
Robin's θ(p_n) ≥ n(log n + log₂n − 1.076869) ⇒ ω < log N/A(N), then (log N)^ω/ω! ≤ (e log N/ω)^ω ≤ N^{G(N)}.
Thus Baker's conjecture ⇒ ABC_f with f_B(N) := (6/5)·N^{G(N)} for N ≥ 16 (f_B(16) = 19.2 ≥ 9, so Lemma 2.1 covers
N ≤ 15). N^{G(N)} is increasing for N ≥ 16: with L = log N, d/dL[L·F(A(L))] = F(A) + F′(A)(1 − 1/log L) =
[(1 + log A)A − log A·(1 − 1/log L)]/A² > 0 since A ≥ 1 there. Hence Φ_{f_B}(n) = log(6/5) + G(R_max) log R_max with
R_max = 16800·10^n, and (2.1) reads

    n ≤ (k+1)·( 4.2253 + 0.0792 + G(16800·10^n)·(n + 4.2253) ).                                             (3.2)

Since G → 0, (3.2) fails exactly once (k+1)·G(16800·10^n) drops below 1 − O(k/n), i.e. at A(R_max) ≈ (k+1)(1 + log A):
A ≈ 302.6 for k = 44, log log R_max ≈ 308.3, n ≈ 10^{133.3}. The row "Baker explicit" of the table in §0 is the exact
root of (3.2) (`N_baker_G` in `nk.py`; with G₁ in place of G the exponents drop by ≈ 1.9, e.g. 10^{131.3} at k = 44).
So Baker's explicit conjecture does yield a finite explicit N(k) — log₁₀N(k) ≈ 83 at k = 29, 133 at k = 44, roughly
3k — and it beats the unconditional Matveev chain by hundreds
of orders of magnitude, but it is useless for enumeration. (A two-regime variant using c < N^{1.72} below a threshold
R_* gives the same exponents + 1.3; `N_baker` in the code.)

### 3.4 Robert–Stewart–Tenenbaum, *A refinement of the abc conjecture*, Bull. LMS 46 (2014) 1156–1166
Fetched from tenenb.perso.math.cnrs.fr/PPP/abc.pdf. Notation: k = k(abc) the squarefree kernel (= rad), log_j the
j-th iterate of log. **Conjecture A** (their (1.5)–(1.6)): *there exists a real number C₁ such that, if a and b are
coprime positive integers, c = a + b and k = k(abc), then*

    c < k·exp( 4√(3 log k/log₂k) · (1 + log₃k/(2 log₂k) + C₁/log₂k) ),                                    (RST 1.5)

*and there exists C₂ and infinitely many coprime pairs with the reverse inequality c > k·exp(4√(3 log k/log₂k)·(1 +
log₃k/(2log₂k) + C₂/log₂k)).* Their Remark (ii): under their heuristic (the kernels of a, b, a+b statistically
independent, Robert–Tenenbaum's asymptotics for integers with small kernel) "we may select … C₁ = β + ε, C₂ = β − ε,
where β := 1 + log 3 − (13/6) log 2" (= 0.59679…), i.e. the true constant is β. Conjecture B/C are sharper forms with
the same unspecified constants B₀, B₁, B₂, B₃(ε). The 2014 paper is **not explicit**: C₁ "exists", and the value β + ε
is "for large k" (and conditional on their model). Martin–Miao [MM] quote the same two statements with K₄, K₅ and note that
they make the lim sup of the merit (q−1)² log R log₂R exactly 48.

**Explicit instantiation RST[C₁].** For a real C₁ ≥ 0, RST[C₁] is (RST 1.5) *with that C₁, for every coprime pair
with k ≥ 16* (log₃k ≥ 0 for k ≥ e^e = 15.15, which the consistency argument below needs; for k ≤ 15 Lemma 2.1 applies). Facts:
- RST[C₁] is consistent with every known abc triple for every C₁ ≥ 0: a triple violating it has merit
  (q−1)² log k log₂k > 48·(1 + …)² ≥ 48, and the record merit is 38.67 (Bonse 2011, [MM]; de Smit's list has 131
  triples with merit > 24).
- RST[C₁] with C₁ < β is expected to be FALSE by RST's own (1.6) (infinitely many triples exceed the bound with
  C₂ = β − ε). In particular the leading-term version c < k·exp(4√3·√(log k/log₂k)) used in LIT2 §3 (and in the
  "4√3" row of §0) is expected false — it is RST[C₁] with the bracket replaced by 1. The smallest honest explicit
  instantiation is therefore C₁ slightly above β; I headline C₁ = 1 and tabulate C₁ ∈ {0, β, 1, 2, 5, 10}.
- RST[C₁] ⇒ ABC_f with log f(N) = 4√(3L/log L)·(1 + log log L/(2 log L) + C₁/log L), L = log N ≥ log 16, extended by
  the constant f(16) below 16 (f(16) ≥ e^{11} ≥ 9). For C₁ > 0 log f is not monotone near L = log 16 (the C₁/log L
  term decreases), so Φ_f(n) is a genuine sup; the code evaluates it on a 20 000-point grid and checks that for
  N ≥ 10^{3.7} (C₁ = 1; 10^{9.7} for C₁ = 2, 10^{73} for C₁ = 10) the sup is the right endpoint, so for n ≥ 100,
  Φ_f(n) = log f(16800·10^n).

**N(k) under RST[C₁]** (largest n with n ≤ ρ_f(n); verified at N and N+1 in `nk.out`):

| k | 4√3 only | C₁ = 0 | C₁ = β | C₁ = 1 | C₁ = 2 | C₁ = 5 | C₁ = 10 |
|---|---|---|---|---|---|---|---|
| 16 | 927 | 1123 | 1242 | 1324 | 1534 | 2211 | 3489 |
| 20 | 1320 | 1600 | 1766 | 1881 | 2174 | 3121 | 4908 |
| 22 | 1540 | 1866 | 2058 | 2191 | 2530 | 3623 | 5690 |
| 25 | 1897 | 2298 | 2532 | 2694 | 3105 | 4436 | 6951 |
| 26 | 2024 | 2451 | 2700 | 2871 | 3309 | 4722 | 7394 |
| 27 | 2154 | 2609 | 2872 | 3054 | 3517 | 5016 | 7849 |
| 28 | 2287 | 2770 | 3049 | 3241 | 3731 | 5317 | 8315 |
| 29 | 2424 | 2936 | 3230 | 3433 | 3951 | 5626 | 8792 |
| 31 | 2709 | 3280 | 3607 | 3832 | 4407 | 6266 | 9779 |
| 34 | 3163 | 3828 | 4206 | 4466 | 5131 | 7279 | 11341 |
| 35 | 3321 | 4019 | 4414 | 4687 | 5383 | 7632 | 11883 |
| 36 | 3483 | 4214 | 4627 | 4912 | 5640 | 7991 | 12436 |
| 42 | 4525 | 5471 | 5999 | 6363 | 7291 | 10294 | 15971 |
| 44 | 4900 | 5923 | 6491 | 6883 | 7883 | 11117 | 17231 |

Shape: n ≈ (k+1)²·48·(1 + …)²/(log 10 · log(n log 10)) — quadratic in k, as LIT2 §3 said; the bracket squared is
1.5 at C₁ = 1 and n ≈ 10^{3.8}, which is where the factor 1.4 between the leading-term value and RST[1] comes from.

### 3.5 Browkin–Brzeziński n-conjecture
Browkin–Brzeziński, *Some remarks on the abc-conjecture*, Math. Comp. 62 (1994) 931–939 (statement as quoted in
arXiv:2409.13439 §1): for n-tuples of integers with a_1 + … + a_n = 0, gcd(a_1, …, a_n) = 1 and no vanishing proper
subsum, lim sup log max|a_i|/log rad(a_1⋯a_n) = 2n − 5; equivalently, for every ε there is K(n, ε) with max|a_i| <
K(n,ε)·rad(a_1⋯a_n)^{2n−5+ε}. **Not explicit** (K(n,ε) unspecified; lower bounds for the lim sup are the subject of
the 2024 paper). It is worth recording what it would give, because our equation is *itself* an n-term S-unit
equation: (1.1) reads 10^n + Σ_j c_j 10^{E_j} − M − 1 = 0 with n = k+3 terms, every term a {2,3,5,7}-unit (c_j =
9(d_j−1) is 7-smooth), overall gcd 1 (the term 1), and no vanishing proper subsum (a vanishing subsum would contain
exactly one of −M, −1 and have the complementary positive terms sum to 1 or M; the first is impossible since every
c_j ≥ 9, and the second forces the complement to be {−1} alone). Hence rad(product of all terms) ≤ 210 and the
n-conjecture gives, in one stroke and with no chain,

    10^n ≤ K(k+3, ε)·210^{2k+1+ε},   i.e.   n ≤ 2.3222·(2k+1+ε) + log₁₀ K(k+3, ε)   (= 207 + log₁₀K at k = 44).

Linear in k. Nobody has proposed an explicit K(n, ε); the strong n-conjecture (pairwise coprime terms) does not
apply (the terms share the primes 2, 3, 5, 7).

### 3.6 The IUT-claimed effective abc (Mochizuki–Fesenko–Hoshi–Minamide–Porowski, Kodai Math. J. 2022; Zhou,
arXiv:2503.14510, 2025)
These are claimed *theorems*, not conjectures, and their status is disputed; I record them only because they are the
only fully explicit "abc inequalities" in print. Zhou's abstract: for coprime a + b = c with log|abc| ≥ 700,
log|abc| ≤ 3 log rad(abc) + 8√(log|abc|·log log|abc|), and for 0 < ε ≤ 1/10, |abc| ≤ max{exp(400 ε^{−2} log(1/ε)),
rad(abc)^{3+3ε}}, "reducing the constant from 1.7·10^{30} (MFHMP) to 400". Exponent 3 on |abc|: since |abc| ≥ ac ≥
a² in our triples, this is c ≤ rad^{3/2+…}, exponent ≥ 3/2 on c — vacuous by Remark (iii) of §2. Gives nothing.

### 3.7 Lang–Waldschmidt, and "Matveev with constant (1+ε)"
Lang, *Elliptic Curves: Diophantine Analysis* (1978), introduction to Ch. X–XI, pp. 212–217; Waldschmidt, *Open
Diophantine Problems*, Moscow Math. J. 4 (2004), Conjecture 2.5 (arXiv math/0312440): *for any ε > 0 there is C(ε) >
0 such that for nonzero rational integers a_i, b_i with a_1^{b_1}⋯a_m^{b_m} ≠ 1,* |a_1^{b_1}⋯a_m^{b_m} − 1| ≥
C(ε)^m·B/(|b_1|⋯|b_m|·|a_1|⋯|a_m|)^{1+ε}, B = max|b_i| (the PDF extraction garbles the display; Stewart's Waterloo
notes give the same shape with A_i² in place of |a_i|; the exact placement of B does not matter below). **Not
explicit** — C(ε) is only asserted to exist, in Lang's book, in Waldschmidt's 2000 monograph and in the 2004 survey;
no explicit value has been proposed anywhere I could find.

As a hypothetical, take the weakest reading: **LW(ε, c₀):** for positive integers α_i ≥ 2 and integers b_i with
Λ := α_1^{b_1}⋯α_t^{b_t} − 1 ≠ 0, log|Λ| ≥ −(1+ε)(Σ_i log α_i + t log B) − t·c₀. (c₀ = −log C(ε).) This is the
"(1+ε)-form": the heights enter the exponent *additively* with coefficient (1+ε). Note that putting (1+ε) in front
of Matveev's *product* A_1⋯A_t would not do: for our forms the product is P₀·log N_j with P₀ = log 2·log 3·log 7·log 10
= 3.41 (or 1.84 if a = 0), so the coefficient of log N_j would be ≥ 1.84(1+ε) > 1 + 1/k and the chain would be
vacuous. Applying LW(ε, c₀) to the forms of BAKER-CHAIN Lemma 3.3 (t = 4: 2, 3, 7, 10; t = 5 with N_j; B ≤ 3.33n + 2
since a < n log 10/log 2):
- top: log 80 − g_0 log 10 ≥ log Λ_0 ≥ −(1+ε)(log 420 + 4 log B) − 4c₀;
- interior: log 80 − g_j log 10 − log N_j ≥ log Λ_j ≥ −(1+ε)(log 420 + log N_j + 5 log B) − 5c₀, and log N_j ≤
  (n − E_j) log 10 + log 9 ≤ (n − g_j) log 10 + log 9, so g_j(1+ε) log 10 ≤ εn log 10 + log 80 + ε log 9 + (1+ε)(log 420
  + 5 log B) + 5c₀;
- bottom: −n log 10 ≥ log|Λ_k| ≥ −(1+ε)(log 420 + log N_k + 5 log B) − 5c₀, giving the same bound for E_k.
Summing: n(1 − kε/(1+ε)) ≤ C_top(n) + k·C_int(n)/(1+ε) with C_top, C_int = O(log n) + O(c₀); solved by fixed-point
iteration (`N_LW`). At ε = 1/(2(k+1)):

| k | c₀ = 0 | c₀ = 10 | c₀ = 50 | c₀ = 100 |
|---|---|---|---|---|
| 29 | 1291 | 2590 | 7578 | 13721 |
| 31 | 1391 | 2783 | 8126 | 14706 |
| 36 | 1645 | 3267 | 9498 | 17172 |
| 44 | 2058 | 4048 | 11701 | 21128 |

So LW is *better* than abc in shape (the top gap costs only O(log n), and the constant enters once per gap rather than
through √(n/log n)), and everything hinges on C(ε), about which the literature says nothing.

## 4. Vertex by vertex

### 4.1 What the existing 10^4000 corpus closes
Under hypothesis H, a vertex s is closed by the corpus iff N_H(k_max(s)) ≤ 4000 (children have ≤ N digits, hence
are corpus elements, hence are the listed children). Max k_max per tree (TABLES.md Table A): T_2: 29, T_4: 31,
T_6: 36, T_8: 44.

| hypothesis | k closed by 10^4000 | Tier B (k ≤ 29) | 128421199872 (31) | 3416267673274176 (34) | 913217421312 (35) | 1438916737499136 (36) | 112717121716224 (42) | 727326941773824 (44) |
|---|---|---|---|---|---|---|---|---|
| RST[1] | k ≤ 31 | all 13 closed | closed | extend to 10^{4466} | 10^{4687} | 10^{4912} | 10^{6363} | 10^{6883} |
| RST[β] | k ≤ 31 | closed | closed | 10^{4206} | 10^{4414} | 10^{4627} | 10^{5999} | 10^{6491} |
| RST[0] | k ≤ 34 | closed | closed | closed | 10^{4019} | 10^{4214} | 10^{5471} | 10^{5923} |
| 4√3 only (expected false) | k ≤ 36 | closed | closed | closed | closed | closed | 10^{4525} | 10^{4900} |
| RST[2] | k ≤ 29 | closed | 10^{4407} | 10^{5131} | 10^{5383} | 10^{5640} | 10^{7291} | 10^{7883} |
| Baker explicit | none (N ≥ 10^{42}) | — | — | — | — | — | — | — |

The extension cost: the number of {2,3,7}-units below 10^X is ≈ (X log 10)³/(6 log 2 log 3 log 7) = 1.37·X³, i.e.
8.8·10^{10} candidates at X = 4000 (the existing run) and 4.5·10^{11} at X = 6883 (×5), each to be tested for a zero
digit; the near-repunit structure (≤ 44 non-1 digits among ≈ 7000) could be used to prune, but a plain extension is
the honest certificate.

### 4.2 Trees and persistence
With the corpus trees as they stand (max persistence of a corpus vertex: Δ = 2: 5 (368947264), Δ = 4: 4
(128421199872), Δ = 6: 7 (3416267673274176), Δ = 8: 5 (1783627776); computed from `zf_below_1e4000.txt` this
session), closure of a tree gives pers(N) ≤ 1 + max pers for every N with Δ(N) = Δ, since p(N) is a vertex.

### 4.3 Why no abc-type hypothesis closes k ≥ 42 with the existing corpus
For (2.1) to give n ≤ 4000 at k = 44 one needs Φ_f(4000) ≤ log 10·(4000/45 − 4.2253) = 194.9, i.e. c/rad(abc) ≤
e^{194.9} = 10^{84.7} for every coprime triple with rad(abc) ≤ 10^{4004.2}. The RST model predicts triples with
log(c/k) ≈ 4√(3L/log L)(1 + log log L/(2 log L) + β/log L) ≈ 261 at L = log k ≈ 9220 (the leading term alone is 220);
so the required statement is contrary to the model at exactly that scale, and k = 42, 44 (and under RST[β], k ≥ 34)
genuinely need the extended enumeration.

## 5. The theorem

**Hypothesis RST[C₁]** (C₁ ≥ 0 real). For all coprime positive integers a, b with c = a + b and N := rad(abc) ≥ 16,
    c < N·exp( 4√(3 log N/log log N)·(1 + log log log N/(2 log log N) + C₁/log log N) ).
(RST 2014 Conjecture A asserts this for some C₁; their model gives C₁ = β + ε = 0.597 + ε for large N; every C₁ ≥ 0
holds for all known triples.)

**Theorem C (conditional, fully explicit).** Assume RST[1]. Let y = 2^a 3^b 7^c be a zero-free {2,3,7}-unit with n
decimal digits of which k ≥ 1 are different from 1. Then n ≤ N(k), where N(k) is the largest integer n with

    n ≤ (k+1)·( 4.2253 + (1/log 10)·4√(3L/log L)·(1 + log log L/(2 log L) + 1/log L) ),   L := log(16800·10^n);

in particular N(16) = 1324, N(22) = 2191, N(29) = 3433, N(31) = 3832, N(34) = 4466, N(35) = 4687, N(36) = 4912,
N(42) = 6363, N(44) = 6883 (table in §3.4). *Proof:* Lemma 2.1 and §3.4 give ABC_f for f(N) = exp(4√(3 log N/log₂N)
(1 + log₃N/(2log₂N) + 1/log₂N)) (N ≥ 16, constant below); Theorem A gives (2.1); Φ_f(n) = log f(16800·10^n) for
n ≥ 100 (§3.4); the stated values are the verified roots of (2.1) (`nk.out`). ∎

**Corollary C1 (the trees).** Assume RST[1]. Throughout, a *child* of a vertex s is a {2,3,7}-unit y ≥ 10 with
p(y) = s (PAPER.md §2.1) — such a y is automatically zero-free and 5-free, so Theorem C applies to it, and its number
of digits ≠ 1 is at most Ω(s) = k_max(s); "digital root" means the multiplicative digital root Δ(N) (the terminal
digit of the digit-product orbit). (a) For every vertex s of T_2 ∪ T_4 ∪ T_6 ∪ T_8 with k_max(s) ≤ 31
— that is, every vertex of T_2 and of T_4, all 13 Tier-B and all 15 Tier-A vertices, the 5 closed-below-height
vertices and the Tier-C vertex 128421199872 — every child of s has at most 3832 digits, hence is an element of the
10^4000 corpus, hence is one of the listed children; the antecedent trees of 2 and of 4 are exactly T_2 (33
vertices) and T_4 (4, 14, 27, 72, 98, 189, 294, 1161216, 128421199872), and **every integer with digital root 4 has
persistence ≤ 5, every integer with digital root 2 has persistence ≤ 6.** (b) Let C′ be the set of zero-free
{2,3,7}-units below 10^{6883} and T′_6, T′_8 the trees built from C′. If every vertex of T′_6 has k_max ≤ 36 and
every vertex of T′_8 has k_max ≤ 44 (true of the present T_6, T_8; new vertices, if any, must be checked), then the
antecedent trees of 6 and 8 are exactly T′_6 and T′_8; if moreover C′ adds no vertex (as expected), every integer with
digital root 6 has persistence ≤ 8 and every integer with digital root 8 has persistence ≤ 6. For T′_6 alone the
corpus below 10^{4912} suffices.

(a) needs no computation beyond the existing corpus; it does not use the modular enumeration, Lemma C, the sandwich,
Matveev or Yu at all — RST[1] plus the 10^4000 corpus closes everything with k_max ≤ 31 outright. (b) needs the
extension of the corpus from 10^{4000} to 10^{6883} (×5 the existing run) — **done 2026-10-21 (RESULT-SIEVE.md: no
zero-free {2,3,7}-unit above 140 digits below 10^{6884}; independently Chaffin's enumeration to 10^{20000}), so (b)
holds unconditionally on the computational side and Theorem D (PAPER.md §6.5) follows from RST[1].**

**What is explicit and what is not.** Theorem C is an ordinary theorem from an explicit hypothesis: every constant in
RST[1] and in N(k) is a number. The hypothesis is *our* instantiation of a conjecture whose authors assert only the
existence of C₁; the value 1 is justified by (i) RST's own model, which puts the truth at β = 0.597 for large N, and
(ii) the fact that no known triple comes within a factor 48/38.67 of violating RST[0]. It is not implied by, and does
not imply, the Masser–Oesterlé abc conjecture as usually stated. If one prefers an abc(ε, K) hypothesis: ε = 1/90 and
K = 10^{40} close k = 44 with the existing corpus, but that is stronger than RST predicts (RST-type bounds imply only
K ≈ 10^{58} at the optimal ε, with the same N = 4900–6900); ε = 1/90 and K = 10^{84.6} give N(44) ≤ 8000. Among
conjectures stated in the literature with every constant specified, only Baker's 2004 explicit abc yields a finite
N(k), and it is 10^{83}–10^{133} digits; Granville–Tucker's c < rad² and the IUT inequalities yield nothing.

## 6. Residual points
1. Formulas of RST (1.5)–(1.6), of CSS Theorem 1.3 and of Waldschmidt's Conjecture 2.5 were read through PDF text
   extraction; (1.5) was cross-checked against Martin–Miao's restatement and the (3.1) definitions against CSS's
   own identity G = F(A), F(x) = (1 + log x)/x. The Laishram–Shorey table of ω_ε is not used.
2. The merit record 38.67 is as reported by Martin–Miao (2014); de Smit's list was not fetched.
3. The persistence corollaries use the corpus maxima computed this session from `zf_below_1e4000.txt` (368947264: 5,
   128421199872: 4, 3416267673274176: 7, 1783627776: 5) and the per-tree max k_max from TABLES.md Table A (29, 31, 36,
   44).
4. Nothing here is machine-checked; the roots of (2.1) are computed in double precision. A referee pass (chat
   session, 2026-10-21 15:50 EDT, independent 40-digit full integer scan to n = 30000) reproduces all fourteen N(k)
   values under RST[1] and the C₁ = 0, β, 2 and bare columns exactly, with margins ρ(N)−N ≥ 0.0088 (k = 27); it also
   re-verified Lemma 1.1 on 300 random corpus elements (coprimality, radical bounds), Lemma 2.1 by exhaustion to 10^9,
   RST (1.5) against the published PDF, and the corpus against a brute-force enumeration below 10^80 (equal sets).
   Four wording fixes from that pass are applied above (log₃ domain, α for v₂(y′), the definition of child,
   multiplicative digital root). The exhaustiveness of the corpus above 10^80 remains a premise of the generating code. In every verified row the
   inequality holds at N(k) and fails at N(k)+1, but the margins can be small: 1.4·10⁻⁴ at N(k) (RST[2], k = 22) and
   0.005 at N(k)+1 (RST[2], k = 28) — far above the ≈10⁻¹² rounding error of the evaluation, yet a reader who wants
   slack may use N(k)+1 everywhere; no conclusion in §4–§5 changes.

## 7. Code
`/home/claude/night/conditional/nk.py` — Theorem A for f = RST[C₁] (grid sup for Φ, root scan, verification at N, N+1),
leading-term RST with κ ∈ {4√3, 8, 10}, Baker explicit via (3.1) (one- and two-regime), plain abc(ε, K) thresholds,
RST ⇒ abc(ε, K) conversion, and LW(ε, c₀). Output: `/home/claude/night/conditional/nk.out`.

## 8. Sources fetched this session
- Robert, Stewart, Tenenbaum, *A refinement of the abc conjecture*, Bull. LMS 46 (2014) 1156–1166: https://tenenb.perso.math.cnrs.fr/PPP/abc.pdf (also https://uwaterloo.ca/pure-mathematics/sites/default/files/uploads/documents/refinement-abc-conjecture.pdf).
- Laishram, Shorey, *Baker's explicit abc-conjecture and applications*, Acta Arith. 155 (2012): https://arxiv.org/pdf/1112.2461.
- Chim, Nair, Shorey, *Explicit abc-conjecture and its applications*, Hardy–Ramanujan J. 41 (2019): https://hrj.episciences.org/5117/pdf.
- Chim, Shorey, Sinha, *On Baker's explicit abc-conjecture*, Publ. Math. Debrecen 94 (2019): https://archive.mpim-bonn.mpg.de/3173/1/preprint_2018_51.pdf (abstract https://publi.math.unideb.hu/paper/2303/abstract/10_5486_PMD_2019_8397_abstract.pdf).
- Martin, Miao, *abc triples*: https://arxiv.org/pdf/1409.2974 (merit record; restatements of Baker 1996 and RST).
- Browkin–Brzeziński n-conjecture as quoted in *Improved lower bounds for strong n-conjectures*: https://arxiv.org/pdf/2409.13439v2.
- Waldschmidt, *Open Diophantine Problems* (Lang–Waldschmidt Conj. 2.5): https://arxiv.org/pdf/math/0312440; Waldschmidt, Lahore abc proceedings (Granville–Tucker, Baker 1996, RST restatements): https://webusers.imj-prg.fr/~michel.waldschmidt/articles/pdf/abcLahoreProceedings.pdf; Stewart's Waterloo notes: https://uwaterloo.ca/pure-mathematics/sites/default/files/uploads/documents/stewart.notes_1_0_0.pdf.
- Zhou, *The inter-universal Teichmüller theory and new Diophantine results over the rational numbers. I*: https://arxiv.org/abs/2503.14510.
- Wikipedia, abc conjecture (quality records): https://en.wikipedia.org/wiki/Abc_conjecture.
