# Preimage trees of the nonzero even multiplicative digital roots: a computer-assisted enumeration and its frontier

*Working draft, 2026-10-19/20. Numbers marked ⟨…⟩ are filled from the sweep outputs
(`trees_mac.jsonl`, `trees_c.jsonl`, `runall_final.jsonl`); nothing here is asserted beyond those files.*

## 1. Setting and statement

Let p(n) be the product of the decimal digits of n and let the *persistence* of n be the number
of iterations of p needed to reach a single digit, the *digital root* Δ(n). Sloane (1973)
conjectured persistence ≤ 11 in base 10; 277777788888899 attains 11. Brier, Clavier, Gutsche and
Naccache (2021) proved the conjecture for odd Δ by enumerating the finite *antecedent trees*
A_Δ: vertices are the integers y = 2^a 3^b 7^c (the only possible values of p after the first
step, once Δ ∉ {0, 5}) whose orbit ends at Δ, with an edge y → p(y). They left Δ ∈ {2,4,6,8}
open; [2026 2-adic paper] bounded the exponent a for each vertex, making each tree's
completeness a finite problem of size they estimated beyond classical reach.

Let S = {2^a 3^b 7^c}. For s ∈ S the *children* of s are the y ∈ S, y ≥ 10, with p(y) = s. For
Δ ∈ {2,4,6,8} let T_Δ be the tree obtained by exhaustive enumeration of all zero-free elements
of S below 10^4000 (8,807 elements; 32, 8, 83, 50 multi-digit vertices for Δ = 2, 4, 6, 8,
matching the counts in [BCGN]).

**Theorem 1 (closed vertices).** For each of the ⟨N_closed⟩ vertices s of T_2 ∪ T_4 ∪ T_6 ∪ T_8
listed in Table A, the children of s are exactly the children in T_Δ.

**Theorem 2 (vertices closed by the Baker–lattice sandwich).** For each of the ⟨N_sandwich⟩ vertices
listed in Table B — those whose enumeration leaves open patterns at level 96 — the children of s are
exactly the children in T_Δ. Proof: every candidate of an open pattern other than its checked anchor has,
by Lemma C at depth D (its lowest 96D digits are determined up to the copy choices, and the resulting
congruences cut the (b,c)-coset to finitely many sub-cosets with explicitly computed nearest points),
at least 10^{⟨…⟩} digits, while by Theorem U (iterated Matveev bound, one linear form per digit gap:
BAKER-CHAIN.md) any child with k non-1 digits and 2-adic exponent a has fewer than G(k, a) digits,
log₁₀G ≈ 11.5 + 13.9k; for every open pattern of these vertices the former exceeds the latter at some
D ≤ ⟨6⟩. Theorem U is an ordinary proof conditional on Matveev's theorem (Bugeaud–Mignotte–Siksek 2006,
Thm 9.4); nothing else in this paper depends on a transcendence result. ⟨Before the sandwich these
vertices were "closed below 1.3×10^27 digits"; Lemma C at depth 1 alone closes ~94% of their open
patterns outright.⟩

**Theorem 3 (A_4).** The children of 1161216 are exactly ⟨{128421199872} or "… below 10^27"⟩.
Every integer N with Δ(N) = 4 and persistence ≥ 5 satisfies p^{pers(N)−3}(N) = 1161216, and
persistence ≥ 6 requires p^{pers(N)−5}(N) to be a child of 128421199872 other than those in
T_4 ⟨(T_4 has none)⟩, hence a number with more than 4000 digits whose non-1 digit multiset is one
of the ⟨878⟩ multisets of Table C (all with at least 15 non-1 digits).

**Corollary.** ⟨persistence bounds per even root, as far as the closed region supports them⟩.

The ⟨18⟩ vertices of Table D (12 in T_6, 5 in T_8, 1 in T_2, 1 in T_4) are not covered; for them
the enumeration below would need between 10^15 and 10^22 residue patterns.

## 2. Method

2.1 *Equations.* A child y of s with non-1 digit multiset M (product s, |M| = q) is
y = R_n + Σ_j (d_j − 1)10^{e_j}, R_n = (10^n − 1)/9, with distinct positions e_j < n. Unknowns:
n, the e_j, and (a, b, c). The 2-adic valuation a is bounded by an explicit tail enumeration.

2.2 *Residue patterns.* For a prime p ∤ 10, y mod p depends only on the residues of n and the
e_j modulo ord_p(10). At level L the primes are those of 10^L − 1 outside {2,3,5,7}; levels
12, 24, 48, 96 are used. A pattern is (n mod L, multiset of (d, e mod L)). The condition
y ≡ 2^a 3^b 7^c (mod p) is linear in (a,b,c) after discrete logarithms; the system over all
primes of a level is solvable iff the vector of logarithms lies in the image H of Z^3, a
condition that decomposes into ℓ-primary components and is tested by table lookup; its
solution set is a coset of a fixed lattice, whose representative is assembled by CRT.
Observed: at level 12, 1 in 40 patterns passes, and the a-coordinate is pinned modulo 12.

2.3 *Lifting.* A pattern at level L has 2^{q+1} children at level 2L (fewer after symmetry);
the new primes' congruences are imposed relative to the parent lattice.

