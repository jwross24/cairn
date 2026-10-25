# X5 Lemma (ii) in Lean: additive kill when (p − 1) | d₁

`X5Kill.lean` (md5 4a2f8428) checks with `lake env lean` against the Mathlib pinned in `cairn/lean/lake-manifest.json`
(toolchain leanprover/lean4:v4.34.0-rc1), run on the host from `cairn/lean`, rc 0 (`pos.out`).
`#print axioms X5.kill_193`: `[propext, Classical.choice, Quot.sound]`, so no `sorryAx` and no project axiom.

## What is proved

- `X5.additive_kill`: for a prime p, units u, v of ZMod p, and integers d, b, c, if (p − 1) | d, d | b and d | c,
  then u^b · v^c = 1. This is EXPERIMENTS-X §X5 Lemma (ii) with Λ_L ⊆ d·Z² as the hypothesis.
- `X5.kill_193`: the instance p = 193, u = 3, v = 7, d = d₁ = 13545045360000. (193 − 1) | d₁ is discharged by norm_num.
- `X5.d₁_factor`: d₁ = 2^7·3^2·5^4·7·11·41·59·101.

## Statement-level match

- The Lean hypotheses `d₁ ∣ b` and `d₁ ∣ c` are the content claim: every vector of Λ_96 has both coordinates divisible
  by d₁. Lean does not prove that claim.
- The content claim rests on two independent exact computations:
  - the chat's EXPERIMENTS-X §X5;
  - Codex blind P9 in `tier0-opt/codex-prompts/PROMPTS-2026-10-21.md`. Its HNF is the intersection, confirmed by a maximal-minor index.
- Cairn re-checked both HNF columns mod all 20 primes, and confirmed that their gcd is d₁.
- So the 193 kill is Lean-checked conditional on a computed fact. It is not a Lean proof that the level-192 prime 193 is
  additive for Λ_96.
- Lemma (i), content = d₁, is not formalized.
- The 769 kill is outside (ii): 768 ∤ d₁, and its trivial image holds by direct computation only.

## Planted negative

`X5Neg.lean` (md5 694c141a) is the same file with 769 in place of 193. It is refused with rc 1, and the divisibility goal
reduces to `⊢ False` (`neg.out`).

## Limits

- The check ran on the host, not in the Cairn gate container.
- No Cairn substrate node records it.
- This is a persistence-lane note, not a Cairn PROVEN claim.
