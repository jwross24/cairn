# Sprint: fresh attacks on Tier B and Tier C (opened 2026-10-23 16:30 EDT by chat; owner of the ledger decides)

*Calibration: this file states the problem exactly, lists what is known to fail and why, and registers directions with
a decisive test each. Nothing here is a result. RULE 2 applies: no label changes without evidence; Conjecture Z is not
a target.*

## 1. The problem, exactly

- Tier B: 13 vertices, 4.0×10^17 level-12 patterns, k = 20–29. Tier C: 6 vertices, 2.9×10^22 patterns, k = 31–44
  (FRONTIER.md). Generic survival at level 12 is 1/49.5 (dpcount, exact Monte Carlo); the 12 → 24 lift (2^{k+1}
  children per survivor, DP-filtered to ≈ 1/115 exact tests) is the wall: ≈ 8×10^15 Tier-B parents × ≥ 1 ms.
- The predicted open set at level 96 is the anchored set: ~10^5 anchor pairs (y, w) per vertex carrying 10^11–10^14
  patterns (RESULT-anchorfirst.md), and 679/679 recorded open level-96 patterns are anchored. The sandwich/shadow
  certificate closes any single pattern in seconds (Cairn: k = 31 in 32 s at level 480), so Tier B's anchored open
  set (~4×10^9 patterns) is ~days in C — *if* "every level-96 survivor is anchored" were a theorem. It is not: an
  unanchored survivor is an accident with expected count patterns × ~10^-38 per level-96 pattern, i.e. ~10^2 over
  Tier B/C; nothing finds them except the enumeration.
- What X20 adds (HSHADOW.md §8): for an anchored pattern the modular side is witnessed by the anchor at every
  level; everything that kills is (i) the 2,5-adic window, whose verdict depends only on the digits in the classes
  e < a + 15 (2-adic) and e < 7 (5-adic), and (ii) at trivial-image primes, the additive condition Δ ≡ −w/9 on the
  digits moved out of the shadow. The digits at high classes are invisible to the window and enter only through Δ
  (additive) or through coset tests at nontrivial primes (random, 1/index each).

## 2. What is known to fail, and the exact reason (do not retry without a new mechanism)

- Bulk kills at level 12 (character sums, MITM on digits, s-vector/class-sum collapse): the level-12 condition is
  V·2^{−a} ∈ ⟨3,7⟩ mod m₁₂ — a *multiplicative* condition on an *additive* fold; the parent's class at the next level
  (the image x_p of its coset at the new primes) is a multiplicative function of V mod m₁₂ and cannot be tracked by an
  additive DP over digit placements. The s-vector (class-sum) collapse is unsound for the lift: splits of a class
  sum are not realizable by single digits. X1: no first level other than 12 reduces the total.
- Per-anchor closure by additive filters: for an anchor (y, w, ν) the union over its patterns and children of Δ is a
  digit box {Σ σ_e 10^e : 0 ≤ σ_e ≤ v_e} of size up to 10^22 (10^30 at ×10 copies); the trivial-prime product is
  1.5×10^5 (192), 1.8×10^23 (192 ∧ 480); candidates after the filter ≈ box / product — not ≤ 1 once copies multiply.
  Character-sum counting cannot certify (main term < 1 needs error o(1); square-root cancellation gives 10^11).
- The window at any depth is blind to classes ≥ a + 15 ("depth 2 never kills"); Lemma C cannot be pushed.
- Literature (SURVEY-2026-10-21.md, LIT2.md): every complete resolution of a many-term exponential equation pays
  exponentially per term; no effective bound better than (C log n)^k; Skolem-type local–global is open for 3 terms.

## 3. Directions registered (each with its decisive test; tag [chat]/[Cairn]/[Codex]/[agent])

D1 [chat, agent] **Per-anchor exact closure as a bounded-digit congruence.** For a wrap-w anchor, a level-L child of
any of its patterns is a vector σ (digit sub-sums per class and copy) and passes the trivial primes iff a *linear*
form in σ ≡ −w/9 (mod P_T). This is a bounded-knapsack in base 10 with a modulus; with P_T larger than the box the
solution is unique and testable in O(1), with P_T smaller the count is box/P_T. Test: on one real Tier-C anchor from
hits_v*_sample3000_7.txt (smallest pattern count), compute the exact number of (pattern, child) pairs surviving the
192 trivial primes by a dense DP (state: class, carry, remaining digit counts, residue mod 148417), then the fraction
surviving each further prime (19841, 976193, 6187457 by image-coset sets) and the window — measure the accident
ladder at Tier C exactly where enumeration is impossible. Decides whether any additive route can reach ≤ 1 candidate
per anchor at a usable level. Prediction (chat): counts follow box/148417 and 1/index per nontrivial prime within ×2;
the ladder does not reach < 1 before copies multiply the box faster than the primes.

