# Certifying the sandwich lower bound over ALL copy choices at once

*2026-10-21, research scout (mathematics + light computation). Code: `peranchor.py` (library), `run_all.py`
(driver, 43 patterns × all representations → `run_all.jsonl`, `summary.txt`), `exp_scale.py`, `exp_margin.py`
(scaling and positive controls), `test2.py` (differential against `deepcut.deep_cut`). Inputs: the 43 survivors
of `SANDWICH-full.txt` (s, M, a, y per line; representations rebuilt with `deepcut.all_representations`), Λ_96
from `deepcut.kernel_lattice`. Total compute ≈ 1.1 CPU-hours, one process. Everything in the certificate path is
exact integer / rational arithmetic (gmpy2 mpz/mpq); floats appear only in reported log10 values.*

## 0. Summary of verdicts

| idea | statement | verdict | key numbers (43 patterns, 88 representations) |
|---|---|---|---|
| 1a. B&B (digit-ordered Fincke–Pohst ≡ branch and bound) | enumerate digit words in position order, prune a node when its coset's exact nearest point already exceeds the Baker radius | **works, exact, but NO exponential gain** | 43/43 certified; 18,555 nodes total vs 3,902 distinct sub-cosets (pruning only ever fires in the last block: pruned = leaves on every pattern) |
| 1b. Box-CVP over a linear range (the lattice lift proper) | ONE box-constrained CVP in dimension 2 + f certifies min ‖(b,c)‖ over the union of all 2^f words of positions [s, 2s−a) | **SURVIVED — the enumeration of the last two blocks disappears** | 43/43 certified with **0 enumeration nodes**, 263 LLLs of dimension ≤ 16, 10.9 s LLL total; exact minima agree with the enumeration 88/88 (and with `deep_cut` 40/40, with the C port 43/43 to 2 dp); 54/54 planted union points found |
| 2. Per-anchor | one computation per anchor decides all its patterns | **KILLED** as a relaxation (branching (1+\|M\|) per position up to the frontier ≈ 3^184), and **empty** as sharing (263 level nodes, 263 distinct keys) | — |
| 3. Dual / sub-lattice bound Λ* | nearest point of Λ* = Λ_D + Σ Z v_j | **KILLED, quantified**: g = gcd(10^h, w_j) = 10^{e_min} with e_min = 3–8, so Λ* certifies 10^{122–125} digits against G = 10^{128–199} | index lost ≈ 10^{h − e_min} ≈ 10^185 per block |

