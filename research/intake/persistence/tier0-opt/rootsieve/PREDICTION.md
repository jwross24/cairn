# ROOT-SIEVE prediction (written before any compute)

Question: is there an anchor-free, additive necessary condition on a level-12 pattern that cuts the
enumeration by 100x or more before the multiplicative test?

## Odds

- Verdict "100x or more": 5%.
- Verdict "partial (a real but sub-100x cut)": 60%.
- Verdict "dead (nothing beyond what the pipeline already applies)": 35%.

## Reasoning behind the odds (read, not yet measured)

- Pattern representation: positions are known mod 12 only, n mod 12. A condition can bite only if it is a function
  of (nu, digit values, classes mod 12). Of the additive facts about x = 2^a 3^b 7^c, the ones that are functions of
  that data are: 3 | x (digit sum, needs only nu mod 3 and the multiset), 7 | x (period 6 divides 12), x mod 11/13/37/
  101/9901 (already the multiplicative test), and the lowest classes (the 2-adic and 5-adic windows).
- The 3 | x and 7 | x facts are the "rank" of MAP.md L4. The branch-split lane (tier0-opt/branchsplit, math/r1-branch-split)
  already applies them to the level-12 survivors: 19-20x fewer survivors, predicted from the three-way split
  57.14% / 38.10% / 4.76% (21x). It does not touch the enumeration hot loop. So the live question is whether that
  21x can be moved into the hot loop (enumerate only rank-2 patterns: 3 | x via nu, 7 | x via the last class) and what
  the rank-0 and rank-1 streams then cost. Expected hot-loop cut: about 15-21x, not 100x.
- 5-adic window: 3 is a primitive root mod 5^s, so x mod 5^s carries no constraint without the (b, c) coset, and the
  coset pins b mod 9900, c mod 900, hence x mod 5^3 at most (order of 3 mod 5^4 is 500, which does not divide 9900).
  That is the K = 3 tail the kernel already applies, and it needs V, so it cannot prune a prefix.
- 2-adic window: the weakest consequence over a in {a0, a0+12, ...} is chain-feasibility at a = a0 < 12, and a0 = 0
  (one twelfth of the survivors) has no constraint at all. Swapping the quantifier (enumerate a0 first) cannot lower the
  hot-loop cost: the a0 = 0 class still needs the full enumeration, and a0 is only known after V.
- 3-adic and 7-adic depth (9, 27, 49 dividing x): the reachable set of x mod 3^j over all lifts of a pattern should
  be everything, so no constraint beyond 3 | x. To be measured.

## Expected cut factors (to be compared with the measurement)

| condition | on residue survivors | in the hot loop |
|---|---|---|
| rank (3 | x, 7 | x with the b = 0 / c = 0 coset test) | 19-21x | at most 21x, needs a separate rank-0/1 path |
| 2-adic chain beyond the K = 3 tail | 1.5-3x | 0 |
| mod 9 / 27 / 49 | 1.0x | 0 |
| anything keyed on actual positions (Lemma C, Theorem F) | not available at level 12 | 0 |

Combined best case I expect: 20-60x on survivors, at most 21x on the hot loop. I expect to report "partial".
