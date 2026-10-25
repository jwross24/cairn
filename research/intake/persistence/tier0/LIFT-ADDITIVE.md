# The additive lift 12 → 24: the level-24 kill is a subset-sum congruence once the exponent coset is used

*2026-10-21 20:20 EDT, chat session. Code `addlift.py` (self-test built in). Answers Cairn's 2026-10-20 16:10 question
("can level-24 children be tested or pruned without materializing ~5×10² per level-12 survivor … applying Lemma
C-style constraints before the lift?") with a validated prototype. Calibration: the mechanism is exact (every child
list below was checked against brute force, 120/120 patterns); the cost figures are projections against the cost
model's unit costs and need Cairn's measurement on the 228 gated equations.*

## 1. Mechanism (same as the shadow certificate, one level down)

A level-12 survivor fixes, for each admissible exponent a ≡ a_0 (mod 12), the coset C_a = v_a + Λ_12 of (b, c)
(Λ_12 = kernel of 3^b7^c at 11, 13, 37, 101, 9901; index 8.9×10^6, content 900 = 2²3²5²). A level-24 child has
value V' = V + (10^12 − 1)·Δ with Δ(S, sn) = Σ_{j∈S}(d_j − 1)10^{e_j} + sn·10^ν/9 — additive in the 2^(q+1) shift
bits. It passes a new prime p ∈ {73, 137, 99990001} iff V'/2^a ∈ x_p·H_p, where H_p is the image of Λ_12 in (Z/p)^*
and x_p the coset's class: measured image indices 36, 4 (8 after the 10-adic cut), 900 (4500 after the cut) — so
|H_p| = 2, 34→17, 111100→22220. Hence **a child passes p iff Δ ≡ (2^a x_p h − V)/(10^12 − 1) (mod p) for some
h ∈ H_p**: an allowed residue set of size |H_p|. For p = 73, 137 that is ≤ 34 residues modulo 10001 — a subset-sum
DP over Z/10001 across the q digits (plus the ν-shift term) lists every child passing both primes without
touching the other 2^(q+1). The three primes are NOT independent (they are tied through the coset), so the
per-prime sets are necessary conditions only: the DP is a prefilter and each candidate gets the exact sequential
coset intersection (`child_passes`, three discrete logs) as the verdict.

## 2. Validation

`python3 addlift.py --max 60 --seed 3` and `--seed 11`: 120 real level-12 survivors (anchored level-96 records of
trees_mac_1250.jsonl reduced mod 12, k = 6–12, a as recorded), DP child set == brute force over all 2^(q+1) children
on **120/120**. Two bugs found by the self-test and fixed on the way (independent per-prime final test → exact
sequential test; the V ≡ 0 (mod p) case handled by the coset-class formula instead of u = (10^12−1)/V). Measured
on 320,000 children: candidates after the 10001-DP are 1/115–1/123 of the children (independence would say
1/147: mild positive correlation), survivors after the exact test 1/2300–1/3100 — on anchored parents exactly one
child each, the shadow.

## 3. Cost per level-12 survivor (projection; unit costs from the 16:10 cost model)

| q | children 2^(q+1) | now: 6.1 µs/child | join24 (×9) | additive: DP 6×10001×(q+1) + 6×2^(q+1)/115 exact tests (~2 µs in C) |
|---|---|---|---|---|
| 13 | 16,384 | 100 ms | 11 ms | ≈ 1 ms + 1.7 ms ≈ **3 ms** |
| 18 | 524,288 | 3.2 s | 0.36 s | ≈ 1 ms + 55 ms ≈ **56 ms** |
| 22 | 8.4×10^6 | 51 s | 5.7 s | ≈ 0.9 s |
| 29 | 1.07×10^9 | 6500 s | 720 s | ≈ 110 s |

(The factor 6 is the admissible a values a ≡ a_0 mod 12, a ≤ A ≈ 64; one DP with the union of the six allowed sets
does the same.) For q ≥ 24 a bitset DP over Z/99990001 (12.5 MB per layer, ≈ 20 ms for the layers) lists the
children passing the strongest prime directly, ≈ 2^(q+1)/4500 of them, which the small primes then cut: ≈ 30 ms
at q = 29 against 720 s — but at Tier A's q ≈ 13 the small DP is the right tool.

