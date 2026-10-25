# The survivor-word lift: the final stage without depth

*2026-10-21 16:30 EDT, chat session. Code `wordlift.py` (uses deepcut.py, deepcut_lift.py, descent.py, lattice.py).
Run logs `WORDLIFT-run.txt` (the 43 level-96 sandwich survivors), `WORDLIFT-hik.txt` (k = 14–16 sample).
Calibration: same standing as Lemma C + the Baker sandwich — ordinary proof conditional on Matveev/Yu (U″) for the
6 patterns that need the bound, an unconditional modular kill for the 37 that do not; nothing Lean-checked.
Not PROVEN. No vertex changes status (all 43 were already closed by the sandwich); what changes is the COST.*

## 1. The idea (TIERB-FINAL.md §4.2a)

The sandwich raises the DEPTH D of the 10-adic window at a fixed level 96: every extension of a depth-1 survivor
survives, so the sub-coset count grows like (2^r)^(D−1) and only the lattice index 10^96 per depth pays. Raising the
LEVEL instead (96 → 192 → 384) was known to be stronger per step (new primes of 10^L − 1 multiply the index AND the
window doubles) but cost 2^(k+1) children per representation (`deepcut_lift.py`: 14,298 s for the 43, 37/43 closed).

The word lift keeps the level's power and drops the exponent from k to r: after Lemma C depth 1 at level 96 a
surviving WORD has fixed digits (copy 0, position e_j < 96) and r unplaced digits (copy t_j ≥ 1). Only the unplaced
digits and ν have a choice at level 192: t_j mod 2 and ν + 96·{0,1} — 2^(r+1) children. Each child is cut by the
seven new primes of level 192 (discrete logs, `child_coset`) and then by Lemma C depth 1 at K = 192, whose window
t < 2 either fixes an unplaced digit with t ≡ 1 at t = 1 or pushes it to t ≥ 3. Then 192 → 384 the same way with
t mod 4. The state of a digit is (e, t fixed) or (e, t ≡ ρ mod m, t ≥ 1); the level-L pattern value is
R_{ν mod L} + Σ (d_j − 1)10^{e_j + 96(t_j mod m)}, which is the candidate's residue modulo every level prime p ≠ 3
(10^{96 t} ≡ 10^{96 (t mod m)} mod p); the Lemma C word at K = L is R_L + Σ_{fixed} (d_j − 1)10^{e_j + 96 t_j}.
Equal positions modulo L are allowed (distinct actual positions can share a residue); equal ACTUAL positions inside
the window are not.

## 2. Result on the 43

`WORDLIFT-run.txt`: **43/43 closed, 102 children in all, 657 s** (≈ 150 s of it the kernel-lattice and
new-prime setup; ≈ 12 s per pattern in Python). 37 patterns are **CLOSED-cut** — no child survives level 384 at
depth 1 (the same 37 the full-representation lift closed); the other 6 (14336, 28672 ×4, 42336 — exactly the ones
that needed sandwich depth 2–3) each keep ONE child at level 384 with certified lower bound **10^(10^239.0–239.2)
digits** against U″ = 10^61.8–10^93.2: closed with 150+ orders of margin. Words per pattern 1–12 (25 patterns have
a single depth-1 word); r = 1–7 (median 3).

Why 10^239: Λ_384 has index 4.3×10^103 (shortest vector ≈ 10^52) and the depth-1 window at K = 384 adds
≈ 10^192 of 5-adic/2-adic index, hence ≈ 10^(52 + 192) — compared with 10^72 at level 96 depth 1 and 10^120 at
depth 2. One level doubling is worth 3.5 depths. The bound does not depend on the pattern (only the anchor coset's
nearest point can lower it, and it never did).

## 3. What it means for the final stage

- **Level 384, depth 1, beats U″ for every k ≤ 30** (U″ ≤ 10^232 at k = 29; 10^246 at k = 31, a = 0 — just above).
  For k = 31–44 one more doubling (level 768; its new primes must be PH-feasible — to be checked with
  `new_primes(768, 384)`) gives ≈ 10^(27 + 52 + 384) ≫ 10^345. So the sandwich DEPTH enumeration disappears
  from the plan: every final-stage pattern is cut-or-sandwiched at depth 1 of level 384 (768 for Tier C).
