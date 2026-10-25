# LIT3: literature lane N4, what 2022-2026 and LIT2's gaps change for W1 / W2 / Wall 1

2026-10-21. Builds on tier0/LIT2.md (not repeated: Stewart 1980, Bugeaud 2018/2026, Bugeaud-Kaneko 2018, Bennett-Bugeaud-Mignotte,
Corvaja-Zannier, Evertse/ESS/Amoroso-Viada, Bajpai-Bennett 2023, Miyazaki 2025, Bertok-Hajdu 2016, Dimitrov-Howe 2021).
Raw sources: `raw/` beside this file (PDF + pdftotext). "READ" = I opened the fetched full text and read the cited
statements; "ABSTRACT" = only abstract/intro read; "RECALLED" = from memory or a search snippet, not opened.
Search coverage is limited (web search returns few hits for 2024-2026 arXiv); absence below is an observation, not a finding.

## 0. Bottom line

1. The only 2022-2026 work that touches the program directly is **Fonga, arXiv:2608.27802 (28 Aug 2026)**. It proves the
   Brier-Clavier-Gutsche-Naccache Conjecture 2 (uniform bound on v2 over the family "fixed exceptional digits, arbitrary 1s, no 0")
   by exactly the digit-by-digit 2-adic recursion that the theta lane's T7 derived independently, and adds a finite recursion
   (Theorem 4.1) that returns the EXACT max v2 per digit multiset. This is a rigorous replacement for the "two_adic_bound
   non-terminating for k >= 36" and the "A = 118-144 documented" values.
2. No published effective result has better than exponential-in-k dependence; nothing found for the per-gap target (theta < 1)
   or an effective Roth with polynomial 1/eps. W1 as stated is not met by anything I found.
3. The one constant-improvement tool that is new since LIT2's era is the **Mignotte-Voutier three-logarithm kit (2023)**:
   measured gains of about 10^5 and 10^6 over Matveev on two worked examples, against a needed 10^14-10^16 per gap. It applies
   only to forms with exactly 3 logarithms, i.e. the rank-1 branches, and only to the archimedean half of the two-ended chain.
4. For W2: the Skolem line (Bilu-Luca-Nieuwveld-Ouaknine-Purser-Worrell; Bacik-Ouaknine-Purser-Worrell) is a genuine
   output-unconditional / termination-conditional certificate framework, so such a certificate is RULE-2-admissible. But it is a
   residue-class partition certificate for ONE variable, with the tool timing out for orders >= 7. It is the same species as our
   modular ladder and Dimitrov-Howe lifting; it does not remove enumeration.
5. For Wall 1: the character-sum literature I found (Chang-Shparlinski, Castro-Chang, Kerr-Mohammadi-Shparlinski, Hauck-Shparlinski) has
   hypotheses (intervals, prime or square-free moduli, upper bounds on counts) that do not fit a digit-pattern sumset modulo
   Q = 2^a 5^b; none yields a rigorous count below 1 for a specific equation.

## 1. Source entries

### 1.1 P. N. Fonga, *The Multiplicative Persistence Conjecture: Resolving the 2-Adic Obstruction for Nonzero Even Targets*, arXiv:2608.27802v1 (28 Aug 2026). READ (full text; proof of Thm 3.1 and Thm 4.1 read line by line). Not peer reviewed (arXiv only).
- Statement. Family A_b(nu): positive integers with exactly nu_d copies of each digit d = 2..b-1, any number of 1s, no 0. q = sum nu_d.
  Theorem 3.1: for prime p | b, e = v_p(b), lambda = log_p(b)/e, B(nu) = 1 + (b-1) sum (d-1) nu_d, rho_p(nu) = max({0} U {v_p((b-1)(d-1)-1) : nu_d > 0, p | d}):
  v_p(x) = 0 unless an exceptional digit is divisible by p; otherwise v_p(x) <= floor(rho lambda^q + log_p B (lambda^q - 1)/(lambda - 1)) for lambda > 1.
  Mechanism (Lemma 2.2): writing (b-1)x = -1 + sum c_j b^{a_j}, the partial sum T_j has v_p(T_j) <= lambda v_p(T_{j-1}) + log_p B (position far above v/e does not change the valuation; otherwise T_j < B b^{v/e} and p^{v_p(T_j)} <= T_j).
  Theorem 4.1: exact max v_p over a prescribed multiset by a finite recursion on states (M, a, T): place the next exceptional digit at positions a < t <= floor(v_p(T)/e), finish with the leading 10^L for a < L <= v_p(T)/e.
