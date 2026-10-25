# Anchor-first census of the six Tier-C vertices: the predicted level-96 open sets

*2026-10-20, scout `anchorfirst` (`/home/claude/scouts/anchorfirst/`). Code: `anchorfirst.py` (stages 1–5, C kernel
`anchor_dp.c`, helpers `anchorlib.py`, `sandwich_lite.py`), `anchorfirst_sandwich.py` (stage 6: the tier0 sandwich,
filter statistics, benchmark). Logs: `anchorfirst-run.log`, `anchorfirst-sandwich-part1.log` (filters + benchmark),
`anchorfirst-sandwich-part2-v0.log`, `anchorfirst-sandwich.log` (vertices 1–5). Inputs: `tierC.txt`, the
S-unit list generated in-process; tier0 is imported, not modified. Calibration: the anchor census is exact on the
sampled (y, k) pairs (every reported representation is checked by the integer identity, every count is an exact DP
count cross-checked by a second, independent Python DP on the enumerable hits); the extrapolation to the full anchor
set is a uniform-sample estimate with the quoted standard errors; the "open set = anchored set" step is the heuristic
hypothesis stated in the task, not a theorem.*

## 0. Result in one paragraph

Under the anchoring hypothesis the level-96 open set of each Tier-C vertex is **not** a few dozen patterns: it is
10^11–10^14 patterns per vertex, carried by only ~4–11×10^4 anchor pairs (y, k) (about 3–10% of the 1.1 M pairs that
pass the cheap filter), on ~10^4 distinct small S-units y, **and the six predicted counts agree to within a factor
1.0–1.7 with FRONTIER.md's independent, sweep-calibrated forecast of open@96 for every vertex** (Table 2). The
counts are large because the Tier-C equations have 13–44 digits, most of them 2s and 3s, and an improper
representation of an anchor may stack digits in one residue class and let them carry: one 8-digit anchor,
11010048 = 2^19·3·7 with wrap k = 10, alone carries ~10^9 patterns per (ν) for four of the six vertices.
Every sampled anchored pattern that was decided (22/22 in stage 6, 18 of 30 lines in stage 5; k = 14–40 digits) is
**CLOSED at depth 1 by Lemma C** (exact, reduced verdict; tier0's full `deep_cut` agrees on every pattern it could
finish, 10/22 within 10^6 cases / 12 s). The Baker–lattice sandwich itself is irrelevant at Tier C below depth 7 (G(17, 1) = 10^331 >
10^312 = depth-6 lower bound), so a Tier-C pattern that survives depth 1 cannot be closed by the sandwich at depth
≤ 6; the sample contained no depth-1 survivor, but the expected survival rate (≈ #low-digit copy choices / 640 000,
i.e. 10^-4–10^-1 per pattern) applied to 10^11–10^14 patterns leaves 10^9–10^12 survivors per vertex, each needing a
depth 7–18 sandwich over 2^k sub-cosets. Anchor-first therefore replaces the 10^19–10^22-pattern enumeration by an
explicit, much smaller object, but closing Tier C still needs new mathematics.

## 1. Method

**The object.** A level-96 pattern P = (ν, {(d_j, e_j)}) of the equation (s, M) (digits d_j ∈ M, positions e_j ∈
[0, 96) with multiplicity allowed) is *anchored* on the S-unit y = 2^a 3^b 7^c if

    y + k·R_96 = R_ν + Σ_j (d_j − 1)·10^{e_j}   over Z,   R_m = (10^m − 1)/9,   k ∈ Z.       (†)

Then every candidate y′ of P satisfies y′ ≡ y (mod R_96) (OPEN-PATTERNS.md), P passes the level-96 residue sieve, and
a = v₂(y) is P's 2-adic exponent. The task's range 0 ≤ k ≤ 9 is not the full range: the right side of (†) is at most
R_96 + W_max·10^95 with W = Σ(d_j − 1) ≤ 126, so k ≤ 1 + 9·W_max/10 ≈ 115 is possible in principle. We scan
k ∈ [−9, 224] (derived from the digit-sum bound below) and find anchors at k up to 100 — **half or more of the
anchored patterns of every vertex have k ≥ 10** (Table 1: 50–66 % have k ≤ 9, 22–29 % have k = 0). No negative k
occurs.

**Stage 1 — anchor candidates.** All S-units y = 2^a 3^b 7^c < 10^98 with a ≤ 60: 609 796 numbers. (The anchors found
have a ≤ 44 and 2–22 digits; the a-distribution falls off steadily, so a ≤ 60 loses nothing visible.)