- Cost per surviving pattern: Σ over words of 2^(r+1) children × (two levels) × (7 + 4 prime cuts + one 10-adic
  cut). On the 43: 102 surviving children. (The prime cut needs no discrete log for the kill test: the coset's image
  mod p is the index-i_p subgroup, so membership is one modular exponentiation; the log is needed only for the
  survivor's sub-coset.) See §5 for how words and r grow with k.
- The planted bookkeeping test (300 random placements with t_j ∈ {0,…,9}, ν shifts 0–3, checked against the true
  residues modulo the 3-free part of 10^L − 1 and the true lowest L digits): 295/296 branches found with the right
  values; the one miss is a planted word ending in the digit 5 at position 0, which the code kills as not an
  S-unit — correct. (Note for the record: R_n mod (10^L − 1) is NOT R_{n mod L} — the two differ by a multiple of
  R_L — but they agree modulo every prime p ≠ 3 dividing 10^L − 1, which is all the level ever uses.)

## 5. The k = 14–16 sample (`WORDLIFT-hik.txt`, one representation per pattern — `--first`, cost measurement only)

21 anchored patterns of trees_mac_1250.jsonl with k = 14–16, anchors ≥ 10^9 and ≤ 7 twos (the many-2s wrap
anchors make `all_representations` intractable; the sweep's recorded (ν, ε) avoids that in the real pipeline).
10 are killed by Lemma C depth 1 (words = 0). The other 11:

| k | words | r | alive at 192 | alive at 384 | verdict |
|---|---|---|---|---|---|
| 14 | 2 | 8 | 2 | 0 | CLOSED-cut |
| 14 | 24 | 8 | 24 | 0 | CLOSED-cut |
| 14 | 24 | 8 | 24 | 1 | CLOSED-sandwich (10^239 vs U″ 10^112) |
| 14 | 32 | 8 | 32 | 0 | CLOSED-cut |
| 15 | 1 | 9 | 1 | 0 | CLOSED-cut |
| 15 | 12 | 9 | 12 | 3 | CLOSED-sandwich (10^239 vs U″ 10^114) |
| 15 | 3 | 8 | 3 | 0 | CLOSED-cut |
| 15 | 32 | 10 | 32 | 0 | CLOSED-cut |
| 16 | 3 | 10 | 3 | 0 | CLOSED-cut |
| 16 | 90 | 12 | 90 | 0 | CLOSED-cut |

21/21 closed; 227 surviving children in all; 772 s. Two readings:

- **r ≈ k − 5 and words grow with k** (1–12 at k ≤ 11; up to 90 at k = 16). The reason is structural: the
  depth-1 verdict at level 96 depends only on positions < 9 (DEEPCUT.md), so every digit of the anchor identity
  at a position ≥ 9 is free to sit at copy 0 or not — the words multiply by ≈ 2 per such digit, and r counts the
  ones left unplaced. For Tier-B anchors (≈ 30 digits, k = 20–29) that is ≈ 2^20 words with r ≈ 10–24: the
  children Σ_words 2^(r+1) ≈ 3^(k − 9) ≈ 10^9–10^10 per surviving pattern. **The word lift removes the depth
  exponent and a factor 20–140 of the cost; it does not remove the 2^k of the copy choices.** TIERB-FINAL.md §3
  stands: with ≈ 2×10^9 surviving patterns the Tier-B final stage is ≈ 10^19 cheap operations, the same order as
  the enumeration or above it.
- **Exactly one child per word survives level 192, on every pattern (alive192 = words, 11/11 and 43/43), and it
  is the shadow** — the continuation of the anchor's own identity (unplaced digits with the identity's t mod 2).
  Accidental survivors are expected at rate 2^(r+1)·10^−35 ≈ 0, so this is not a coincidence but it is also not
  a proof. **Hypothesis H-shadow (for Cairn's queue):** a level-96 depth-1 word has at most one level-192
  child, the shadow. If H-shadow had a proof (a carry argument on the lowest 192 digits, say), the per-word cost
  would drop from 2^(r+1) to 1 and the level-384 step (where the shadows die, 0–3 survivors on 54 patterns) would
  be the whole final stage; the words themselves (2^(#digits at e ≥ 9)) would remain.

## 4. To do / for Cairn

1. Port to the C final stage: replace the depth loop by the word lift (96 → 192 → 384), keep U″ only for the
   residual survivors; re-run the 1335 final-stage sandwich patterns and compare verdicts (expected: identical
   closures, most now CLOSED-cut).
2. Measure words × 2^r by k on the final-stage patterns (the C port has the recorded (ν, ε)); the 43 give
   r ≤ 7, words ≤ 12.
3. Level 768 new primes (PH-feasibility) for the k ≥ 31 case; and the base-b analogue (`sandwich_b.py` →
   word lift) for bases 8/6/12, where the lift is the same code with b in place of 10.
4. Red-team items specific to this file: the state transition (ρ, m) → (ρ + m·b, 2m) and the window rule
   "fix at t = ρ iff ρ ≥ 1" — a second blind implementation is the right check; the planted test above is mine.
