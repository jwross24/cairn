# v2bound: exact 2-adic bound (Fonga, arXiv:2608.27802, Theorem 4.1) as a candidate replacement for `two_adic_bound`

Status: candidate, not swapped. Nothing under `tier0/` was touched.

## 1. What Theorem 4.1 computes (raw/2608.27802.txt lines 440-720 read, including the proof of the recursion)

- Family A_10(nu): positive integers whose decimal expansion has exactly nu_d copies of each digit d in 2..9, any number of 1s (including none), no 0.
- Value: max over the family of v2(x), exactly (base b = 10, p = 2, e = 1). Eq. (16): max{0} U { V(D minus d, 0, T_d) : d in D even }, T_d = 9(d-1) - 1.
- Recursion on states (remaining multiset, a = highest occupied position, T = 9x_partial - 1 + ...): the next exceptional digit goes at a position t in (a, v2(T)]; a position above v2(T) cannot change the valuation (its term has valuation > v2(T)), so the branch contributes v2(T). When the multiset is empty the leading repunit length L ranges over (a, v2(T)] (eq. 15).
- Fit to what the engine needs. The engine bounds a = v2(y) of a child y whose non-1 digits are exactly the multiset M, zero-free, 1s arbitrary: that is the family, with the same hypotheses. The "0" in eq. (16) covers a = 0 (odd y, or no even digit in M). "Digit above the top" is the L range. Nothing outside these hypotheses is used.
- Old engine function vs. exact: the old tail DP also admits states with leftover digits unused (`ended`), i.e. sub-multisets, so old >= exact on every multiset. On the full multiset the low-k-digit divisibility test is itself exact, which is why the two agree on most multisets. The old function does not terminate in practice for k >= 36 because the tail set explodes, not because the bound is infinite.
- Seam: the paper is arXiv-only, one source. I read the proof of (13)-(16) and found no gap, and the code below was checked against brute force (section 3), but I have not Lean-checked it.

## 2. Files