**Stage 2 — the cheap filter.** For U = y + kR_96 write q = U div 10^96 and D = digit sum of U mod 10^96. Since
V = U − R_ν = Σ(d_j − 1)10^{e_j} has digit sum ≤ W (each carry lowers the digit sum by 9) and the top part q costs
mass ≥ 10q at position 95, and subtracting R_ν changes the digit sum by at most 95: a necessary condition is
D + 10q ≤ 95 + W_max. It passes **1 109 618 of the 137 204 100 raw (y, k) candidates (0.81 %)**. The task's three
filters were measured separately on random candidates (`anchorfirst-sandwich-part1.log`, per (y, k, ν) triple):

| filter (per (y, k, ν)) | raw candidates, vertex 3416… | raw, vertex 1284… | after stage 2, vertex 3416… | after stage 2, vertex 1284… |
|---|---|---|---|---|
| digit sum mod 9 ≡ ν + W, W ∈ W-set | passes 100 % | 100 % | 100 % | 100 % |
| non-background digits of U (lowest 96) ≤ 2k_max | 6.2 % | 4.6 % | 70 % | 64 % |
| lowest 20 digits producible by ≤ k_max digits of mass ≤ W_max (carry DP, no product constraint) | 99.9 % | 33 % | 97 % | 44 % |
| all three | 6.1 % | 1.5 % | 68 % | 28 % |

The mod-9 filter is vacuous at Tier C because every W-set is an interval of length ≥ 9 (it covers all residues).
The low-20-digit DP is weak for 30–44-digit multisets (two digits per position suffice for any 20 digits); it bites
only on the 13–31-digit vertex. The mass filter D + 10q ≤ 95 + W_max is the one that does the work, and it is
exactly the digit-sum invariant pushed to all 96 digits.

**Stage 3 — exact anchor test (C, `anchor_dp.c`).** For each surviving pair and each ν ∈ [0, 96) with V ≥ 0, a
DP over positions 0..95 with state (carry ∈ [0, 15], carries-so-far, exponent vector (a′, b′, c′) of the digits
placed) decides whether V = Σ(d − 1)10^e for some digit multiset of product exactly 2^A 3^B 7^C and mass W in the
vertex's W-set, and **counts the patterns** (distinct multisets of (d, e) pairs, summed over the vertex's multisets of
that mass) exactly in double precision. Pruning: remaining-mass bounds per exponent vector (min/max mass tables),
the digit-sum invariant, the count of non-zero digits of V ≤ k_max + #carries. Cost: 1–5 ms per (y, k) pair for the
five smaller vertices, ~130 ms for 1438916737499136 (exponent space 25·7·7). The full 1.1 M pairs would cost ≈ 1.5
(smallest) to 40 (largest vertex) CPU-hours per vertex — beyond this scout's budget, so **stage 3 ran on a uniform
random sample of 3000 of the 1 109 618 pairs (0.27 %, seed 7), the same sample for all six vertices.** All
extrapolations below are sample fraction × 1 109 618 with binomial standard errors.

Correctness checks (`test_dp.py`, run by the previous session): the six multiset lists of `tierC.txt` are exactly
the full factorization lists (306/925/911/834/2446/829); the C DP reproduces `classify_open.exact_identity` on
the documented example (111132, M = {3,2,2}: ν = 5); 150 synthetic anchored patterns (random M, ν, positions, with
repeated positions and positions above the top) were all re-found; the Python DP (`anchorlib.representations`)
re-derives the same pattern counts on every enumerable hit and every explicit representation satisfies (†).

**Stage 4 — explicit representations (Python).** For hits with ≤ 2000 patterns, a second DP (state: carry, count
vector of digits used) enumerates the representations with predecessor links; counts must agree with the C DP
(asserted) and each representation is verified by (†).

**Stage 5/6 — Lemma C and the sandwich.** For each sampled representation: (i) the exact depth-1 Lemma C verdict,
enumerating only the copy choices of the classes e < a + 9 (the verdict depends only on the target mod 5^5·2^{a+9};
`sandwich_lite.verify_reduction` checks for each a that both basis vectors of Λ_96 are ≡ 1 mod 5^5 and 2^9 and that
the kernel generators 1 + 5^5 and 1 + 2^9 are in the image, so the reduction is exact); (ii) tier0's own
`deepcut.deep_cut` driven as in `sandwich.py` — depth 1..6, 10^6 cases, plus a 12 s wall cap per call —
reporting CLOSED-cut / CLOSED-sandwich / BUDGET / open; the upper bound is `baker_chain.baker_upper_bound(k, a)`.