D2 [agent, Cairn] **The anchoring hypothesis as a theorem for a class.** A level-96 survivor is a coset of Λ_96
(index 2.8×10^56) consistent with the 10-adic pinning K*. Question: is there a *covering-radius / lattice* argument
that a coset passing the level-96 sieve *and* the pinning to K* digits must contain a point of ≤ 96 digits, for
patterns whose digit mass is bounded (W = Σ(d−1) ≤ 126)? If the answer is "no in general but yes with probability
1 − 10^-38", the hypothesis stays empirical and Tier B needs the enumeration. Test: compute, for the recorded 679
open level-96 patterns, the ratio (anchor norm)/(covering radius of the pinned sublattice); a theorem would need a
structural gap. Literature agent: "small solutions of congruences in cosets of lattices / Minkowski with digit
constraints / Bombieri–Vaaler".

D3 [agent] **The multiplicative–additive mismatch as the research question.** Sums Σ s_i ζ^i (ζ = 10 of order d | L
mod p) landing in a multiplicative subgroup H ⊂ F_p^×: is there any structure beyond equidistribution when the s_i
are bounded (sum-product in subgroups, Bourgain–Glibichuk–Konyagin, Heath-Brown–Konyagin on digit sums; Gauss sums
of cyclotomic classes)? If a nontrivial *deterministic* obstruction existed for small digit masses, it would be a bulk
level-12 kill. Expected answer: no (equidistribution is the theorem), but the agent should find the sharpest known
statement and any case with structure (e.g. d = 2: V mod 11 = S_0 − S_1, the alternating digit sum).

D4 [Cairn] **Cost model of an enumeration that avoids the lift's exact tests.** Given D1's measured ladder, re-fit
the 12 → 24 → 48 → 96 lift with the additive DP ported (X11/X17) and the trivial-prime products per level
(192: 2, 288: 2, 480: 7, 672: 6, 1056: 5 — ladder of EXPERIMENTS-X), at ns-per-DP-cell in C on all 10 cores and on a
GPU for the dense DP: what is the Tier-B makespan today? The question to answer is not "can we" but "how many
orders of magnitude short, exactly" — the number that tells us whether hardware or mathematics is missing.

D5 [chat] **Where the 10^2 expected unanchored survivors would be.** Expected count per vertex of unanchored
level-96 survivors = (level-96 patterns) × (sieve density 10^-38 × pinning factor). Compute it per Tier-B vertex from
the exact index of Λ_96 and K*; if it is ≪ 1 for the small vertices, those vertices' Tier-B closure under
"enumeration of anchors + shadow certificate" would be a theorem *conditional on no accident*, with the accident
probability stated — not a proof, but a precise statement of what remains (RULE 2 label: conditional, with the
probability as the hypothesis). Decide whether that statement is worth having.

D6 [Codex] **Blind re-derivation of §1–2** from the statements only: is any "known to fail" claim wrong? One wrong
line here is worth more than any D1–D5 result.

## 4. Order of work
D1 and D5 start now (chat); D3 and D2's literature parts go to agents now; Cairn takes D4 when the cost model's
inputs are ready and D2's data part (covering radii on the 679) if it wants it; Codex D6 on this file as it stands.
Results go to this file's §5 with calibration tags; the ledger gets one line per result.

## 5. Results

