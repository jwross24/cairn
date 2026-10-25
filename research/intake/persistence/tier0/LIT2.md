# LIT2 — Literature scout: can anything beat the exponential-in-k Baker chain, or close Tier C without pattern enumeration?

*2026-10-20, scout `lit2`. Sources fetched this session are listed per entry (arXiv/journal). Where I could not reach the
original (Stewart 1980, Evertse 1984 formulas lost to OCR) I say which secondary source the statement is quoted from.
Derivations marked [own] are mine, not from the literature, and are included only to show *what strength of theorem*
would be needed for (A).*

## 0. Bottom line (one paragraph)

Our bound n < G(k,a) with log₁₀ G ≈ 11.5 + 13.9k (+ k log₁₀ log G) is Stewart's 1980 iterated-gap argument made
explicit; its shape — number of digits ≤ (C·log n)^{k+1}, i.e. (Ck log k)^{k+O(1)} — is **exactly** the shape of every
effective result in the literature on S-units with few nonzero digits (Stewart 1980; Bugeaud–Kaneko 2018, Lemma 3.1
and Thm 1.2; Bugeaud 2018; Bugeaud 2026). No published effective bound has better-than-exponential dependence on k.
The reason is structural: Baker/Matveev/Yu give "gap ≤ C·h(rest)·log B" with C ≳ 10¹³, so the admissible size
*multiplies* at every digit; a polynomial-in-k bound needs "gap ≤ ε·h(rest) + O(log n)", which is the strength of the
Lang–Waldschmidt conjecture or of abc (and *is* what the Subspace theorem gives — ineffectively). On the other side,
every known complete resolution of an exponential equation with many terms (Dimitrov–Howe 2021: 22–25 terms;
Bertók–Hajdu 2016: 9 unknowns; Bajpai–Bennett 2023: 5 terms) is a residue-class lifting/sieve whose cost is exponential
in the number of terms (Dimitrov–Howe: ×3.5 per extra term, 8.6 CPU-days at 22 terms). **Neither (A) nor (B) exists in
the literature. Tier C (k = 31–44) is beyond current unconditional methods; conditionally on a Robert–Stewart–Tenenbaum-
strength abc it would collapse to n = O(k²/log k) ≈ 5·10³ digits, which is a finite search, but that is not a proof under
RULE 2.**

## 1. Paper-by-paper

Notation: n = number of decimal digits of y′ (our n); k = number of non-1 digits (standard form 9y′+1 has k+1 nonzero
digits plus the leading 10^n); S = {2,3,7} (or {2,3,5,7} for the 10-adic side).

### 1.1 C. L. Stewart, *On the representation of an integer in two different bases*, J. reine angew. Math. 319 (1980), 63–72.
(Could not fetch the Crelle scan — robots-blocked; statements taken from Bugeaud–Cipu–Mignotte, Bugeaud–Kaneko 2018 §1,
Bugeaud arXiv:2608.23017 §1.)
- **Statements.** (i) Two bases: for multiplicatively independent a, b and m > 25, BC(m,a) + BC(m,b) ≥
  log log m/(log log log m + C) − 1 (BC = number of digit blocks; C effective in a, b). (ii) S-unit/power case: for
  multiplicatively independent a, b ≥ 2 and n beyond an effective bound, the base-b expansion of aⁿ has more than
  log n/(2 log log n) nonzero digits — equivalently, for an S-unit N: #nonzero digits > log log N/(2 log log log N).
- **Dependence on k.** Inverting (ii): an S-unit with k nonzero digits has log log N ≲ 2k log log log N, i.e.
  number of digits ≤ (C log n)^{k} ≈ (Ck log k)^{k}. This is our chain (BAKER-CHAIN.md) with unspecified constants.
- **Method.** Baker's theory of linear forms in complex logarithms applied once per digit gap; the upper block enters
  as an algebraic number of height ≈ (n − E_j) log b. Effective, but constants not made explicit.
- **Verdict.** It *is* our Theorem U. Nothing to gain; confirms our shape is the state of the art.

