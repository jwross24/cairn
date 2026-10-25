# Red team, round 2: the Baker–lattice sandwich (SANDWICH.md / deepcut.py / baker_chain.py / descent.cut_coset / lattice.py)

*2026-10-20 ~19:00–20:30 EDT, second red-team agent, after the index-bookkeeping fix of `deep_cut` (the round-1
report is kept below as an appendix; its scripts `a*.py` are untouched). All scripts of this round are
`/home/claude/redteam/rt_*.py` with logs `rt_*.log`; they import the tier0 code via `sys.path` and write only here.
Inputs: `/tmp/survivors3.txt` (the 43 sandwich patterns), the three sweep files
(`/home/claude/tier0/runall_final.jsonl`, `/tmp/trees_c.jsonl`, `/tmp/trees_mac_0545.jsonl` ≡ the uploads copy).
Machine was shared and loaded; every run is one niced process, the longest ~18 min.*

## Verdict table (round 2)

| # | Attack | Verdict |
|---|--------|---------|
| 1a | Planted genuine 10-adic points (a real S-unit 2^a 3^b* 7^c* whose lowest 96D digits ARE a chosen pattern word, for adversarial copy choices: all k digits in one class at copies 0,1,2; the same (d,e) three times; class = ν; a digit above the window; classes 95/0; random) through the CURRENT `deep_cut` | **SURVIVED** — 10/10 planted points kept (two more random cases E4/E5 were still running at report time; `rt_plant10adic_DE.log` has their result) in a surviving sub-coset at every depth ≤ D, reported bound ≤ the point's digit count (`rt_plant10adic.py`, logs `rt_plant10adic*.log`). The index-keyed fix is complete for these cases. |
| 1b | Synthetic small-index lattices with a planted point through `cut_coset` | **SURVIVED** — 48/48 kept, and on K ≤ 12 the returned coset equals the true solution set on an 81×81 window (`rt_small_lattice.py`). |
| 2 | Wrong k / wrong a / anchor not in coset | **WEAKNESS (medium, latent)** — confirmed round 1: `sandwich.py` has no `v2(y) == a` check and reports CLOSED with an empty verdict when `reps == []`. New: for the 43, `v2(y) == a` holds for all (checked); vertex-level data all at last level 96 (checked for all 3 files). |
| 2′ | **NEW — driver collapses patterns by key (s, M, a, y)** (`seen` set in `deepcut.py` main and `sandwich.py`) | **WEAKNESS (medium, latent; verdict unchanged)** — with 5-field records two distinct recorded patterns on the same anchor collapse to one and the FIRST record's (ν, eps) filter is applied: `runall_final.jsonl` s=324 M=22339 a=2 y=111132 has patterns (ν=4, eps=(0,4,1,4,4)) and (ν=4, eps=(0,5,1,3,3)); `DEEPCUT-run.txt` line 21 shows `reps=1`: the second pattern was never evaluated. Re-run: it closes at depth 1 (`rt_seen_collapse.py`). Same class as the `deep_cut` dict bug. |
| 2″ | **NEW — the `or reps` fallback is not conservative** | **WEAKNESS (low, latent)** — if a recorded (ν, eps) matches no representation, `sandwich.py`/`deepcut.py` evaluate *all other* representations and report CLOSED; the recorded pattern itself stays unexamined (round 1 called this "conservative"; it is not). Never fires on the data: all 27 recorded patterns are enumerable (`rt_attack_Q_all.log`). |
| 3 | "n ≥ 192 except the anchor" | **SURVIVED** — λ₁(Λ_96) = 7.85·10^27 (round 1, reconfirmed by the kernel build); a candidate with (b′,c′) ≠ (b_y,c_y) has ‖(b′,c′)‖ ≥ λ₁ − ‖anchor‖ ⇒ n > 0.477·λ₁/√2 ≈ 2.6·10^27 ≥ 96D for every depth used; a candidate with (b′,c′) = (b_y,c_y) is y itself. No candidate with 96 ≤ n < 192 can exist. Exact argument in §3. |
| 4 | Copy-choice enumeration completeness (top digit, same class different copies, class = ν, all in one class) | **SURVIVED** — these are exactly the planted cases of 1a (constructed by hand as words L*, then realised as true S-units); all generated and kept. The enumeration at depth D is the full set {t_j ∈ {0..D−1} ∪ {≥D}, distinct positions}; no constraint from n or ν applies (n ≥ 10^27). |
| 4′ | **NEW — `all_representations` caps the pattern value at y + 9R_96 ("digit mass < 10^97"), but a pattern value can reach R_95 + 8k·10^95 (several digits in high classes)** | **WEAKNESS (medium, latent; verdicts unchanged)** — exhaustive scan of V = y + kR_96, 10 ≤ k ≤ 8|M|+1, over all 679 anchors of the three files: **8 anchor/multiset pairs in 5 vertices (42336, 111132, 148176, 236196, 1411788) have representations at k = 18 (and k = 27) that the pipeline never examined** (`rt_attack_k10.py`, `rt_attack_k10.log`). Running the deep cut on all 15 such representations: every one CLOSED-cut at depth 1 (`rt_eval_unexamined.py`). The certificate "all representations of the anchor are closed" was incomplete for those vertices; the fix is k ≤ 8|M|+1 (or scanning V ≤ R_95 + 8k·10^95). |
| 4″ | Engine guarantees only V ≡ y (mod Q), Q = (10^96−1)/189 (round-1 §8a), now over ALL 679 anchors, with the structural digit filter (≤ 2k+2 digits ∉ {0,1}) and the placement DP on every surviving V ≤ R_95 + 8k·10^95 | **SURVIVED** — 8949 candidate values tested, 0 representable with 189 ∤ m (`rt_attack_Q_all.py`, 18 min). Also: the only m < 2000 whose repeating block is ≤ 1 digit away from {0,1}^6 or is 999999 (carry-absorbable) are m ≡ 0, 21 (mod 189) — i.e. exactly V ≡ y (mod R_96) — which is why only the k ≥ 10 gap of 4′ exists. |
| 5 | Baker side | **SURVIVED** — 17 certificates (k, a) of the run re-verified in interval arithmetic (Φ(N)/N = 0.9978, fixed point within 10^0.3 below N); G(k,a) monotone in a; 1981 zero-free S-units in [10^3, 10^15] (a up to 45, including a-dominant ones where a > 2.1n + 2) pass every asserted in-domain inequality, max B_exact/B_max = 0.996; B_max = 2.1n + 2 + a ≥ a trivially, so the a-dominant case is covered by the "+a" term (`rt_baker.py`). Lemma 5.1 re-derived by hand (§5). |
| 6 | Floating point in certified comparisons | **SURVIVED** — unchanged from round 1 (min margin 10^4.98 after the fix; only `log10` of exact ints in the comparison). New: `nearest_norm`'s ±2 window is *provably* exact for a Lagrange-reduced basis (|Δy| ≤ 1, |Δx| ≤ 1, proof in §6) and agrees with an exact CVP on 3000 deliberately skewed reduced bases with ‖u2‖/‖u1‖ up to 10^4 (`rt_nearest_skew.py`). |
| 7 | `cut_coset` 2-adic branch for a ≥ K, a = K−1, K−2 | **SURVIVED** — brute force over the full period of (b, c) for K ∈ {3, 4}, a ∈ 0..K+2, genuine and random targets, Z² and an index-11 coset: 156/156 exact matches (`rt_cutcoset_edge.py`). |
| 7′ | **NEW — `cut_coset` asserts (crashes) when the word is ≡ 0 (mod 5)** | **WEAKNESS (low, loud)** — a pattern with digit 5 in class 0 at copy 0 makes L ≡ 0 (mod 5) and `log3_mod5k` raises `AssertionError` instead of treating the case as dead (`rt_plant10adic` probe at the end of §7). None of the 43 multisets contains a 5; a crash is loud, not a wrong closure. |
| 8 | Other: the anchor's coset is the right coset; levels; the anchor is never a candidate | **SURVIVED** — every equation with open patterns ended at level 96 in all three files; for every anchor the deep-cut coset (b_y,c_y)+Λ_96 equals C_V ⊇ C_engine; the anchor y itself has (b,c) = (b_y,c_y) and is excluded by construction. |

