# Lane 2 COSTMODEL: Tier B level-12 -> 24 lift from measured inputs (everything marked MODELED is an extrapolation beyond k = 18 / C = 6.5e4)

Scripts: scripts/rates_by_k.py, scripts/costmodel_l2.py (log: logs/costmodel_l2.txt), scripts/costmodel2.py. Data: the 2,364 swept equations of tier0/trees_mac.jsonl.eqs.jsonl + trees_c.jsonl
(read 2026-10-21 ~20:30, the file is still growing), the 228 gated equations (gate.jsonl, eval_J24/BEST), Tier B multisets from tier0v2.multisets.

## 1. What "sv12" is, and why 5e-3 x 2^(k+1) is not the lifted population
`levels[0]` of an equation record is [12, patterns, survivors, {OPEN, RESOLVED(descent)}]. Only the OPEN survivors are written to parents24.txt and lifted; the rest are resolved by the word-local
10-adic descent. Pooled over the sweep (rates_by_k.py), per k: OPEN/survivors = 0.19 (k = 5), 0.10 (9), 0.078 (12), 0.039 (13), 0.027 (15), 0.043-0.066 (17-18). So 88-97% of "sv12" is not lifted.
The sweep also contradicts the rising trend in rates.json (fitted when only k <= 13 equations existed): pooled survivors/pattern is 1.16e-4 at k = 8 and 4.6e-5 (12), 5.9e-5 (15), 2.5e-5 (16), 1.5e-5 (17), 2.2e-5 (18); it falls.
| k | OPEN parents per pattern (pooled, equations in sweep) | 95% CI |
|---|---|---|
| 11 | 4.78e-6 (271 eq) | [4.78e-6, 4.78e-6] |
| 14 | 2.14e-6 (57 eq) | [2.14e-6, 2.14e-6] |
| 16 | 1.20e-6 (16 eq) | [1.20e-6, 1.20e-6] |
| 18 | 9.20e-7 (5 eq) | [9.17e-7, 9.24e-7] |
(CIs are binomial and understate: equations differ by x/ 10 at 90%, composition matters.)
Per-equation log fit (k >= 11, 646 equations with OPEN > 0): ln(OPEN/patterns) = -8.25 - 0.318 k, slope 5-95% (bootstrap over equations) [-0.386, -0.251], residual sd 1.40 (x/ 10.1 at 90%).
Extrapolation (MODELED): k = 20: 4.5e-7 [2.8e-7, 7.5e-7]; k = 26: 6.7e-8 [2.7e-8, 1.7e-7]; k = 29: 2.6e-8 [8.7e-9, 7.7e-8]; each x/ 10 for a single equation.
The pooled-by-k series (slope -0.235 per digit from k = 11 to 18) gives about 2.7x more at k = 29 (7e-8); the fit above drops equations with zero OPEN parents, which biases it upward, the pooled series has few equations at k >= 17.
Both bracket: 2.6e-8 .. 7e-8 at k = 29, against the chat's 5e-3 (a factor 7e4-2e5 lower).

## 2. Children per OPEN parent (the multiset symmetry)
A parent has 2 * prod over slots (m + 1) children (equal digits at equal residues are one slot). Under uniform residues E[prod (m+1)] for n copies of a digit over 12 residues = n!/12^n [x^n] ((1+x)e^x)^12 (exact, scripts).
Measured children per OPEN parent / this expectation = 0.87 (k = 11), 0.78 (13), 0.69 (15), 0.58 (17), 0.54 (18) (survivors are biased toward collisions); ln(ratio) = 0.627 - 0.068 k, extrapolated 0.48 (k = 20), 0.32 (26), 0.26 (29).
Tier B vertex means (constant median ratio 0.82): 6e4 (k_max 22), 7e4-9e4 (k_max 20), 1.3e5-1.5e5 (25-26), 3.5e5 (27-28), 4.1e5 (29), 8.8e5 (vertex 13884223438848); with the trending ratio about 0.6x of that.
2^(k+1) at k = 29 is 1.07e9: the chat's per-parent child count is 2.6e3 times the model (k = 29 vertex).