**Benchmark of `classify_open.exact_identity`** (synthetic anchored patterns, random positions in [0, 96)): k = 6:
0.04 s; k = 10: 0.5 s; k = 14 and k = 20: > 30 s (timeout). It is unusable at Tier C (k = 13–44); the C DP decides all
96 ν of a pair in milliseconds, i.e. ≥ 10^5× faster.

## 2. Results

**Table 1 — anchor census (sample of 3000 of 1 109 618 filtered (y, k) pairs; predictions = fraction × 1 109 618).**

| vertex s | 2^a3^b7^c | #M | k range | W range | anchored pairs in sample | fraction ± se | predicted anchored (y, k) | hits (y,k,ν,W) in sample | patterns in sample (exact) | **predicted anchored patterns at level 96** | share k = 0 / k ≤ 9 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 3416267673274176 | 2^6·3^27·7 | 306 | 17–34 | 66–126 | 236 (232 distinct y) | 0.079 ± 0.005 | 8.7×10^4 | 6483 | 5.07×10^8 | **1.9×10^11** | 25 % / 66 % |
| 128421199872 | 2^23·3^7·7 | 925 | 13–31 | 43–85 | 108 (106) | 0.036 ± 0.003 | 4.0×10^4 | 2319 | 1.38×10^9 | **5.1×10^11** | 27 % / 50 % |
| 913217421312 | 2^29·3^5·7 | 911 | 14–35 | 45–91 | 131 (129) | 0.044 ± 0.004 | 4.8×10^4 | 3284 | 4.19×10^9 | **1.5×10^12** | 26 % / 50 % |
| 727326941773824 | 2^39·3^3·7^2 | 834 | 17–44 | 57–113 | 279 (275) | 0.093 ± 0.005 | 1.0×10^5 | 9764 | 2.40×10^11 | **8.9×10^13** | 22 % / 51 % |
| 112717121716224 | 2^34·3^8 | 2446 | 16–42 | 50–110 | 233 (230) | 0.078 ± 0.005 | 8.6×10^4 | 7948 | 3.97×10^11 | **1.5×10^14** | 22 % / 51 % |
| 1438916737499136 | 2^24·3^6·7^6 | 829 | 17–36 | 72–116 | 299 (293) | 0.100 ± 0.005 | 1.1×10^5 | 9147 | 3.72×10^11 | **1.4×10^14** | 29 % / 59 % |