**Bottom line.** I could not make the sandwich wrongly close any pattern. The four new findings are all bookkeeping holes
of the same family as yesterday's `deep_cut` bug ("repeated structure collapsed by a dict/set/cap"): (i) the driver's
`seen` set drops a second recorded pattern on the same anchor; (ii) the `or reps` fallback silently substitutes other
patterns; (iii) `all_representations` stops at y + 9R_96 although pattern values reach ~9|M|·10^95 — 15 representations in
5 vertices were never examined (all close at depth 1 when run); (iv) `cut_coset` crashes on words ≡ 0 mod 5. None changes a
verdict on the data; (i)–(iii) are silent and should be turned into assertions/extended ranges before the next sweep.

---

## 1a. Planted genuine 10-adic points (`rt_plant10adic.py`, logs `rt_plant10adic.log`, `rt_plant10adic_DE.log`)

A real S-unit with a few non-1 digits and 200–400 digits does not exist (k ≈ 0.9n), so the test the brief asks for is
realised 10-adically: choose the pattern and the copies by hand, form the word

    L* = R_{96D} + Σ_j (d_j − 1)·10^{e_j + 96 t_j},

and solve 2^a 3^b 7^c ≡ L* (mod 10^{96D}) exactly (`cut_coset` on Z², then a non-negative representative via
(λ,0),(0,λ) ∈ the solution lattice, λ = 4·5^{K−1}·2^{K−a}). The integer 2^a 3^{b*} 7^{c*} then **really has L* as its
lowest 96D digits** (asserted by direct computation), so it is a genuine candidate for every statement the cut makes at
depth ≤ D, and its coset (b*,c*) + Λ_96 is what the engine would assign. A structural fact needed for the construction:
3^b 7^c (mod 20) ∈ {1,3,7,9}, so a word is reachable iff (L >> a) is odd, prime to 5 and ≡ 1,3,7,9 (mod 20) — the image of
<3,7> in (Z/5^5·2^9)^* has index exactly 2 and is this residue class (`image_mod_1600000.pkl`); with a = 0 the word
R_96 + … is reachable only if an *even* digit sits at position 1 (R_96 ≡ 11 mod 20). Helper digits at classes 0..8
are added to each designed pattern to satisfy this.

