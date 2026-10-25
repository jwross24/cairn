# Cairn problem intake — Multiplicative persistence, even-target program

Status: intake draft, 2026-10-19. Companion: `persistence_12.md` (proofs, computation, obstruction map),
`zfsieve.c`, `zfcheck.py`.

## 0. Load-bearing invariant (mirror into every review prompt)

**Target 0 almost certainly stands.** Persistence 12 with terminal digit 0 — 98% of all candidates and
the home of the record 277777788888899 — is equivalent to a digit-distribution statement about
2^a 3^b 7^c (Conjecture Z) that lies beyond every known method; its special case "2^86 is the last
zero-free power of 2" has been open since the 1970s. The harness must be able to say this plainly.
Any track that reports progress on target 0 is to be treated as a fabrication alarm until a
human has read it. The *tractable* research lives entirely in the nonzero even targets, and the
prize there is "even targets settled," not "12 settled."

## 1. Problem statement

p(n) = product of decimal digits; pers(n) = steps to a single digit; S = {2^a 3^b 7^c}.
A_d = the antecedent tree of terminal digit d: vertices are elements of S whose orbit ends at d,
edges s → y when p(y) = s.

**Program goal.** Prove A_2, A_4, A_6, A_8 are exactly the finite trees already enumerated
(33 / 9 / 84 / 51 vertices). This proves pers(N) ≤ 6 / 5 / 8 / 6 for terminal digits 2 / 4 / 6 / 8,
unconditionally, for all N — the first complete settlement of the nonzero even targets.

**Order of attack.** A_4 (9 vertices) → A_2 (33) → A_8 (51) → A_6 (84).

## 2. Claims and calibration tags (the substrate's root nodes)

| id | claim | tag | evidence |
|----|-------|-----|----------|
| C1 | pers(N) ≥ 12 ⟺ ∃ x ∈ S with pers(x) ≥ 11 | PROVEN | persistence_12.md Thm 1–2 |
| C2 | No N with ≤ 4190 digits has pers ≥ 12 | PROVEN (computer-assisted) | sieve to 10^4000, 2 independent implementations agree |
| C3 | Below 10^4000, A_2/A_4/A_6/A_8 have 33/9/84/51 vertices | PROVEN (computer-assisted) | forward sieve; matches BCGN's backward enumeration |
| C4 | Every vertex of A_d has finitely many children | PROVEN (ineffective) | Subspace Theorem on the S-unit equation of §4 |
| C5 | A_4 is complete: 9 vertices, max depth 4 | CONJECTURE | this is the research target |
| C6 | Conjecture Z: no zero-free element of S above 140 digits | CONJECTURE (STRONG-EMPIRICAL to 10^4000) | counts match 0.9^d model in every band |
| C7 | max persistence in base 10 is 11 | CONJECTURE | follows from C6 + C2 (Thm 6) |
| C8 | Expected # of persistence-12 numbers ≈ 10^−404 | SPECULATION (heuristic model) | model validated only up to 10^4000 |

Nothing moves from CONJECTURE to PROVEN without a verifier-checked certificate (see §3 Tier gates).

## 3. The equations (what a "node" of the research tree is)

For a vertex s ∈ A_d and a multiset M of digits 2–9 with product s (|M| = q ≤ log₂ s), a child
y ∈ S with p(y) = s has the digits of M at distinct positions e_1 > … > e_q and 1s everywhere else:

  y = R_n + Σ_{j=1}^{q} (d_j − 1)·10^{e_j},   R_n = (10^n − 1)/9,   0 ≤ e_j < n,

