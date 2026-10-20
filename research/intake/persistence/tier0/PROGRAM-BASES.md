# Program: the persistence conjecture for nonzero digital roots in small bases

*Proposed 2026-10-19 22:30 EDT by the chat session, from a scan of the antecedent trees in bases
6, 8, 9, 12 (`/tmp/basescan2.py`, reproduced below). Status: proposal; nothing built yet.*

## Why

Base 10's even targets have a frontier of ⟨18⟩ vertices at 10^15–10^22 residue patterns that no
enumeration reaches. The same machinery, generalized to base b, produces **complete** theorems in
small bases, because their trees are tiny. Sloane's conjecture per base (Lamont-Smith's table,
OEIS A380137) has never been proved for any base except in the odd-target base-10 case.

## The scan (zero-free S-units below b^D, trees by digital root)

| base | digit primes | base primes (bounded exponents) | free exponents (lattice dim) | nonzero targets: vertices (max q) | conjectured max persistence |
|---|---|---|---|---|---|
| 6 | 2,3,5 | 2,3 → two families 2^a5^c, 3^b5^c | 1 | 2: 9 (12); 3: 2 (3); 4: 13 (15); 1, 5: none multi-digit | 5 |
| 8 | 2,3,5,7 | 2 (a ≤ 2) | 3 | 1: 3 (6); 2: 7 (4); 3: 4 (4); 4: 29 (9); 5: 2 (6); 6: 17 (10); 7: 1 (2) | 6 |
| 9 | 2,3,5,7 | 3 (b ≤ 1) | 3 | 3: 85 (27); 6: 46 (27); 7: 12 (13); 8: 7 (15); 1: 5 (10); 4: 5 (8); 5: 5 (11); 2: 1 (4) | 7 |
| 12 | 2,3,5,7,11 | 2,3 | 3 | 4: 67 (31); 6: 32 (11); 8: 23 (16); 3: 5 (8); 2: 4 (5); 9: 5 (6); 10: 3 (2) | 7 |
| 10 (ours) | 2,3,5,7 | 2 (via the 5-rule: a bounded, 5 excluded) | 2 | 2: 32; 4: 8; 6: 83; 8: 50 (q up to 31) | 11 |

Observed maxima in the scans equal the conjectured values in every base — the trees found are
the whole story if they are complete.

**Base 8 is the prize**: 63 vertices, q ≤ 10, every vertex ≤ 7 base-8 digits. With the engine
generalized, every equation is at most ~10^9 residue patterns. Expected result:

> **Theorem (base 8).** Every integer whose base-8 digital root is nonzero has multiplicative
> persistence at most 6, and the antecedent trees of the digits 1–7 are exactly the 63-vertex
> forest enumerated.

Base 6 is the warm-up (1-dimensional lattices: each equation pins a single free exponent modulo
N, so it is nearly a direct search) and gives persistence ≤ 5 for nonzero roots. Base 9 and 12
split like base 10: most targets close, one or two have q ≈ 27–31 and leave a frontier.

## What generalizes, and what changes

The engine is already structured for this: residue patterns modulo primes of b^L − 1 (outside
the digit primes), discrete logs, a lattice coset in the free exponents (CosetK is
dimension-generic; FastLevel's component tables are too), b-adic pinning (y mod b^K is
constant on a coset once the free-exponent lattice is inside the kernel modulo each base prime
power), and the descent lemma with v_p for each base prime p | b. What changes per base:
- the digit set {2,…,b−1} and its factorizations;
- which exponents are bounded (base primes: tail enumeration generalizes verbatim) and which are
  free (lattice dimension 1–3);
- R_n = (b^n − 1)/(b − 1) and the tail arithmetic modulo b^K;
- the level ladder: primes of b^L − 1 with useful rank deficiency (to be measured: in base 10
  level 12 was special because of 9901; each base needs its own "special" level).

Validation is *easier* than in base 10: trees are tiny, so brute force over all y of each
equation's shape up to 25–30 base-b digits is cheap and is a strong oracle; the known-child
corpus is complete and small.

## Plan

1. `engine_b.py`: a base-parametrized Python engine (no C needed for bases 6 and 8), reusing
   lattice3/fastlevel/descent with b and the prime split as parameters. Gate: brute force per
   equation to 25 digits; positive controls = the scanned trees.
2. Base 6 end to end (hours). Base 8 end to end (a day). Then 9 and 12 as far as they go.
3. Cairn: blind re-implementation audit per base from the written method (same protocol as
   base 10), Lean lemmas restated for general b, and the tables.
4. Paper: one paper, all bases: "The multiplicative persistence conjecture for nonzero digital
   roots: complete in bases 6 and 8, the even-target frontier in bases 9, 10, 12, and the
   uniform reduction to the zero-free S-unit problem."

## Risk

The level ladder in another base may lack a level with real kill power (base 10's level 12 is
special). If the best level kills, say, only 1 in 5 instead of 1 in 40, the lift fan-out grows
and some base-9/12 vertices fall out of reach; bases 6 and 8 are small enough that this cannot
matter. Nothing here touches target 0 in any base: that remains the zero-free S-unit problem,
which this program makes explicit as the single obstruction across all bases.