Results (format: per depth (D′, closed, #surviving sub-cosets, planted point kept, bound, log10 of the planted digit count)):

```
A  one class k=3 copies 0,1,2      a=0 De=[(2,7),(4,7),(8,7),(2,1)]  copies=[0,1,2,0] D=3 : (1,F,1,T,71.89,287.8) (2,F,3,T,120.09,…) (3,F,7,T,167.81,…)
A2 one class k=3 copies 2,0,1                                                            : kept at depths 1,2,3
B  (2,7)×3 copies 0,1,2 (+ (5,40))  a=0                                                  : (1,F,6,T) (2,F,27,T) (3,F,84,T)
B2 (2,7)×3 copies 1,2,0                                                                  : kept at depths 1,2,3
C  class = ν, one digit above window  a=1 De=[(3,20),(8,20),(6,3),…] copies=[0,1,5,…] D=2: (1,F,3,T) (2,F,14,T)
D  classes 95/0, two (3,0) at copies 0/1  a=0 D=2                                        : kept at depths 1,2
E0–E3 random (a ∈ 0..4, k ≤ 6, D ∈ {2,3})                                                : all kept (E4/E5 pending)
```

10/10 planted points kept, 0 lost; at every depth the reported bound is below the planted point's digit count, as it
must be (the point lies in a surviving sub-coset). B/B2 are precisely the case the pre-fix enumeration dropped.

## 1b. Small-index lattices (`rt_small_lattice.py`)

48 random cosets (b*,c*) + L with L of index ≤ 72, K ∈ {3,5,8,12,40,96}, a from 0 to K+1: `cut_coset` keeps the planted
point in all 48 cases, and for K ≤ 12 its output coincides with the true solution set on the 81×81 window around the point.

## 2′. The driver collapses patterns on the same anchor (`rt_seen_collapse.py`)

```
record: (324, (2,2,3,3,9), 2, nu=4, eps=[0,4,1,4,4], y=111132)
record: (324, (2,2,3,3,9), 2, nu=4, eps=[0,5,1,3,3], y=111132)
all representations of the anchor: 3  (the two above and one with (3,95),(9,95))
driver (deepcut.py main / sandwich.py) evaluates only [(4,[0,4,1,4,4])]  -> the other recorded pattern is silently dropped
dropped pattern through deep_cut: depth 1 closed=True (24 cases)
```

`DEEPCUT-run.txt` line 21 indeed reports `s=324 M=22339 a=2 y=111132 reps=1`. The 3-field (Mac/C) files are immune
because every representation of the anchor is evaluated anyway (196 of 653 keys of the Mac file carry several records);
the risk is confined to 5-field records, where the first record's (ν, eps) filter is applied and later records vanish.
Fix: key `seen` by (s, M, a, ν, eps, y), or never filter.

## 2″. The `or reps` fallback

`reps = [r for r in reps if r[0] == nu and Counter(classes) == Counter(eps % 96)] or reps`: an unmatched recorded
pattern is replaced by *all other* representations of the anchor, which are different patterns. Their closure says
nothing about the recorded one. It cannot fire on the current data (every recorded V is y + kR_96 with k ≤ 9, see 4″),
but it is the wrong default; it should raise.

## 3. The "n ≥ 192" premise, exactly

Candidates of a pattern are y′ = 2^a 3^{b′} 7^{c′} with (b′,c′) ∈ (b_y,c_y) + Λ_96 (a is part of the pattern). If
(b′,c′) = (b_y,c_y) then y′ = y: the anchor, excluded. Otherwise (b′,c′) − (b_y,c_y) is a non-zero vector of Λ_96, of
Euclidean norm ≥ λ₁ = 7.8502·10^27 (exact: the reduced basis is Lagrange-reduced, λ₁ = ‖u₁‖). Hence
max(b′,c′) ≥ (λ₁ − ‖(b_y,c_y)‖)/√2 > 5.5·10^27 and n > max(b′,c′)·log10 3 > 2.6·10^27. So every non-anchor candidate
has n ≥ 96D for every D ≤ 10^25: there is no candidate with 96 ≤ n < 192 (or with n < 96) at all; the window
[0, 96D) is always interior and the cut's premise holds at every depth used.

## 4′. The k ≤ 9 cap of `all_representations` (`rt_attack_k10.py` → `rt_attack_k10.log`, `rt_eval_unexamined.py` → `rt_eval_unexamined.log`)

The comment "pattern value = y + k R_96, k ≤ 9 (digit mass < 10^97)" is false: V = R_ν + Σ(d_j−1)10^{e_j} with several
digits in class 95 reaches R_95 + 8k·10^95, i.e. k up to 8|M|+1 multiples of R_96 (V = y + 18R_96 = 2·10^96 + y − 2 is
the typical case: three 7s and a 3 at class 95 give 20·10^95). Scan over all 679 (M, y) anchors of the three files:

```
UNEXAMINED (k=18): s=1411788 M=(2,2,3,7,7,7,7,7,7) y=111132 ;  (k=27): same
UNEXAMINED (k=18): s=111132  M=(2,2,3,3,7,7,7,9) y=13122
UNEXAMINED (k=18): s=236196  M=(3,3,3,3,3,3,4,9,9) y=413343
UNEXAMINED (k=18): s=42336   M=(2,2,3,7,7,8,9) y=111132
UNEXAMINED (k=18): s=148176  M=(2,2,3,4,7,7,7,9) y=13122 ; M=(2,2,2,2,3,7,7,7,9) y=13122 ; M=(2,2,2,2,3,7,7,7,9) y=111132
anchors: 679; V = y + kR_96 (k ≥ 10) passing the digit filter: 6912; representable: 8
```

These 15 representations (enumerated in full by `rt_eval_unexamined.py`) were never run by `deepcut.py`; the five vertices
are among the "closed outright by the deep cut" set of DEEPCUT.md. Running the actual `deep_cut` on them with the
anchors' recorded a: **15/15 CLOSED-cut at depth 1** (expected: their candidates would need digit 1 at position 1, while the
coset pins the last five digits to the anchor's), so no verdict changes — but the certificate was incomplete. The 43
sandwich patterns are unaffected (round 1's §8a scan already covered V < 10^97 for them).

## 4″. Completeness modulo Q over all anchors (`rt_attack_Q_all.py` → `rt_attack_Q_all.log`)

Necessary condition used (proved): V = R_ν + W with W a sum of k single-digit terms has at most 2k digits outside {0,1}
(each term adds ≤ 1 non-zero digit to W; adding R_ν creates a non-{0,1} digit only at a position of W or at the terminal
of a carry chain, and chains start at positions of W). For every anchor, every V = y + mQ ≤ R_95 + 8k·10^95 passing the
filter went through the placement DP: 8949 values, none representable with 189 ∤ m; all 27 recorded 5-field patterns are
of the form y + kR_96, k ≤ 9, with positions < 96. Block structure: mQ consists of repeated 6-digit blocks m·5291 (+carry);
among m < 2000 only m ≡ 0, 21 (mod 189) give a block in {000000, 111111, 999999} (the last absorbed by the carry from y),
which is why the only enumeration gap is the k ≥ 10 one of 4′.

## 5. Baker side (`rt_baker.py` → `rt_baker.log`)

(i) For the 17 (k, a) pairs of the run the certified integers are re-verified (`_certify`, 256-bit intervals) and
Φ(N)/N = 0.9978 for all; at N/10^0.3 the ratio is 1.95, so the fixed point lies within 0.3 orders below N (the bound is
tight to the grid). (ii) G(k,a) ≤ G(k,a′) for a ≤ a′ (0→1→2→3→40, k ∈ {5,8,11}). (iii) 1981 zero-free S-units
2^a 3^b 7^c ∈ [10^3, 10^15], a ≤ 45 — including a-dominant ones such as 2^40·3 (n = 13, a = 40 > 2.1n+2 = 29.3) — pass
`positive_control` (every inequality of Lemmas 3.1–3.2 and Prop. 4.1 with the real Matveev constants); max
B_exact/B_max = 0.996. B_max = 2.1n + 2 + a ≥ a holds identically, so the case "a is the largest coefficient" is covered
by the "+a" term, and the other coefficients satisfy b + 2 < 2.096n + 2, c < 1.184n, n ≤ 2.1n, 1 ≤ n.
Lemma 5.1 re-derived: Φ = Σ α_i T^i, α_i ≥ 0, T = 1 + log(2.1ν + 2 + a); d/dν[T^i/ν] ∝ iνT′ − T with νT′ < 1 and
T ≥ 1 + log ν ≥ i for ν ≥ e^{i−1}; i ≤ k+1 is covered on [e^k, ∞); `_certify` checks N > e^k. The chain itself
(Lemmas 3.1–3.3, Prop. 4.1) was re-read line by line; non-vanishing (numerators ≡ −1 mod 9), the 80·10^{−g} bounds and
the N_j bounds are correct for digits in {2..9}, which is what pattern candidates have (zero-free by definition).

## 6. Floating point and the exactness of `nearest_norm`

The only floats on the certified path are `math.log10` of exact integers (nn, U) and the comparison `bound > logU`
(margins ≥ 10^4.98). `nearest_norm` must return the *minimum* norm over the sub-coset (a lower bound for every
candidate), so missing the true nearest point would be unsound. Proof that the ±2 window is exact for a Lagrange-reduced
basis (‖u₁‖ ≤ ‖u₂‖, |⟨u₁,u₂⟩| ≤ ‖u₁‖²/2, which `_reduce` guarantees up to float-rounding slack in `round(d/n)`):
let t = x_t u₁ + y_t u₂ be the target and v* = x*u₁ + y*u₂ a closest lattice point; ‖u₂*‖² ≥ ¾‖u₂‖², the covering
radius is ≤ ½√(‖u₁‖² + ‖u₂*‖²), so |y* − y_t| ≤ ½√(4/3 + 1) = 0.764 and |y* − round(y_t)| ≤ 1.27 ⇒ |Δy| ≤ 1; for the
chosen y*, the optimal x is round(x_t + (y_t − y*)μ) with |μ| ≤ ½, so |x* − round(x_t)| ≤ 0.5 + 0.38 + 0.5 < 1.4 ⇒
|Δx| ≤ 1. The code searches ±2. Empirically: 3000 skewed reduced bases (‖u₂‖/‖u₁‖ up to 10^4, μ ≈ ±½) agree with an
exact CVP (`rt_nearest_skew.py`); round 1 checked ±6 on every sub-coset of the corrected run.

## 7. `cut_coset` edge cases (`rt_cutcoset_edge.py` → `rt_cutcoset_edge.log`)

For K ∈ {3,4} and every a ∈ 0..K+2 (so a = K−2, K−1, K, K+1, K+2 are all hit) the coset returned by `cut_coset` was
compared with brute force over the exact period 4·5^{K−1}·2^{max(K−a−2,0)} of (b,c), for genuine targets
2^a 3^b 7^c mod 10^K and for random admissible targets, on Z² and on an index-11 coset: 156 cases, 0 mismatches. The
`Kp <= a` branch (word must be ≡ 0 mod 2^K, then only the 5-adic congruence) and the k2 ∈ {1,2} branches are exact.
In `deep_cut` the branch is unreachable (K = 96D > a ≤ 42). Found in passing (7′): a word with L ≡ 0 (mod 5) (digit 5 in
class 0 at copy 0) triggers `assert u % 5` in `log3_mod5k` — `deep_cut` raises instead of marking the case dead. Loud.

## 8. Other checks

- All equations with exceptional/open records ended at level 96 (runall_final: 27/27 records; trees_c: 83/83 equations;
  trees_mac: 299/299), so Λ_96 is the right lattice everywhere.
- For every anchor y of the 43, `v2(y) == a` (table in the session log); the deep-cut coset (b_y,c_y)+Λ_96 is the full
  solution coset C_V of the level-96 congruences, a superset of the engine's (possibly descent-cut) coset: conservative.
- Candidates are zero-free with exactly |M| non-1 digits by definition of the pattern, matching Theorem U's domain and k.
- Repeated-structure audit of the other containers: `all_representations`' `tried` set (dedup by digit values) is
  correct because equal digit values give equal remainders; `classify.canon`/`pattern_iter` are multiset-correct;
  `descent.descend` consumes by index. The only collapses found are 2′ (driver `seen`) and the former `deep_cut` dict.

## Reproduce (from `/home/claude/tier0`, each a single process)

```
python3 /home/claude/redteam/rt_seen_collapse.py          # 2′  (1 min)
nice python3 /home/claude/redteam/rt_attack_Q_all.py       # 4″  (18 min)  -> rt_attack_Q_all.log
nice python3 /home/claude/redteam/rt_attack_k10.py         # 4′  (15 min)  -> rt_attack_k10.log
nice python3 /home/claude/redteam/rt_eval_unexamined.py    # 4′  (1 min)   -> rt_eval_unexamined.log
nice python3 /home/claude/redteam/rt_plant10adic.py        # 1a  (~15 min) -> rt_plant10adic.log  (SKIP_AC=1 for D/E only)
nice python3 /home/claude/redteam/rt_small_lattice.py      # 1b  (1 min)
nice python3 /home/claude/redteam/rt_cutcoset_edge.py      # 7   (3 min)
nice python3 /home/claude/redteam/rt_nearest_skew.py       # 6   (1 min)
nice python3 /home/claude/redteam/rt_baker.py              # 5   (2 min)
python3 /home/claude/redteam/rt_attack_Q.py                # 4″ on the 43 only (5 min) -> rt_attack_Q.log
```

---
---

# Appendix: round-1 report (earlier agent, unchanged)

# Red team: the Baker–lattice sandwich (SANDWICH.md / deepcut.py / baker_chain.py)

*2026-10-20, red-team agent. Goal: make the sandwich wrongly CLOSE a pattern, or find a logical gap.
Everything here runs from `/home/claude/tier0` (classify_open opens a relative file) and writes only
under `/home/claude/redteam`. Inputs used: the 43 patterns of `SANDWICH-run.txt`
(`/tmp/survivors3.txt` over `/tmp/trees_mac_0545.jsonl`). All runs are single-process, each a few minutes
except the fixed-enumeration re-run (background, niced; logs in this directory).*

## Summary of verdicts

| # | Attack | Verdict |
|---|--------|---------|
| 1 | Planted genuine S-units (40 real 200–400-digit y″, each followed through the code's own bookkeeping) | **BROKEN (code)** — `deep_cut`'s copy-choice enumeration is incomplete whenever a representation contains the same (d, e) pair twice: the original bookkeeping loses **40/40** planted points at depth 2; the index-keyed re-implementation keeps **40/40** to the maximum depth their size allows. 57 of the 88 representations behind the 43 CLOSED patterns have repeated (d, e); their depth ≥ 2 case lists were incomplete (worst case 585 of 1152 required cases missing). **Verdicts survive the corrected re-run** (see §1: 43/43 still CLOSED, 10 bounds changed, min margin 10^5.3 → 10^4.98). |
| 2 | Wrong k (M with one digit fewer / more than the anchor uses) | **WEAKNESS (medium)** — no representation is found and the pattern is reported **CLOSED with an empty verdict list** (vacuous `allclosed = True`, same in `deepcut.py`). Did not fire in the real runs (no `reps=0` line), but it is a silent failure mode. |
| 3 | Wrong a / huge a | **WEAKNESS (medium/low)** — `sandwich.py` has no `fct[0] == a` assertion (deepcut.py has one): a record with a wrong a is silently closed with the wrong coset (demonstrated). The `Kp <= a` branch of `cut_coset` is correct for a ≥ K, but `deep_cut`'s pre-check `v2(L) != a` is wrong for a ≥ 96 (would skip the true case); unreachable here (a ≤ two_adic_bound(M) ≤ 42 over the 43 patterns). |
| 4 | Λ_96 coset bound, "n ≥ 192 except the anchor", nearest point | **SURVIVED** — 10^96 − 1 fully factored (20 level primes), basis exactly Lagrange-reduced (λ₁ = 7.8502·10^27), every anchor is the exact nearest point of its coset, every other coset point has ≥ 2.648·10^27 digits; a candidate with n < 192 would need |(b, c)| ≤ 402: impossible. `nearest_norm` (Babai ± 2) agrees with brute force on 3000 random reduced lattices and with a ± 6 search on every sub-coset of the re-run. |
| 5 | Copy-choice enumeration vs. the required case set (digit at the top, class = ν, …) | **SURVIVED after the fix** — nothing is wrongly *excluded* by position (n ≥ 10^27 ≫ 96D, so no position constraint applies and the top digit n − 1 is never inside the window); the only defect is the *omission* of attack 1. The index-keyed enumeration equals the required set on all 88 representations × depths 1–3 (0 differences); the original differs on 81 (rep, depth) pairs. |
| 6 | Baker chain: monotonicity, B, controls | **SURVIVED** — Φ(ν)/ν decreasing on [e^k, ∞) confirmed on 400-point log grids for k ∈ 0..12, 20, 31 and a ∈ {0,1,3,40} (increases exist only below e^k, as the lemma allows); 17 certificates (k, a) of the run re-verified in interval arithmetic; exact B = max(a, b+2, c, n, 1) ≤ 2.1n + 2 + a (max ratio 0.94 on 200 random S-units); **7677 in-domain positive controls** (every zero-free S-unit with 10–60 digits, k up to 57) pass every asserted chain inequality. |
| 7 | Floating point in certified comparisons | **SURVIVED** — only `math.log10` of exact integers enters the final comparison (abs. error ~10^−13 on values ~200); smallest margin after the fix is 10^4.98 digits. `_reduce`'s float rounding cannot produce a wrong lattice (unimodular ops) and exact reducedness was asserted for every sub-coset basis. |
| 8a | Is the engine's pattern among the representations the sandwich closes? (Mac files record only (a, y)) | **SURVIVED for the 43, with a caveat** — the sandwich closes the representations V = y + kR_96 (k ≤ 9) of the anchor, but the engine only guarantees V ≡ y (mod P), P = (10^96−1)/189 (the level primes exclude 3 and 7). Exhaustive scan of all m < 18900 with V = y + mP: for every (M, y) of the 43 patterns, every V of the required digit shape is in the code's list (all at k = 0). The hypothesis is verified here, not by the pipeline; (ν, e_j) should be recorded in the sweep files. |
| 8b | Vacuous CLOSED in `deepcut.py` main (same as 2) | WEAKNESS (medium) — not triggered in `DEEPCUT-run*.txt` (no `reps=0`). |

**Bottom line.** No pattern is wrongly closed *in the end*: after replacing the enumeration, 43/43 (pending the
last k ≥ 10 patterns, see §1.4) are still CLOSED by the sandwich at the same depths, with the minimum margin
reduced from 10^5.3 to 10^4.98 digits. But the certificate as produced by `deepcut.deep_cut` is unsound for
any representation with a repeated (d, e) pair (57 of the 88 representations), because at depth ≥ 2 it
silently drops every case in which two equal digits of one class both sit below 96D. The fix is one line
of bookkeeping (key `fixed`/`free` by index, not by (d, e)); `fixed_deepcut.py` is a drop-in with exact
self-checks.

---

## 1. Attack 1 — planted genuine solutions (BROKEN in the code, verdicts survive)

### 1.1 The defect

`deepcut.deep_cut` tracks which digits are already placed with `fixed = dict(((d, e), t) for d, e, t in
assigned)` and `free = [(d, e) for d, e in De if (d, e) not in fixed]`. If the representation contains the
pair (d, e) twice (e.g. two 2s in class 5, which is common: a 7 at a position can be represented as two 4s
there, and the CARRY anchors produce exactly this), then once one copy is fixed at copy t the other is
never free again: it is implicitly "above every depth". The cases {e, e+96}, {e, e+192}, {e+96, e+192}, …
for the two equal digits are never generated.

`a0_dup_enum.py` copies the enumeration loop verbatim (lattice cut replaced by pass-through) and compares
the set of words L mod 10^{96D} with the required set (all copy assignments with distinct positions):

```
two equal digits one class   depth 2: deep_cut generates 3 distinct L; required 4; MISSING 1   -> [(2,5),(2,101)]
28672 M=78888 rep            depth 2: generates 81; required 108; MISSING 27;  depth 3: 256 vs 448, MISSING 192
two different digits one class: no difference at any depth (the bug needs equal (d, e))
```

`a0_reps_dups.py`: of the 88 representations evaluated for the 43 CLOSED patterns, **57 contain a repeated
(d, e)** (e.g. `s=28672 M=22222222278 … (2,7)×3, (2,8)×3, (2,5)×2`).
`a5_enum_complete.py`: against the required set, the original enumeration is wrong on **81 (representation,
depth) pairs**, worst `s=28672 M=22222222278 depth 2: 585 of 1152 required cases missing`; the index-keyed
enumeration (`fixed_deepcut.py`) differs on 0.

### 1.2 Planted real S-units (`a1_planted.py 7 40`)

Full enumeration is impossible for a real 300-digit S-unit (k ≈ 0.9n), so the TRUE copy assignment is
followed through the code's own bookkeeping at each depth (the truth must be one of the enumerated cases):

```
y = 2^2 3^154 7^202: n = 245, k = 226, repeated (d,e) below 384: 23
   orig : the code's word differs from y mod 10^192 at D=2; digits it cannot place: [(4, 96), (8, 107), ...]
          (that wrong word: survives the cut; either way the planted point is lost)
   -> original bookkeeping keeps the point up to depth 1, index bookkeeping up to depth 2
40 planted S-units: (depth reached by ORIGINAL, depth reached by INDEX) -> (1,2): 13  (1,3): 19  (1,4): 8
```

Every genuine S-unit is lost by the original bookkeeping at depth 2 (a real number always has repeated
(d, e) pairs below 192); the index bookkeeping keeps all 40 up to ⌊n/96⌋ (the depth the cut's premise
n ≥ 96D allows). Note the dropped-digit word *survives* the cut: consistent with the blind audit's
"depth 2 never kills", so the missing cases are not killed either — they produce *additional sub-cosets*
with their own (slightly different) bounds, which the original never evaluated.

### 1.3 Corrected re-run (`a0_sandwich_fixed.py`, logs `a0_sandwich_fixed_k9.log`, `a0_sandwich_fixed_k10plus.log`, table by `a0_compare.py`)

Same pipeline as `sandwich.py` with `deep_cut_fixed` (index-keyed; identical words merged, which is exact
since the sub-coset is a function of L alone; plus two exact self-checks on every surviving sub-coset:
the basis is Lagrange-reduced and the ± 2 nearest point equals a ± 6 search):

```
pattern                                   k  log10U | orig D orig bound | fixed D fixed bound | margin(fixed)
28672 78888 2 1411788                     5   105.9 |      2     120.03 |       2      119.99 | 14.09  (bound changed)
28672 2244788 0 78121827                  7   128.5 |      3     167.96 |       3      167.63 | 39.13  (bound changed)
8192 2244448 0 330812181                  7   128.5 |      3     168.09 |       3      168.06 | 39.56  (bound changed)
14336 22224478 0 330812181                8   145.3 |      3     167.99 |       3      167.93 | 22.63  (bound changed)
18144 22333467 0 60761421                 8   145.3 |      3     167.53 |       3      167.16 | 21.86  (bound changed)
42336 22234779 3 1134213192               8   161.7 |      3     167.79 |       3      167.47 |  5.77  (bound changed)
8192 22222488 0 330812181                 8   145.3 |      3     167.83 |       3      167.18 | 21.88  (bound changed)
14336 222222478 0 330812181               9   162.2 |      3     167.87 |       3      167.18 |  4.98  (bound changed)   <- new minimum margin
18144 222333347 1 44471322                9   180.3 |      4     215.95 |       4      215.77 | 35.47  (bound changed)
28672 222224478 0 330812181               9   162.2 |      3     167.99 |       3      167.61 |  5.41  (bound changed)
(26 further patterns: identical depth and bound)
```

k ≤ 9: **36 of 36 CLOSED**, same depths; 10 bounds moved down by up to 0.7 orders of magnitude; the
minimum margin is now 10^4.98 (was 10^5.3). k ≥ 10 (7 patterns): see §1.4.

### 1.4 Status of the k ≥ 10 patterns

RE-RUN-STATUS-PLACEHOLDER

### 1.5 Why the verdicts survive (and when they would not)

The dropped cases are depth ≥ 2 extensions of depth-1 survivors; by the blind audit's structural fact
(the depth-1 sublattice maps onto the kernel of G_192 → G_96) they always survive and give sub-cosets of
the same index, hence bounds of the same order (10^120 at D = 2, 10^168 at D = 3, …). The margins
(≥ 10^4.98) absorb the resulting variation (≤ 0.7 orders). A pattern with margin < ~1 order could flip;
none of the 43 is in that regime. Synthetic lattice test: the planted-point check of §1.2 is exactly the
lattice test the brief asks for (true congruences of a real point against Λ_96), done on real points
instead of a small-index lattice, which avoids an unrealistic pattern.

Reproduce: `cd /home/claude/tier0 && python3 /home/claude/redteam/a0_dup_enum.py && python3
/home/claude/redteam/a1_planted.py 7 40 && python3 /home/claude/redteam/a5_enum_complete.py && nice python3
/home/claude/redteam/a0_sandwich_fixed.py 9 && python3 /home/claude/redteam/a0_compare.py`.

## 2. Attack 2 — wrong k (`a23_wrong_record.py`)

The loop body of `sandwich.py` was copied verbatim and fed modified records of the genuine pattern
`s=14336 M=227888 a=0 y=78121827` (control: CLOSED-sandwich at D = 2, bound 10^120.09 > 10^111.70):

```
M = (2,7,8,8,8)   (one '2' dropped) -> ('CLOSED', k=5, log10U=94.98, reps=0, [])
M = (2,2,7,8,8,8,8) (one '8' added) -> ('CLOSED', k=7, log10U=128.49, reps=0, [])
```

`all_representations` finds nothing (the anchor identity needs exactly M's digits), `reps` is empty,
the `for` loop never runs, `allclosed` stays `True` and the pattern is counted **CLOSED with an empty
verdict**. The same vacuous path exists in `deepcut.py` (`closed_all = True` before the loop). It did
not fire in any real run (`grep -c "reps=0 " SANDWICH-run.txt DEEPCUT-run*.txt` → 0), but a malformed
sweep record would be "closed" silently. Fix: `assert reps`. (A wrong recorded (ν, eps) that matches no
representation falls back to *all* representations — conservative, fine.)

## 3. Attack 3 — wrong a, huge a (`a23_wrong_record.py`)

- Record `a = 1` for the anchor 78121827 = 3^13·7^2 (a = 0): `sandwich.py` runs and reports
  `('CLOSED', …, [('CLOSED-cut', 1, 64)])` — a bogus closure with the anchor's (b, c) but the wrong a
  (wrong coset, wrong 2-adic cut). `deepcut.py` asserts `fct[0] == a`; `sandwich.py` does not. An anchor
  that is not an S-unit crashes (`TypeError`), which is at least loud.
- a ≥ K: `cut_coset(co, 200, L, 96)` with L = (2^200·3^123·7^77) mod 10^96 keeps the true point (the
  `Kp <= a` branch requires only L ≡ 0 mod 2^96 and then the 5-adic congruence with 2^{−a}: correct).
  But `deep_cut` pre-filters with `if v2(L) != a: continue`; here v2(L) = 96 ≠ 200, so the true case
  would be skipped — a false kill for a ≥ 96. Unreachable: the engine caps a at `two_adic_bound(M)`,
  which is ≤ 42 over the 43 patterns' multisets (`a4_lattice.py`), and for a < 96D the pre-check is
  exact (y′ = L + 10^{96D} m ⇒ v2(y′) = v2(L)). Latent only.

## 4. Attack 4 — the Λ_96 premise (`a4_lattice.py`)

```
(i)   10^96-1 fully factored; 20 primes other than 2,3,5,7 used (3 appears as 3^3, 7 once; no other repeated prime)
(ii)  Λ_96 basis exactly Lagrange-reduced: λ1 = 7.8502e+27 (= |u1|, exact integer norm), index 2.8100e+56
(iii) 17 anchors: each is the exact nearest point of its coset; every other coset point has ≥ 2.648e+27 digits
(iv)  nearest_norm vs brute force (±40 window) on 3000 random reduced lattices/cosets: 0 mismatches
(v)   a candidate with n < 192 digits needs |(b,c)| ≤ 402; non-anchor coset points have |.| ≥ 7.85e27: impossible
```

Two distinct coset points differ by a non-zero lattice vector, of norm ≥ λ₁ (exact, from the reduced
basis); so a second point within the n < 192 region (|(b, c)| ≤ 192·log 10/log 3 ≈ 402) would be within
402 + 30 of the anchor, far below λ₁. The depth-2 premise n ≥ 192 holds for every non-anchor point.
The `_reduce` routine rounds `d / n` in floating point; a wrong rounding would only leave a
not-quite-reduced basis, and exact reducedness was asserted for Λ_96 and for every sub-coset basis in
the re-run (it never failed). The ± 2 neighbourhood is more than enough for a reduced 2-D basis (± 1
suffices); verified by brute force and by the ± 6 cross-check.

## 5. Attack 5 — the copy-choice enumeration (`a5_enum_complete.py`, `a0_dup_enum.py`)

Required case set at depth D: every assignment t_j ∈ {0, …, D−1} ∪ {≥ D} with distinct positions
e_j + 96 t_j. No constraint from n or ν applies: n ≥ 2.6·10^27 ≫ 96D, so every window position is an
interior digit, a pattern digit may sit at the top position n − 1 (it is then the leading digit, n
unchanged) and a class e_j = ν is nothing special (ν + 96t < n for t < m). The code imposes no such
constraint, so nothing is wrongly excluded; the only defect is the omission of attack 1. With the
index-keyed enumeration the generated set equals the required set on all 88 representations × depths
1–3 (depth 3 skipped for k ≥ 9 where the 4^k reference enumeration is too large).

## 6. Attack 6 — the Baker chain (`a6_baker.py`)

```
(a) 7677 zero-free S-units with 10..60 digits (k up to 57) pass every asserted chain inequality (in-domain)
(b) Phi(nu)/nu on 400-point log grids over [e^k, 10^(log10 G + 50)], k in 0..12,20,31, a in 0,1,3,40: no increase
    (k=11, a=0: Phi/nu increases only for log10 nu <= 4.4, below log10 e^k = 4.78: as the lemma allows)
(c) 17 (k, a) pairs of the run: certificate re-verified (N > e^k, Phi(N) < N in iv arithmetic); float log10 N within 1e-9
(d) exact Matveev B = max(a, b+2, c, n, 1) vs 2.1 n + 2 + a on 200 random S-units: max ratio 0.9377
```

Lemma 5.1's proof is checked by hand: d/dν[T^i/ν] has the sign of iνT′ − T with νT′ < 1 and T ≥ 1 + log ν ≥ i
for ν ≥ e^{i−1}; all i ≤ k + 1 are covered on [e^k, ∞), and `_certify` checks N > e^k. I could not
construct a (k, a) where the monotonicity assumption fails where the code relies on it. The B bound is
sound (b + 2 < 2.096n + 2, c < 1.184n, exponent of N_j is 1 ≤ n). Non-vanishing of the forms and the
digit hypothesis d_j ∈ {2, …, 9} match the patterns' candidates (zero-free by definition of the sweep).

## 7. Attack 7 — floating point (`grep`, `a6_baker.py (c)`, re-run self-checks)

Floats in the certified path: `digits_bound` = 0.5·log10(nn) − 0.5·log10 2 + log10(log10 3) with nn an
exact integer; `logU = math.log10(U)` with U the certified exact integer; the comparison `bound > logU`.
Absolute error of `math.log10` on an int is ~10^−13 at these magnitudes; the smallest margin in the
corrected run is 10^4.98 digits (4.98 in log10), i.e. a relative margin of ~2 %, 11 orders above the
float error. No margin anywhere near 10^−12 relative. Interval re-verification of log10 U agrees to 10^−9.
`_reduce`'s float `round(d / n)` and `math.hypot` in `shortest()` (display only) do not enter the bound.

## 8. Other attacks

**8a. Is the engine's pattern among the representations closed?** (`a8_identity.py`) The Mac sweep file
records only (a, y) for each open pattern (`[[0, 7411887, False]]`), so `sandwich.py` closes every
representation V = y + kR_96 = R_ν + Σ(d_j − 1)10^{e_j}, e_j < 96, k ≤ 9. What the lattice actually
guarantees is only V ≡ y (mod P) with P = Π level primes = (10^96 − 1)/189: the primes 3 and 7 are not in
the lattice. Any V of the required digit shape with V ≡ y (mod P) must be found; V < 10^97 so V = y + mP
with m < 18900. Exhaustive scan over m (filter: digits ∉ {0, 1} ≤ 2k + 2, which is a proven necessary
condition; then the full placement DP) for all 43 (M, y): **every admissible V is in the code's list, all
at k = 0**. The only near-repunit m are m = 21 + 189j (i.e. k = 1 + 9j) and none of them admits a
representation. So the hypothesis holds for these 43 patterns; it is not enforced by the pipeline (the
sweep should record (ν, e_j), and the sandwich should check that the recorded pattern is in the list
rather than silently taking all representations).

**8b. Lower-bound side, other checks (by reading).** digits ≥ max(b, c)·log10 3 ≥ ‖(b, c)‖/√2·log10 3 holds
for b, c ≥ 0 and the nearest-point norm is over all coset points (including negative ones), so the bound
is valid. Using Λ_96 instead of the engine's (possibly further cut) coset is a superset: conservative.
`cut_coset`'s 5-adic (3 is a primitive root mod 5^k) and 2-adic ((−1)^s 5^t) decompositions are correct
and Lean-checked per DEEPCUT.md; `k2 == 1` returns the coset unchanged (conservative). The `BUDGET`
outcome is reported as not closed (conservative). The vacuous-close path of attack 2 is the only
non-conservative control-flow defect found.

## Files

- `a0_reps_dups.py` — list representations of the 43 patterns and flag repeated (d, e) (57 of 88).
- `a0_dup_enum.py` — verbatim copy of the enumeration vs the required set (shows the missing cases).
- `fixed_deepcut.py` — index-keyed `deep_cut_fixed` with exact self-checks.
- `a0_rerun.py`, `a0_sandwich_fixed.py`, `a0_compare.py` — side-by-side and full corrected re-run; logs `a0_sandwich_fixed_k9.log`, `a0_sandwich_fixed_k10plus.log`.
- `a1_planted.py` — planted genuine S-units through both bookkeepings (`a1_planted.log`).
- `a23_wrong_record.py` — wrong k / wrong a / huge a (`a23_wrong_record.log`).
- `a4_lattice.py` — Λ_96 facts, nearest point (`a4_lattice.log`).
- `a5_enum_complete.py` — enumeration completeness on all representations (`a5_enum_complete.log`).
- `a6_baker.py` — Baker chain checks (`a6_baker.log`).
- `a8_identity.py` — representation completeness mod the level primes (`a8_identity.log`).