## 3. ns per child
join24 (gate.jsonl, cpu_new/children) on the 7 equations with > 5e8 children: 1.5-2.9 ns (reference lvlN 35-40 ns). By children per parent C: 3.0 ns at C = 3e3, 2.3 ns at 2.2e4, 1.7 ns at 6.5e4; fit
ns = e^2.71 C^-0.19 (join24), e^2.68 C^-0.30 (BEST, this lane): extrapolated to C = 3e5: 1.3 ns and 0.34 ns; to C = 2e6: 0.91 and 0.19 ns (MODELED; the exponent is fitted over a factor 25 in C).

## 4. Tier B total (MODELED)
| quantity | chat's reading | this model (central) | range |
|---|---|---|---|
| level-12 OPEN parents | 2e15 (sv12 5e-3 x 4e17 patterns) | 2.9e11 | 2.1e11-4.2e11 (fit), up to ~8e11 (pooled slope) |
| children per parent at k = 29 | 1.07e9 | 4.1e5 (vertex 1811939328) | 2.5e5-4.1e5 |
| children, whole Tier B | 8.5e21 | 7.8e16 | 4.7e16 (trending ratio) - 2e17 |
| core-seconds at join24 speed (1.6 ns) | 1e15 | 1.2e8 (1.4e3 core-days) | 3e7-4e8 (0.3-2 ns, children range) |
| at BEST speed (0.34 ns at C = 3e5, MODELED) | | 2.6e7 (3.1e2 core-days) | 5e6-1e8 |
This agrees with the lift-ideation lane (1.2e17 children) and tierb-lift/model.py (join24 2.15e3 core-days); it replaces the 1e15 s reading by a factor of order 10^7.
Level 12 itself (4e17 patterns x 5 ns = 2e9 core-s = 2.3e4 core-days, 846 GPU-h in the lift-ideation model) is >= 10x the modeled 12 -> 24 lift: the lift is not Tier B's wall; the 12-level enumeration and the level-48 stage are larger.
Level 48: with join24 the 214 level-48 equations cost 82.6 s against 59.4 s for the 228 level-24 equations (gate.jsonl, same machine), so after the 12 -> 24 speedup the 24 -> 48 stage is the larger lift cost.

## 5. Exact correction to append to the ledger
"Correction (Lane 2, 2026-10-21, COSTMODEL.md): REDUCTION.md §3's 12 -> 24 cost line uses sv12 (level-12 survivors, 88-97% of which are RESOLVED(descent) and never lifted, and whose measured rate FALLS with k) times 2^(k+1)
children. Lifted level-12 parents (OPEN) are about 2.9e11 at Tier B (2.6e-8 .. 7e-8 of patterns at k = 29, falling about x0.73-0.79 per digit), each with about 4e5 children at k = 29 (multiset symmetry; 2^30 ignores it), so
about 8e16 children (range 5e16-2e17) and about 1.2e8 core-seconds at join24's 1.6 ns/child (3e7-4e8), not 1e15 s. The 12 -> 24 lift is not Tier B's wall; the level-12 enumeration (about 2e9 core-s) is larger. MODELED, extrapolated from k <= 18."

