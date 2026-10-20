# Multiplicative persistence ≥ 12: what is provable, what is computed, and where the wall is

Notation. For a positive integer n let p(n) be the product of its decimal digits, and
pers(n) = min { k ≥ 0 : p^k(n) < 10 }. So pers(277777788888899) = 11.
Let S = { 2^a 3^b 7^c : a, b, c ≥ 0 }.

Everything in §1–§3 is a proof. §4 is a verified computation. §5 states exactly which
single unproven statement separates us from a proof, and why it is out of reach today.
§6 is a heuristic, labeled as such.

---

## 1. Structure theorem

**Lemma 1.** For every n ≥ 10, pers(n) = 1 + pers(p(n)).  *(Definition.)*

**Lemma 2.** If pers(n) ≥ 2 then n contains no digit 0, and p(n) = 2^a 3^b 5^c 7^d.
*Proof.* A digit 0 gives p(n) = 0 < 10, so pers(n) = 1. Otherwise every digit is in
{1,…,9}, and each of these factors over the primes 2, 3, 5, 7. ∎

**Lemma 3.** If pers(n) ≥ 3 then p(n) is not divisible by 10.
*Proof.* If 10 | p(n), its last digit is 0, so p(p(n)) = 0 and pers(n) = 2. ∎

**Lemma 4 (odd multiples of 5 die fast).** If p(n) is an odd multiple of 5 then pers(n) ≤ 5.
*Proof.* Let m = p(n), odd with last digit 5. If m has an even digit, p(m) is divisible by
10, so p(p(m)) = 0, pers(m) ≤ 2 and pers(n) ≤ 3. Otherwise all digits of m are odd and one of them is 5,
so p(m) is again an odd multiple of 5. By induction the orbit of m consists of odd multiples
of 5 until it reaches a single digit, which is 5. Brier–Clavier–Gutsche–Naccache
(arXiv:2110.04263, 2021) prove that every integer whose multiplicative digital root is 5 has
persistence at most 5; hence pers(n) ≤ 5. ∎

(The BCGN result is the only external theorem used. Everything else here is elementary.)

**Theorem 1 (structure of a persistence-12 number).** Suppose pers(N) ≥ 12 and write
x_i = p^i(N). Then

1. x_1 ∈ S and pers(x_1) ≥ 11;
2. x_1, x_2, …, x_7 all lie in S;
3. x_1, …, x_10 are all zero-free and ≥ 10.

*Proof.* (3): x_i ≥ 10 for i ≤ 11 by definition of pers(N) ≥ 12, and x_{i+1} = p(x_i) ≥ 10 > 0
forces x_i zero-free for i ≤ 10.
(1): By Lemma 2, x_1 = 2^a 3^b 5^c 7^d. By Lemma 3, not both a ≥ 1 and c ≥ 1. If c ≥ 1 then
a = 0 and x_1 is an odd multiple of 5, so pers(N) ≤ 5 by Lemma 4, contradiction. So c = 0 and
x_1 ∈ S. pers(x_1) = pers(N) − 1 ≥ 11 by Lemma 1.
(2): The argument in (1) used only pers ≥ 6 (to invoke Lemma 4). Since pers(x_j) ≥ 12 − j ≥ 6
for j ≤ 6, applying it to x_j in place of N gives x_{j+1} ∈ S for j + 1 ≤ 7. ∎

**Theorem 2 (equivalence).** A number of persistence ≥ 12 exists if and only if some
x ∈ S has pers(x) ≥ 11.
*Proof.* (⇒) Theorem 1(1). (⇐) Given x = 2^a 3^b 7^c with pers(x) ≥ 11, let N be the
digit string 2…2 3…3 7…7 (a twos, b threes, c sevens; take N = 11 if a=b=c=0). Then p(N) = x,
so pers(N) = 1 + pers(x) ≥ 12 by Lemma 1. ∎

So the entire problem is: **does S contain an element of persistence ≥ 11?**
The known persistence-11 number is exactly this construction:
2^19·3^4·7^6 = 4996238671872 has persistence 10, and 277777788888899 is the smallest N with
p(N) equal to it.

