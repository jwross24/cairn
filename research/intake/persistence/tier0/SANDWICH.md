# The Baker–lattice sandwich: closing every enumerated vertex

*2026-10-20 15:30 EDT, chat session, from two scouts' work (`LLL-BOUND.md`, `BAKER-CHAIN.md`) and Lemma C.
Code: `sandwich.py` (uses `deepcut.py`, `baker_chain.py`). Calibration: the upper bound is an ordinary
mathematical proof resting on Matveev's theorem (Bugeaud–Mignotte–Siksek, Ann. Math. 163 (2006), Thm 9.4,
quoted verbatim in BAKER-CHAIN.md); the lower bound is Lemma C with an exact nearest-point computation.
Neither is machine-checked, so under RULE 2 the status is "closed by the sandwich" — the same standing as
the classical results this project builds on (BCGN 2021 use Baker-type bounds nowhere; Bugeaud–Kaneko do).
Not PROVEN in the Lean sense.*

## The two bounds

**Upper (Theorem U, BAKER-CHAIN.md).** Let y′ = R_n + Σ_{j=1}^k (d_j − 1)10^{E_j} (d_j ∈ {2..9}, n > E_1 > … >
E_k ≥ 0) be an integer of the form 2^a 3^b 7^c. Then n < G(k, a), an explicit function obtained by applying
Matveev's lower bound for linear forms in logarithms to one form per digit gap, the lower part of the
number entering the next form as a rational of bounded height. Numerically log₁₀ G(k, 0) ≈ 11.5 + 13.9k and
log₁₀ G(k, a≥1) ≈ 13.4 + 15.6k (plus log-log corrections): G(6,0) = 10^111.7, G(7,0) = 10^128.5,
G(8,1) = 10^161.7, G(11,0) = 10^196.1, G(31,0) = 10^541. This is Stewart's/Bugeaud's iterated-gap argument
specialised to our equation; IDEAS.md §D and OPEN-PROBLEM.md wrongly treated the exponential dependence
on k as "beyond computation" — it is, for k ≈ 31, but not for the k ≤ 11 of the vertices we enumerate.

**Lower (Lemma C at depth D, DEEPCUT.md).** For an open level-96 pattern, every candidate other than the
checked anchor has ≥ 10^27 digits, so its lowest 96D digits are determined up to the copy choices;
imposing them leaves finitely many sub-cosets p + Λ_D of the (b, c) lattice. Every point of such a
sub-coset has norm ≥ that of its exact nearest point (Babai + neighbour search on the reduced basis), so
every candidate has at least min_p ‖p_nearest‖/√2 · log₁₀3 digits. Each depth multiplies the bound by
≈ 10^48 (D = 1: 10^72, D = 2: 10^120, D = 3: 10^168, …) at a cost of a few hundred cut operations.

**Sandwich.** If the lower bound at some depth exceeds G(k, a), the pattern has no candidate: CLOSED.

## Result

- The four patterns that survived every modular ladder (levels 96/192/384/288/480; DEEPCUT.md):
  14336 (k=6): closed at D=2, 10^120.1 > 10^111.7; 28672 ×2 (k=7): D=3, 10^167.7 > 10^128.5;
  42336 (k=8, a=1): D=3, 10^167.1 > 10^161.7. **4/4.**
- All 43 level-96 survivors of the 05:45 sweep file (12 vertices, k = 5–11): **43/43 closed** (`SANDWICH-run.txt`); depths used: see the run log; depths 2 (7 patterns), 3 (26), 4 (10) per the C port's full-enumeration re-run (SANDWICH-full.txt); the smallest margin is 10^4.96 digits.
- Consequently every vertex of the base-10 sweep enumerated to level 96 is CLOSED, by: residue levels →
  Lemma C depth 1 (closes ~94% of open patterns) → sandwich for the rest. The "closed below height"
  category is empty for enumerated vertices. The 18 enumeration-frontier vertices are unchanged.

## What the frontier is now

