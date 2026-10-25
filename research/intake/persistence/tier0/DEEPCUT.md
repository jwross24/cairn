# The full-depth 10-adic cut: 42 of the 47 "closed below 10^27 digits" vertices are closed outright

*2026-10-20 03:10 EDT, chat session. Code: `deepcut.py` (level 96), `deepcut192.py` (level-192 lift for the
survivors). Inputs: the sweep files only (`runall_final.jsonl`, `trees_c.jsonl`, `trees_mac.jsonl` as of
00:05). Calibration: STRONG-EMPIRICAL → the argument is exact and every step is checked by positive
controls, but it has not been blind-reimplemented or Lean-checked; see "Verification" and "What a second
implementation must reproduce". Full run log: `DEEPCUT-run.txt`.*

## Statement

**Lemma C (deep cut).** Let P be an open pattern at level 96 of an equation (s, M), with 2-adic exponent a,
positions e_j ∈ [0, 96) (the residues as integers), ν ∈ [0, 96), and coset C ⊂ Z² in (b, c). Suppose every
point of C other than one explicitly checked point has max(b, c) > 192·log 10 / log 3 (true here: the
lattice bound gives ≥ 10^27 digits). Then every candidate y′ = 2^a 3^b 7^c of P, (b, c) ∈ C, other than the
checked point has n ≥ 192 digits, and for D ∈ {1, 2} its lowest 96D digits are

   y′ ≡ L := R_{96D} + Σ_{j} (d_j − 1)·10^{e_j + 96 t_j}   (mod 10^{96D}),   with t_j ∈ {0, …, D−1} or "≥ D",

positions distinct. Hence v₂(L) = a and 3^b 7^c ≡ L/2^a (mod 5^{96D}) and (mod 2^{96D−a}): three linear
congruences in (b, c) (descent.cut_coset, K = 96D). If for every admissible choice of the t_j the
congruences are inconsistent with C, then P has no candidate besides the checked point: P is CLOSED.
Otherwise the surviving sub-cosets give a new height bound (their shortest vectors).

The argument needs no anchor; it is the engine's Lemma B (10-adic pinning + descent) pushed to the full
period instead of K* ≤ 5 digits, with the 2^q copy choices enumerated explicitly. What makes it bite at
level 96 and not at 12 is the index of Λ_96 (2.8×10^56): the 10-adic unit group mod 10^96 is no longer
covered by the coset's image, so a target is hit with probability ≈ 10^−6 per case (measured on random
S-units: the cut multiplies the coset index by 2×10^88 against a group of size 2.5×10^95).

## Result

Over all 299 open (vertex, multiset, anchor) triples (964 representations, every representation of each
anchor with positions in [0,96) and value y + kR_96, 0 ≤ k ≤ 9, since the C-pipeline files do not record
(ν, e_j)):

- **288 patterns CLOSED** at depth ≤ 2 (most at depth 1, i.e. by the lowest 96 digits alone).
- **11 patterns survive**, all in 5 vertices of T_6/T_8 from the Mac/C sweep: 8192 (3 patterns), 14112 (1),
  14336 (5), 32928 (1), 49392 (1); anchors 330812181 = 3^9·7^5 (a = 0, five patterns), 57177414 = 2·3^5·7^6, 2722734 = 2·3^4·7^5,
  777924 = 2^2·3^4·7^4, 7411887 = 3^2·7^7, 78121827 = 3^13·7^2. Each has exactly one surviving chain at every depth: bound 10^1.7e120 digits at
  depth 2, 10^2.2e216 at depth 4, and after the lift to level 192 (new primes 193, 769, 19841, 976193,
  6187457, 834427406578561; one child of 128–1024 alive) 10^2.3e226 at depth 2. The chain is structural:
  compatibility at depth D is decided in the fixed finite group Z²/(Λ_96 + M), so a chain that passes
  depth 1 passes every depth — these 11 patterns have a genuine 10-adic solution and the deep cut can
  only push their bound up linearly in the depth (each depth ×10^48 digits, at ~2^q cases per depth).

**Per vertex: 47 vertices had open patterns; 42 are now CLOSED outright, including all 16 bounded vertices
of T0′ (so T0′ reads: all 53 vertices CLOSED).** The 5 remaining vertices are closed below 10^2.3e226
digits (depth-2 at level 192), a bound that can be raised to any 10^(48D) at cost 2^q·D.