---

## 2. Size transfer

**Theorem 3.** Let log₁₀ 9 = 0.954242…. If N has D digits then x_1 = p(N) has at most
⌊0.954243·D⌋ + 1 digits. Consequently: if no x ∈ S with at most M digits has pers(x) ≥ 11,
then no N with at most ⌊(M − 1)/0.954243⌋ digits has pers(N) ≥ 12.
*Proof.* p(N) ≤ 9^D = 10^{D log₁₀ 9}. ∎

**Theorem 4 (orbit shrinkage).** If x has d ≥ 2 digits then p(x) has at most
⌊0.954243·d⌋ + 1 digits, so along any orbit the digit count decays at least geometrically
with ratio ≈ 0.9542 per step: from a D-digit N, x_10 has at most ≈ 0.626·D + 22 digits.
(There is no comparable lower bound, because digits equal to 1 contribute nothing.)

---

## 3. Minimal counterexample normalization

**Lemma 5.** If a persistence-12 number exists, the smallest one has no digit 1 and no digit 0,
and its digits are non-decreasing. Removing a 1 or sorting digits does not change p(N) and
only decreases N. ∎

**Corollary.** Combining with the published lower bound (OEIS A003001: a(12), if it exists,
exceeds 2.67·10^30000), a minimal counterexample N has ≥ 30001 digits all ≥ 2, so
x_1 = p(N) ≥ 2^30001 > 10^9031: **x_1 is a zero-free element of S with at least 9032 digits.**

---

## 4. Verified computation (this session)

Program: `zfsieve.c` enumerates every (a, b, c) with 2^a 3^b 7^c < 10^dmax. For each
candidate it maintains the low 144 decimal digits exactly (24 limbs of 10^6) and the leading
11 digits via 80-bit log arithmetic; a 0 in either window rejects the candidate with no
possibility of a false rejection. Survivors are recomputed exactly with GMP (`zfcheck.py`),
filtered for zero-freeness, and their persistence computed. The sieve was validated against a
brute-force enumeration to 370 digits (identical output: 8807 zero-free elements).

Results:

| range searched            | triples (a,b,c) | zero-free elements of S | largest zero-free | max pers |
|---------------------------|-----------------|-------------------------|-------------------|----------|
| < 10^370 (brute force)    | 7.0 × 10^7      | 8807                    | 140 digits        | 10       |
| < 10^600 (sieve)          | 3.0 × 10^8      | 8807                    | 140 digits        | 10       |
| < 10^4000 (sieve)         | 8.79 × 10^10    | 8807                    | 140 digits        | 10       |

The largest zero-free element of S found: 2^25 · 3^227 · 7^28 (140 digits).
The only elements of S with persistence 10 are 2^4·3^20·7^5 = 937638166841712 and
2^19·3^4·7^6 = 4996238671872; both map to 438939648 and share the rest of their orbit.

**Theorem 5 (unconditional, this computation).** Every zero-free element of S below
10^4000 has at most 140 digits; there are exactly 8807 of them, and none has persistence
≥ 11. By Theorem 3, **no integer with at most 4190 digits has persistence ≥ 12.**
(Run time: 70 CPU-minutes on two cores; 87,932,095,342 triples; 17,961 sieve survivors,
8807 of which are zero-free, all re-verified exactly.)

This is far weaker than the published bound (30000 digits) and is reported only as an
independent, from-scratch confirmation with code you can read in full.

---

## 5. The exact obstruction

**Conjecture Z (zero-freeness).** Every element of S with more than 140 digits contains the
digit 0. Equivalently: S has exactly 8807 zero-free elements. (Verified for all elements of
S below 10^4000.)

**Theorem 6 (conditional).** Conjecture Z implies that no integer has persistence ≥ 12.
*Proof.* By Theorem 1, a persistence-12 number N gives x_1 ∈ S zero-free with pers(x_1) ≥ 11.
By Conjecture Z, x_1 is one of the 8807 zero-free elements of S with ≤ 140 digits, all of
which were enumerated in §4 and have persistence ≤ 10. Contradiction. ∎