For k ≤ ~15 the sandwich always wins (G(15, a) ≈ 10^293 needs D ≈ 6; sub-coset counts stay in the
thousands). For the frontier vertices (k = 25–31) the obstacle is only the enumeration to level 96
(10^15–10^22 patterns at level 12) — the sandwich would then need D ≈ 11 at 2^{31}-scale case counts, which
is also out of reach. So the even-target conjecture reduces, with this method, to a finite computation of
known cost (≈ 10^22 pattern evaluations plus the lifts) for 18 vertices; everything else is done.

## Verification

- Theorem U: BAKER-CHAIN.md — Matveev's statement fetched from two sources and compared; non-vanishing
  of each form is elementary (numerators ≡ −1 mod 9); the self-referential inequality n ≤ Φ(n) solved by
  a monotonicity lemma with an independent Pethő–de Weger closed-form cross-check; positive controls on
  genuine S-units (the identities, size bounds and Matveev inequalities hold for them). To do: an
  independent re-derivation (Codex/Cairn) of the constants and of Lemma 5.1.
- Lower bound: Lemma C (two blind implementations, Lean for the arithmetic core); the nearest-point
  computation is the one used for the anchors throughout the sweep.
- A planted check of the sandwich logic: for a pattern whose anchor is the vertex's own child (SELF), the
  anchor itself sits in the level-96 coset with norm ~10; it is excluded from the cut (n < 96) and the
  nearest points of the surviving sub-cosets are ≥ 10^72 — as expected; the sandwich never "closes" the
  anchor itself.

## Independent review (Codex GPT-6-Astra, run by Cairn; ledger 12:15 Mac time)

BAKER-CHAIN.md re-derived from the published Annals text of BMS Thm 9.4 (pp. 988–989) and arXiv
math/0403046: **sound after fixes, high confidence; all 99 tabulated bounds valid.** Fixes, none changing
the table: two positive controls contain zero digits / negative intermediate forms and sit outside Lemma
3.2's domain (restate as absolute-value variants); two abbreviated §6 values (10^111.70, 4.5·10^161) sit
just below the fixed point — safe values 10^111.704 and 4.6·10^161 (the code's table values are the safe
ones); `ceil(N)+1` on a float is not an exact certificate — interval evaluation at each returned integer
validates all 99 (to be added to `baker_chain.py`). Blind sandwich (no access to our code): **4/4 closed
at the same depths**, margins 8.4 / 39.2 / 39.1 / 5.5 orders of magnitude. Our 43/43 run has minimum
margin 10^5.3, far above the 10^0.004 corrections.

## Red team (REDTEAM-SANDWICH.md, 19:50 EDT) — no false closure; four latent driver holes fixed

Attacks: planted genuine 10-adic points (real S-units whose lowest 96D digits form hand-built pattern
words: all digits in one class, (d,e)×3, class = ν, digit above the window, classes 95/0) survive every
depth 10/10; 48/48 synthetic planted lattice points survive the cut; the "n ≥ 192 except the anchor"
premise holds exactly (non-anchor points differ from the anchor by a Λ_96 vector of norm ≥ 7.85×10^27);
the ±2 Babai window is proved exact for a Lagrange-reduced basis; cut_coset's 2-adic edge cases
(a ≥ K, K−1, K−2) match brute force 156/156; the Baker certificates re-verified in interval arithmetic
and 1981 zero-free S-units up to 10^15 pass every in-domain inequality; float margins ≥ 10^4.98.
Found and fixed (none changes a verdict on our data; all of the "repeated structure collapsed by a
dict/set/cap" family): the driver's `seen` key dropped a second recorded pattern on the same anchor
(one case in runall_final: s = 324, closes at depth 1); the `or reps` fallback could substitute other
representations for an unmatched record (never fired); `all_representations` capped the wrap value at
k ≤ 9 while pattern values reach 8|M|·10^95 — 15 representations (k = 18/27) in five vertices were never
examined, all close at depth 1 when run; `cut_coset` asserted instead of marking dead on a word ≡ 0 mod 5.
Earlier today Cairn found the same family in `deep_cut` itself (identical (d,e) pairs collapsed at
depth ≥ 2): fixed; the four survivors re-run with identical verdicts, one sub-coset count/bound now
exactly matching Codex's blind value. All runs are being redone on the fixed code (SANDWICH-run.txt,
DEEPCUT-run-0545.txt will be replaced).