## Verification done

1. Real S-units survive: 289/289 random y′ = 2^a 3^b 7^c with ≥ 290 digits, a ∈ {0,…,34}, placed in their
   own coset (b,c) + Λ_96, survive the cuts at K = 96, 192, 288 (`cut_coset` + Λ_96 never produces a false
   kill on a genuine point).
2. The case enumeration generates the true lower-digit choice: a synthetic y′ with 6 pattern digits
   (two in one class) at chosen copies 0/1/2 — its y′ mod 10^{96D} is among the L values built at every
   depth, and the depth-1 count is 48 = 2^6 − 2^4 (the class collision excluded).
3. The level-96 patterns all come from equations whose last level is 96 (checked in the files), so
   Λ_96 is the right lattice; using the anchor's coset (b_y, c_y) + Λ_96 is a superset of the engine's
   coset (which may carry descent cuts), hence conservative.
4. Anchors are the engine's recorded exceptional points with the recorded a (asserted).

## What a second implementation must reproduce (for Cairn/Codex)

From OPEN-PATTERNS.md's anchors alone: build Λ_96 from the discrete logs of 3 and 7 at the primes of
10^96 − 1 except 3 and 7; for each (s, M, a, y) enumerate the representations and the copy choices, apply the
three congruences at K = 96 and 192, and report CLOSED / bound per pattern. Expected: 288 CLOSED, the 11
listed survivors, the same per-vertex split. A planted check: pick any real y′ with ≥ 300 digits and
confirm it survives its own chain.

## Consequences

- PAPER.md Theorem 2 shrinks to the 5 listed vertices (and the sweep's new closed-below vertices will be
  run through the same cut as they arrive); Theorem 1 gains 42 vertices. The "frontier" is unchanged
  (the 18 enumeration-bound vertices).
- The engine should run the deep cut as its final stage after level 96 (`deepcut.deep_cut` needs only
  the coset, a, ν, positions). For base 8 the analogous cut is 2-adic only (one base prime) and the lattice
  is 3-dimensional; whether it kills or only bounds is to be measured.
- The 11 survivors are the first open patterns of the whole project that are not explained by a small
  anchor's shadow alone: they are 10-adically consistent chains. That is a sharper object than before.

## Blind re-implementation (04:25 EDT, fresh Claude agent, no access to deepcut.py; `lemma_c_blind.py`, `AUDIT-DEEPCUT-blind-claude.md`)

Written from this file and OPEN-PATTERNS.md alone, with its own p-adic logarithms and its own coset
arithmetic (brute-force-verified on 200 random small cosets). Results: Λ_96 index 2.8100×10^56 and
shortest vector 7.8502×10^27 (match); positive control 50/50 genuine S-units survive at K = 96 and 192;
negative control 30/30 corrupted-digit points excluded; **288 CLOSED / 11 survivors, the same 11 lines,
the same 5 vertices, the same anchors**; surviving sub-coset shortest vectors 10^120.6–10^121.1 (match).
Representation count 975 vs 964 here (it enumerates k up to 9 including k = 9 reps; no verdict changes).

Two structural facts it established that sharpen the lemma:
- The image of Λ_96 in (Z/5^96)^* has index 2500 = 4·5^4 and in (Z/2^96)^* index 2^8: a depth-1 case
  survives with probability 1/640000 ≈ 1.6×10^−6, and **the verdict depends only on the target modulo
  5^5·2^9** — i.e. on the pattern digits at positions < 9 and their copy choices. Lemma C is therefore a
  statement about the lowest nine digits, which is why Lemma B at K* ≤ 5 nearly, but not quite, had it.
- Depth 2 never kills (the depth-1 sublattice maps onto the kernel of G_192 → G_96): deeper cuts only
  multiply the index by 10^96 per depth. "One surviving chain" means one depth-1 survivor.
Calibration unchanged (STRONG-EMPIRICAL): two independent implementations agree; no Lean, no Codex yet.

## Status 06:45 EDT (sweep file of 05:45, 52 Mac vertices; `DEEPCUT-run-0545.txt`)