2.4 *10-adic pinning and descent.* On a coset, 2^a 3^b 7^c mod 10^K is constant for K up to
an explicit K*(level, a) (3, 4, 5, 5 at levels 12–96); the last K* digits of y are therefore
known and must be digits of the pattern. If v₂(9Y − 10^{K*}) ≠ a, the next non-1 digit or the
end of the number lies within a bounded window, which is enumerated (Lemma B); each case cuts
the coset by three congruences and recurses.

2.5 *Outcomes.* A pattern is dead, exact (y determined and verified), or open. An equation is
closed when no pattern is open; the vertex is closed when all its equations are. For an open
pattern the coset's shortest vector gives the height bound of Theorem 2: all but at most one
coset point have max(b,c) ≥ 2.8×10^27. The exceptional point is computed (Babai) and checked.

2.6 *Carry coincidences.* Every open pattern met in the computation is anchored on a genuine
small element of S: either the vertex's own known child (a = t silences Lemma B), or a number
from a sibling tree impersonated by two digits in one residue class whose (d−1) contributions
sum to 10 — indistinguishable from a carry by every prime at every level. 111132 = 2²3⁴7³ and
13122 = 2·3⁸ anchor most of them. No modular method can close these; a height bound is the best
available.

## 3. Verification

(i) Positive controls: all 8,807 known elements as children of their parents must survive
every level and be recovered under their own pattern; a 14-digit synthetic control exercises
the residue lift. (ii) Brute force to 24–28 digits per equation. (iii) Two blind
re-implementations from the written method (Claude; Codex — a second model family) confirm the
seven Tier-0 vertices of T_4. (iv) Replication: ⟨N⟩ vertices computed independently on two
machines agree in every count. (v) Mutation testing: ⟨score⟩. (vi) A differential gate between
the C pipeline and the pure-Python engine, per equation and level, passed on 53 vertices; it
caught three silent false-closure bugs during development. (vii) Lemmas A and B in Lean 4
⟨status⟩.

## 4. The frontier, stated as a problem

The enumeration is exponential in q and the kill per level is a fixed constant, so the
⟨18⟩ vertices of Table D are beyond it. What would close them is an **effective middle-gap
bound**: if y = 2^a 3^b 7^c has two consecutive non-1 decimal digits at positions e > e′, then
e − e′ ≤ C·log(max(a,b,c)) with C not depending on the lower part of y. Baker's theory gives
this for the top gap (archimedean form with constant log 9) and the bottom gap (5-adic form with
constant 1), but for interior gaps the relevant constant has height growing with e′, and Yu's
bound degenerates. The Subspace Theorem gives finiteness of each equation ineffectively. A
proof of the middle-gap bound, even with an astronomical C, would make every equation decidable
by LLL reduction; combined with the lattice method above it would likely close all ⟨18⟩.

## Tables (generated)

A, B, C, D — see `tables.py` ⟨to be generated from the jsonl files when the sweep ends⟩.

## 5. Other bases (added 2026-10-20)

The method is base-independent: for base b the digit primes are the primes below b; those dividing b
have bounded exponents (a p-adic tail enumeration), the others are free and carry the lattice; the
level primes are those of b^L − 1 = ∏_{d|L} Φ_d(b) outside the digit primes. `engine_b.py` implements
this uniformly; `ladder.py` gives each base's kill profile (LADDER.md: every base has a level with a
sudden rank gain — 12 for bases 6 and 10, 16/20 for base 8, 15 for base 9, 18 for base 12).

**Theorem 5.1 (base 8).** ⟨The antecedent trees of the digits 1–7 in base 8 consist of the ⟨63⟩
vertices of Table E; for ⟨N⟩ of them the children are exactly those listed, and for the remaining
⟨M⟩ every unlisted child has more than 10^⟨1.0e15⟩ digits. In particular every integer with nonzero
base-8 digital root and fewer than 10^⟨…⟩ digits has multiplicative persistence ≤ 6.⟩

**Theorem 5.2 (base 6).** ⟨same shape; 29 vertices; two one-dimensional families 2^a5^c, 3^b5^c;
height bound 10^2.6e16 digits; persistence ≤ 5.⟩

Bases 9 and 12: ⟨census — feasible/infeasible vertex counts from LADDER.md; the frontier phenomenon of
base 10 reappears in base 9 (vertices with 27 non-1 digits).⟩

**Open patterns are anchored (all bases).** Every open pattern of every run (base 10: 299 of 299 across
47 vertices; base 6: 20 of 20; base 8: ⟨…⟩) is an exact improper representation of a genuine S-unit
y below 1.2×10^9 (OPEN-PATTERNS.md): y + {0, R_L} = R_ν + Σ(d_j − 1) b^{e_j} with the pattern's residues
read as positions in [0, L). For such a pattern every candidate is ≡ y (mod R_L), so no level separates
it from y; the residual statement for each closed-below vertex is therefore the explicit one: no
y·∏ p^{Δ_p} with Δ in the pattern's kernel lattice realizes the pattern properly. This is sharper than
the middle-gap formulation of §4 and is the form in which the frontier should be attacked.

**Verification in other bases.** Blind scoring (no controls; found set compared with the exhaustive
corpus of zero-free S-units below b^D afterwards), planted invalid controls, and mutation testing with
two gates — the found set and the per-level count/solution signature (`redteam_base.py`; base 8: 25/25
blind, 4/4 planted, 6/6 mutants; the found-set gate alone scores 3/6 because the exceptional-point
fallback recovers children redundantly). Replication: the base-8 run at levels 12/24/48 on two engine
versions agrees on all 55 common vertices; the level-96 run on the Mac is compared vertex by vertex.
