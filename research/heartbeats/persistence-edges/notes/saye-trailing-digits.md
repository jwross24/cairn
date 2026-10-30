# Saye, ternary digits of 2^n: does the trailing-digit tree carry over?

Source: R. I. Saye, "On two conjectures concerning the ternary digits of powers of two",
arXiv:2202.13256 (v2 2022-03-23), J. Integer Sequences 25(3) 2022. Read: abstract page and arXiv HTML,
2026-10-29. Already cited in cairn as the design reference for H9
(`research/intake/persistence/HYPOTHESES.md:89`, `:239`), so this note adds the carry-over analysis only.

## The construction (documented: paper §2–4)

- 2 is a primitive root mod 3^k, order u_k = 2·3^(k-1). The last k ternary digits of 2^n depend only on
  n mod u_k.
- Lemma 1(iii): d_{k+1}(2^(i·u_k + j)) ≡ d_{k+1}(2^j) + i·d_1(2^j) (mod 3), so the three lifts j, j+u_k,
  j+2u_k realize all three values of digit k+1.
- Depth-first tree, prune a node whose newest digit is the forbidden one. Survival 2/3 per level gives
  Θ(2^K) nodes covering all Θ(3^K) exponents n < u_K. K = 46 verifies Erdős's and Sloane's ternary
  conjectures for n ≤ 2·3^45 ≈ 5.9e21 (64 cores, a few days).
- The tree never closes a conjecture. Its output is "verified for n < u_K", a finite range, because one
  generator makes each depth-K class a single exponent below u_K.

## Base-10 analog for S = 2^a 3^b 7^c (verified: probe at the end of this note, 2026-10-29)

Probe: subgroup closure of {3, 7} in (Z/10^k)^*, k ≤ 6, and next-digit sets over each class.

- **⟨3,7⟩ has index 2 in (Z/10^k)^* for every k ≥ 2** (20 of 40 units mod 100, 2·10^(k-1) of
  4·10^(k-1) in general). Both generators are ≡ 3 (mod 4) and quadratic non-residues mod 5, so the odd
  part y = 3^b 7^c always satisfies χ_4(y) = (y/5). An H9 implementation testing membership in the full
  unit group stays sound but prunes 2× less than one testing the true subgroup at level 2.
- **For k ≥ 2, each class mod 10^k has exactly 10 lifts mod 10^(k+1), and they realize all 10 values of
  digit k+1.** This is the base-10 Lemma 1(iii): branching 10, survival = |allowed digits| / 10.
- 2 and 3 are primitive roots mod 5^k (checked k ≤ 8), so an even y = 2^a·(odd) with a < k has its
  5-adic part unrestricted by the index-2 character; the filter applies to the a = 0 branch.

## What carries over and what does not (inferred from the two facts above; not run on any equation)

1. **Pruning carries over, closure does not.** With two or three generators a depth-K class is a coset of
   a rank-2 or rank-3 lattice, infinite, not a single exponent. Saye's "verified for n < u_K" has no
   analog without an archimedean box on (a, b, c).
2. **The all-ones thread never dies.** For E(s, M), y = R_n + L with L fixed by the special-digit
   placement. Because all 10 next digits are realized at every level, exactly one lift continues the 1s
   at each level once the level-2 character condition holds. The tree therefore keeps one live thread per
   special placement forever, converging 10-adically to L − 1/9. These are the anchored patterns that
   H1/H10 and Wall 1 already describe; the suffix tree cannot remove them, and closing each needs the
   Baker/LLL side (`tier0/BAKER-CHAIN.md`, `tier0/LLL-BOUND.md`).
3. **Where H9 can win.** Per level, a non-anchored branch survives with probability about
   |{1} ∪ M| / 10, so off-thread nodes die fast. That supports H9's prediction of fewer lift nodes, but the
   live-thread count is a floor that grows with the number of special placements, C(K, q') for q'
   specials inside the window.

## Verdict for the loop

No new method beyond H9. Concrete inputs for the H9 kill test: use the index-2 subgroup, and expect a
survivor floor equal to the anchored-thread count rather than zero. Confidence: HIGH on the two verified
group facts (k ≤ 6), MEDIUM on the thread-count floor (argued, not measured on a cairn equation).

Leads from the reference list: Gupta 1978 (powers of 2 as sums of distinct powers of 3), OEIS
A351927/A351928 (record trailing runs). Dimitrov–Howe, Lagarias, Narkiewicz are already in cairn.

## Probe

Run with `uv run python -I <file>`; output on 2026-10-29: index 2 for k = 2..6, 10 lifts with 10 distinct digits for k = 2..5, all three primitive-root checks True.

```python
import sys
from math import gcd

def subgroup(gens, mod):
    seen = {1}
    frontier = [1]
    while frontier:
        nxt = []
        for x in frontier:
            for g in gens:
                y = x * g % mod
                if y not in seen:
                    seen.add(y); nxt.append(y)
        frontier = nxt
    return seen

for k in range(1, 7):
    mod = 10 ** k
    units = sum(1 for x in range(mod) if gcd(x, 10) == 1)
    h = subgroup([3, 7], mod)
    print(f"k={k} |<3,7> mod 10^k|={len(h)} units={units} surjective={len(h)==units}")

for k in range(1, 6):
    lo = subgroup([3, 7], 10 ** k)
    hi = subgroup([3, 7], 10 ** (k + 1))
    fib = {}
    for y in hi:
        fib.setdefault(y % 10 ** k, set()).add(y // 10 ** k % 10)
    sizes = {len(v) for v in fib.values()}
    print(f"k={k}: lifts per class={len(hi)//len(lo)} distinct next-digit counts={sorted(sizes)}")

for p, mod_base in ((2, 3), (3, 5), (2, 5)):
    ok = all(len(subgroup([p], mod_base ** k)) == (mod_base - 1) * mod_base ** (k - 1) for k in range(1, 9))
    print(f"{p} primitive root mod {mod_base}^k for k<=8: {ok}")
```