- My check: re-implemented Thm 4.1 for p = 2, b = 10 (about 25 lines, scratchpad `fonga.py`) and reproduced the paper's worked example D = {4,4,7} -> max v2 = 7 (x = 111744 = 9^-1 (1005696)). One example only; the other three table rows (13, 15, 9) not rerun.
- Fit. The family is exactly our y' + R_n structure with 9y'+1 = 10^L + sum 9(d_i - 1) 10^{r_i}, the 2-exponent a = v2. Hypotheses fit exactly (digits 2..9 fixed multiset, 1s free, no 0).
- Consequence. (a) The explicit Thm 3.1 bound is exponential in q: lambda^q = 10^16.16 (q = 31), 10^22.94 (q = 44) (my arithmetic: q log10 log2 10), so a <= ~10^17 at q = 31. As a bound on a it is vacuous next to the documented A = 118-144; it only certifies that a is finite and bounded without Baker. (b) Thm 4.1 returns the exact tmax(D), a PROVEN-ON-PAPER finite procedure; its cost on a q = 31-44 multiset is unmeasured (branching up to (v/1) positions times |distinct digits| per level, memoizable on (M, a, T)). (c) It is the published form of the theta lane's T7 (p_{m+1} <= 6.32 + 3.32 p_m: same lambda = log2 10 = 3.32, same log2 B term); the independent derivation raises T7 from "to audit" to "matches a second source", still one arXiv source. (d) It does not touch the interior-gap Baker barrier.
- Same paper, Section 5: restates the Brier et al. backward-graph completeness criterion (S^2(x) = s => S(x) in U_delta) and says Thm 3.1 plus the BCGN lifting algorithm gives a finite procedure per even target. No new bound on n.