**Tier A:** ≈ 3×10^14 level-24 children ≈ 2×10^10 parents; at ≈ 3 ms each ≈ 6×10^7 s ≈ 700 core-days → ≈ 70
days on the Mac's 10 cores — against ≈ 2×10^9 s now. A ×30 on the critical path, on top of nothing else.
**Tier B:** ≈ 2×10^15 parents × ≥ 1 ms = 6×10^4 years. The additive lift does not change the verdict on Tier B;
it changes Tier A from "months, maybe" to "weeks, surely" if the projection holds.

## 4. What Cairn should do with it

1. Measure, not project: run `addlift.py`'s mechanism on the 228 gated level-24 equations (the C port needs: the
   level-12 coset per (survivor, a) — five discrete logs at smooth primes, table-driven; the DP; the exact test on
   candidates). Gate = byte-identical level-24 survivor sets vs the production binary, two mutants (drop a residue
   from an allowed set; use the independent test as the verdict) caught, timing on one core.
2. The same mechanism at 24 → 48 (new primes 17, 5882353, 9999999900000001; image indices of Λ_12 there: 4, 48,
   900 — of the level-24 coset: larger) and 48 → 96, where the children counts are smaller and the images smaller.
3. Combine with the 10-adic cut (Lemma C at K = 12, the descent's K* = 3 pinned digits) BEFORE the lift only if the
   number of words stays small; on the data above the cut raised the 137 and 99990001 indices by 2 and 5.

## 5. The same measurement at 24 → 48 and 48 → 96 (exact; kernels of the full prime sets)

Λ_24: index 3.4×10^13, content 2³·3²·5²·11. New primes of level 48 and the image of Λ_24 there: 17 → |H| = 2 (index 8);
5882353 → |H| = 122549 (index 48); 9999999900000001 → |H| = 2.5×10^11 (index 39600). So the 24 → 48 lift has a weak
additive prefilter (mod 17, 1/8) and two exact tests; its cost per level-24 parent ≈ 2^(q+1)/8 exact tests.

Λ_48: index 2.1×10^30, content 2⁴·3²·5⁴·11·101. New primes of level 96 and the image of Λ_48: **97 → |H| = 1
(trivial), 353 → 2, 641 → 8, 1409 → 8, 449 → 28, 69857 → 4366, 206209 → 179, 66554101249 → 3.5×10^8,
75118313082913 → 7.1×10^10.** So at 48 → 96 a DP over Z/(97·353) = 34241 states with 2 allowed residues lists
the children passing both (1/17000 of them), 641 and 1409 cut another ×14000 by two modexps each, and the four
large primes see ≈ 2^(q+1)·4×10^-9 candidates (≈ 4 at q = 29, 0 at q ≤ 22). The 48 → 96 lift is essentially free
with the additive structure; its cost today is 78 µs per child.

**Where the wall is, with numbers.** The additive lifts make every level after 12 cheap per parent (≥ ×30 at 12 → 24,
≈ ×10^4 at 48 → 96). What they cannot change is the number of level-12 parents: ≈ 4×10^-4–5×10^-3 of all level-12
patterns (rates.json, k = 13 → 29). Tier B has ≈ 2×10^15 of them; at the ≈ 1 ms floor of the 12 → 24 DP that is
≈ 6×10^4 core-years. The only ways past are a first level with a larger index than level 12 (but L^k patterns grow
faster than the index: level 48 has ×4^k patterns for ×2.4×10^9 index, a loss for every k ≥ 16) or a method that
does not list level-12 survivors at all, which the dpcount scout showed does not exist for the multiplicative test.
This is the Tier-B obstruction, stated as a measurement rather than a cost estimate; Lane 2's remaining job is to
confirm the per-parent floor on the 228 gated equations and to port the three additive lifts for Tier A.

## 6. X17 — the sweep's actual situation: a known only mod 12 (22:15 EDT)

At level 12 the engine knows a modulo 12 and tests every admissible a ≡ a₀ (mod 12), a ≤ A. One DP serves all of
them: the allowed residue sets of the ≈ 6 admissible a's are unioned (204 of 10001 residues), the reachability DP
runs once, and each candidate (S, sn) is tested exactly only for the a's whose own set contains its residue. On 15
real level-12 survivors with A = 64 (5–6 admissible a each): DP survivor set == brute force over all (a, child) pairs
15/15; candidates 729 of 197,632 (a, child) pairs (1/271) — i.e. the a-freedom costs nothing extra in the DP and the
exact-test count stays ≈ 2^{q+1}/50 per parent. This is the form to port.