Union over the six vertices: 317 anchored (y, k) pairs on 311 distinct y in the sample (most anchors serve several
vertices). Patterns per (y, k, ν, W) hit are heavy-tailed (median 10^3–10^5, max 6×10^6 to 3.4×10^9); patterns per
anchored (y, k) pair: median 1.5×10^4 to 2.3×10^6, max 7×10^7 to 4.4×10^10. The three largest hits of each vertex carry
only 2–3 % of its total, so the sample total is not dominated by a single outlier; the extrapolation's dominant
uncertainty is the tail, not the binomial error on the pair fraction (which is ± 6 %). The biggest contributors are
tiny anchors read with k = 10 (V = 10·R_96 + y: 97 digits, 89 leading 1s, then y's digits + 1): 11010048 = 2^19·3·7
(vertices 1284…, 9132…, 7273…, 1127…), 8200916911152 = 2^4·3^21·7^2 (3416…), 1021217202747 = 3^11·7^8 (1438…, k = 0,
ν = 2–4, i.e. an "almost all digits above the top" reading).

**Table 2 — the prediction against FRONTIER.md's forecast** (open@96 ≈ 10^-8 × level-12 patterns, interval ×0.1–×30,
calibrated on the sweep's closed vertices; produced before this census and with no anchor input).

| vertex | level-12 patterns | FRONTIER forecast open@96 | anchor-first prediction | ratio |
|---|---|---|---|---|
| 3416267673274176 | 1.72×10^19 | 2×10^11 | 1.9×10^11 | 0.9 |
| 128421199872 | 2.57×10^19 | 3×10^11 | 5.1×10^11 | 1.7 |
| 913217421312 | 8.59×10^19 | 9×10^11 | 1.5×10^12 | 1.7 |
| 727326941773824 | 5.53×10^21 | 6×10^13 | 8.9×10^13 | 1.5 |
| 112717121716224 | 9.86×10^21 | 1×10^14 | 1.5×10^14 | 1.5 |
| 1438916737499136 | 1.38×10^22 | 1×10^14 | 1.4×10^14 | 1.4 |

Two independent routes to the same six numbers (one extrapolates the empirical open rate of enumerated vertices, the
other counts anchors) agreeing within ×1.7 is the strongest evidence this scout produced for the hypothesis at Tier C:
if the open sets contained anything but anchored patterns in appreciable number, or if the anchored patterns were
not all open, the forecast and the census would not line up.

**Table 3 — Lemma C depth 1 and the tier0 sandwich on sampled anchored patterns** (stage 5: 30 representation lines,
some repeated, with `maxchoices` 20 000; stage 6: 22 representations, exact reduced verdict with 300 000 choices, full
`deep_cut` depth ≤ 6, ≤ 10^6 cases, 12 s per call). "BUDGET" in stage 5 = more than 20 000 low-class choices (not decided);
"BUDGET-time" = `deep_cut`'s 2^k depth-1 enumeration did not finish in 12 s.

| vertex | stage 5 (reduced, 20 000) | stage 6 exact depth-1 | stage 6 tier0 `deep_cut` | digit counts k in stage 6 | depth the sandwich would need for k_min / k_med / k_max |
|---|---|---|---|---|---|
| 3416267673274176 | CLOSED 5, BUDGET 1 | CLOSED 7/7 | CLOSED-cut D=1: 1 (k = 17, 480 cases); BUDGET-time 6 (k = 34) | 17, 34×6 | 7 / 10 / 14 |
| 128421199872 | CLOSED 3 | CLOSED 6/6 | CLOSED-cut D=1: 5 (1.2×10^3–6.6×10^5 cases); BUDGET-time 1 | 15,15,17,20,21,22 | 5 / 9 / 12 |
| 913217421312 | CLOSED 3, BUDGET 3 | CLOSED 6/6 | CLOSED-cut D=1: 4; BUDGET-time 2 | 18–22 | 6 / 10 / 14 |
| 727326941773824 | CLOSED 4, BUDGET 2 | (no enumerable hit within the 75 s budget) | — | — | 7 / 12 / 18 |
| 112717121716224 | CLOSED 3, BUDGET 3 | CLOSED 2/2 | BUDGET-time 2 | 39, 40 | 7 / 12 / 17 |
| 1438916737499136 | BUDGET 3 | CLOSED 1/1 | BUDGET-time 1 | 23 | 7 / 11 / 14 |
| **total** | **CLOSED 18, undecided 12** | **CLOSED 22/22, 0 survivors** | **CLOSED-cut 10, BUDGET-time 12** | 15–40 | |

On every pattern where tier0's full enumeration finished, it agreed with the reduced verdict (CLOSED, same
conclusion; the full count of cases is larger because it also enumerates the copy choices of the classes e ≥ a + 9,
which cannot change the verdict). No pattern survived depth 1 in either stage; no CLOSED-sandwich verdict is
possible at Tier C below depth 5 (k = 13) and none below depth 7 for k ≥ 17.

## 3. Runtime

Single process throughout (the previous session of this scout built the pipeline; this session let its final run
finish and added stage 6). Final census run: 1006 s wall (Python ≈ 8 CPU-min; C DP on 3000 pairs: 53 s for
112717121716224, 405 s for 1438916737499136, 1–3 min each for the other four, cached from the 16:11–16:43 run); pair
scan (stage 2) ≈ 5 min; stage 6 ≈ 17 min (filters 3 min, benchmark 1 min, sandwich stage 503 s for vertices 1–5 plus 90 s for vertex 0 and an aborted first attempt of 4 min). Development
and the earlier partial runs of the previous session are estimated at ≤ 45 CPU-min. Total ≈ 1.5 CPU-hours, within the
2-hour cap; the machine carried another scout's process at 100 % throughout (load ≈ 2 on 2 cores).

## 4. Honest assessment

*Prediction.* Under the anchoring hypothesis, the level-96 open set of each Tier-C vertex consists of the anchored
patterns counted above: 1.9×10^11, 5.1×10^11, 1.5×10^12, 8.9×10^13, 1.5×10^14, 1.4×10^14 patterns (sample-based, ±6 %
on the anchored-pair fraction, larger on the heavy tail of patterns per anchor; the full census would take 1.5–40
CPU-hours per vertex in C). The anchors themselves are few — 4×10^4 to 1.1×10^5 (y, k) pairs per vertex on roughly
10^4 distinct S-units of 2–22 digits — and the explicit list for the sample is in `hits_v*_sample3000_7.txt`. This
is a complete description of the predicted open set in closed form (anchor, wrap k, ν, W, and an exact count of
the patterns of each), which is what the enumeration to level 96 would produce after 10^19–10^22 pattern
evaluations.