## 6. Reconciliation with tierb-lift/logs/h12_*.jsonl (added 2026-10-21 20:56 EDT; §1-§5 above are unchanged and §5's numbers are superseded by the table below)
Scripts: scripts/reconcile.py, glm_open.py, reconcile2.py, reconcile3.py.
**Populations.** (i) My §1 fit used the sweep records (tier0/trees_mac.jsonl.eqs.jsonl, 2,233 equations with npat > 2e6, one row per equation, parents = levels[0] OPEN); k-only, composition-blind.
(ii) The h12 logs are 226 rows over 7 vertices (124416, 14336, 28672, 3211264, 393216, 9437184, 9633792), npat >= 196,560, parents = lift24.parents. 155 of the rows are also in the sweep with identical npat.
**Why the two disagree.** (1) Definition: on the same equations the sweep OPEN count divided by h12 lift24.parents has median 10.9 (k=6), 14.5 (7), 17.6 (8), 19.3 (9), 19.0 (10), 19.5 (11), 18.2 (12), 17.9 (13): the h12 run is the branch-split pipeline, whose parents are about 1/19 of the OPEN survivors (the 19 is the number recorded in tierb-lift/PREDICTIONS.md P1). At k = 15, 17, 18 (and the k = 20, 21 vertex-9437184 rows, whose parents files are the gate corpus) the counts are IDENTICAL to the sweep (ratio 1.00). So the quoted series 1.4e-6 (k=9) ... 2.5e-6 (13), 3.2e-6 (15) ... 3.6e-6 (21) is a series divided by 19 for k <= 13 and undivided for k >= 15; its "flat or rising" shape is largely that switch. Per-pattern parents are therefore NOT comparable across k in that table, and it is not a population-level trend.
(2) Composition: the k >= 15 rows are 2-heavy multisets. Sweep OPEN/pattern stratified by f2 (fraction of digits equal to 2), pooled per k (logs/eqs_open.json): f2 >= 0.7 stays flat at 2.6e-6 .. 3.4e-6 from k = 13 to 18 (n = 2-14 equations per k); 0.3 <= f2 < 0.7: 2.4e-6 (13), 2.5e-6 (14), 2.0e-6 (15), 1.9e-6 (16); f2 < 0.3: 1.1e-6 (13) falling to 4.6e-7 (18). My §1 pooled and fitted rate (slope -0.32 per digit) mixed the f2 < 0.3 equations that dominate the high-k sweep with the 2-heavy ones; the sweep reaches high k mostly through low-f2 equations while the Tier B high-k multisets are 2-heavy (pattern-weighted f2 0.47 overall, 0.81 at k = 26, 0.90 at k = 29). That is the error in §1.
**Refit (Poisson regression with offset ln npat, k >= 13, bootstrap over equations):**
f2 < 0.3: ln rate = -10.69 - 0.228 k (slope 5-95% [-0.308,-0.122], n = 61); 0.3-0.7: -11.72 - 0.066 k ([-0.212, +0.067], n = 105); f2 >= 0.7: -13.19 + 0.033 k ([0.003, 0.052], n = 51); rates at k = 16: 6.0e-7, 2.8e-6, 3.2e-6.
Out-of-sample check of the old k-only model (fit k <= 14, predict the 57 equations with k >= 15): predicts 1.19e7 OPEN against 1.33e7 observed (-11%), so the aggregate was right on that set, but for the wrong reason (a low-f2 majority); the f2-linear model fails the same check (-39%), so I use the stratified form.
Including the h12 rows changes nothing for k >= 15 (same data) and cannot be added for k <= 13 without the factor 19; with that factor they sit inside the sweep (they are a subset of vertices).
**Tier B 12 -> 24 total, reconciled (MODELED; 13 vertices, all multisets; children per parent = 2 E[prod(m+1)] x measured ratio with trend, 0.6x of constant-ratio):**
| quantity | stratified fit | 5-95% (equation bootstrap) | plateau hypothesis (rate frozen at its k = 16 value) | previous §4/§5 |
|---|---|---|---|---|
| OPEN level-12 parents | 8.4e11 | 4.6e11 - 1.6e12 | 1.0e12 | 2.9e11 |
| children (trend ratio) | 2.5e17 | 1.3e17 - 5.2e17 | 3.0e17 | 7.8e16 |
| children, constant ratio 0.82 | up to ~4e17 central, ~9e17 at the top of the interval | | | |
| core-seconds at join24 (1.3 ns at C = 3e5) | 3.2e8 | 1.7e8 - 6.8e8 | 3.9e8 | 1.2e8 |
| core-days at join24 | 3.7e3 | 2.0e3 - 7.9e3 | 4.5e3 | 1.4e3 |
| core-days at BEST (0.34 ns) | 9.8e2 | 5e2 - 2e3 | 1.2e3 | 3.1e2 |
This agrees with the lift-ideation lane (1.2e17 children; 1.87e3 Mac-days mixed) and tierb-lift/model.py to within a factor 2-3; the chat's 1e15 s remains off by 3e6. The 12 -> 24 lift is still 6x smaller than the level-12 enumeration (2e9 core-s). Uncertainty not in the intervals: the plateau extrapolates from k <= 18 to 29 on 2-14 equations per k.
**Corrected ledger sentence (replaces the §5 numbers):** "Tier B lifted (OPEN) level-12 parents ~8e11 (4.6e11-1.6e12; sv12 counts descent-resolved survivors and is not the lifted set; the OPEN rate is composition dependent and flat at ~3e-6 per pattern for 2-heavy multisets), ~3e5 children each at k = 29, ~2.5e17 children (1.3e17-5.2e17), ~3e8 core-seconds at join24's measured 1.3-1.6 ns/child, not 1e15 s."
