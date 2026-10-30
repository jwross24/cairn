# persistence-edges: overview

Run: 7 wakeups on 2026-10-29, owner session cairn-d2, closed on the stop condition "3 consecutive
wakeups with no new lead" (iterations 5, 6, 7). Objective: methods adjacent to the even-target
multiplicative persistence program (`research/intake/persistence/INTAKE.md`) that could settle or prune
a nonzero even target.

## Bottom line

No source found here settles or prunes a nonzero even target. Every adjacent method lands on one of two
walls that cairn has already mapped: it either verifies a finite range (Saye) or bounds a count or a
dimension (Narkiewicz, Zhao–Li, Abram–Lagarias). Neither kind of statement can certify that a specific
S-unit is absent, which is the content of an E(s, M) closure. That is Wall 1 in `HYPOTHESES.md`.

The run produced two concrete inputs for the open H9 suffix-search hypothesis, both verified by an
exhaustive probe embedded in `notes/saye-trailing-digits.md`:

1. ⟨3,7⟩ has index 2 in (Z/10^k)^* for every k ≥ 2 (both generators are ≡ 3 mod 4 and non-residues
   mod 5). A suffix search on the a = 0 branch should test membership in that subgroup; the full unit
   group is sound but prunes half as much.
2. For k ≥ 2 each class mod 10^k has exactly 10 lifts mod 10^(k+1), realizing all 10 next digits. So
   the all-ones thread of R_n + L survives every level, one live thread per special placement: H9 can
   prune off-thread nodes at rate |{1} ∪ M|/10 per level but has a nonzero survivor floor and cannot
   close an equation alone.

One negative, also verified: 2^a 3^b 7^c covers every residue mod 9, 27 and 81, so digit-sum congruences
(the base-10 analog of Bonuccelli–Colucci–de Faria's parity invariant) remove no candidate.

## Reading map

- **Finite-range verification by trailing digits.** Saye (one generator, base 3) is the clean model:
  a primitive root mod p^k turns digit constraints into a 3-ary tree with survival 2/3, verified to
  n ≤ 2·3^45. In base 10 with three generators the tree becomes a lattice-coset tree with 10 lifts per
  level, and the finite-range conclusion needs an archimedean box. Idowu (2026) restates the same tree in
  repunit coordinates.
- **Counting and dimension.** Narkiewicz (already in cairn) and Zhao–Li bound how many exponents give a
  digit-restricted power, N^σ with σ < 1. Abram–Lagarias compute exact Hausdorff dimensions of
  digit-restricted sets under several multipliers, valid in any base. Both are statements about density
  or 10-adic measure.
- **Variant problems.** Bonuccelli–Colucci–de Faria map the shifted and nonzero-digit persistence
  problems; their growth results are conditional on de Faria–Tresser, and the one unconditional
  classification relies on a base-3 collapse with no base-10 counterpart.

## Editorial picks

1. Saye, arXiv:2202.13256 (JIS 2022) — the cleanest lift lemma in the literature; the model for H9.
   `notes/saye-trailing-digits.md`
2. Abram–Lagarias, arXiv:1308.3133 (J. Fractal Geom. 2014) — an exact automaton for joint digit
   constraints under several multipliers, valid in base 10; dimension-only conclusions.
   `notes/abram-lagarias-cantor.md`
3. Zhao–Li, arXiv:2405.06220 (Quaest. Math. 2025) — the counting bound in its most general published
   form (number fields, any unramified base); σ ≈ 0.954 for base 10.
4. Bonuccelli–Colucci–de Faria, JIS 23 (2020) 20.10.7 — the map of shifted persistence; low yield for
   even targets. `notes/colucci-shifted-persistence.md`

Four picks rather than ten: the stop condition held before the source pool grew, and the rest of what
was read fell below the bar (see `SCRATCHPAD.md` Deprioritized).

## Disagreements between sources

None of substance. The sources agree that digit questions on powers of small primes are beyond
present methods at the integer level (Lagarias's framing of 1 ∉ E(Z_3); Dogmachine on erdosproblems.com
#406, 2025-08-09; Idowu's own disclaimer). They differ only in what partial statement each proves:
finite range, count, or dimension.

## Open questions

- Does cairn's H9 implementation, when built, use the index-2 subgroup ⟨3,7⟩ on the a = 0 branch?
- Is the anchored-thread floor the dominant H9 survivor count on a real A_4 equation? Argued here, not
  measured.
- Would an Abram–Lagarias product automaton for sibling children y, ry of one vertex give the H9 search
  a smaller exact representation than level-by-level enumeration? Design idea only.
- Has anyone extended Fonga's digit-by-digit 2-adic recursion (arXiv:2608.27802) to v_3 or v_7? No
  citing work existed in OpenAlex on 2026-10-29.

## Guardrail

Target 0 stayed out of scope. No source read here claims progress on it.
