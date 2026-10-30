# Lean Kernel Arena

Source: https://arena.lean-lang.org/ (round 2026-09: https://arena.lean-lang.org/round/2026-09/), repository
https://github.com/leanprover/lean-kernel-arena, read 2026-10-29 via Exa search highlights; the nanoda checker
page https://arena.lean-lang.org/checker/nanoda/ lists per-test results.

## What it is
A public scoreboard from the Lean FRO. Every independent Lean kernel runs the same suite: invalid proofs that
must be rejected, valid proofs that must be accepted, and corner cases with no expected verdict, plus timing on
Mathlib, Std, cslib and a navier-stokes-euler project. Ranking is by wrongly accepted invalid proofs first.
Results are comparable only within a round. An August 2026 Lean FRO post counts 16 checkers over 121 valid and 62
invalid tests, with five passing every test.

## Round 2026-09 numbers (71 invalid, 130 valid, 18 corner cases)
- `official v4.34.0`: 71/71 invalid rejected, 130/130 valid accepted, mathlib in 32.9 min.
- `official-v4.28.0`: **6 invalid proofs wrongly accepted**, 1 declined.
- `nanoda 4c544ed`: 71/71 invalid rejected; 2 valid declined.
- `still-nanoda` (a cache-study port): 6 invalid wrongly accepted. `nyaya`: 11. `rpylean`: 3.
- `parse-only v4.34.0`, a control that checks nothing, wrongly accepts 65 of 71: the suite's invalid proofs are
  real kernel-level tests, not parse errors.
- The `bugs/` category (18 tests in 2026-09, 26 on the current page) has named regressions such as
  `forged-quot-ind`, `nat-rec-k-lie`, `rec-k-lie`, `large-elim-prop-bool`, `loose-bvar-value`.

## For cairn
- cairn pins `leanprover/lean4:v4.34.0-rc1`; the arena scores `v4.34.0` final. Whether rc1 carries every
  kernel fix behind the 6 regressions v4.28.0 fails is not established. This is a direct question for RULE 2's
  "green Lean check": compare the rc1 and final kernel sources, or run rc1 against the arena's `bugs/` suite.
- The arena's invalid-proof suite is a ready-made planted-negative corpus for cairn's gold arm: each test is a
  proof that a correct kernel must refuse.
- One kernel family agreeing with itself is the configuration Kumar's exploit beat; a second checker that ranks
  clean in the current round (nanoda, lean4lean, or a fast one like `mathgraph`) is the arena's own
  recommendation shape.

## Leads out
- https://github.com/leanprover/lean-kernel-arena: test sources for `bugs/`, and which bug each one encodes
- The `bugs/` entry, if any, that encodes Kumar's July double-kernel exploit
- https://roclocality.org/2026/05/01/university-of-rochester-takes-lean-kernel-arena-top-spot/ (a nanoda cache port)