### 1.2 Y. Bugeaud, *On the digital representation of integers with bounded prime factors*, Osaka J. Math. 55 (2018), 315–324; arXiv:1609.07926.
- **Thm 1.1** (k ≥ 2 nonzero digits, S finite, ε > 0): [u_j^{(k)}]_S < (u_j^{(k)})^ε for j large — the S-part of
  integers with ≤ k nonzero digits is eventually tiny; hence only finitely many such integers are S-units. **Proof via
  Schmidt's Subspace theorem: ineffective** for every k.
- **Thm 1.2** (k = 3, i.e. three nonzero digits): effective c₄, c₅ with [u]_S ≤ u^{1−c₄}, and P[u] > (1−ε)(log log u)
  (log log log u)/(log log log log u). **Cor 1.3:** any large n not divisible by b that is (1−ε)(log log n)(log log log n)/
  (log log log log n)-smooth has ≥ 4 nonzero digits.
- **Method (Thm 1.2):** one case split on the top gap (m > 2n: Matveev archimedean, Thm 2.2 with constant 8·30^{n+3}n^{9/2};
  m ≤ 2n: Yu's p-adic bound, Thm 2.3, p = smallest prime of b). No iteration. The paper says the power-saving S-part
  argument "works only for k ≤ 3".
- **Dependence on k.** Effective part only for k ≤ 3; general k only via Subspace (ineffective).
- **Verdict.** Not usable for Tier C (k ≥ 31): the effective results stop at three digits; the all-k result is ineffective.

### 1.3 Y. Bugeaud, H. Kaneko, *On the digital representation of smooth numbers*, Math. Proc. Cambridge Philos. Soc. 165 (2018), 533–540; arXiv:1704.00432.
- **Lemma 3.1 (the engine).** N with k nonzero digits at positions 0 = n₁ < … < n_k, all prime factors in
  S = {q₁<…<q_s}, log N ≥ 2 log b·(8 log b/log 2)^k. Then
  n_k ≤ (c·C^s·(k−2)·∏ log q_i·log(k log q_s))^{k−2}   (k* = max(k−2,1)),
  c effective depending on b, C absolute. [(3.3) in the paper.]
- **Thm 1.2** (the clean form): for n with exactly k nonzero digits, (log log n)/k ≤ c + log k + ω(n)(C + log log P[n]) +
  log log(k log P[n]). **Cor 1.5:** every integral S-unit n ≥ n₀(b,S,ε), b ∤ n, has > (1−ε) log log n/log log log n nonzero
  digits (Bugeaud 2026 quotes it with (1/2) in place of (1−ε)). **Thm 1.1:** P[u_j^{(k)}] > (1/(k−2) − ε)(log log u)(log log log u)/(log log log log u).
- **Method.** NOT an iteration: Case n_k ≥ 2n_{k−1}: Matveev on the top gap. Case n_k < 2n_{k−1}: pigeonhole over the
  k−2 interior gaps — choose the least ℓ with n_{1+ℓ} ≥ n_k^{ℓ/(k−2)}; then the lower part has height ≲ n_k^{(ℓ−1)/(k−2)}
  while v_p(Λ_u) ≥ ¼ n_k^{ℓ/(k−2)}; Yu's theorem gives n_k^{1/(k−2)} ≤ c C^s ∏log q_i (k−2) log(n_k^{1/(k−2)}). Constants
  c, C **not explicit**.
- **Dependence on k.** Number of digits ≤ (C_S·k·log k)^{k−2}: exponential in k log k, same as our G(k,a); the base has a
  factor k from the pigeonhole and C^s·∏log q_i ≈ our P₀·C(t); their log B factor is log(n_k^{1/(k−2)}) ≈ log(k log k) rather
  than our log n ≈ log(k log k) — identical order. Remark 4.3: for fixed k ≥ 4 the method gives only
  [u]_S ≤ u·exp(−(log u)^{(1−ε)/(k−2)}) — again exponent 1/(k−2), i.e. the same k-dependence; they state the k = 3
  power-saving "does not extend to k > 3".
- **Verdict.** The cleanest published proof that "(C log n)^{k}" is intrinsic to Baker-type methods on this problem. The
  pigeonhole trick replaces the k-fold iteration by one inequality but does not change the exponent. Nothing for Tier C.

### 1.4 Y. Bugeaud, *On the binary representation of powers of 3*, arXiv:2608.23017 (24 Aug 2026).
- **Thm 1.2** (S finite, digit word of factor complexity ≤ Cℓ, b^{⌊n/(C+2)⌋} ∤ x): for m large x_m has a prime factor outside
  S; [x_m]_S < x_m^{1−δ}. Subspace theorem, **ineffective**. **Thm 1.6 (effective, Matveev):** if the digit word of an
  S-unit is W^t then t ≤ C(S,b). Intro restates Stewart 1980 and Bugeaud–Kaneko Cor 1.5 as the only effective digit-count
  bounds for S-units.
- **Verdict.** Confirms that as of Aug 2026 the effective state of the art is unchanged (Stewart/B–K shape). Thm 1.6 is a
  "periodic digit word" result — our near-repunits R_n + bumps are not of the form W^t once k ≥ 1.

### 1.5 M. Bennett, Y. Bugeaud, M. Mignotte, *Perfect powers with few binary digits and related Diophantine problems*, Ann. Sc. Norm. Super. Pisa (5) 12 (2013), 941–953; and *…, II*, Math. Proc. Cambridge Philos. Soc. 153 (2012), 525–540.
- **Thm 2.1:** x^a + x^b + 1 = y^q ⇒ q < C (absolute) or q | φ(x). **Thm 2.3:** x₁^a + x₂^b + x₃^c + 1 = y^q ⇒ q ≤ C log⁴ max x_i.
  **Remark 5.2:** for x^a + x^b + x^c + x^d + 1 = y^q (five digits) they *cannot* bound q in general — only when b is not
  too large compared with c (a gap condition). Part II solves x^a + x^b + 1 = y^q for x ∈ {2,3} and 2^a+2^b+2^c+1 = y^q (q ≥ 5)
  completely, with Laurent's two-log bound (25.2·(max{log b₀+0.38,10})²·h(α₁)h(α₂)) and Bugeaud's p-adic two-log bound.
- **Verdict.** ≤ 4 nonzero digits, perfect-power target (different equation). Their obstruction at five digits is the same
  "height of the rest" obstruction. Nothing for Tier C.

### 1.6 P. Corvaja, U. Zannier, *Finiteness of odd perfect powers with four nonzero binary digits*, Ann. Inst. Fourier 63 (2013), 715–731; *S-unit points on analytic hypersurfaces*, Ann. Sci. ENS 38 (2005), 76–92; *On the Diophantine equation f(aᵐ,y) = bⁿ*, Acta Arith. 94 (2000), 25–40.
- Finiteness of odd perfect powers with exactly four nonzero binary digits; tools: Subspace theorem (via integral values of
  analytic series at S-unit points), Roth, 2-adic Padé, two-log bounds. **Ineffective.**
- **Verdict.** Ineffective; no size bound. Not usable.

### 1.7 J.-H. Evertse, *On sums of S-units and linear recurrences*, Compositio Math. 53 (1984), 225–244. H. P. Schlickewei, *Linear equations in integers with bounded sum of digits*, J. Number Theory 35 (1990), 335–344. Evertse–Schlickewei–Schmidt, *Linear equations in variables which lie in a multiplicative group*, Ann. of Math. 155 (2002), 807–836. Amoroso–Viada, Duke Math. J. 150 (2009).
- Evertse Thm 2 (K = Q form; numdam OCR drops the display, quoted as in Evertse–Győry, *Unit Equations*, Ch. 6): for
  every ε > 0 there is C(ε,S,n) — **ineffective** (Schlickewei's p-adic Subspace theorem) — such that for S-unit integers
  x₀,…,x_n with no vanishing subsum, |x₀+…+x_n| ≥ C·(max|x_i|)^{1−ε} (up to the S-part of the sum). Applied to our
  prefix sums 10^n + Σ_{i≤j} c_i 10^{E_i} − M = 1 − Σ_{i>j} c_i 10^{E_i} this says **every prefix gap n − E_{j+1} ≤ εn + C**:
  the ε-version of the gap bound, i.e. the polynomial-in-k shape — but C is ineffective.
- ESS 2002: number of non-degenerate solutions of a₁x₁+…+a_N x_N = 1 in a rank-r group ≤ exp((6N)^{3N}(r+1)); Amoroso–Viada
  ≤ (8N)^{4N⁴(N+r+1)}. For us N = k+2 (k+3 terms, one normalised to 1), r = 4 (group ⟨2,3,5,7⟩): all our solutions are non-degenerate (all terms but −M, −1
  positive; no subsum vanishes since c_j ≥ 9). So the *number* of Tier-C solutions is finite and explicitly bounded
  (doubly exponential in k) — sizes are not. Schlickewei 1990 is the digit-sum special case of the same count.
- **Verdict.** The Subspace theorem delivers the ε-gap (polynomial-in-k) statement; it is the *only* place that shape
  exists, and it is ineffective. Not usable for closure.

### 1.8 P. Bajpai, M. A. Bennett, *Effective S-unit equations beyond 3 terms: Newman's conjecture*, arXiv:2308.05162 (2023).
- **Thm 1:** nondegenerate solutions of a₁u₁+…+a₅u₅ = 0 in S-units with |S| ≤ 3 are effectively bounded; Thm 7: (n−4)×n systems.
  Method: Vojta's pigeonhole matching of large terms + Matveev + Yu + Laurent two-log + Hajdu's small fundamental units;
  computation ≈ 1.2·10⁷ cases with moduli 2⁴⁸…2⁹⁰, N₁₈₀ = gcd(2¹⁸⁰−1,3¹⁸⁰−1).
- Intro: three-term S-unit equations are effective by Baker; for n ≥ 4 terms effective resolution "remains, in almost every
  situation, beyond current technology"; previous record Vojta 1983 (n = 4, |S| ≤ 3), Skinner.
- **Verdict.** General effective S-unit equations stop at 5 terms as of 2023. Our k+3 ≥ 34-term equation is effective at all
  *only* because every term is a bounded multiple of a power of 10 (Stewart's structure); Bajpai–Bennett's matching trick
  needs |S| ≤ 3 and few terms. Nothing for Tier C.

### 1.9 T. Miyazaki, *Solving an infinite number of purely exponential Diophantine equations with four terms*, arXiv:2503.00843 (2025).
- n^x + (n+1)^y + (n+2)^z = (n+3)^w, n ≡ 3 (mod 4): only (3,3,1,1,2), (3,3,3,3,3). Baker (real and p-adic) + congruences +
  Bertók–Hajdu's algorithm. Abstract: effective resolution of S-unit equations with ≥ 4 terms is "an open problem".
- **Verdict.** Confirms 4 terms is the frontier for general purely exponential equations in 2025.

### 1.10 Cs. Bertók, L. Hajdu, *A Hasse-type principle for exponential Diophantine equations and its applications*, Math. Comp. 85 (2016), 849–860; arXiv:1407.6499. Also Hajdu–Tijdeman, *Skolem's conjecture confirmed for a family of exponential equations*, Acta Arith. 192 (2020), 105–110 (and II, III).
- **Conjecture (Skolem-type):** if a₁b₁₁^{α₁₁}⋯ + … = c has no solutions, there is m with no solutions mod m. **Thm 2.1:**
  true for almost all c (density). **Method:** exhaustive search for small solutions (heuristic completeness) → for each
  unknown, replace a_i by a_i b^{α₀} and find a modulus m killing the modified congruence ⇒ α < α₀; iterate. Moduli built
  from primes with λ(m) composed of 2s and 3s (Erdős–Pomerance–Schmutz); moduli up to ≈ 7·10¹². **Solved completely:**
  3^a+5^b+11^c+13^d+17^e−19^f = 0 (6 unknowns), 1+5^{a₁}+…+5^{a₈}−17^{a₉} = 0 (9 unknowns), 2^a3^b+5^c7^d−11^e13^f = 1.
  No Baker bound used; A (bound on the smallest exponent) "not computable in advance". Hajdu–Tijdeman 2020 prove the
  conjecture itself only for u^x − v^y = 1 with u or v prime.
- **Dependence on #terms.** Not analysed; the modulus search enumerates residues of all exponents mod λ(m) — i.e. it *is*
  residue-pattern enumeration — and the largest instance is 9 exponents.
- **Verdict.** This is the literature version of our modular ladder. It does not avoid pattern enumeration, is conditional
  in its completeness step, and tops out at 9 unknowns. Not (B).

### 1.11 V. Dimitrov, E. Howe, *Powers of 3 with few nonzero bits and a conjecture of Erdős*, arXiv:2105.06440 (2021).
- **Thm 1.1:** 3^x is a sum of ≤ 22 distinct powers of 2 only for x ≤ 25. **Thm 1.2:** 2^x is a sum of ≤ 25 distinct powers
  of 3 only for x ∈ {0,2,8}. Unconditional, "completely elementary": a chain of moduli M₁ | M₂ | … (M₁ = 2⁴·7·73, 64 factors,
  mostly primes ≡ 1 mod 2^u3^v), lifting solutions level by level; balanced steps by meet-in-the-middle on sorted partial
  sums, unbalanced steps by discrete logs; stop when every exponent is "determinate". No linear forms in logarithms. They
  note Stewart's effective bound gives B(22) > 4.9·10⁴⁶ and B(25) > 5.4·10⁵⁴ for these problems ("grow very quickly").
- **Cost (Table 3, wall-clock s, Magma, quad-core):** n=13: 19; 14: 52; 15: 145; 16: 457; 17: 1469; 18: 5746; 19: 17744;
  20: 53617; 21: 139347; 22: 743737. Growth ≈ ×3.5 per extra term. Table 5 (powers of 2 in base 3): n=20: 789; 22: 9792;
  24: 140036 (≈ ×12 per two terms).
- **Verdict.** The largest complete resolution of an "S-unit with few nonzero digits" equation on record: 22–25 terms,
  by residue-class lifting whose cost is exponential in the number of terms. Extrapolating ×3.5 per term to our k = 31–44
  gives 10⁴–10¹⁰ × 8.6 days — the same conclusion as FRONTIER.md's Tier-C estimate. This is (B)'s negative answer by
  example: the best practitioners also enumerate residue patterns.

### 1.12 Bértok–Hajdu–Luca–Sharma, *On the number of non-zero digits of integers in multi-base representations* (Debrecen preprint). Ádám–Hajdu–Luca, *Representing integers as linear combinations of S-units*, Acta Arith. 138 (2009).
- Finiteness/counting for w_{S₁}(n)+…+w_{S_k}(n) ≤ T via Evertse's theorem (count ≤ (235(T−1)²)^{(k−1)(T−1)⁴s}, ineffective
  sizes); effective Thm 2.2 for two sets: w⁺_{S₂}(n) > c₂ log log n/log log log n (Matveev, Luca–Stewart style — again the
  Stewart shape); complete lists for {2,3,5} partitions by the Bertók–Hajdu local method. Ádám–Hajdu–Luca: #{n ≤ x representable
  as Σ a_i s_i} ≪ (log x)^{tk}, Subspace, ineffective.
- **Verdict.** Same two tools, same shapes. Nothing new for Tier C.

### 1.13 Repunits / near-repunits (item 3).
- R_n an S-unit: trivial by Zsigmondy (as BAKER-CHAIN §8 notes); Bugeaud–Mignotte, *On integers with identical digits*,
  Mathematika 46 (1999) and *Sur l'équation (xⁿ−1)/(x−1) = y^q* treat repdigits that are perfect powers (Baker + modular),
  not S-units. Searches for "near-repunit"/"almost repdigit" + S-unit/prime factors return only "almost repdigits in
  k-generalized Lucas sequences"-type papers (one perturbed digit, Baker + LLL) — k ≤ 1–2 perturbations, standard
  Baker-and-reduce. **No paper treats R_n + many bumps as an S-unit.** Bugeaud 2026 Thm 1.6 (digit word W^t ⇒ t ≤ C) is the
  nearest effective statement about repetitive digit words and does not cover perturbed repunits.

## 2. Answers to the five questions

**Q1 (few nonzero digits, S-units).** What is bounded: Stewart/B–K bound the *number of nonzero digits from below* by
≈ log log N/log log log N (equivalently, the *number of digits* n from above by (C log n)^{k+O(1)} ≈ (Ck log k)^{k});
Bugeaud 2018 bounds the *S-part* (effective only for k ≤ 3). Shape in k: **every effective result is k^{O(k)}**; none is
better than exponential; the only polynomial-shape statements (Evertse 1984, Corvaja–Zannier, Bugeaud 2018 Thm 1.1) are
Subspace-theorem results with **ineffective** constants. Applicability to our "all-1 background": 9y′+1 converts to the
standard form with k+1 nonzero digits, so everything applies verbatim with k+1 for k; the all-1 background buys nothing
extra (the lower part Σ_{i>j} c_i 10^{E_i} − 1 still has height ≈ E_{j+1} log 10 in the p-adic chain, and the upper part
N_j height ≈ (n−E_j) log 10 in the archimedean chain). Bugeaud–Kaneko's pigeonhole (choose the gap index ℓ where the
rest is smallest relative to the gap) is a neater proof than iteration but gives the same exponent.