**D3 — bulk kill at level 12: RULED OUT, with the exact reason (agent sweep, 16:25 EDT; scripts sub3.py, dp.py, runs.py on the chat box).**
Computed, not in the literature: the index of ⟨3,7⟩ in F_p^× at the level-12 primes is 1 for p = 11, 13, 101, 9901
(at 9901: ord 3 = 825, ord 7 = 180, generating everything) and 2 only at p = 37 (squares), where 2 is a non-residue, so
with a free 2-exponent even 37 carries no bit. The level-12 "subgroup" mechanism therefore carries zero bits beyond
the zero fibers p | V (≈ |box|/p each); the measured 1/49.5 survival is the C0 (10-adic) component plus zero fibers.
Through d ≤ 18 the only robust nontrivial indices are 513239 (d = 11, m = 2, 2 ∈ H) and 5882353 (d = 16, m = 4; index 2
against ⟨2,3,7⟩) — equidistribution again, one or two bits each. Structure that exists: V(s) = image of Σ s_i ζ^i ∈ Z[ζ_d]
under the degree-1 prime (p, ζ − 10), so V depends only on the φ(d) cyclotomic coordinates (for 9901: four linear
forms a₀…a₃ in the s_i, V ≡ a₀ + 10a₁ + 100a₂ + 1000a₃); zero fibers; a Galois/norm relation tying a vector to its
class-permutations (never kills both); shift/negation invariance. Exact counts over the full simplex Σ s_i ≤ 130,
d = 12 (|B| = 8.7×10^16): QR/NR mod 37 differ by 9×10^-10 relative; residues mod 9901 deviate ≤ 5.3×10^-4 — no hidden
bias. Sharpest known bound = exact Gauss-sum identity + multidimensional Pólya–Vinogradov / Banks–Conflitti–Shparlinski
(Illinois J. Math. 46, 2002), Dietmann–Elsholtz–Shparlinski (Trans. AMS 369, 2017); Burgess needs length ≥ p^{1/4+ε}.
Verdict: no deterministic obstruction for bounded S; the only "bulk" is fiber-wise table lookup (= the engine's
exact test organized by cyclotomic coordinates), which the GPU lane already approximates. Direction closed.

**D2 — the anchoring hypothesis cannot be a theorem by lattice methods (agent sweep, 16:40 EDT).** Covering radius of
Λ_96 (det 2.8×10^56) is ≈ 10^28 and Banaszczyk's transference is tight up to constants, so no theorem puts a point of
the anchor box T = {(b,c) ≥ 0 : 3^b 7^c < 10^97·2^{-a}} (|T| ≈ 1.2×10^4) into a coset — a 10^24 gap. Extra 10-adic
congruences only enlarge the index. What IS rigorous: if λ₁(Λ_96) > 234 (one Gauss reduction to check), distinct
points of T lie in distinct cosets, so exactly |T| ≈ 1.2×10^4 of the 2.8×10^56 cosets are anchored, each by a UNIQUE
anchor. The Gaussian heuristic for nearest-point distance is a theorem at radii ≤ λ₁/2. Closest literature: Lagarias
(J. LMS 79, 2009) on ternary expansions of 2^n — finiteness unprovable, same "no accidental survivor" shape;
Dimitrov–Howe (2021) succeed because the modulus is grown past the number (congruence ⇒ equality) — unavailable here
since m₉₆ ≈ 10^57 < V < 10^97 for level-96 folds and V_L < 10^L in general. The anchored identity 9y − 9Σ d_j 10^{e_j} −
w(10^96 − 1) = 0 is a ≤ 48-term S-unit equation, so Evertse–Schlickewei–Schmidt / Amoroso–Viada give (ineffective)
finiteness of nondegenerate anchors — irrelevant to congruences. Clean residual: **Hypothesis H** — a fold's coset C_V
not explained by an anchor is no likelier to pass the sieve than a uniform coset; under H the number of unanchored
survivors is Poisson with mean N_pat(level L) × p_sieve(L). Chat's correction of the agent's flag: N_pat must count
level-96 patterns (positions mod 96), ≈ level-12 patterns × 8^k ≈ 10^40 for Tier B, against p_sieve(96) ≈ 10^-38 (index
of the image of ⟨3,7⟩ in the residue group): mean ≈ 10^2 at level 96 — but the same accident must then pass the
level-192 and 384 primes (another ≈ 10^-35 and 10^-12) and the windows, so under H the mean number of unanchored
level-384 survivors over all of Tier B/C is ≈ 10^-45. This is D5's number.