So the multiplicative-persistence conjecture has been *reduced* to Conjecture Z plus a
finite computation that is already done. Why can't we prove Conjecture Z?

* It contains, as the special case b = c = 0, the statement "2^86 is the last zero-free
  power of 2" — an open problem since the 1970s.
* The best available tool, Baker's theory of linear forms in logarithms, yields results of
  the type "the number of *nonzero* digits of 2^n tends to infinity" (Stewart, 1980). It
  cannot force a single specified digit to *appear*; proving a 0 appears somewhere in
  9000 digits is equivalent to a strong form of equidistribution of the digits of
  2^a 3^b 7^c, which is not known for any such sequence (not even normality of 2^n in
  base 10).
* The alternative route in the literature (Brier et al.; the 2026 2-adic-obstruction
  paper) tries to bound the exponent a via the 2-adic valuation of digit products, and is
  currently stuck exactly at even terminal digits.

Any claimed "proof that 12 is impossible" that does not resolve Conjecture Z (or something
at least as hard) is not a proof.

---

## 6. Heuristic (not a proof): the counterexample does not exist

Model: the inner digits of a d-digit element of S are independent uniform digits.
Evidence for the model: in §4, the number of zero-free elements of S in each 10-digit band
tracks Σ 0.9^d over the band to within statistical noise, all the way down to zero.

Under the model, the number of elements of S with d digits is ≈ 4.12·d² (the (a,b,c)
simplex has volume 1.373·D³ below 10^D), so the expected number of zero-free elements with at
least d₀ digits is about 41·d₀²·0.9^{d₀}. At d₀ = 141 this is ≈ 0.3 (consistent with finding
none); at d₀ = 9032 — the minimum size of x_1 by §3 — it is about **10^−404**.

That is the probability of a persistence-12 number existing, under the only model that has
ever matched the data. It is not a proof. It is the reason nobody is searching.

---

## 7. Decisive summary

* Proven: persistence ≥ 12 exists ⟺ some 2^a 3^b 7^c has persistence ≥ 11; the first ten
  iterates of a counterexample are zero-free and the first seven lie in S; a minimal
  counterexample's first product is a zero-free 2^a 3^b 7^c with ≥ 9032 digits.
* Proven conditionally: Conjecture Z ⟹ max persistence is 11.
* Computed: no zero-free 2^a 3^b 7^c beyond 140 digits up to the search limit; no
  persistence ≥ 12 below the transferred digit bound.
* Open: Conjecture Z, which is at least as hard as the zero-free-powers-of-2 problem.
* Heuristic: a counterexample exists with probability ~ 10^−404.

---

## 8. Attack on Conjecture Z — the honest map

### 8.1 How the conjecture splits by terminal digit

Let Δ(N) = p^{pers(N)}(N) ∈ {0,…,9} be the terminal digit.