679 anchored patterns (3665 representations), depth 1: **636 CLOSED; 56 vertices had open patterns, 44 are
now CLOSED outright, 12 carry survivors** (43 patterns): 8192, 14112, 14336, 18144, 23328, 27216, 28672,
32928, 34992, 42336, 49392, 148176. Survivors cluster on a few anchors: 330812181 = 3^9·7^5 (a = 0; vertices
8192, 14336, 28672), 2722734 = 2·3^4·7^5, 44471322, 60761421, 777924, 1361367, 1134213192, … The survival
rate per pattern stays near 6% as the vertices grow (more cases per pattern), so the final sweep will
leave a few dozen patterns in roughly 15–20 vertices closed below 10^(1e72) digits (depth 1; ×10^48 per
further depth). Those are the project's real residue: 10-adically consistent shadows of specific small
S-units.

## Lifting the survivors to levels 192/384, 288 and 480 (12:30 EDT; `deepcut_lift.py`, logs `DEEPCUT-lift-*.txt`)

A level-96 pattern lifts to level mL (m children per digit and for ν); each child's coset is cut by the
new primes' congruences (only the discrete-log-feasible primes are used — a subset of a level's primes is
a valid, weaker level; the 55-/112-digit unfactored parts of Φ_128(10), Φ_384(10) and the 40-digit
cofactor of Φ_192(10) are omitted), and Lemma C is applied at K = mL. Results on the 43 survivors of the
05:45 run:
- 192 then 384 (primes 193, 769, 19841, 976193, 6187457, 834427406578561, 1253224535459902849; then 3457,
  12289, 418725889, 1265011073): **37 of 43 closed**. Six survive, in 14336, 28672 (five, all a = 0, anchors
  78121827 = 3^13·7^2 and 330812181 = 3^9·7^5) and 42336 (a = 1, anchor 3281116734).
- 288 (factor-3 lift; 19, 3169, 8929, 13249, 52579, 98641, 333667, 1067329, 999999000001): closes the two
  330812181 patterns; the four others survive.
- 480 (factor-5 lift; 22 new primes up to 100009999999899989999000000010001): closes none of the four.
So, after every modular ladder available at this height, the residue of the base-10 sweep as of 05:45 is
**4 patterns in 3 vertices**: 14336 (M = 227888, a = 0, anchor 78121827), 28672 (M = 2227888 and 2244788,
a = 0, anchor 78121827), 42336 (M = 22334677, a = 1, anchor 3281116734 = 2·3^14·7^3); log `DEEPCUT-lift-480.txt`. The persistent ones are "digit above the top" shadows (e.g. 78121827 =
7812·1827 read with ν = 7 and an 8 in place of the top 7): their candidates carry ≥ 95 leading 1s, which
makes them the natural target of an archimedean (Baker–Davenport/LLL) bound on top of the lattice — an
expected gain from 10^66 to ~10^113 digits, still a bound, not a closure. Recorded as the next idea, not
done.

## Second blind re-implementation: Codex (GPT-6-Astra, run by Cairn 02:40 Mac time; ledger)

From DEEPCUT.md + OPEN-PATTERNS.md only, on the 00:05 snapshot: **299 patterns, 288 CLOSED, the same 11
survivors, 42 of 47 vertices fully closed; per-pattern comparison by Cairn: 0 verdict disagreements.**
Its planted checks pass (a real ≥ 300-digit y′ survives its own chain; a perturbed congruence kills it).
Non-verdict differences: it enumerates more representations (979; repeated residues, ν = 0, k > 9 — all in
patterns that close anyway), counts sub-cosets per pattern rather than chains, and gets depth-2 bounds a
factor 2–5 lower (norm convention). It caught the "except 3" wording above. With the Claude blind audit
(same verdicts) and the Lean lemmas `candidate_modEq` (y′ ≡ y mod R_L for every candidate of an anchored
pattern) and `deep_cut_core` (y′ ≡ 2^a·ℓ mod 10^K ⇒ v₂ = a and the two unit-group congruences, any K),
Lemma C's verdicts now rest on three implementations in two model families and its arithmetic on Lean;
the enumeration and lattice steps are not Lean-checked, so the calibration stays STRONG-EMPIRICAL under
RULE 2, at the same standard as Theorem T0.