**D5 — consequence (chat, 16:45 EDT).** Under H the closure of a Tier-B vertex is: enumerate its anchors (10^5 pairs,
hours in C), run the shadow/480 certificate on their patterns (≈ 10^9 per vertex for Tier B, ≈ ms each in C — days on
the Mac), and state the residual "no unanchored fold passes the level-384 sieve" with its Poisson mean. RULE 2 label:
"closed by the sandwich (U″) for the anchored set; unanchored set excluded only under Hypothesis H (mean 10^-45)" — a
conditional closure whose hypothesis is a uniform-coset heuristic, not a named conjecture. Whether the project wants that
label is the owner's call; chat's view: worth having as a precise statement of what the enumeration would add (it would
add exactly the removal of H), not as a theorem.

**D1 — first measurements (chat, Python, 17:00–17:30 EDT; d1_ladder.py in scouts/anchorfirst/).** Two real Tier-C
anchors run to the end: y = 11010048, k = 10, ν = 95 (vertex 0; 20 patterns) and y = 16003008, k = 55, ν = 89
(438 patterns): **458/458 patterns have no depth-1 word** (every copy choice of the low classes e < a + 9 fails the
K = 96 window), so the ladder is vacuous on them — consistent with the scout's 40/40. The ladder beyond depth 1 can
only be measured on the rare patterns (10^-2–10^-4) that keep a word; four anchors of ≈ 1,500 patterns each (one per
vertex 0, 2, 4, 5) are running to find some. Two further anchors with 3 patterns each: also 0 words.

**D4 — chat's estimate, to be replaced by Cairn's measurement.** Tier B: ≈ 8×10^15 level-12 survivors; per survivor
the additive 12 → 24 DP is ≈ k × 10^4 ≈ 3×10^5 bit-operations plus ≈ 2^{k+1}/115 exact tests at ≈ 1 µs (the dominant
term for k ≥ 20: 2^{21}/115 ≈ 2×10^4 tests ≈ 20 ms at k = 20, ≈ 10 s at k = 29). Even if the exact tests were free,
the DPs alone are ≈ 2.4×10^21 bit-operations ≈ 2.4×10^8 GPU-seconds at 10^13 bit-ops/s — 8 GPU-years; with the exact
tests at the measured rates the Mac figure is ≈ 10^4–10^5 core-years. Gap to a one-year job on the Mac: ≥ 4 orders of
magnitude; to a one-year job on ~10 GPUs: ≈ 1 order, if the exact tests can be made additive too (they cannot at the
nontrivial primes 99990001-type: X11). So Tier B is a large-compute problem (national-facility scale), not an
impossibility — and not a Mac problem. Tier C (×10^5 more patterns, k up to 44) is out of reach of compute entirely.