*Empirical basis.* Every one of the 679 open level-96 patterns recorded in the base-10 sweep (56 vertices, k ≤ 11;
plus 20/20 in base 6) is anchored (OPEN-PATTERNS.md, DEEPCUT.md), 679/679, with the anchor being the Babai-nearest
coset point the engine computed; two blind re-implementations reproduce the classification. The heuristic behind
"exactly": a pattern passes the level-96 residue sieve iff V·2^{−a} lies in the image of ⟨3, 7⟩, a subgroup of index
≈ 10^38 in the residue group of the level primes (index of Λ_96 = 2.8×10^56 against ≈ 10^94 residues; the task's
figure of 10^-55 per pattern includes the engine's further 10-adic checks). At Tier C the hypothesis is tested only
indirectly, by Table 2: the two routes agree within ×1.7 for all six vertices. What this scout did **not** do: run
the engine on any Tier-C pattern (impossible, that is the point), or prove that anchored patterns with k ≥ 10 or
with repeated residue classes are all open in the engine's sense (they pass the residue sieve by (†); the
engine's Lemma B at K* ≤ 5 may already kill some of them, which would only make the predicted open set smaller —
the count above is an upper bound for the hypothesis' open set, and Lemma C depth 1, which contains Lemma B, is
what we measured).

*What a spurious survivor would be.* A level-96 pattern that passes the residue sieve without any S-unit y
satisfying (†): V·2^{−a} in the image of ⟨3, 7⟩ by accident. It would be invisible to this census (we enumerate
anchors, not patterns), and it would be the one kind of open pattern Lemma C cannot be expected to handle with
the anchor's coset — but it would also be exactly as far from a genuine solution as any anchored pattern: its
candidates are still ≥ 10^27 digits by the lattice bound. With ≈ 10^-38 (or 10^-55) per pattern and the 679/679
record, the expected number is ≪ 1; no sweep has ever produced one.

*What this means for closing Tier C.* The sandwich cannot close any pattern with k ≥ 17 at depth ≤ 6 (G(17, 1) =
10^331 > 10^312), so at Tier C "the sandwich" means "Lemma C depth 1 or nothing": depth 1 kills a pattern with
probability ≈ 1 − (#copy choices of the classes e < a + 9)/640 000, i.e. 90–99.99 % per pattern, and in our 52
sampled pattern lines killed all 40 that were decided. But 10^11–10^14 patterns at 10^-2–10^-4 survival leave 10^9–10^12
depth-1 survivors per vertex, each needing a depth 7–18 sandwich with 2^k ≈ 10^5–10^13 sub-cosets per depth — far
outside any budget. **Anchor-first converts "enumerate 10^19–10^22 patterns" into "close 10^11–10^14 explicitly
listed anchored patterns", a 10^8-fold reduction in the object, but not into a computation we can finish; the
missing piece is a closure argument that works per anchor (y, k) rather than per pattern** — e.g. a Baker bound
or lattice cut that uses only y′ ≡ y (mod R_96) and y′ ≡ V (mod 10^{96D}) for all copy choices at once, which is
one coset per (y, k, ν), i.e. ≈ 10^6 objects per vertex instead of 10^14. Nothing in this census is a candidate
for a genuinely open equation: no anchored pattern reached a state the sandwich could have closed and failed to.

## 5. Files

- `anchorfirst.py` — stages 1–5 (S-units, filter, C DP on the sample, representations, Lemma C depth 1 reduced).
- `anchorfirst_sandwich.py` — stage 6: the task's three cheap filters' rejection rates, the `exact_identity`
  benchmark, the tier0 sandwich (`deepcut.deep_cut` + `baker_chain.baker_upper_bound`) and the exact reduced depth-1
  verdict on sampled patterns; `sandwich_sample3000_7.json` holds the per-pattern rows for vertices 1–5 (vertex 0's
  rows are in `anchorfirst-sandwich-part1.log` and `anchorfirst-sandwich-part2-v0.log`).
- `anchor_dp.c` / `anchor_dp` — the C anchor DP; `anchorlib.py` (tables, Python DP, representation check);
  `sandwich_lite.py` (reduced Lemma C, `verify_reduction`); `test_dp.py` (correctness checks).
- `pairs.txt` (1 109 618 filtered (y, k, D+10q)), `pairs_sample3000_7.txt`, `hits_v{0..5}_sample3000_7.txt`
  (y k ν W count), `table_v*.txt` (DP tables), `results_sample3000_7.pkl`.
