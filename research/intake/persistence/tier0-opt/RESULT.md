# Tier 0 of the antecedent tree A_4 is closed (computer-assisted, 2026-10-19)

Status under Cairn's taxonomy: **computer-assisted proof, AuditOnly** — one implementation, one
author, cross-checked but not independently re-derived. It becomes PROVEN only after a second
model family re-implements the method from this description and matches every verdict.

## Statement

Let S = {2^a 3^b 7^c}, p(y) = product of decimal digits. For a vertex s of the antecedent tree,
its *children* are the y ∈ S, y ≥ 10, with p(y) = s.

**Theorem T0.** The children of 4, 14, 27, 72, 98, 189, 294 are exactly

| s | children |
|---|----------|
| 4 | 14 |
| 14 | 27, 72 |
| 27 | none |
| 72 | 98, 189, 294, 1161216 |
| 98, 189, 294 | none |

**Corollary.** Every integer N with multiplicative digital root 4 and persistence ≥ 5 satisfies
p^{pers(N)−3}(N) = 1161216. Persistence ≥ 6 with digital root 4 requires an iterate that is a child
of 1161216 or of 128421199872 other than the known one, hence (by the 10^4000 enumeration) an
iterate with more than 4000 digits. The persistence bound 5 for digital root 4 now rests only on
the two remaining vertices 1161216 (118 equations, q ≤ 16) and 128421199872 (925 equations, q ≤ 31).

These are the first complete child-enumeration certificates for a nonzero even target. Brier–
Clavier–Gutsche–Naccache (2021) proved the analogous statements for odd targets and listed the
even targets as open; the 2026 2-adic-bound paper made the even-target search finite but did not
perform it.

## Method (one page; enough to re-implement)

A child with non-1 digit multiset M (product s), arrangement D = (d_1..d_q) at positions
e_1 > … > e_q, is y = R_n + Σ (d_j−1)10^{e_j}, R_n = (10^n−1)/9. Unknowns n, e_j, a, b, c.

1. **2-adic bound.** v_2(y) is decided by the last k digits; enumerate k-digit tails over {1}∪M
   (sub-multisets of M, zero-padding allowed for short numbers) divisible by 2^k until none exist.
   Gives a ≤ A(M). (A = 2, 6, 6, 0, 8, 0, 13, 16 for the multisets here; max 16.)
2. **Residue patterns.** For p | 10^L − 1, p ∉ {2,3,5,7}: y mod p depends only on (n, e_j) mod L.
   y mod p ∈ 2^a⟨3,7⟩ ⟺ b·log3 + c·log7 ≡ log(y_p) − a·log2 (mod p−1). Level 12 primes:
   11, 13, 37, 101, 9901; level 24 adds 73, 137, 99990001; level 48 adds 17, 5882353,
   9999999900000001; level 96 adds 97, 353, 449, 641, 1409, 69857, 206209, 66554101249,
   75118313082913. Every discrete log is verified by re-exponentiation.
3. **Lattice.** The congruences over all primes define a coset of a rank-2 lattice in (b,c), or
   are inconsistent (pattern dead). Implemented with exact 2-D lattice arithmetic (Lagrange-
   reduced bases), unit-tested against brute force. An exact prefilter decomposes membership
   into ℓ-primary components of ∏ Z/(p−1); verified identical to the lattice on every survivor set.
4. **Lifting.** A survivor at level L splits into 2^{q+1} patterns at level 2L; each inherits the
   coset and meets the new primes.
5. **10-adic pinning.** On a coset, 2^a 3^b 7^c mod 10^K is constant for K ≤ K*(coset, a)
   (3^β7^γ ≡ 1 mod 5^K and mod 2^{K−a} on the basis). So the last K* digits of y are known.
   If n ≤ K*, y is known exactly: verify or kill. If n > K*, the known tail must consist of digits
   from {1}∪M at positions matching the pattern: else kill.
6. **2-adic descent (new here).** 9y = 10^n + Σ_{high} 9(d_j−1)10^{e_j} + (9Y − 10^{K*}). With
   t = v_2(9Y − 10^{K*}) and m = min(n, e_high) ≥ K*: if m > t then a = t. So a ≠ t forces the
   next event (a high digit or the end of the number) into [K*, t]: finitely many cases, each
   extending the known tail, cutting the coset by 2^a3^b7^c ≡ Y' (mod 10^{K'}) (two linear
   congruences via logs in (Z/5^K)^* = ⟨3⟩ and (Z/2^K)^* = ⟨−1⟩×⟨5⟩), and recursing.
   This resolved every pattern that plain lifting left open (notably the known child 1161216
   appearing under sibling arrangements with K* stuck at 5).
7. An equation is closed when no pattern remains OPEN; a multiset is closed when all its
   arrangements are (residues do not see digit order, so the multiset is the correct unit).