**Q2 (Skolem / p-adic / Chabauty for many exponents).** No. Skolem's p-adic method needs as many independent p-adic
analytic equations as unknown exponents (over Q one equation ⇒ effectively one free exponent after fixing the residues of
the others — the residue fixing *is* pattern enumeration); Strassmann handles one variable. For purely exponential
equations in many unknowns the only general-purpose tools are (i) Baker-type bounds (3 terms in general; 4–5 terms with
|S| ≤ 3 via Vojta/Bajpai–Bennett matching; arbitrary terms only for the single-base digit structure, Stewart), and
(ii) Skolem-conjecture-type modular sieving (Bertók–Hajdu, Dimitrov–Howe) whose cost is exponential in the number of
unknowns and which is in general conditional on the (unproved) Skolem conjecture. Chabauty is inapplicable (no curve).

**Q3 (repunits, R_n + perturbations).** Nothing beyond Zsigmondy for pure repunits; no literature on R_n + k bumps as
S-units for k > 2. The closest families (almost-repdigits in recurrences) are k ≤ 2 Baker-and-LLL.

**Q4 (≥ 20 exponential terms solved).** Yes, exactly one line of work: Dimitrov–Howe 2021 (22 and 25 terms), pure
residue-class lifting + meet-in-the-middle, 8.6 CPU-days at 22 terms, ×3.5 per term. Bertók–Hajdu: 9 unknowns.
Bajpai–Bennett: 5 terms with Baker. Nothing with ≥ 20 terms uses Baker; nothing with ≥ 26 terms exists.