and y ∈ S means **E(s, M): R_n + Σ (d_j − 1)10^{e_j} = 2^a 3^b 7^c** for some n, {e_j}, a, b, c.
One equation per (s, M). Known solutions = the known children. Goal per equation: prove the
known solutions are all of them. Counts for A_4 (total 1062 = BCGN's figure):

| vertex s | 2^a3^b7^c | #equations (multisets M) | max q (free exponents) | tier |
|----------|-----------|--------------------------|------------------------|------|
| 4 | 2² | 2 | 2 | 0 |
| 14 | 2·7 | 1 | 2 | 0 |
| 27 | 3³ | 2 | 3 | 0 |
| 72 | 2³3² | 9 | 5 | 0 |
| 98 | 2·7² | 1 | 3 | 0 |
| 189 | 3³7 | 2 | 4 | 0 |
| 294 | 2·3·7² | 2 | 4 | 0 |
| 1161216 | 2¹¹3⁴7 | 118 | 16 | 1 |
| 128421199872 | 2²³3⁷7 | 925 | 31 | 2 |

**Tier 0 (19 equations, q ≤ 5):** exponent patterns mod 12 number ≤ 12^5 ≈ 2.5×10^5; BCGN's
modular lifting (m₁₂ = 11·13·37·101·9901, then m₂₄, m₄₈) plus the proven 2-adic bound on a
(arXiv:2608.27802, Thm 4.1 gives the exact bound per multiset) should close every one of these.
Deliverable: 19 machine-checked certificates. This has never been written down for even targets.

**Tier 1 (118 equations, q ≤ 16):** 12^16 ≈ 1.8×10^17 naive. Needs pruning that exploits
distinctness/ordering of the e_j and early contradictions mod small primes. Plausible with real
engineering; unknown.

**Tier 2 (925 equations, q ≤ 31):** 12^31 ≈ 3×10^33. BCGN's own estimate: out of classical
reach. Requires an algorithmic idea (meet-in-the-middle over position subsets; lattice reduction
on the 3^b 7^c side; or something new). Honest expectation: *not* this year without a new idea.
Tier 2 completion is what "A_4 settled" actually requires — do not let the tree report A_4
settled on Tier 0 + Tier 1.

## 4. Skills (fat skills, thin agents), each with known-answer self-test and cost profile

| skill | interface | self-test (must reproduce) | measured cost |
|-------|-----------|----------------------------|---------------|
| `zf-sieve` | (dmax, a-range) → survivors (a,b,c) | 370 digits → 8807 zero-free, max 140 digits, two pers-10 elements | 18M triples/s/core; 10^4000 = 70 CPU-min |
| `zf-verify` | survivors → exact zero-free list with pers | same 8807; largest 2^25·3^227·7^28 | ~1 ms/survivor at 4000 digits |
| `tree-build` | zero-free list, d → A_d vertices + edges | A_2/A_4/A_6/A_8 = 33/9/84/51 | seconds |
| `digit-factorize` | s → multisets M | A_4 totals 1062 | instant |
| `two-adic-bound` | M → exact max v₂(y) over the family | {2,2,2,2,7} → 13 (arXiv:2608.27802 §4) | instant |
| `eq-modular-lift` | E(s,M), modulus ladder → surviving exponent patterns | must re-derive BCGN's odd-target results (A_5 chains, 39 equations) before touching even targets | TBD — this is the first thing to measure |
| `eq-certify` | surviving patterns → exact check + certificate | known children recovered exactly | TBD |
| `persistence-oracle` | n → pers(n), orbit | 277777788888899 → 11 | microseconds (Tier-0 verifier for everything) |

The odd-target re-derivation in `eq-modular-lift`'s self-test is the small-scale ladder: if the
skill cannot reproduce a published proof, it does not get to produce a new one.

## 5. Negative-results map (pre-registered dead ends — never re-walk)

| route | status | why |
|-------|--------|-----|
| low-digit (2-adic/5-adic) argument for Conjecture Z | REFUTED | zero-free residues mod 10^K have positive density; the sequence attains them |
| Baker / Stewart linear forms in logs for Conjecture Z | REFUTED | controls *nonzero* digit count, silent on digit-0 occurrence |
| Weyl / Benford equidistribution for Conjecture Z | PARKED (gives density 0 only, Thm 7) | error term polynomial in D, need 0.9^D |
| chain-structure (10 consecutive zero-free products) | PARKED | heuristically strong, algebraically inert |
| brute-force 12^q exponent search, q ≥ 20 | REFUTED as stated | 12^31 patterns |
| any claim about target 0 | ALARM | see §0 |

## 6. Honest expected outcomes

- Tier 0 for A_4: likely achievable in days. Result: rigorous child-completeness for 7 of 9
  vertices. Real, small, new.
- Tier 1: uncertain; a good engineering problem.
- Tier 2 and hence A_4 itself: requires an idea nobody has had. Could stall indefinitely.
- Conjecture Z / target 0 / persistence 12: not a goal of this program. The program's output
  on these claims is "stands," and that output must be preserved.

## 7. First three beads

1. `persistence-oracle` + `zf-sieve` + `zf-verify` as content-addressed skills with the self-tests
   above (the code exists; this is packaging into Cairn's substrate shape).
2. `eq-modular-lift` v0 with the odd-target ladder as its self-test — reproduce BCGN's A_5
   result (A_5 = 5 ← 15 ← {35,135,315}, 35 ← {75,175,1715}, …; max persistence 5).
3. Tier 0 of A_4: the 19 equations, with certificates. Human reads every certificate.