What the box-CVP does NOT do: it does not remove the enumeration of the digit words *below* the start s of the
linear range. The honest cost model is (§4): cost ≈ #words below s × poly(f), with s ≥ (frontier + a)/2, i.e.
the exponent of the enumeration is roughly halved (square root of the enumeration cost), not removed. For the 43
patterns the words below s = 192 number 1–36 per pattern because only r ≤ 7 pattern digits remain unplaced after
depth 1 (the depth-1 survivor is the anchor's shadow and consumes the rest); that is why the whole thing costs
seconds in Python.

Immediate free gain for the existing pipeline, independent of all this: the C port (and `deep_cut`) count
identical digits as distinguishable, so they evaluate 59,124 "sub-cosets" where there are 3,902 distinct ones
(ratio 47× on the k = 11 pattern: 34,476 vs 728). The minima are identical; the cost was symmetric overcounting.

## 1. Setting and the exact tools

Pattern (ν, {(d_j, e_j)}_{j≤k}), anchor y = 2^a 3^b 7^c, coset C = (b, c) + Λ_96. Every non-anchor candidate y′
has ≥ 10^27 digits, so for any m ≤ 10^25 its lowest m digits are
y′ ≡ R_m + Σ_j (d_j − 1)·10^{e_j + 96 t_j} (mod 10^m) (digit j at copy t_j, or absent when e_j + 96 t_j ≥ m; distinct
positions; each digit at most once), and the condition 2^a 3^b 7^c ≡ that (mod 10^m) cuts C to a coset of
Λ^{(m)} = {Δ ∈ Λ_96 : 3^{Δb} 7^{Δc} ≡ 1 (mod 5^m) and (mod 2^{m−a})}. The union of these cosets over all admissible
words is U_m; the sandwich needs min_{U_m} ‖(b, c)‖ > N(G) := the norm that gives G digits
(‖(b,c)‖ ≥ N ⇒ max(b,c) ≥ N/√2 ⇒ ≥ (N/√2)·log10 3 digits).

**Tool A — exact linear extension (Codex T1 as an algorithm).** For a coset v0 + Z u1 + Z u2 whose units agree
mod 10^m (lattice ⊆ Λ^{(m)}) and 1 ≤ h ≤ m − a, with y0 the unit at v0 and t_i = 3^{u_i,1} 7^{u_i,2} − 1,
the unit at v0 + z1 u1 + z2 u2 is ≡ y0 + z1·y0 t_1 + z2·y0 t_2 (mod 10^{m+h}) (the proof in
NOTE-2026-10-21 §5.1: y0 t² ≡ 0 mod 10^{m+h} because v2 ≥ a + 2(m−a) ≥ m + h, v5 ≥ 2m). Hence
"2^a 3^b 7^c ≡ Y (mod 10^{m+h})" is A_1 z1 + A_2 z2 ≡ (Y − y0)/10^m (mod 10^h), A_i = y0 t_i/10^m mod 10^h.
`extend_exact` applies this in steps h ≤ m − a (falls back to `descent.cut_coset` below m = 12); the valuation
hypotheses are asserted at every call. Kill test: on random extensions it returns the same coset as `cut_coset`
(same index, mutual containment of base points), 1,000× faster at K = 384 (1 ms vs 2 s); and the whole DP built on
it reproduces `deep_cut` (which uses only `cut_coset`) exactly, see §2.

**Tool B — digit-ordered branch and bound (`dp_bound`).** Positions in increasing order; at a position whose
class carries unplaced pattern digits, branch over "digit 1" and each distinct remaining digit value of that
class; cut the coset to the new precision; prune when the exact nearest point (Babai + ±2 window on the
Lagrange-reduced basis, `deepcut.nearest_norm`) has norm² ≥ N². A pruned node's every refinement is a sub-coset of
it, so the pruning is sound. With no pruning this is an exact enumeration of U_m's minimum at precision m, with each
distinct digit word visited once (identical (d, e) pairs are interchangeable).

**Tool C — the lattice lift (box-constrained CVP, `cvp_block`).** Fix a node: coset co (units ≡ Y mod 10^s),
remaining digits, range [s, s+h) with h ≤ s − a. Boolean variables x_i, one per (remaining digit j, position
p ∈ [s, s+h) with p ≡ e_j mod 96), weight w_i = (d_j − 1) 10^{p−s}. By Tool A every word's sub-coset is
{z : A z − Σ w_i x_i ≡ β (mod 10^h)}, β = (T − y0)/10^s, T = Y's digits then 1s. So

  U = { v0 + z1 u1 + z2 u2 : (z, x) ∈ Z^{2+f} with A·z − W·x ≡ β (mod 10^h), x ∈ {0,1}^f, and Σ_{i∈g} x_i ≤ 1 for every
  group g } where the groups are "all positions of one digit" and "all digits of one position".

The congruence set is a coset p + K of a lattice K ⊂ Z^{2+f} (basis from unimodular column operations on
[A_1, A_2, −w_1, …, −w_f, 10^h]). Embed E(z, x) = (2(z1 u1 + z2 u2), 2λ x_1, …, 2λ x_f, 2λ Σ_{g_1} x, …, 2λ Σ_{g_G} x)
∈ Z^{2+f+G} and target τ = (−2 v0, λ, …, λ), with λ = ⌊√N²⌋ + 1. Then for (z, x) ∈ p + K:
‖E(z,x) − τ‖² = 4‖(b,c)‖² + 4λ² Σ_i (x_i − ½)² + 4λ² Σ_g (Σ_g x − ½)².

*Lemma (exact box encoding).* If x is admissible (Boolean, groups ≤ 1) every penalty term equals λ², so the
distance² is 4‖(b,c)‖² + λ²(f + G). If x is not admissible some integer term is ≥ 9λ², so the distance² is
≥ λ²(f + G) + 8λ² > 4N² + λ²(f + G) because λ² > N²/2. Hence the lattice points of E(p + K) within squared radius
R² = 4N² + λ²(f + G) of τ are EXACTLY the admissible words' points with ‖(b,c)‖ ≤ N. ∎
(The target has a component orthogonal to the lattice's span when G > 0; the enumeration accounts for it exactly.)

Certification: integral LLL (Cohen 2.6.7, δ = 0.99, with the (z, x) coordinates carried along and asserted equal to
the reduced vectors' preimages, so the reduced basis spans the same lattice) followed by exact rational
Schnorr–Euchner enumeration at fixed radius R². "No lattice point within R²" ⇒ min_U ‖(b,c)‖ > N ⇒ every candidate
of the union has more than G digits. In "min mode" (shrinking radius, started from the all-ones word's own nearest
point) the same routine returns the exact minimum over U together with the word and the point; the point is then
re-verified end to end: 2^a 3^b 7^c mod 10^{s+h} is recomputed and must show the claimed digits in [s, s+h).

**Tool D — dual bound (`dual_bound`).** Λ* = Λ^{(s)}-coset ∩ {A z ≡ β (mod g)}, g = gcd(10^h, all w_i): a single
coset containing U; its nearest point is a valid lower bound.

## 2. Kill tests — exactness (the bound must dominate the true minimum over ALL x)

1. DP vs `deep_cut` (Python, Pohlig–Hellman cuts, distinguishable digits), all representations with k ≤ 8
   (`test2.out`, `test2b.out`): **40/40 identical** — identical CLOSED verdicts and identical minima to 10^−9 in
   log10, at the pattern's own depth (2 or 3). Where `deep_cut` reports more survivors (e.g. [3, 36, 189] vs 36
   leaves for M = 22222488) the extra ones are permutations of identical digits; the minima coincide.
2. DP vs the C port's `min-bound` column (SANDWICH-full.txt, all 43 patterns including the depth-4 ones with
   k = 9–11): **43/43 agree to the 2 printed decimals**; distinct sub-cosets 3,902 vs the port's 59,124.
3. CVP (min mode) vs DP exact minimum at precision s + h (`run_all.jsonl`, field `cvp_min_match`): **88/88
   representations identical** (exact integers; e.g. k = 11: 214.6320 = 214.6320 at precision 384; a > 0 cases at
   precision 384 − a). Where the CVP covers more than the pattern's depth (s = 192, h = 192 − a reaches depth 4 for
   depth-3 patterns) the DP was run to the same precision.