**D1 — six anchors, 4,969 patterns, 0 depth-1 words (17:40 EDT; D1-*.txt in scouts/anchorfirst/).** Anchors
(vertex: y, k, ν; patterns): v0: 11010048, 10, 95 (20); v0: 16003008, 55, 89 (438); v0: 20302176190464, 9, 12 (1,503);
v2: 15059072, 10, 87 (1,500); v5: 39530064, 46, 89 (1,506); v0: 1474500111630336, 0, 8 (3 of 20). Every copy choice of
the low classes fails the K = 96 window on every pattern, so the per-pattern survival at depth 1 is < 10^-3 here
(0/4,969; the scout's 10^-2–10^-4). The accident ladder (192 primes → window → 384) therefore cannot be measured on
samples of this size in Python; it needs the surviving patterns, which are ~10^-4 of 10^11–10^14 per vertex.

**D7 (new) — the per-anchor depth-1 structure (d7_lowconfig.py).** The window verdict of a word depends only on the
fixed-value vector f = (f_e)_{e < a+9}, f_e ∈ {0} ∪ {d − 1 : d placed at class e}, through L = R_96 + Σ f_e 10^e
mod 2^{a+10}·5^6; all patterns of an anchor share V's low digits, so the depth-1 fate of all 10^9–10^14 patterns of an
anchor is decided by the set F of achievable f-vectors (≈ Π_e (1 + #values at e)), of which a fraction 1/640,000
survives. A layered DP over classes (state: carry × window residue) computes F's residues without enumerating
patterns; on y = 16003008 (a = 6, P = 15) it exceeds 2.4×10^7 states in Python (fine in C), i.e. |F| ~ 10^7–10^9 and
~10^2–10^3 surviving f-classes per anchor. So "closure per anchor" at depth 1 is a real object — ~10^3 surviving
window classes per anchor instead of ~10^14 patterns — but each surviving class still carries all its high-class
completions into the level-192 ladder, where the high digits enter through Δ (additive, 148417) and the nontrivial
primes (coset tests, 1/index each, non-additive). The remaining per-anchor problem is exactly §2's bounded-digit
congruence with the nontrivial-prime filters; no shortcut found. Status: structure exact, closure not reached.

**τ-lemma test (background, ~650/1335 at 17:40):** both 393216 G2 patterns reached; τ ≠ 0 words = 8 + 4, exactly the
wrap-1 representations' words; with the two 3211264 patterns the count is Cairn's 16; 0 mismatches so far.

**Update 2026-10-24 09:00 EDT (chat).**
- *Hypothesis H is not testable on existing data — retracting ask (1).* The sweep's 151 closed vertices have ≈ 10^13–10^14
  level-12 patterns at k ≤ 17, i.e. ≲ 10^28 level-96 patterns; at p_sieve ≈ 10^-38 the expected number of accidental
  (unanchored, non-rational-anchored) survivors in everything ever recorded is ≈ 10^-10. The observed 0 accidents in
  18,069 final13 survivors (8 rational anchors, 18,061 positive) is therefore consistent with H but carries no evidence
  for it at Tier B/C scale (10^40 patterns, mean ≈ 10^2 at level 96, ≈ 10^-45 at level 384). H is an extrapolation of the
  uniform-coset heuristic, full stop; the only thing that removes it is the enumeration (D4's compute).
- *Tier C has a first finite bill (Cairn's lanes, tier0-opt/tierc-rank, tierc-r2shadow, tierc-r2bill).* Smallest vertex
  3416267673274176: anchored open@96 2.1×10^11; depth-1 survivors 7.2×10^6 [1.4×10^6, 1.5×10^7], essentially all wrap-0
  shadows (5/25,082 wrap-0 vs 0/14,918 wrap > 0 — the τ-corollary); rank-0 closed by the cut via dlog base 2 mod R_96
  against the 2-adic bound; 5/5 rank-2 and 13/14 rank-1 survivors closed by the 480 sandwich at 10^301–10^302 (chat's
  prediction "cut or sandwich, none open" held); bill ≈ 40 core-years [0.1, 240] before Theorem F, top end k = 30–34
  pending. Conditional on H and on Lemma C / Matveev / Yu / the pattern list. This is the concrete form of D5 for Tier C.
- *Theorem F* (Cairn lane 1) = the family form of the witness criterion, proved from the content lemma (ledger 03:10):
  survival of a wrap-0 shadow at level L ⟺ 10^ν + 9·S_U ≡ 0 (mod 2^{a+v₂(d₁(L))+2} · 5^{v₅(d₁(L))+1}); 718× on the shadow
  decision; irrelevant for Tier C's non-shadow survivors (kill criterion fired correctly).
- *τ test* complete: 14,325/14,325 words, 0 mismatches (HSHADOW §7 addendum).

**D5-B — the anchored census of ALL 13 Tier-B vertices, exact (chat box, 2026-10-24 09:15–10:45 EDT; scouts/anchorfirstB13/,
the scout's anchorfirst.py + anchor_dp.c run on tierB13.txt with every (y,k) pair instead of a sample; 5,364 s wall).**
S-units y < 10^98 with a ≤ 60: 609,796; (y,k) pairs passing the digit-sum filter: 654,777 (k ∈ [−9, 224]); phase 1 (C DP)
on all of them, every ν; phase 2 (Python) on the small hits agrees with the C counts and verifies the representations by
the integer identity; Lemma C depth 1 on the 12 sampled representations of the first vertex: 12/12 CLOSED.

| vertex | s | multisets | k_max | anchored (y,k) pairs | (y,k,ν,W) hits | anchored level-96 patterns (exact) |
|---|---|---|---|---|---|---|
| 71663616 | 2^15·3^7 | 406 | 22 | 11,107 | 136,040 | 2.999×10^8 |
| 226492416 | 2^23·3^3 | 308 | 26 | 12,061 | 162,000 | 3.121×10^8 |
| 1194891264 | 2^11·3^5·7^4 | 149 | 20 | 15,676 | 168,763 | 3.133×10^8 |
| 169869312 | 2^21·3^4 | 382 | 25 | 12,004 | 158,712 | 4.270×10^8 |
| 4182119424 | 2^10·3^5·7^5 | 126 | 20 | 17,592 | 180,844 | 2.877×10^8 |
| 1792336896 | 2^10·3^6·7^4 | 161 | 20 | 17,000 | 189,122 | 4.070×10^8 |
| 13884223438848 | 2^14·3·7^10 | 45 | 25 | 31,734 | 304,796 | 2.888×10^8 |
| 2113929216 | 2^25·3^2·7 | 247 | 28 | 17,711 | 275,430 | 1.334×10^9 |
| 1811939328 | 2^26·3^3 | 387 | 29 | 16,935 | 267,860 | 1.560×10^9 |
| 11329339392 | 2^19·3^2·7^4 | 150 | 25 | 21,370 | 297,259 | 1.374×10^9 |
| 4444263936 | 2^9·3^11·7^2 | 262 | 22 | 22,417 | 318,727 | 1.978×10^9 |
| 3699376128 | 2^23·3^2·7^2 | 212 | 27 | 19,613 | 301,185 | 1.892×10^9 |
| 1783627776 | 2^20·3^5·7 | 449 | 26 | 19,340 | 303,086 | 6.649×10^9 |
| **total** | | | | | | **1.712×10^10** |

Reading. Under the anchoring hypothesis H the level-96 open set of the whole of Tier B is 1.7×10^10 explicitly listed
patterns (the forecast 10^-8 × 4×10^17 = 4×10^9 is within ×4), on 2.3×10^5 anchor pairs. Every one is a final-stage
pattern of the kind the C port closes at ≈ 33 ms (Lemma C depth 1 kills most; Theorem F decides the shadow in µs; the
480 route does the rest): **≈ 5×10^8 core-seconds ≈ 18 core-years at the current per-pattern cost, likely ≈ 2–4 core-years
after Theorem F and C enumeration of the representations — months on the Mac.** The smallest vertex (3×10^8 patterns) is
≈ 1–2 weeks. That is the concrete form of D5: "Tier B closed, conditional on H" is a finishable program; what it does not
remove is H itself (D4's compute). The hits files (y k ν W count) for all 13 vertices are in census-tierB/hits_tierB13.tgz.

**D5-B continued — depth-1 survival over the Tier-B anchored census (d5b_depth1.py; DEPTH1-v0.txt, DEPTH1-v8.txt; 11:00–13:00 EDT).**
Weighted samples of census hits, ≤ 30 patterns per hit, exact reduced depth-1 verdict (cut_small on the low-class copy
choices): vertex 71663616 — 89,939 patterns from 3,000 hits, **178 survive (0.20%)**; vertex 1811939328 (the last A_2
vertex) — 45,000 patterns from 1,500 hits, **165 survive (0.37%)**. In both, **every survivor comes from a wrap-0
representation** (178/36,660 wrap-0 = 0.49%; 0/53,279 for wraps 1, 9, 10, 18, 19, 27, 28; and 165/17,790 vs 0/27,210): the
depth-1 window kills every wrap ≥ 1 representation in the sample — the 2,5-adic analogue of the τ-corollary (for wrap w ≥ 1
the shadow's window value differs from y by w·R_96 plus the ν-term, which is not ≡ 0 modulo 2^{a+v₂+2}5^{v₅+1} in general).
Survivors by k: 11–19 for the first vertex, 14–25 for the second; none at the top k. Consequence for the program: the
Tier-B remainder after depth 1 is ≈ 0.2–0.4% of 1.7×10^10 ≈ **3–7×10^7 patterns**, all wrap-0 shadows of small anchors,
each a Theorem-F/480-certificate case of seconds at most: **≈ 10^6–10^7 core-seconds in C = days on the Mac**, not months.
The enumeration of the 1.7×10^10 representations (C) and the depth-1 cut itself are then the dominant cost.

## 6. Conclusion of the sprint (chat, 2026-10-24 13:15 EDT; proposed text for FRONTIER.md)

Tier B and Tier C each split into two parts with different natures.

*The anchored part is finite, explicit and priced.* Under the anchoring hypothesis H — "every level-96 survivor's coset
contains a small (positive or rational) S-unit point", true for 18,069/18,069 recorded survivors but untestable at scale
on existing data — the open set at level 96 is the anchored census: Tier B, all 13 vertices: 1.71×10^10 patterns on
2.3×10^5 anchor pairs (exact, 90 min); the smallest Tier-C vertex: 2.1×10^11 patterns. Lemma C depth 1 removes 99.6–99.8%
of the Tier-B patterns (every wrap ≥ 1 representation, 0.2–0.4% of the wrap-0 ones survive); the rest are shadows of small
anchors, decided by Theorem F and the level-480/1152 certificate in seconds. Bills: Tier B ≈ days of C after the
representations are enumerated (the enumeration and the depth-1 pass dominate); Tier C smallest vertex 5.4 core-years
[3.6, 7.8] for the survivors (Cairn R2BILL), the depth-1 pass over 2×10^11 patterns on top. Label available at the end:
"anchored set closed by the cut / by the sandwich (U″); unanchored set excluded under H only".

*The unanchored part is Hypothesis H, and nothing but the level-12 enumeration removes it.* An accident is a fold whose
Λ_96-coset is generic (nearest point near the covering radius 10^28) and passes the PH-feasible primes anyway; no
lattice, transference or character-sum statement distinguishes it beforehand (D2, D3), and the level-12 structure carries
zero multiplicative bits (D3). Expected accidents are Poisson with mean ≈ 10^2 at level 96 over Tier B and ≈ 10^-45 after
level 384, but these are heuristics, not bounds. Removing H costs the sweep: Tier B ≈ 8×10^15 level-12 survivors through
the additive lift (≈ 8 GPU-years for the DPs alone, ≈ 10^4–10^5 Mac core-years), Tier C 1.7×10^19 level-12 patterns for
the smallest vertex (≈ 55 GPU-years at 10^10/s). National-facility compute, with a known algorithm; not impossible, not
a Mac.

*What would change the picture.* A deterministic reason that folds of bounded digit mass cannot be accidental survivors
(none known; equidistribution is the theorem); or a Skolem-type local–global theorem for the three-term equation
9·2^a3^b7^c − 10^n = c₀ (open); or an effective bound polynomial in k for the k-term S-unit equation (conditional on abc /
RST, inadmissible under RULE 2). Everything else in this sprint is bookkeeping of a well-understood object.

*Addendum (13:50 EDT): wrap census of the 1.71×10^10.* Wrap 0: 6.42×10^9 (37.5%), wrap 1: 4.64×10^9, wrap 9: 3.35×10^9, wrap 10:
1.76×10^9, wraps 18/19: 8.4×10^8; the rest < 10^8. Since the depth-1 window condition for wrap w reads
10^ν + 9·S_U + w ≡ 0 (mod 2^{a+v₂(d₁)+2}·5^{v₅(d₁)+1}) (Theorem F with the +w from V − y = w·R_96; for w ≥ 1 it needs the
digits at positions < 5 and ν < 5 to balance w modulo 5^5, which is why 0/80,489 wrap ≥ 1 samples survive), a program may
run the depth-1 pass on the wrap-0 6.4×10^9 first and treat wrap ≥ 1 by the same explicit congruence as a prefilter —
sound either way, since the congruence is the exact window verdict.

**D8 — can a Skolem-type theorem replace the enumeration? NO, by pigeonhole (agent sweep of BHT I–III, Bertók–Hajdu 2016,
Dimitrov–Howe; 16:10 EDT).** Bérczes–Hajdu–Tijdeman's modulus m = m′·m″ needs the right side ±1 (it turns x^n ≡ c into an
order condition; part III states the proof "cannot be modified to cover values of ε different from ±1"), and m depends on c
in both stages; Bertók–Hajdu's general-c procedure is explicitly conditional on Skolem's conjecture. Uniformity over a family
F of constants is governed by counting: the congruence is unsolvable for c iff c mod m ∉ I_m, the image of (a,b,c,n), so a
fixed sieve certifies a family only if |F| + |I_m| ≲ m. For our folds, F = the 10^40 level-96 patterns of Tier B reduced
mod 10^96 − 1 and I_m = the S-unit residues (|I| ≈ 10^57): |F|·|I|/m ≈ 10 expected coincidences — the accidents — and no
choice of m below 10^40·|I| removes them; above it, the check is per c, i.e. the enumeration. Dimitrov–Howe succeed only
because their modulus chain grows past the number (their Lemma 3.1 even shows a single modulus admits extraneous
solutions). Verdict: the enumeration is the proof; H is removable by computation only. Direction closed; do not retry
without a genuinely new idea about the structure of F mod m (D3 says it has none at level 12).