### 1.2 M. Mignotte, P. Voutier (appendix M. Laurent), *A kit for linear forms in three logarithms*, arXiv:2205.08899v3 (29 Sep 2023). READ (abstract, Sec 1.1-1.5, Thm 2.1 statement, example bounds; proofs not read). Code: github.com/PV-314/lfl3-kit (Pari), URL from the paper, not fetched.
- Statement. Interpolation-determinant (Laurent) method for Lambda = b1 log a1 + b2 log a2 + b3 log a3 (three algebraic numbers, general number field), Thm 2.1: under conditions (2.7)-(2.13), either Lambda' > rho^{-KL} or a degeneracy (2.14)/(2.15) holds. Process: Matveev first gives B1, then the kit gives B2, then degenerate two-log (Laurent) gives B3, iterate (3 iterations suffice).
- Stated gains: Example 1 (y^p = F_n) bound on p from about 2*10^12 (Matveev) to 18*10^6; Example 2 (x^2 + 7 = y^p) from about 3*10^13 to 25*10^6. So factors about 10^5 and 10^6. Authors: "typical". Real forms within 50% of their optimum; imaginary forms optimal; further factors about 1.5, 5, 2 conjectured from three listed improvements (Sec 1.5).
- Hypotheses: exactly three logs, "most suited when at least one algebraic number is a variable" (Sec 1.3): fits a form with one varying rational. Does not apply to 4-5 logarithm forms.
- Fit for us. Our archimedean forms have logs of {2,3,7,10} and the varying rational N_j. B3/H3 (h3-h4/REPORT.md) established that no archimedean form has fewer than the 2^a-folded count; with 2^a folded into the rational N_j' (B3's fold) the form has logs {3,7,10,N_j'}: four in the generic rank-2 branch, THREE in a rank-1 branch (exponent of 3 or of 7 forced to 0: logs {3,10,N_j'} or {7,10,N_j'}), two (Laurent) for pure 2^a, which is finite anyway. B1 puts about 38% of patterns in rank 1. The p-adic (5-adic Yu/Bugeaud-Kaneko) half of the two-ended chain has no three-log kit.
- Number [own arithmetic, not run on our instance]: B1's one-ended multiplier is 10^18.6 per non-1 digit; the kit's 10^5-10^6 would give 10^12.6-10^13.6 on the archimedean half in rank-1 branches. W1 needs about 10^7.6 one-ended (log10 G' <= 168 at k = 44, from MAP.md). So at best 40-50% of the required log-gain on about 38% of patterns; no depth-1 closure.
- Verdict: MEDIUM-LOW impact, cheap to test, must be run on a real chain instance before any claim (the examples had heights about 10^3; ours carry heights about (n - E_j) log 10 up to 10^2-10^3 in the variable).

### 1.3 J. Bilu, F. Luca, J. Nieuwveld, J. Ouaknine, D. Purser, J. Worrell, *Skolem Meets Schanuel*, MFCS 2022, LIPIcs 241, 20:1-20:15; arXiv:2204.13417. READ (abstract, intro, Sec on certificate and experiments; proofs not read).
- Statement. Algorithm for the Skolem Problem (zero of u_n = sum c_i alpha_i^n) for SIMPLE integer LRS, and its bi-infinite version. Whenever it terminates it outputs a stand-alone certificate: a partition of the index set into residue-class subsequences, each with at most one zero (witnessed by a prime p dividing all other terms' values) or none (witnessed modulo m). Termination proven assuming the Skolem Conjecture (exponential local-global principle) and the weak p-adic Schanuel Conjecture. Output correctness is unconditional.
- Experiments (their table): with a 60 s timeout, success 100% at orders 2-4, then timeouts 5.1% (order 5), 46% (6), 85% (7), 96% (8), 99% (9+) of simple LRS; with 60 s x order timeout, order 7 still 76.5% timeouts.
- Relevance: (i) answers the brief's question: a certificate with conditional termination and unconditional output is a real object in the literature and, if produced for our equation, would be admissible under RULE 2 (the verification is the unconditional part). (ii) Mechanism = residue partition + p-adic Skolem on one variable, i.e. our modular ladder species. Our equation has k + 3 independent exponents, not one index n, so the algorithm does not apply as stated; order 7 already times out at 60 s.
- Concrete consequence for W2: none numeric. It supports reframing Tier C as "produce a bound-free local-global certificate" (no Baker constant) rather than "bound n then enumerate"; the cost is the residue-class count, the same enumeration.

### 1.4 P. Bacik, J. Ouaknine, D. Purser, J. Worrell, *On the p-adic Skolem Problem*, arXiv:2504.14413v4 (11 May 2026), STACS 2026, LIPIcs 51. ABSTRACT only read (plus search snippets).
- Output unconditionally correct, termination under p-adic Schanuel; computes all p-adic zeros to any precision; tool implementation (skolem.mpi-sws.org, zenodo 15858619). Applies to Simultaneous Skolem. Single variable again. Not usable for k + 3 exponents; cited as the current state of the certificate-producing line.

### 1.5 V. Ziegler, *On the number of solutions to S-unit equations*, arXiv:2609.15487 (14 Sep 2026). ABSTRACT + intro read.
- a1 x + a2 y = a3 with fixed a1, a2: at most (|S|+1)/2 solutions if h(a3) is large (effective). Two unknowns. Not applicable (k + 3 terms). Also V. Ziegler, arXiv:1804.10453 (2018): effective finiteness for a1 U_{n1}+...+ak U_{nk} = b1 V_{m1}+...+bl V_{ml} with dominant roots; reproves Stewart's digit bound as a special case: same Stewart shape. ABSTRACT only.

### 1.6 Y. Bugeaud, *On the difference between squares and integral S-units*, arXiv:2503.22084v2 (Apr 2025). READ (abstract, Thm 1.1-1.2). x^2 - q1^a1...qt^at: S-part <= |.|^{1/2+eps} (ineffective) and an effective lower bound on the greatest prime factor tending to infinity. Two-term (square vs S-unit); no digits. Not applicable. Also Bugeaud, *Zeckendorf representation of smooth numbers*, arXiv:1909.03863 (2019): same Matveev/Yu method, Zeckendorf digits. ABSTRACT only.

### 1.7 M. Hauck, I. Shparlinski, *Smooth numbers with few non-zero binary digits*, MPIM preprint 2023-11. READ (abstract, Thms 1.1-1.3).
- EXISTENCE of smooth numbers with few nonzero binary digits: infinitely many n-bit integers that are Y^{1+o(1)}-smooth with at most alpha n + O(n^{1/2} log n) nonzero digits, Y = exp(2 e^{-gamma/2} ... (log N)^{1/2}...) (Thm 1.2), and a regime with n^alpha digits (Thm 1.3); proofs via character sums (Iwaniec short sums) and cyclotomic factors (2^k + 1 smooth for k a primorial). Smoothness grows with N, so S is not fixed: no contradiction with Bugeaud-Kaneko. Useful as a warning that "no sparse S-unit" statements need S fixed. No tool for Tier C.

### 1.8 Character sums into subgroups (Wall 1)
- M.-C. Chang, I. Shparlinski, *Double character sums over subgroups and intervals*, arXiv:1401.6611 (2014). ABSTRACT + intro read. Prime p; sums over interval x subgroup G of order T; nontrivial if H >= p^{1/4+eps} (Burgess) or T >= p^{1/2+eps}; application to primitive roots with 3 nonzero binary digits.
- K. Castro, M.-C. Chang, *Multiplicative energy of polynomial images of intervals modulo q*, Rev. Mat. Iberoam. 34 (2018) 1093-1101. READ (intro, Thm 1.1). q square-free, all p | q below q^{1/(160 d^4 m^{2d})}, f monic of degree d < (log|I|)^{1/8}, I an interval; if f(I) mod q lies in a subgroup G of Z_q^*, then |G| >= min{|I|^{m/2}, q^{1-eps}}. This is a lower bound on |G| from containment, not an upper bound on |f(I) cap G|.
- M.-C. Chang, *Short character sums for composite moduli* (Graham-Ringrose type; Thm 5: short sums over an interval, moduli with small prime factors, N > p^C and a log-condition). READ abstract and Thm 5. Raw file `chang-short-char-sums-composite.*`.
- B. Kerr, A. Mohammadi, I. Shparlinski, *Additive energy of polynomial images*, arXiv:2306.10677 (2023). ABSTRACT only: additive energy of f(I) mod m; application to character sums.
- Fit. None matches: (a) all sum over an interval or polynomial image of an interval; our set is {R_nu + sum eps_j w_j}, a Boolean-weight subset sum (a generalized arithmetic progression of dimension up to 44 with huge steps), (b) moduli prime or square-free, ours 2^a 5^b-type, (c) outputs are asymptotic lower bounds on |G| or nontrivial-saving upper bounds, with absolute constants not tuned to give "fewer than 1 hit". Chang's "number of factorizations in a GAP" (Thm 2.2 in Castro-Chang: r_h(n) < exp(C_{d,h} log J / log log J)) is the one GAP tool, but the constant is not explicit. Concrete number for Wall 1: none.
- Honest limit: the program's own measurements (H1 §7: model predicted 42 accidents, observed 0) say the uniform model overshoots by >= 29x, so any character-sum bound built on equidistribution would have to beat an already-overshooting heuristic; no source here does.

### 1.9 Brier, Clavier, Gutsche, Naccache, *The Multiplicative Persistence Conjecture Is True for Odd Targets*, arXiv:2110.04263 (2021). ABSTRACT + greps. Origin of Fonga's Conjecture B (their Conjecture 2). Persistence-specific, already in the program's intake; listed for completeness. R. Saye, *On two conjectures concerning the ternary digits of powers of two*, arXiv:2202.13256 (2022): READ abstract/intro; verifies Erdos and Sloane ternary-digit conjectures for 2^n, n <= 2*3^45 (about 5.9e21) by a recursive construction of 2^n with prescribed TRAILING ternary digits. A search method like H9 (suffix recursion), not a proof; useful as an engineering reference for suffix lifting at 10^21 scale.

### 1.10 Not found / not obtainable
- No 2022-2026 Bugeaud-and-coauthor effective S-unit digit result beyond those in LIT2 and 1.6 (searched; two search passes).
- No Dimitrov-Howe follow-up beyond its Rocky Mountain J. Math. 55 (2025) publication; no Bertok-Hajdu successor beyond a number-field extension (Monatsh. Math., RECALLED from snippet).
- No effective Roth/Subspace with polynomial 1/eps for S-unit approximation. Known effective alternatives are Bombieri-Cohen (Thue-Siegel with Dyson, RECALLED from a survey snippet) and Murty-Pasten (modular forms, RECALLED), both for few-term or hypergeometric settings, not 30+ terms.
- No Matveev-type constant improvement for 4-5 logs beyond Matveev 2000 / Yu 1999-2007 / Bugeaud-Laurent two-log p-adic. No recent "sharp constants" paper located.
- Counting side (not sizes): ESS / Amoroso-Viada bounds in LIT2; a search snippet reports Hirata-Kohno et al. (arXiv:2211.14399, Pade, two-variable S-unit count (3.1 + 5(3.4)^m) 45^s) RECALLED from snippet only. They count, they do not bound sizes.

## 2. Ranked top 5 by expected impact, and what a lane does tomorrow

1. **Fonga Thm 4.1 as the exact 2-adic bound (impact: closes a real gap, small numerically).**
   Port the recursion (memoized on (M, a, T)) into the pipeline as the replacement for two_adic_bound, which does not terminate for k >= 36 (H9) and as the source of A in B3's a-fold (log10 G' stays 279.5-281.5 / 394-402). Kill test (30 CPU-min): reproduce Fonga's table rows 7, 9, 13, 15; run on three real Tier-C multisets with q = 31, 36, 44; report tmax and wall time; planted negative: a deliberately raised digit position beyond v/e must not change the maximum, and a mutated recursion (allow t > v/e) must change the result on D = {4,4,7}. Calibration tag: PROVEN-ON-PAPER for a one-source proof I read; a Lean statement would raise it.
2. **Mignotte-Voutier kit on the rank-1 branches (impact: bounded, about 10^5-10^6 per archimedean gap on about 38% of patterns).**
   Build the three-log form {3 or 7, 10, N_j'} for one Tier-B-sized rank-1 vertex, run lfl3-kit, compare with the Matveev value in baker_chain.py; if the factor is >= 10^4, recompute the two-ended G' for rank-1 patterns and the sandwich depth. Prediction written now: depth drops by 1 on rank-1 survivors, no depth-1 closure. Kill: factor < 10^3 on our heights.
3. **Reframe Tier C as a bound-free local-global certificate (Skolem / Bertok-Hajdu / Dimitrov-Howe species) and state its admissibility.**
   Output-unconditional, termination-conditional certificates are legitimate under RULE 2 if the checker is independent and exact. The lane should write one page defining the certificate format for our equation (class of exponent vectors mod lambda(m) -> killing modulus or isolated genuine point), and cost it from Dimitrov-Howe's measured x3.5 per term. Expected outcome: it formalizes what the ladder already is and records the conditional status of termination; no speedup.
4. **Fonga plus T7 as a Lean target.** The recursion lemma (v_p(T_j) <= lambda v_p(T_{j-1}) + log_p B) is a short induction; a green Lean statement plus a statement-level review would move the a-bound from STRONG to RULE-2 PROVEN and let the pipeline drop the "A = 118-144 documented" assumption.
5. **Saye-style trailing-digit recursion check against H9.** His recursive construction of 2^n with prescribed trailing ternary digits reached 5.9e21; compare its branching and dedup with H9's valuation-aware suffix search before building H9, as a design reference only.

Nothing above supplies (W1) per-gap constants 10^14-10^16 smaller, an effective Roth with polynomial 1/eps, (W2) a non-enumerative many-term decision, or (Wall 1) a rigorous accident count.