## Cost correction (23:20 EDT) — the sandwich's enumeration is exponential in k·log D

With the dict collapse fixed, the depth-D enumeration is what it must be: every extension of a depth-1
survivor survives (DEEPCUT.md), so the number of sub-cosets at depth D is ≈ (D+1)^k (minus class
collisions), not the [3, 24, 63, 120] the buggy run printed for k = 10. The verdicts of SANDWICH-run.txt
(43/43) were therefore computed as minima over SUBSETS of the sub-cosets and must be recomputed over all
of them; the four survivors re-run on the fixed code keep their verdicts with k ≤ 8 (depth ≤ 3: ≤ 4^8
sub-cosets), but the k = 10–11 patterns at depth 4 need 10^7–10^8 cut operations — hours in Python,
seconds in Cairn's C port, which reportedly reproduces the verdicts after the fix. The honest cost of the
sandwich per pattern is (D+1)^k·(cut + exact nearest point); for Tier-A vertices (k up to 22, depth up to
7) that is 8^22 ≈ 10^20 — infeasible as is. Two ways down: raise the LEVEL instead of the depth (each
level lift multiplies the lattice index "for free" — levels 192/384/288/480 gave 10^66 uncut, ≈ 10^110 at
depth 1 — at the price of m^(k+1) children per lift, most of which die), or a bound on the union of the
sub-cosets that does not enumerate them (open). Until one of these is in place, "closed by the sandwich"
is established for k ≤ 11 and is a cost question, not a correctness question, beyond that.

## Night of 2026-10-21: what the C port, the box-CVP and the paper pass changed

- Cairn's C port re-ran the 43 over the FULL sub-coset enumeration (SANDWICH-full.txt): 43/43 closed, margins
  10^4.96–10^43.5, 59,124 sub-cosets in 76 s; depths 7/26/10. The cost correction above overstated the growth:
  measured counts are far below (D+1)^k (34,476 at k = 11, depth 4, against 4.9×10^7) because class collisions
  and the v₂/5 kills prune; and 59,124 "sub-cosets" are 3,902 distinct ones (identical digits counted as
  distinguishable) — identical minima.
- RESULT-peranchor.md (scout): the union over all copy choices of a block is ONE box-constrained closest-vector
  problem in dimension 2 + f (Codex's T1 linear congruence used as an algorithm, the Boolean box and the
  one-digit-per-position rule encoded exactly by a quadratic penalty): 43/43 certified with 0 enumeration
  nodes, 263 LLLs of dimension 3–16 in 11 s of Python, exact minima agreeing with the enumeration 88/88 and
  with the C port 43/43. It halves the enumeration exponent (cost ≈ words below the frontier × LLL), does not
  remove it; the decisive parameter is r = digits left unplaced after depth 1 (r ≤ 7 on all 43). Per-anchor
  sharing and the sub-lattice dual bound are killed with numbers.
- B3 (Cairn, audited 23:50): the two-ended Matveev + Bugeaud–Kaneko chain gives log₁₀G′ = 281 (k = 31),
  394–402 (k = 44) and lowers every depth on the 43 (1 on 16, 2 on 27); it holds for any fixed a ≪ n.
  To be installed as Theorem U′ (constants per BK (2.2) as a safe weakening of Yu).
- Scope correction: over the 133 final-stage vertices Lemma C depth 1 closes 4673/5440 = 85.9% of open
  patterns (the 93.7% figure is the k ≤ 11 set); 194 patterns were not reached before the Mac's cutoff, so
  21 enumerated vertices are still closed-below-height at this hour, not zero. PAPER.md (full draft, TABLES.md)
  states exactly what each file supports.