4. Positive controls (`exp_margin.py`): 54 planted admissible words on six patterns (random placements of the
   remaining digits at copies 2–3), radius = the planted sub-coset's nearest norm + 1: the certificate found a
   union point of norm ≤ the planted one **54/54** (always the true minimum, which is ≤ the plant).
5. Negative control: `cvp_block` asserts that any returned point is admissible and that its unit has the claimed
   digits; never fired in 400+ calls. The enumeration code was also checked against brute force on random 4-D
   lattices (`test3.py`).

## 3. Kill tests — cost, on the real patterns

Columns (from `summary.txt`): Cport# = sub-cosets evaluated by the C port at the pattern's depth; DP# = distinct
sub-cosets (DP leaves) at that depth; B&B# = nodes of the pruned DP; lvl# = nodes at the CVP start level s
(96 for depth-2 patterns, 192 otherwise); r = max remaining digits at level s; dim = 2 + f (max); enum = enumeration
nodes in certification mode; LLL = seconds of integral LLL (Python); t = seconds for the whole record (exact DP +
B&B + CVP certification + CVP min mode + DP at s + h).

```
idx      s M            a k D   logG reps Cport#   DP#   DPmin  B&B# lvl# r dim enum  LLLs   CVPmin   DP@s+h cert dual  t
  0  14336 47888        0  5 2  94.98    1      2     2  120.07    27    1 1   3    0   0.0 120.0717 120.0717 Y=  75.2    0
  8  28672 2227888      0  7 3 128.49    1     12    12  167.72    99    6 2   6    0   0.1 215.1497 215.1497 Y= 216.4    1
 22  18144 22333467     0  8 3 145.33    5    147    36  167.16   204    9 4  10    0   0.3 215.3263 215.3263 Y= 122.9    3
 29   8192 22222488     0  8 3 145.33    2    189    48  167.18   226   12 4  10    0   0.3 214.4275 214.4275 Y= 124.6    3
 30  14336 222222478    0  9 3 162.22    4    882   112  167.18   457   18 5  12    0   0.9 214.9023 214.9023 Y= 123.1    8
 36  14336 2222222278   0 10 4 179.15    2   5304   224  215.41   860    8 6  14    0   0.8 215.4125 215.4125 Y= 124.1    6
 38  18144 2222233337   1 10 4 199.07    1    208   208  214.92  1073   12 4  10    0   0.7 214.3473 214.3473 Y= 123.8    6
 41  28672 2222222478   0 10 4 179.15    4  16224  1820  214.90  7816   36 6  14    0   2.4 214.9023 214.9023 Y= 123.1   45
 42  28672 22222222278  0 11 4 196.13    2  34476   728  214.63  2519   12 7  16    0   1.9 214.6320 214.6320 Y= 123.1   18
(full table of 43 rows: summary.txt)
totals: Cport 59,124 sub-cosets (76 s in C; Python deep_cut: hours) | DP 3,902 leaves | B&B 18,555 nodes |
        CVP: 263 start nodes, 263 LLLs (dim 3–16), 10.9 s LLL, 0 enumeration nodes, all 43 certified
```