- `fonga_v2.py`: Python implementation. `two_adic_bound(M, kcap=200)` has the engine's signature and returns an int (raises RuntimeError if the value is >= kcap, as the old one raised on non-termination). `exact_max_v2(M, slack, leading_lo, node_limit, stats, target)` is the full interface; it raises `Budget` when `node_limit` nodes are exceeded (new failure mode: the old function hung instead).
- `fonga_v2.c` / `fonga_v2_c`: the same recursion on 256-bit words (valuations are computed mod 2^256; it prints OVERFLOW and exits 2 if a sum vanishes mod 2^256, never a wrong value). About 35-100 M nodes/s. Python and C agree on all 2015 recorded multisets and on the node count of the first Tier-C multiset (116,817,496).
- Mutation parameters: `slack` (positions up to v2(T)+slack; -1 is the off-by-one), `leading_lo` (first allowed repunit length, a+leading_lo).
- Tests: `diff.py {recorded,plants,mutants}`, `recap.py`, `t5.py` (new vs original function exec'd from tier0v2.py, 300 random, k <= 9), `t6.py` (brute force), `t7.py` (C vs Python), `tierc_c.py`, `tierc_long.py`. Results in `diff_*.jsonl`, `tierc_c.jsonl`.

## 3. Differential results (2026-10-21, one core, nice 10)

- Paper's four examples: {4,4,7} 7, {2,2,2,2,7} 13, {2,2,4,7} 15, {2,7,8} 9. All match.
- Brute force over all arrangements with up to 12 digits (11 multisets, k = 3-4): exact value reproduced in every case (never exceeded by brute force).
- Recorded multisets (runall_final, trees_c, trees_mac): 2015 distinct, k <= 19; the old function terminates on all. new > old: 0. new == old: 1670. new < old: 345 (largest drop 11, e.g. {4,9,2}: 12 vs 16; all drops are sub-multiset looseness in the old value).
- Planted children: 162 recorded child integers, new >= v2(child) on all 162 (0 violations). Planted S-units: all 8807 zero-free 2^a 3^b 7^c below 10^4000 (`zf_below_1e4000.txt`): 8244 confirmed new >= a (early-exit search), 0 violations, 563 not decided inside the 200,000-node cap (k = 10 to 110, mixed even digits). Those 563 are open observations, not passes; rerun with the C kernel's `-n` budget or a target-mode C port if wanted.
- Planted negative: on 1179 plants with k <= 10, the off-by-one `slack = -1` gives 483 violations (value below the true a) and `leading_lo = 2` gives 19; the intended recursion gives 0. `slack = +1` changes nothing (positions above v2(T) are inert, as the paper says); `leading_lo = 0` only loosens (107 larger values), never tightens. The plants refuse the mutants, so they can fail. In C, `-s -1` differs from baseline on 248 of 300.

## 4. Tier-C values (FRONTIER.md vertices; multiset = the k_max multiset, all digits 2, 3 and 7)

The vertex has 306-2446 multisets; I computed the one with the most digits (all prime digits, the largest k). Other multisets of the same vertex (with 4, 6, 8, 9) have fewer digits but more even-digit kinds and are not measured here.

| vertex 2^a 3^b 7^c | k | A (exact) | nodes | C seconds |
|---|---|---|---|---|
| 2^6 3^27 7 | 34 | 120 | 1.17e8 | 2.9 |
| 2^23 3^7 7 | 31 | 120 | 6.0e8 | 19 |
| 2^29 3^5 7 | 35 | 129 | 1.59e8 | 4.4 |
| 2^24 3^6 7^6 | 36 | not finished (150 s and 560 s runs both timed out) | not recorded | > 560 |
| 2^34 3^8 | 42 | 152 | 1.74e9 | 36.5 |
| 2^39 3^3 7^2 | 44 | 157 | 2.77e8 | 8.6 |

The Python version does the first row in 93 s and exceeds 2e8 nodes on the second. The documented expectation A of 100-160 holds (120-157). The 2^24 3^6 7^6 row is the hardest because 7 contributes an even d-1 = 6; runs of 150 s and 560 s timed out; a detached job (`tierc_long.py`, 4 h cap) is queued to start at 05:30 and appends its row to `tierc_c.jsonl`.

## 5. Does swapping change a recorded verdict?

A enters the engine only as the cap on a at level one (`split_by_a(v, A)` in fastlevel.py, `for a in range(A + 1)` in export_level.py and export_cfg.py, the K array and the header of the exported level files). It does not appear in any later step.

- Argument. Every child has a <= exact max (Theorem 4.1, verified against 8244 genuine S-units and 162 recorded children), and exact <= old (the old value maximizes over a superset of states). The new range 0..A_new is therefore a subset of the old range and contains every a of every child. A pattern at an a in (A_new, A_old] cannot carry a child; removing it can only remove DEAD or spurious OPEN survivors. So no recorded SOLUTION changes, and a CLOSED equation stays CLOSED with the same solution list.
- What can change. (a) Counters that count (a, pattern) pairs, per-level survivor counts, and the K array in exported levels shrink for the 345 multisets with a lower value. (b) An equation recorded OPEN could close if all its open patterns sit at a in (A_new, A_old]; the logs do not record a per OPEN pattern, so I cannot say whether that happens. All 105 vertices in the three result files are CLOSED, so none can change verdict. In runall_final every `exceptional` entry has a <= A_new. (c) Golden files and gate corpora that embed A (gatev2 corpus quotes A of 0-36; level-file headers) change byte-wise and need regeneration.
- Not argued: anything about multisets with k >= 20 that were never run, since the old function never produced a value there.

## 6. Swap procedure (not performed)

1. Copy `fonga_v2.py` beside the engine (`tier0/`, `tier0-opt/`, `tier0-opt/pydesc/`; all carry their own `tier0v2.py`).
2. In each `tier0v2.py`, make `two_adic_bound(M, kcap=200)` return `fonga_v2.two_adic_bound(M, kcap)` and drop `_two_adic_bound`. Keep `Budget` unhandled so an over-budget multiset stops loudly. `tier0.py` has its own copy (line 64) and is used by `crosscheck.py` and `solve_equation`; change it the same way or leave it as the independent oracle.
3. For k >= 30 or any multiset with several even digit kinds, call the C kernel (`fonga_v2_c digits...`) and cache the value; the Python path is for k <= 25.
4. Before accepting: rerun `diff.py recorded` (expect 0 greater), `diff.py plants`, and `gatev2 --fast` after regenerating its A-bearing fixtures; rerun three recorded vertices (one per tier) and diff the `sols` lists (must be byte-equal) and the `(a,pattern)` counters (must be <=).
5. Planted negative on the swap: `slack=-1` build must fail `diff.py plants`.