**Q5 (height-free middle gap).** No unconditional bound on a gap whose constant omits the height of the complementary
part is known; we found none and the structure of Baker's inequality (the A_i are multiplied, so h(rest) enters at least
linearly with coefficient C log B ≥ 10¹³) forbids it. Closest results: (a) k = 1 (two nonzero digits): both parts have
bounded height, gap bounded absolutely (two-term S-unit equation; Bugeaud 2018 Thm BES); (b) k = 2, 3: Bugeaud 2018 Thm 1.2
bounds the whole number but still through the heights; (c) B–K Lemma 3.1: there always exists *one* gap index ℓ with
gap ≥ n_k^{ℓ/(k−2)} while h(rest) ≲ n_k^{(ℓ−1)/(k−2)} — a "relatively height-free" gap, which is why the exponent is
1/(k−2) and not better; (d) ineffectively, Evertse 1984 / Corvaja–Zannier: every prefix gap ≤ εn + C(ε) — height-free up to
ε, constant ineffective; (e) conditionally, Lang–Waldschmidt or abc give (d) effectively — see §3.

## 3. [own] What strength of theorem (A) would require — the conditional picture

Using only Lemmas 3.1–3.2 of BAKER-CHAIN.md (0 < Λ_j ≤ 80·10^{−g_j}/N_j, Λ_k = −1/(M+1)) and replacing Matveev by a
conjectural bound:

- **Lang–Waldschmidt** (Lang, *Elliptic Curves: Diophantine Analysis*, 1978; Waldschmidt, *Diophantine Approximation on
  Linear Algebraic Groups*, 2000, Introduction; Stewart's Waterloo notes state it as |Λ| > C(ε)^{…}/(B₁⋯B_t A₁⋯A_t)^{1+ε}):
  log|Λ_j| ≥ −(1+ε)(log N_j + log 420 + 5 log B) + O_ε(1). With log Λ_j ≤ log 80 − g_j log 10 − log N_j the −log N_j cancels
  and **g_j ≤ ε n + O(log n) + C(ε)**, g₀ ≤ O(log n) + C(ε), E_k ≤ εn + …. Hence n ≤ (k+1)(εn + O(log n) + C(ε)); with
  ε = 1/(2k+2): **n ≤ 2(k+1)(O(log n) + C(1/(2k+2)))** — linear in k up to C(ε). (Matveev differs from this only in
  having C·log B·log N_j, C ≈ 10¹³, in place of (1+ε) log N_j; that single constant is the whole gap between k^{O(k)} and
  O(k log k).)
- **abc** (c ≤ K_ε rad(abc)^{1+ε}) on the triples (M, 1, N_k10^{E_k}), (N_j10^{E_j}, Σ_{i>j}c_i10^{E_i}−1, M), (10^n, Σc_j10^{E_j}−1, M):
  rad ≤ 420·(rest), giving every gap ≤ εn + C_ε, so again n ≤ (k+1)(εn + C_ε) ⇒ **n ≤ 2(k+1)·C_{1/(2k+2)}**.
- **Robert–Stewart–Tenenbaum refinement** (Bull. LMS 46 (2014), 1156–1166: c < k·exp(4√(3 log k/log₂k)(1 + o(1))), k = rad):
  each gap ≤ 4√3·√(n log 10/log(n log 10))/log 10 + O(1) ≈ 5.2√(n/log n), so n ≤ (k+1)·5.2√(n/log n) ⇒
  **n ≲ 27(k+1)²/log n** — for k = 44 about 5·10³ digits. (Baker's explicit abc, c < (6/5)rad(log rad)^ω/ω!, has ω unbounded
  here and only yields n ≤ e^{O(k)}.)

So (A) is *equivalent in strength* to a linear-forms-in-logarithms bound with coefficient (1+ε) on the height of the
algebraic part — conjectural — and under RST-abc Tier C would reduce to a search of S-units below 10^{5·10³}
(≈ 10¹¹ triples (a,b,c)); under plain Matveev no such reduction exists. None of this is admissible under RULE 2.

## 4. Recommendation

- **(A) is not available.** All effective bounds for S-units with k nonzero digits — Stewart 1980, Bugeaud–Kaneko 2018,
  Bugeaud 2018/2026 — are of our shape (C log n)^{k+O(1)}; the exponential-in-k dependence is a property of Baker-type
  inequalities (gap ≤ C·h(rest)·log B with C ≫ 1), not of our proof. Improving it to polynomial in k would be a new theorem
  of Lang–Waldschmidt/abc strength. Improving the *constants* (Matveev's 30^{t+3}, better two/three-log bounds à la Laurent
  or the p-adic Bugeaud–Laurent for the j = 0 and j = k forms) changes log₁₀ G by at most a few units per gap, i.e. G
  from 10^{541} to perhaps 10^{450} at k = 31 — still hopeless against a lattice lower bound of 10^{72+48(D−1)} per pattern,
  and does not touch the enumeration barrier.
- **(B) is not available.** Every complete resolution of a many-term exponential equation in the literature (Dimitrov–Howe
  22–25 terms, Bertók–Hajdu 9 unknowns, Bajpai–Bennett 5 terms) enumerates residue classes of the exponents and pays
  exponentially in the number of terms (×3.5 per term measured). Skolem's p-adic method does not scale beyond one free
  exponent per equation; the Subspace theorem gives finiteness and counts (ESS: ≤ exp((6(k+3))^{3(k+3)}·5) solutions) but no
  sizes (N = k+2 variables after dividing by one term; r = 4). There is no non-enumerative closure method for k ≈ 31–44 in the literature.
- **Therefore Tier C is genuinely beyond current unconditional methods**, by the same margin as "powers of 3 with ≤ 30 nonzero
  bits" is beyond Dimitrov–Howe. The honest options are: (i) treat Tier C as the finite computation of known cost that
  FRONTIER.md describes (a GPU level-12 kernel does not reach 10²² patterns either); (ii) record the conditional result
  (RST-abc ⇒ n = O(k²/log k), a 10¹¹-triple search) as a separate, clearly conditional statement; (iii) look for
  *problem-specific* structure that is not "few nonzero digits" — e.g. divisibility of 9y′+1 by 10^{E_k} combined with
  y′ ≡ R_{E_k} (mod 10^{E_k}) gives E_k ≤ C log n unconditionally via Yu (bottom block short), and the same for the top
  gap via Matveev; but every interior gap still costs a factor K₁ ≈ 10¹⁶. I found no idea in the literature that avoids this.