Observations.
- **B&B prunes only in the last block**: on every pattern `pruned == leaves` — no node was ever pruned before the
  last block (the B&B was allowed two further blocks and never needed them). This is the frontier phenomenon of §4: the lattice index must exceed N² before any pruning can
  happen, and that happens only inside the last block. B&B therefore costs 3–5× the number of distinct sub-cosets
  (the internal nodes), with no exponential gain. Idea 1 as "Fincke–Pohst with box constraints enumerated in
  position order" IS this B&B (the relaxation over the not-yet-assigned high positions is the coset of
  Λ^{(next position)}), so the box-CVP's gain must come from the mixed LLL basis, not from the box pruning.
- **The CVP certification never enumerates**: 0 nodes on all 263 instances; the cost is the LLL in dimension
  2 + f ≤ 16 (≤ 2.4 s per pattern in pure Python; fplll would be 100× faster). The exact minimum (min mode) costs
  3–95 enumeration nodes on the real patterns.
- **Why the real patterns are cheap**: after depth 1 only r ≤ 7 digits remain unplaced (the depth-1 survivor is
  the anchor's shadow and places the others at copy 0). The number of start nodes at level 192 is ≤ 2^r = 36 at
  most. r, not k, is the parameter: r = 1–3 for k ≤ 7, 1–4 for k = 8, 2–7 for k = 9–11.

Scaling with r (`exp_scale.py`: the k = 11 pattern's main level-192 node with synthetic extra digits (2, e) in
new classes; CVP over [192, 384); certification radius G = 10^196.13; min mode exact):

```
 r  dim  G  LLL(s)  cert nodes  min-mode nodes   exact min   DP check (leaves)
 7   16  13   0.23      0            1,358        215.5144    match (112)
 9   20  15   0.48      0           11,667        215.2117    match (1,008)
11   24  17   2.2       0          109,045        214.2538    (DP too slow in Python)
13   28  19  10.6       0        1,085,900        214.0440
```
Certification stays at 0 nodes; LLL grows like dim^4 in this Python implementation. Finding the EXACT minimum is
exponential in r (×10 per two digits ≈ the number of sub-cosets × 10) — as it must be: the exact minimum is a
list-type quantity (T3). The certificate is cheap because it only needs the ball of radius N to be empty and N sits
far below the lattice scale.

Margin needed (`exp_margin.py`, r = 11, dim 24): certification enumeration nodes vs how far the radius sits below
the true minimum (in digits of log10): 0 → 686 nodes (finds the point), 0.5 → 173, 1 → 100, 2 → 13, 3 → 9,
5 → 1, ≥ 8 → 0. The sandwich margins of the 43 patterns are 5–40 digits, so all 43 are in the trivial regime.
Heuristically (Gaussian heuristic on the embedded lattice, GS profile ≈ balanced after LLL) the trivial regime
needs margin ≳ (d/4)^{d/2} in index, i.e. ≈ 0.5·d·log10(d/4) digits of margin: 9 digits at d = 24, 21 at d = 42,
42 at d = 68 — observed ≈ 5 at d = 24, consistent.

## 4. What is and is not gained — the frontier argument (analysis, not Lean)

Let I(m) = [Z² : Λ^{(m)}] ≈ 2.8×10^56 × 10^{m}/(2^9·5^5) for m ≥ 9 (saturation of Λ_96's image, T3/H2), and let N
be the Baker radius, N² ≈ 10^{2 log10 G}. A coset of Λ^{(m)} contains a point of norm < N with probability
≈ πN²/I(m) (≈ 1 while I(m) < N²). Hence every digit word below the frontier m* := the position where I(m*) = πN²
(m* ≈ 2·log10 G − 56 + 9 + 0.4 ≈ 27.8k − 25 for a = 0: 280 for k = 11, 586 for k = 22, 1,200 for k = 44) produces a
sub-coset that meets the ball, and any method that lists sub-cosets must list all words below m*: that is T3 in
quantitative form and it is exactly what the B&B measured (pruning only after the frontier).

The box-CVP does not list. Its cost is: (#words below s) × LLL(dim 2 + f) + enumeration, where the linear range
[s, 2s − a) must contain the frontier plus the margin, so s ≳ (m* + margin + a)/2. Words below s number
≈ (s/96)^r (one placement choice per block per remaining digit, minus collisions): the exponent is halved relative
to the enumeration's (m*/96)^r. On the 43 patterns that is 263 start nodes against 3,902 distinct (59,124 listed)
sub-cosets, and the CVPs themselves are free. Projection for a Tier-A pattern (k = 22, G ≈ 10^350, depth 7 in the
old count): m* ≈ 590, s = 384 (words of blocks 1–3 enumerated: ≈ 4^r), one CVP of dimension 2 + 4r per word;
for r = 10: ≈ 10^6 LLLs of dimension 42 (≈ 1 s each with fplll, 10^6 s single-threaded) against 8^10 ≈ 10^9 cut
operations; for r ≤ 6 (as on all 43 current survivors) ≈ 4,000 LLLs — minutes. So Tier A becomes a question of r,
the number of digits the anchor shadow leaves unplaced, which should be measured on Tier-A survivors before anything
else (it is ≤ 7 on everything closed so far; the Codex T1 remark "527-digit coordinate bounds" concerns the parent
coset of Λ_96, where linearity has not started yet — the correct start is a depth-1 survivor, s = 96, where the
coordinates in the Λ_1 basis are ≤ 10^{28}, far below the modulus).

Extending the linear range (to shrink the enumerated prefix further) is possible on paper but costly: positions
[s, s+H) with s < H ≤ 2s make Log(target) a quadratic Boolean function (Möbius pairs x_i x_j for p_i + p_j < s + H),
each pair an extra Boolean with an exact penalty encoding (q = (x_i + x_j − 2y − ½)² + …, checked), so the dimension
grows like r² and the margin needed by the enumeration like (d/4)^{d/2}: dimension ≈ 135 at r = 11 needs ≈ 100
digits of margin. Relaxing z-quadratic terms instead (free variables for z1², z1 z2, z2²) loses 3·log10(Z²) ≈ 450
digits of index: dead. The clean regime is one linear block pair, dimension 2 + f ≤ ~40.

## 5. Idea 2 — per-anchor closure: assessed, not feasible

- As a relaxation ("all placements of a sub-multiset of M at positions < 96D"): the DP would branch
  (1 + number of distinct digit values of M) at EVERY position, and §4 says no pruning before the frontier
  m* ≈ 280 (k = 11): ≥ 3^{184} nodes. As a lattice lift: one Boolean per (digit value, position), f ≈ 3·280,
  dimension 850, and every low-position variable has a unit weight (T4): neither enumeration nor LLL survives.
- As sharing between patterns of one anchor: the only object the patterns of an anchor share is the Λ_96-coset C,
  whose depth-1 DP costs 10–30 nodes (the 2^9·5^5 criterion kills by position 9). Everything expensive depends on
  the pattern's own digits. Measured: 263 start-level nodes over the 43 patterns, 263 distinct
  (anchor, Y mod 10^s, remaining digits) keys — zero reuse, even for anchor 330812181 (126 nodes, 11 patterns).
  H8-style memoisation has nothing to memoise here.
Verdict: KILLED. The right unit is the pattern (indeed the depth-1 survivor node), and it is already cheap.

## 6. Idea 3 — dual bound: killed, quantified

Λ* = (level-s coset) ∩ {A z ≡ β (mod g)}, g = gcd(10^h, (d_j − 1) 10^{p_j − s} over the bits in the range).
The lowest class in the range decides: g = 10^{e_min} (times 2 or 5 when d − 1 ∈ {5} or is even and no other
digit interferes). On the 43 patterns (`dual` column, best node): e_min = 3–8 at level 192, Λ* certifies
10^{120.9–124.6} digits against G = 10^{128.5–199.1}; the full block would give 10^{215}. The index lost per block
is 10^{h − e_min} ≈ 10^{184–189}. The relaxation that keeps the index — "digits in a run of positions are zero" —
is not a lattice condition but a short-interval condition, and the lift that encodes it exactly IS the box-CVP of
§1. So idea 3 is the f = 0 degenerate case of idea 1 and it is useless exactly when T4 says it is (some w_j with
gcd(w_j, 10^h) small, i.e. a low pattern class). Verdict: KILLED.

## 7. Status of the certificate and what to do next

Certified for the 43 patterns: by the B&B (exact enumeration with sound pruning) AND by the box-CVP (LLL +
exact enumeration at the Baker radius), with the two methods' exact minima agreeing with each other and with
`deep_cut`/the C port. Not Lean-checked; same standing as Lemma C (two independent implementations of the cut
agreeing, exact arithmetic, planted positive controls). The sandwich's lower bound no longer depends on
enumerating the copy choices of the last two blocks.

Next: (1) measure r (digits left unplaced after depth 1) on the Tier-A/Tier-B open patterns — it decides
everything; (2) port `cvp_block` to C/fplll (LLL dominates; BKZ-20 as a safety net for dim > 30) and feed it
the depth-1/2 survivor nodes from the C port; (3) replace distinguishable-digit case counting by distinct words in
the C port (15× on the current survivors for free); (4) a Lean statement of the box-encoding lemma and of Tool A
(the Lean `two_generator_lift` already covers the linearisation core).
