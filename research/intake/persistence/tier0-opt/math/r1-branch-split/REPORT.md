# R1.1 / H11 branch split: kill-test verdict (2026-10-20)

Written by the Cairn orchestrator from the lane's final report; the lane's own write was refused by the harness.
Implementation: `engine/` (a Python filter on the unmodified C kernels; patch `engine_vs_tier0.diff`;
`BRANCHSPLIT=off` gives production). Logs, drivers and gate JSON under `logs/` and `engine/`.

Verdict: SURVIVED. Sound; 19–20× fewer level-12 survivors and level-24 children tested; the predicted 21× at levels
24–96 is falsified (1.0–1.3×); final open sets identical to production.

## Soundness (PROVEN-ON-PAPER)
- y mod 3 = ν + Σ(d−1) mod 3 depends only on the multiset and ν; y mod 7 depends on ν mod 6 and ε mod 6.
- y ∈ ⟨2,3,7⟩, so 3 ∤ y forces b = 0 and 7 ∤ y forces c = 0.
- The filter only drops patterns whose coset has no point with b = 0 and/or c = 0 (a gcd test). It never edits a
  coset, so descent, the tail test and Lemma C see the same objects. Children inherit the branch, so true children pass
  at every ancestor. y = 3 or 7 is excluded by y ≥ 10; a = 0 is harmless; EXACT lines are unfiltered. The mod-27
  problem of IDEAS.md §A does not arise.
- Evidence: 200k random integers, 0 mismatches against the branch function; all 608 plants matched.

## Gates
- (a) 87/87 equations on 72, 224, 10800, 14336, 8192, 28672: identical solutions and children. PASS.
- (b) 608/608 planted children recovered, all four (b > 0, c > 0) classes (the lane's exhaustive plant list; gatev2's
  harness itself not run). PASS.
- (c) Final level-96 open sets identical to production in all 87 equations. All removals happen at level 12; every
  removed pattern re-checked infeasible by an independent congruence solve (1,042,583 for 14336, 8192, 10800, plus 72
  and 224 in full; a 1/40 sample, 35,917, for 28672). None feasible.
- (d) Production vs split:

| Quantity | Predicted | Observed |
|---|---|---|
| Level-12 survivors | 12.6× | 19.0–20.1× |
| Level-24 children tested | 12–21× | 18.7–20.1× |
| Survivors at levels 24–96 | 21× | 1.0–1.3× |

The level-12 ratio is set by the bounded a (a ≤ A ≈ 22–50); only the class 3 | y and 7 | y keeps nearly everything,
the other three keep under 0.3% (pre-tail engine sample 18.2–21.3). Later survivors are already branch-compatible.

## Mutants (wrong subgroup in one branch)
- swap37: 60/608 plants lost; vertex 224 refused ("POSITIVE CONTROL LOST … y=2744").
- drop3: 142/608 plants lost; vertex 224 refused (y = 41472).
- Vertices 72 and 10800 refuse neither (their children take the EXACT path or sit in the 3 | y, 7 | y class): a
  coverage fact.

## Speedup (denominator: wall time of the current pipeline per vertex)
- Measured, best of 3, 2 cores, load 10–13: 1.07–1.36×; 28672 17.0 s → 12.5 s (level 12 6.2 s untouched; lvlN
  7.4 s → 1.0 s; the Python filter adds ~1.4 s a C-side check would avoid).
- Tier B, extrapolated from q ≤ 13 (not run): the lift is ≥ 90% of the work, so roughly 5–10×; capped by the 24→48
  lift, thinned only 1.2–1.9×.

## Unverified
Tier B numbers (extrapolation); the 19–20 vs 12.6 explanation (argued); no C-side filter built; the recorded 8192 and
14336 production rows predate the libpydesc swap and differ only in the "survived" field, so baselines are the lane's
own off-runs.
