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

## Which bugs, and cairn's pin (read 2026-10-29)
- Arena page https://arena.lean-lang.org/round/2026-09/checker/official-v4.28.0/ lists what v4.28.0 wrongly
  accepts: `nested-unused-param`, `proj-of-imax-prop`, `proj-of-stuck-prop`, `proj-of-subst-prop`,
  `rec-missing-ih`, `rec-of-subst-prop` (all proofs of `False`); it crashes on `constlevels`
  (lean4 issue 10577, memory corruption in `lazy_delta_reduction_step`).
- No arena test names Kumar or Collatz; the July exploit cannot be tied to a specific test from the repo text.
- Release dates (GitHub releases): `v4.34.0-rc1` 2026-08-10, `v4.34.0` 2026-09-14.
- `gh api repos/leanprover/lean4/compare/v4.34.0-rc1...v4.34.0` lists these kernel fixes, all after rc1:
  #14582 check uniformity of occurrences of the datatypes being declared; #14806 make kernel `is_def_eq`
  caching order-independent; #14807 make the kernel `is_prop` check require a sort; #14808 type-check
  generated recursors in the kernel; #14847 test for the `is_prop` bug; #14849 bound the size of `Nat`
  numerals computed by the kernel.
- Inferred, not verified: these fixes correspond to the arena families v4.28.0 fails (`rec-missing-ih` reads
  like #14808; `nested-unused-param` like #14582; the `*-subst-prop` / `*-stuck-prop` family like
  #14806/#14807). If so, cairn's pinned kernel accepts some arena proofs of `False`. Settling it needs one run:
  the rc1 checker against the arena's `tests/bugs/` exports.
