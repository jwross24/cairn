# H2 results (2026-10-20, 1 core, nice 10, machine load about 24 on 10 cores: every timing is a floor)

Prediction registered first: PREDICTION.md.

## Differential (diff_run.py, diff_result.json)
Reference: tier0/deepcut.py deep_cut at depth 1, run by baseline_deepcut.py (baseline.jsonl: first 347 patterns of the
3,266 deduplicated open patterns in runall_final, trees_c, trees_mac in file order; baseline2.jsonl: every 4th of the
rest, 242 patterns, maxcases 3000 and 10 s wall per pattern). The full 3,266 were not run: deepcut costs about 2 s per
pattern here. 589 patterns, 109 anchors, 3,020 representations; 84 representations (16 patterns) hit deepcut's case or
wall cap and carry no reference verdict.
- Verdict disagreements: 0 of 2,936 compared representations.
- Surviving-case-count disagreements: 0 (the per-anchor count equals deepcut's len(stats[0]) exactly on every rep).
- Per pattern: 538 closed by the per-anchor method, 529 closed by deepcut; the 9 extra are among the 16 capped patterns.
- Anchors in the sample have a in 0..10; larger a is covered only by equiv_check.py.

## Equivalence of the cut and the congruence (equiv_check.py)
Lambda_96 basis vectors map to 1 mod 5^5 and mod 2^9. 183 positive and 217 negative random targets, a in 0..44:
0 mismatches between cut_coset and L == y (mod 5^5 2^(a+9)).

## Planted (planted.py)
1,434 genuine points y * 3^x 7^z with (x, z) in small combinations of the Lambda_96 basis (astronomical size, low 96
digits by modular exponentiation) on 239 anchors: 0 false kills, 218 cross-checked by cut_coset, 0 disagreements.
2,808 zero-free corpus S-units with a+9 <= n < 96 digits as SELF patterns: 2,808 open. Perturbed targets: 1,375 of
1,434 rejected by cut_coset, 0 disagreements with the congruence.

## Cost
Per-anchor method: 0.019 s for all 589 patterns (3,020 reps, 109 anchors): 175 microseconds per anchor, 32 microseconds
per pattern. deepcut: 1,154 s summed (2 s per pattern; includes loaded-machine inflation and the wall cap).
Ratio about 6e4; the hypothesis bound was a per-anchor cost of at most 100x the per-pattern cost.
Projection to a Tier-C vertex (RESULT-anchorfirst.md: 4e4-1.1e5 anchors): automaton compile 10-20 s per vertex
(HEURISTIC, extrapolated from a <= 10). Testing each pattern separately is 32 microseconds in Python, so 1e11-1e14
patterns would take 3e6-3e9 s: the per-anchor method does not remove the pattern count. Signature-cache hit rates at
Tier-C scale and the determinized product with the representation DP are unmeasured.