## Controls

- Positive: every known child (from the verified enumeration of all zero-free elements of S below
  10^4000) survived every level with its true (b,c) in the coset and was recovered exactly.
- Brute force: all y of each equation's shape with ≤ 24–28 digits were enumerated directly;
  the truth sets equal the certified child sets.
- Planted negative: a claimed child not in S trips the control assertion for every vertex.
- Prefilter/lattice equivalence on 1,033 survivors; lattice unit test on 300 random systems.
- DLog assertions on every log used.

## Numbers

| s | multisets | equations | level-12 patterns (largest eq.) | final level | wall |
|---|-----------|-----------|----------------------------------|-------------|------|
| 4 | 2 | 2 | 1.2×10^4 | 24 | <1 s |
| 14 | 1 | 2 | 1.2×10^4 | 12 | <1 s |
| 27 | 2 | 3 | 2.1×10^4 | 12 | <1 s |
| 98 | 1 | 3 | 1.9×10^5 | 12 | 2 s |
| 189 | 2 | 10 | 2.1×10^4 | 12 | 1 s |
| 294 | 2 | 15 | 3.5×10^6 | 24 | 2 min |
| 72 | 9 | 58 | 4.2×10^7 | 48 | 17 min (2 cores) |

## What this does not say

Nothing here touches target 0 or Conjecture Z. Nothing here bounds persistence for digital root 4
unconditionally: vertices 1161216 and 128421199872 remain (Tier 1 and Tier 2 in the intake note).
Tier 1 needs a smarter first level than enumeration (12^17 patterns); the descent in step 6 and
the prefilter make the per-pattern cost small, so the obstacle is enumeration, not resolution.

## Files

`lattice.py` (coset arithmetic + self-test), `tier0.py` (engine), `descent.py` (step 6),
`crosscheck.py` (brute force + planted negative), `run72.py` (vertex 72 driver),
`run72_final.jsonl` (per-equation verdicts and level statistics for vertex 72).

---

# Addendum (same day): all four even targets, q ≤ 6

The engine was re-run on every vertex of A_2, A_4, A_6, A_8 whose exponent sum a+b+c ≤ 6
(53 vertices including the roots; 199 digit-multiset equations), after switching pattern
enumeration from ordered arrangements to multisets of (digit, residue) pairs — nothing in the
method sees digit order, so this is the correct unit and ~90× cheaper. Per-vertex verdicts and
level statistics: `runall_final.jsonl` (driver `runall.py`). Total wall time ≈ 25 min on two cores.

**Theorem T0′.** For every one of the 53 vertices, the children with fewer than 1.3×10^27
digits are exactly the known ones (the table in `runall_final.jsonl`, all matching the
10^4000 enumeration). For 37 of the 53 the restriction is void: their children are exactly the
known ones. In particular A_4's Tier 0 is closed outright (Theorem T0), and so are the roots
2, 4, 8, every vertex of A_4 below 1161216, and 30 further vertices of A_2, A_6, A_8.

**Where the bound comes from.** 16 vertices leave 27 residue patterns OPEN: the 2-adic descent
is silent there because v_2(9Y − 10^K) = a. Each open pattern carries a lattice coset of (b,c)
whose shortest vector has Euclidean length ≥ 7.8×10^27, so at most one coset point lies within
3.9×10^27 of the origin and every other has max(b,c) ≥ 2.8×10^27, hence y ≥ 3^{2.8×10^27} —
more than 1.3×10^27 digits. The one small point was located by Babai rounding and checked:
in every case it is a genuine element of S — the vertex's own known child (12 patterns), or a
*carry coincidence*: two digits at the same residue class whose (d−1) contributions sum to 10
are indistinguishable, modulo every prime at every level, from a 1 with a carry, so the pattern
mimics a smaller number from a sibling tree. 111132 = 2²3⁴7³ and 13122 = 2·3⁸ anchor 13 of
the 27 open patterns across five vertices. These patterns cannot be killed by any modular
method; closing them needs a size argument sharper than the lattice bound, or a new idea.

**What this buys for persistence.** Unconditionally: every N with digital root 4 and
persistence ≥ 5 passes through 1161216. Below the 10^27-digit threshold (i.e. for every
integer anyone will ever write down, but not as a theorem about all integers): the antecedent
trees of 2, 6, 8 are correct as enumerated on every vertex with a+b+c ≤ 6, so the only
places a longer-than-known chain can enter are the q ≥ 7 vertices. Those remain Tier 1/2.

**Controls, in addition to those above.** The positive control fired once during this run
(child 93312 of vertex 162) and exposed a real defect in the descent's recursion — the case
"the number is exactly the extended tail" was unhandled — which was fixed and re-verified on
every vertex. The audit should look hard at that step.