| Δ(N)        | status                                                                                   |
|-------------|------------------------------------------------------------------------------------------|
| 1, 3, 7, 9  | pers ≤ 1, **proved** (Brier–Clavier–Gutsche–Naccache 2021)                               |
| 5           | pers ≤ 5, **proved** (same paper)                                                        |
| 2, 4, 6, 8  | open; BCGN give an exponential-Diophantine program; the Aug-2026 paper (arXiv:2608.27802) supplies the missing 2-adic bound that makes each case a *finite* search — but the search is ~12^30 ≈ 2^107 equations, far beyond classical compute (the authors suggest Grover's algorithm) |
| **0**       | **not addressed by any published method.** The BCGN method works *backward* from the target digit; the target 0 is reached from any number containing a 0 digit, so there is no finite anchor to iterate backward from. |

The persistence-11 champion ends at 0 (…→ 54 → 20 → 0). Every "natural" long chain ends at 0, because the generic way a product-of-digits orbit dies is by acquiring a zero digit. **Target 0 is the main case, and target 0 is exactly Conjecture Z.** (Theorem 6 covers all targets, but for targets 2–8 there is at least an alternative, if astronomically expensive, route; for target 0 there is none.)

### 8.2 Every route into Conjecture Z, and where it dies

**Route 1 — low digits (2-adic / 5-adic).** For a ≥ K, x = 2^a·m has x mod 10^K = 2^K·(m·2^{a−K} mod 5^K). As (a,b,c) vary these residues cover a positive-density subset of (Z/10^K); the zero-free K-digit strings have density 0.9^K > 0, so zero-free residues are always attained. Low digits alone can never force a 0. *(Dead on arrival; this is also why the sieve in §4 can filter but not prove.)*

**Route 2 — leading digits (Weyl / Benford).** This route proves something — see Theorem 7 below — but only a *density-zero* statement, not finiteness, and the gap is exponential: Baker's theorem makes the equidistribution error polynomially small in the digit count D, while "no zero in the leading D digits" has probability 0.9^D.

**Route 3 — Baker / Stewart (linear forms in logarithms).** Stewart (1980) proves the number of *nonzero* digits of 2^n tends to infinity: a number with few nonzero digits is a short sum of powers of 10, which gives a small linear form in logarithms that Baker's theorem forbids. A zero-free number has *all* digits nonzero — the opposite of sparse — so there is no linear form to bound. Baker's machinery is silent on "contains the digit 0".

**Route 4 — chain structure.** A counterexample needs not one but ten consecutive zero-free products: x_{i+1} = 2^{n₂+2n₄+n₆+3n₈}·3^{n₃+n₆+2n₉}·7^{n₇} where n_d counts digit d in x_i. This is a strong constraint heuristically (each step costs another factor 0.9^{digits}) but it gives no new algebraic handle: nothing about the digit counts of x_i is controllable.

**Route 5 — the special case b = c = 0.** Conjecture Z restricted to pure powers of 2 says 2^86 is the last zero-free power of 2. This has been open since the 1970s with no partial result beyond density statements. Any proof of Conjecture Z proves this; so Conjecture Z is at least as hard as a 50-year-old open problem that the best tools in Diophantine approximation have not scratched.

### 8.3 What classical tools do prove

**Lemma 6 (multiplicative independence).** 1, log₁₀2, log₁₀3, log₁₀7 are linearly independent over ℚ.
*Proof.* i·log₁₀2 + j·log₁₀3 + k·log₁₀7 = l means 2^i 3^j 7^k = 10^l = 2^l 5^l; by unique factorization k = 0, j = 0, i = l and 5^l = 1, so l = 0. ∎

**Theorem 7 (zero-free elements of S have density zero).** Let S(D) = {x ∈ S : x < 10^D} and Z(D) ⊂ S(D) its zero-free elements. Then |Z(D)| / |S(D)| → 0 as D → ∞.
*Proof.* Write α, β, γ for log₁₀ 2, 3, 7 and θ(a,b,c) = aα + bβ + cγ, so x = 10^{θ} and frac(θ) determines the leading digits of x. By Weyl's criterion it suffices that for every integer h ≠ 0,
Σ_{(a,b,c): θ ≤ D} e(h·θ(a,b,c)) = o(D³).
Fix (a, b); the inner sum over c is a geometric series with ratio e(hγ) ≠ 1 (γ irrational by Lemma 6), hence bounded by 1/|sin πhγ|, independent of a, b, D. There are O(D²) pairs (a, b), so the whole sum is O_h(D²) = o(D³), while |S(D)| ~ 1.373·D³. Hence frac(θ) is equidistributed mod 1 over S(D). The leading K digits of x form a zero-free block iff frac(θ) lies in a finite union of intervals of total length ρ_K = Σ_{m zero-free, K digits} log₁₀(1 + 1/m). Equidistribution gives limsup |Z(D)|/|S(D)| ≤ ρ_K for every K; and ρ_K → 0 because the Benford probability that the k-th digit is 0 tends to 1/10, so ρ_K ≤ ∏_{k≤K}(1 − p_k) → 0. ∎

Theorem 7 is the ceiling of what Weyl/Baker-type methods give. Making it effective (Baker) yields |Z(D)|/|S(D)| ≤ C·D^{−δ} for some small δ > 0 — but a persistence-12 counterexample needs a single zero-free element with ≥ 9032 digits, and ruling that out requires an error term below 0.9^{9032}, i.e. exponentially small. No known method produces exponentially small error terms for digit distributions of a single exponential sequence; this is the same barrier that leaves the base-10 normality of 2^n, and even "every power of 2 above 2^86 contains a 0", open.

### 8.4 Verdict

Conjecture Z is not provable with any method currently known to mathematics. The reduction in §1–§5 is the complete, honest content: the multiplicative persistence conjecture is equivalent (given the finished finite computation) to a digit-distribution statement about 2^a 3^b 7^c that sits strictly beyond Baker's theorem, and whose easiest special case has been open for half a century. Targets 2–8 admit an alternative finite-but-astronomical program; target 0 — the generic case — admits none.

Sources: Brier, Clavier, Gutsche, Naccache, *The Multiplicative Persistence Conjecture Is True for Odd Targets*, arXiv:2110.04263; *Resolving the 2-Adic Obstruction for Nonzero Even Targets*, arXiv:2608.27802; Stewart, *On the representation of an integer in two different bases*, J. reine angew. Math. 319 (1980); OEIS A003001.

---

## 9. The trees, rebuilt independently (this session)

Every element of S whose orbit ends at a nonzero even digit is zero-free and therefore lies in
the §4 list. Grouping the 8807 verified zero-free elements of S by terminal digit:

| terminal digit | elements of S below 10^4000 | max pers(x) | ⇒ max pers(N), N ≤ 4190 digits |
|----------------|-----------------------------|-------------|--------------------------------|
| 0              | 8626                        | 10          | 11                             |
| 2              | 33                          | 5           | 6                              |
| 4              | 9                           | 4           | 5                              |
| 6              | 84                          | 7           | 8                              |
| 8              | 51                          | 5           | 6                              |
| 1, 3, 7, 9     | 1 each (the digit itself)   | 0           | 1                              |
| 5              | 0 (no element of S is divisible by 5) | — | 5 (BCGN)                   |

The counts 33, 9, 84, 51 are exactly the vertex counts of the antecedent trees A_2, A_4, A_6, A_8
reported by Brier–Clavier–Gutsche–Naccache, obtained there by a completely different
(backward, Diophantine) method. The two computations confirm each other: below 10^4000 the
trees are complete. The tree A_4 in full: 4 ← 14 ← {27, 72} ; 72 ← {98, 189, 294, 1161216} ;
1161216 ← 128421199872 (a leaf). Longest chain: 128421199872 → 1161216 → 72 → 14 → 4.

**Theorem 8 (unconditional).** Any integer with at most 4190 digits has persistence at most
11; if its terminal digit is 2, 4, 6 or 8, its persistence is at most 6, 5, 8 or 6 respectively.

### 9.1 What would finish the even targets

For a vertex s of A_d, the next layer consists of all y ∈ S with p(y) = s. Such a y has at most
log₂ s non-1 digits, so y = R_n + Σ_j (d_j − 1)·10^{e_j} with R_n the repunit and a bounded
number of terms, and y ∈ S reads

  9·2^a 3^b 7^c − 10^n − Σ_j (d_j − 1)·10^{e_j} = −1,

an S-unit equation over {2, 3, 5, 7} in a bounded number of terms. By the Subspace Theorem
(Evertse; van der Poorten–Schlickewei) each such equation has finitely many non-degenerate
solutions, so **every vertex of A_d has finitely many children** — ineffectively. This does not
bound the *depth* of A_d, which is the actual content of the conjecture (an infinite finitely-
branching tree has an infinite path by König's lemma, i.e. unbounded persistence). The 2026
2-adic bound plus BCGN's modular lifting make the depth question a finite but ~2^107-sized
search per target. That search is the open computational problem; it is well-posed and
nobody has done it.

### 9.2 Verdict, unchanged

Target 0 — 98% of all candidates and the home of the persistence-11 record — is Conjecture Z,
untouched by every known method. Targets 2–8 are finite problems of astronomical size. Nothing
proved here or elsewhere moves the needle on whether 12 is possible; everything proved here
sharpens *why* it is almost certainly not, and *where* a proof would have to come from.
