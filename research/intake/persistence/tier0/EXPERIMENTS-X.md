# Experiments X1 and X3 (2026-10-21 evening, chat session) — exact computations, predictions registered in the 20:25 message

## X3 — does a deeper 10-adic cut make the next level's kills additive? **No (prediction falsified).**

Λ_12 ∩ {3^b7^c ≡ 1 mod 5^K·2^K}, a = 0, image index at the level-24 primes (73, 137, 99990001) and level-48 primes
(17, 5882353, 9999999900000001):

| K | lattice index | content | idx at 73 / 137 / 99990001 | image orders | idx at 17 / 5882353 / 10^16-prime |
|---|---|---|---|---|---|
| none | 8.9e6 | 2²3²5² | 36 / 4 / 900 | 2 / 34 / 111100 | 4 / 48 / 900 |
| 12 | 4.5e15 | 2²3²5² | 36 / 8 / 4500 | 2 / 17 / 22220 | 4 / 48 / 900 |
| 24, 48, 96 | 4.5e27 … 4.5e99 | 2²3²5² | 36 / 8 / 4500 | 2 / 17 / 22220 | 4 / 48 / 900 |

For Λ_24 ∩ cut: K = 24 makes the image at 17 trivial (index 16 = p − 1) and multiplies the index at the 10^16 prime
by 5 (39600 → 198000); K = 48, 96 add nothing. Mechanism: the 10-adic cut kernel is 2-adic × 5-adic, so it can only
shrink the 2-part and 5-part of an image; it does so once (at the first window) and saturates. 137's order-17 image
and 73's order-2 image are untouched by any window. Consequence: the 12 → 24 additive prefilter stays at the
73·137 level (≈ 1/115 of children), and the per-parent floor of LIFT-ADDITIVE.md §5 stands.

## X1 — is there a first level better than 12? **No for the first level; one striking level-30 fact.**

Exact, for the k = 29 multiset 2^26·3^3 (vertex 1811939328, Tier B); ρ'_L = [Z² : Λ_L]·φ(Q_L)/Q_L² = probability
that a uniform pattern value is a unit in 2^a⟨3,7⟩ (fixed a); patterns(L) = L·∏_d C(L−1+m_d, m_d).

| L | level primes | log₁₀ Q_L | log₁₀ ρ'_L | log₁₀ patterns | log₁₀ uniform survivors |
|---|---|---|---|---|---|
| 3 | 37 | 1.6 | −0.3 | 4.1 | 3.7 |
| 5 | 41, 271 | 4.1 | −0.02 | 6.7 | 6.7 |
| 6 | 11, 13, 37 | 3.7 | −0.8 | 7.8 | 7.0 |
| 10 | 11, 41, 271, 9091 | 9.1 | −2.1 | 11.2 | 9.1 |
| **12** | 11, 13, 37, 101, 9901 | 9.7 | −2.9 | 12.6 | **9.7** |
| 15 | 31, 37, 41, 271, 2906161 | 13.6 | −3.6 | 14.4 | 10.7 |
| 16 | 11, 73, 101, 137, 17, 5882353 | 15.1 | −3.7 | 14.9 | 11.3 |
| 20 | 7 primes | 19.1 | −6.7 | 16.9 | 10.2 |
| 24 | 8 primes | 21.7 | −8.3 | 18.6 | 10.3 |
| **30** | 11 primes (31, 211, 241, 2161, 9091, 2906161 …) | 27.7 | **−14.5** | 20.7 | **6.2** |
| 36 | 9 primes | 33.3 | −10.9 | 22.6 | 11.7 |
| 48 | 11 primes | 45.7 | −15.5 | 25.6 | 10.1 |
| 60 | 18 primes | 57.7 | −28.5 | 28.1 | **−0.4** |

Readings. (i) As a first level nothing beats 12: every other L has more patterns to evaluate than survivors it
saves, and the sweep's first-level cost is already only ≈ 1 % of its time. (ii) **Level 30 is anomalously selective:**
its eleven primes have p − 1 rich in 3 and 5 (30, 210, 240, 2160, 9090, 2906160, …), so the image of ⟨3,7⟩ has index
10^14.5 in a modulus of 10^27.7 — ρ' is 10^6 times smaller than level 24's with only 10^6 more modulus. At level 60
the uniform survivor count for this multiset is 0.4: **by level 60 the accidents are gone and only anchored
patterns remain** (level 96: 10^−4.3). (iii) Chains: the lift cost is Σ patterns(L_{i+1})·ρ'(L_i) over the chain —
12→24→48→96: 10^15.7 + 10^17.3 + 10^17.5; 15→30→60: 10^14.4 + 10^17.1 + 10^13.6; 10→30→60: 10^18.6 at the first lift.
No chain is better than a constant factor — the lift from the first level dominates and is set by patterns(L₂)·ρ'(L₁),
which the L₁ = 12 chain already minimises within ×3. (iv) The one reusable fact: a level with p − 1 ≡ 0 mod 3·5 for
many primes is where the 3- and 5-parts of ⟨3,7⟩'s image are small — the same mechanism as the content of Λ_96 that
drives the shadow certificate. For the final stage, lifting 96 → 480 (= 96·5, whose new primes have 5 | p − 1) may be
more selective per child than 96 → 192 → 384; to be measured (image indices of Λ_96 at the level-480 primes).

## Status

Both experiments are exact (lattice kernels via discrete logs at every level prime; sympy factorisation of
Φ_d(10)); the "uniform survivors" column is the uniform model, which RESULT-accidents.md validated to level 48.
Predictions registered in the 20:25 chat message: X1 "L = 12 wins for every k ≥ 16" — confirmed; X3 "a deeper cut
makes level-24 images trivial" — falsified (saturation at K = 12). X2 needs the 228 gated equations (Cairn).

## X4 (follows from X1's reading iv) — the level-480 primes against Λ_96: eight trivial images

Image of Λ_96 (content 2^7·3^2·5^4·7·11·41·59·101) at the PH-feasible new primes of levels 192, 288, 480:

- level 192: 193, 769 trivial (as in HSHADOW.md); 19841 → order 31; 976193 → 2179; 6187457 → 8789; two large.
- level 288: **19, 3169 trivial**; 8929 → 31; 13249 → 23; 98641 → 137; 333667 → 167; 52579 → 2921; 1067329 → 1853;
  999999000001 → 12025.
- level 480: **31, 41, 61, 211, 241, 3541, 9091 trivial**; 271, 2161 → order 3; 27961 → 233; 177601 → 37; then
  1703, 2641, 10477, 12109, 13963, 19963, 28834, 786609, 1.3×10^6, 5.9×10^8, 10^24 (the 33-digit prime).

Mechanism: p − 1 divisible by 3·5 (and a 2-power ≤ 2^7) divides the content, so every lattice vector maps to 1.
Consequence for the final stage (the word lift of WORDLIFT.md generalised to a ×5 level): a level-96 word's child
at level 480 is determined by t_j mod 5 for each unplaced digit and a ν-shift in {0..4} (5^(r+1) children); its
value is V + (10^96 − 1)·Δ′ with Δ′ = Σ_{S}(d_j−1)10^{e_j}(10^{96 s_j} − 1)/(10^96 − 1) + ν-term, and at the seven
trivial-image primes it survives iff **Δ′ ≡ 0 (mod 31·41·61·211·241·3541·9091 ≈ 1.2×10^18)**. The shadow has
Δ′ = 0; an accidental hit has probability 5^(r+1)/1.2×10^18 (≈ 0.05 at r = 23); sequential DPs over the factors
(77531 states, then ×211·241, …) certify it exactly. Then the four order-3/37/233 primes and the 10-adic window at
K = 480 act on the (usually unique) survivor. Lower bound at level 480 depth 1 ≈ 10^(28 + ½·log₁₀[new index ≈ 10^136]
+ 240) ≈ 10^336 — just under U″(44, 0) = 10^345; depth 2 (K = 960, +10^240) is far above. So **the final stage for
k up to 44 is a certificate at 96 → 480 (→ depth 2), with no children enumeration** — ready for Tier C the day
Tier C is enumerated, and a cheaper route than 192 → 384 for Tier A/B survivors with large r.

## X5 — the content principle, now a lemma (theory extracted from X1/X3/X4 and HSHADOW)

**Lemma.** Let Λ_L = {(b, c) : 3^b 7^c ≡ 1 (mod Q_L)} and let ⟨3,7⟩ ⊂ (Z/Q_L)^* have invariant factors d₁ | d₂
(so ⟨3,7⟩ ≅ Z/d₁ × Z/d₂ and [Z² : Λ_L] = d₁d₂). Then (i) the content of Λ_L (gcd of all coordinates of all its
vectors) is exactly d₁ — the gcd of the entries of any basis matrix is its first elementary divisor; (ii) for any
prime p ∉ P_L, the image of Λ_L in (Z/p)^* is trivial whenever (p − 1) | d₁ (then Λ_L ⊆ (p−1)Z² ⊆ Ker_p); in that
case the cut at p of any coset v + Λ_L is the single congruence 3^b7^c ≡ V/2^a with V's class fixed, so a child
with value V + (10^L − 1)Δ passes iff Δ ≡ 0 (mod p): the kill is additive. (iii) For a sub-lattice Λ′ ⊆ Λ_L
(10-adic cuts) the content can only grow, and only in the 2- and 5-parts.

Numbers: Λ_12: d₁ = 900 = 2²3²5², d₂ = 9900 (index 8.9×10^6). Λ_96: d₁ = 13 545 045 360 000 = 2^7·3^2·5^4·7·11·41·59·101,
d₂ = 2.1×10^43 (index 2.8×10^56). Words' lattice Λ′_a at level 96: d₁ = 2500·d₁(Λ_96) ⊇ 2^9·3^2·5^8.
Consequences read off directly: level-192 primes 193 (192 | d₁) and 769 (768 ∤ d₁ but trivial anyway — (ii) is
sufficient, not necessary) are additive; level-480 primes 31, 41, 61, 211, 241 (p − 1 | 2^7·3^2·5^4·7·11 …) and 3541
(3540 = 2²·3·5·59 ✓), 9091 (9090 = 2·3²·5·101 ✓) are additive; at level 24 nothing is (72 ∤ 900, 136 ∤ 900), which is
X3's saturation and the 12 → 24 floor. The lemma also says where to LOOK: a modulus whose primes have p − 1 | d₁ of
the current lattice. For Λ_96 that is every prime p ≡ 1 mod stuff dividing 2^7·3^2·5^4·7·11·41·59·101 whose
ord_p(10) is PH-feasible — a list worth generating (X6).

## S1 in the corpus (Lane 3 data)

Of the 8,799 zero-free S-units ≥ 10 below 10^4000, 628 have a zero-free S-unit digit product (the 0.9^{digits}
heuristic predicts 564, bin by bin within noise); the largest such is 268476843674491723183742239912919243314992
(42 digits). Above 42 digits none of the 2,000+ corpus elements has a zero-free S-unit product. So the chain
structure of Z′ lives entirely below 42 digits in the corpus: S1 holds there with a 100-digit margin, and the
heuristic expected number of exceptions above 42 digits is < 1 in total. Still heuristic; recorded as data.

## X6 — the ideal additive-kill primes (from the lemma)

All primes p with (p − 1) | d₁ of the words' lattice (2^9·3^2·5^8·7·11·41·59·101): 1514 of them. Measured image of Λ_96
at every one with ord_p(10) | 480 or 288: trivial, 24/24 (the level-96 primes themselves, then 193, 769 [192];
19, 3169 [288]; 31, 41, 61, 211, 241, 3541, 9091 [480]). The remaining ones need other multiples of 96 as their level:
ord_p(10) ∈ {21, 28, 42, 112} → level 672 (≈ 6 primes), {22, 33, 44, 88} → level 1056 (≈ 5), {50, 75, 125} → 2400.
So the additive-kill ladder for a level-96 survivor is 192 (×2, 2 primes), 288 (×3, 2), 480 (×5, 7), 672 (×7, 6),
1056 (×11, 5): each step's children are m^(r+1) but the DP cost is m·(r+1)·M, independent of m^(r+1).

## X8 — the certificate's hypothesis for every exponent a (exact, a = 0 … 160)

Content of Λ′_a = Λ_96 ∩ (10-adic cut at K = 96): 2^9·3^2·5^8·7·11·41·59·101 for a ≤ 85, 2^8·… at a = 86, 2^7·… for
87 ≤ a ≤ 160 (the 2-adic cut contributes less as 96 − a shrinks). The sufficient condition 768 | content fails for
a ≥ 87, **but the image of Λ′_a at all eleven ladder primes (193, 769; 19, 3169; 31, 41, 61, 211, 241, 3541, 9091) is
trivial for every a ≤ 160** (0 exceptions). So shadowcert.py's runtime assertion holds on the whole range of
exponents any vertex uses (Tier-C A ≤ 144), and the certificate never falls back to the word lift.

## X12 — soundness of the ×5 lift (wordlift480.py)

(1) Bookkeeping with the congruence filter disabled: 296/297 planted placements (t_j up to 14, ν-shifts 0–4) found
with the true residues modulo the 3-free part of 10^480 − 1 and the true lowest 480 digits; the one miss is a
planted word with digit 8 at position 0 under a = 0 — an even number with v₂ = 0, killed correctly.
(2) The identity behind the filter — V_child − V_shadow ≡ (10^96 − 1)·Δ′ with Δ′ as coded (geometric factors
(10^{96 s} − 1)/(10^96 − 1), ν-term 10^ν·9^{−1}·geo[sn]) — holds on 500/500 random (word, shifts, ν-shift) modulo
∏T. Note for the record: as INTEGERS the difference is divisible by (10^96 − 1)/9, not by 10^96 − 1 (the ν-term
carries a 1/9); modulo the ladder primes (all ≠ 3) that is immaterial, which is why the filter is stated mod p.
(3) On the 43 level-96 survivors (WORDLIFT480-run.txt): **43/43 closed — 12 with no survivor at level 480, 31 by the
bound 10^(10^301.9–302.6) against U″ ≤ 10^93**; 7 trivial-image primes on every pattern; in every word exactly the
shadow passed the congruence (part 2: 65,600 children tested, 20 passed = the 20 words). The level-480 bound is
10^63 above the level-384 one, at the cost of 5^(r+1) rather than 2^(r+1) children screened by the congruence.

## X9 — the content lemma in other bases (exact; engine_b kernels, Smith normal forms)

| base | free primes (rank) | d₁(Λ_12) | d₁(Λ_24) | d₁(Λ_48) | d₁(Λ_96) | level-192 PH-feasible primes with trivial image |
|---|---|---|---|---|---|---|
| 10 | 3, 7 (2) | 900 | 2^3·3^2·5^2·11 | 2^4·3^2·5^4·11·101 | 2^7·3^2·5^4·7·11·41·59·101 | 193, 769 (of 7) |
| 8 | 3, 5, 7 (3) | 18 | 144 | 864 | 3456 = 2^7·3^3 | 3457 (of 5) |
| 6 | 5 (1) | 2016 | 3.4×10^6 | 5.8×10^16 | 9.1×10^34 | 145601 (of 2) |
| 12 | 5, 7, 11 (3) | 6 | 48 | 576 | 7488 = 2^6·3^2·13 | none (of 7) |

Reading: d₁ is the SMALLEST invariant factor of the free-prime image, so it falls with the rank of the free group —
rank 1 (base 6) makes every prime with (p−1) | |image| additive, rank 2 (base 10) is the lucky middle, rank 3
(bases 8, 12) leaves only one or no additive prime at level 192. The shadow certificate transfers to base 8
through the single prime 3457 (kill 1/3457 per child, then exact tests) and to base 6 outright; base 12 needs a
different level (one whose primes have p − 1 | 7488: 13 | p − 1 — e.g. level 12·13 = 156) or no certificate.

## X11 — additive lifts at 24 → 48 and 48 → 96 (addlift2.py, self-tests on real level-L1 survivors)

24 → 48: new primes 17 (image order 2 → DP), 5882353 (order 122549 → hash-set filter), 9999999900000001 (exact
only). 12/12 parents: DP child set == brute force; candidates after the mod-17 DP 1/9 of the children. 48 → 96: new
primes 97 (trivial) and 353 (order 2) in the DP (modulus 34241), 449/641/1409/69857/206209 as set filters, two large
primes exact. 12/12 match; the DP leaves exactly one candidate per parent (1/2389 of the children) — the shadow.
Together with addlift.py (12 → 24, 120/120) the whole lift chain has a validated additive prototype; the per-parent
cost is set by the 12 → 24 step and nothing after it.

## X15 — prediction registered (step 3), not yet testable on local data: the words collapse into fate classes at 384

For a pattern with exponent a, the level-384 fate of a word's shadow depends on the word only through the 2-adic
part of its coset base point. Reason: the words of one pattern are cosets of the same lattice Λ′_a inside one Λ_96
coset, so two base points differ by δ ∈ Λ_96; at a level-384 prime p the condition is V/2^a ∈ x_W·H_p with H_p the
image of Λ′_a and x_W varying by the image of δ. At 3457 (p − 1 = 2^7·3^3) both images have order 3 — the SAME
subgroup — so the fate is word-independent; at 12289 (2^12·3), 418725889 (2^14·3·7·1217) and 1265011073 (2^7·…) the
variation lives in the 2-parts, i.e. in (b, c) mod 2^14, which the K = 96 cut determines from L_W mod 2^{16+a}:
the fixed digits at positions < 16 + a. **Prediction:** words agreeing on their copy-0 choices at positions
< 16 + a have identical fates at all four level-384 primes; the number of distinct fates per pattern is at most
2^{#digits at positions < 16+a}, not 2^{#digits ≥ 9} (the words count). Kill condition: two words with the same low
configuration and different 384-fates. Not testable on the 1250 snapshot (every anchor there has < 14 digits, so
every word is its own class); testable on the first Tier-A survivors with anchors above 10^{16+a}. If it holds, the
per-pattern final-stage cost at Tier B drops from (#words)·4 modexps to (#fate classes)·4 modexps, and the words
themselves need only be counted, not listed.

## X16 — why shadows survive 192 always, 384 rarely, 480 mostly (step 6; shadowfate.py, SHADOWFATE-run.txt)

The shadow's value is the anchor's value V = y (wrap 0), so the anchor point (b_y, c_y) satisfies every residue
condition the shadow is tested against; the shadow's coset differs from the anchor point by δ ∈ Λ_96 ∩ Ker_192 (the
anchor is in the same Λ_96-coset and passes the level-192 primes). Hence the shadow passes a prime p AUTOMATICALLY
whenever the image of Λ_96 ∩ Ker_192 at p equals the image of the shadow's own lattice (Λ′ cut 10-adically at K = 96,
192) — and the 10-adic cuts shrink only the 2- and 5-parts. Measured on the 74 words of the 43 patterns, each prime
of levels 384 and 480 (< 10^12) separately:

| prime | p − 1 | predicted pass = \|im Λ′\|/\|im Λ_96\| | observed |
|---|---|---|---|
| 3457, and 20 of the 21 level-480 primes tested | various | 1 (AUTO) | 74/74 each |
| 12289 | 2^12·3 | 0.50 | 38/74 = 0.51 |
| 418725889 | 2^14·3·7·1217 | 0.25 | 31/74 = 0.42 |
| 1265011073 | 2^7·13·17·197·227 | 0.059 by the raw ratio, but the 17-part is already fixed by the level-192 kernel ⇒ AUTO | 74/74 |
| 18453761 | 2^8·5·13·1109 | 0.50 | 38/74 = 0.51 |

So the shadow-killers are exactly the primes whose p − 1 has a 2-part above the content's 2^7 (12289: 2^12;
418725889: 2^14; 18453761: 2^8), each killing with the measured ratio (½, ~⅓, ½): 6/43 shadows survive level 384
(½·⅓ ≈ 1/6 ✓) and 31/43 survive 480 (one killer, ½, over patterns with several words ✓). Consequences: (i) the
final stage needs no shadow kills — the 10^{302} bound closes a surviving shadow — so the 480 route (7 additive
primes, one killer) is strictly the better certificate; (ii) if one wants shadow kills, take primes with large
2-powers in p − 1 whose ord_p(10) divides a usable level (level 768 adds 2^15–2^16 candidates); (iii) the earlier
"accidental survivor" language for shadows at 384 was wrong — the survival probabilities are exact group indices,
not accidents.

**X4 addendum (22:25 EDT).** Depth 2 at level 480 (window K = 960) on a surviving shadow of 32928: bound
10^(10^542.0) (66 cases, survivors [1, 2]) — above U″(44, a) = 10^345 by 200 orders. So the certificate covers
k ≤ 38 at depth 1 and every k ≤ 44 at depth 2, i.e. the entire frontier's final stage.

## X18 — the certificate in base 8 (wordlift_b.py; WORDLIFTB8-run.txt, WORDLIFTB8-nofilter.txt)

Base 8 (free primes 3, 5, 7; level-192 PH-feasible new primes 641, 3457, 816769, 6700417, 18446744069414584321;
only 3457 has trivial image of the words' lattice, as X9 predicted). Word lift 96 → 192 on the first 30 open
level-96 patterns of base8_L96_full.jsonl (vertex 3402, k = 7): with the Δ ≡ 0 (mod 3457) filter, 17,192 children
tested, 397 reach the exact coset test; **27/30 patterns closed outright at level 192** (3 of them already at depth
1), 36 survivors on the other 3 with bound 10^(10^79.4–79.5) digits. The unfiltered run (every child through the
exact test) gives the same 27 closures and the same 36 survivors pattern for pattern — the filter is a pure
accelerator, ×43 here, exactly as the additive-kill lemma says. The remaining 3 patterns need the sandwich against
the base-8 Baker bound or a second level (288: primes with 3^3 | p − 1 are the candidates — d₁ = 2^7·3^3).
This is the base-8 final stage Cairn's Mac sandwich has been grinding (57/70 vertices): the certificate route is
a few seconds per pattern in Python.

## X19 — the additive lift on the engine's real population (accidental level-12 survivors)

Random level-12 patterns of the k = 11 multiset 2^6·3^2·4·7^2 (ν, e_j uniform mod 12), kept when some a ≤ 64 gives a
coset: 40 survivors in 1617 trials (2.5 %, the engine's pass rate with a free). Additive lift vs brute force on 25
of them: **25/25 identical**; DP candidates 559 of 102,400 children (1/183); level-24 survivors 0/25 — accidents die
at the lift, as the uniform model predicts (anchored parents keep exactly their shadow, X11). So on the sweep's
actual parents the DP does the same work as on anchored ones and the exact-test count is ≈ 2^{q+1}/180.
Base 6 (X9's rank-1 case) could not be run: the cloud base-6 file predates exceptional-point recording.


## X2 — RESULT (Cairn, 2026-10-21 21:15; tier0-opt/math/x2-survivors/RESULT.md): prediction FALSIFIED

Chat's registered prediction (≥ 99 % of level-24 descent survivors are anchor shadows at k ≥ 13) fails: on all 228
gated equations the shadow fraction is 0.384 [0.356, 0.413] (438/1140); ≥ 99 % holds only for k ≤ 8. Accidents are
uniform at level 24: observed/model 1.018 [0.979, 1.061] at the residue stage and 1.000 [0.930, 1.075] at the tail
stage — no suppression. 32,056 shadows on 564 anchors (all ≤ 15 digits), each re-verified by an integer identity;
controls 1,200/1,200 planted, 0/100,000 random. Consequence: anchor-first is not a forecast at level 24 either;
RESULT-accidents.md stands in full. Do not retry without a new mechanism.

## Corrections from Cairn's C port of the shadow certificate (tier0-opt/cport-shadow/RESULT.md)

(G1) The level-384 step of shadowcert.py tests the fixed value V; the shadow's level-384 children carry
V₂ = V₁ − 2Δ′ (10^192 ≡ −1 at the four primes), so the prime cut must be applied per branch — the port does, with
meet-in-the-middle on the two smallest-image primes, brute-force-equal on all 14,325 words. Verdict changes: 0/43,
0/1,335; 1,153 of the 1,335 old sandwich closures are now CLOSED-cut outright, smallest sandwich margin 110.8
orders (was 4.93). (G2) On 4 of 1,335 patterns the shadow FAILS 193/769 for some words (τ = 65963) and a
non-shadow child (|S| = 1, sn = 1) is the true level-192 survivor; shadowcert.py would assert there — the port
tests the DP's 8 candidates exactly and closes all four. HSHADOW.md §3 step 2's "every word has exactly its
shadow" is therefore a theorem only when the shadow's own residue test passes; the certificate must carry τ per
word. (G3) content(Λ′_a) constant for a ≤ 63 (and chat's X8: 2^7-part for a ≥ 87, images still trivial).

## X20 — the witness: what kills a wrap-0 shadow, and the depth map of the final stage (2026-10-23, 00:40–03:00 EDT; extinct.py, witness.py, gtable.py, align.py; EXTINCT-run.txt, WITNESS-run.txt, WITNESS-sand6-288.txt, GTABLE-run.txt, ALIGN-run.txt)

**Question (step 1).** Can the sandwich survivors be closed by cutting deeper — level 768 — so the final stage needs no Baker/Yu at all?

**Measurement.** The six CLOSED-sandwich patterns of the 43 were lifted 384 → 768 with the six PH-feasible level-768 primes (257, 15361, 434689, 453377, 859393, 33649448872371457; new_primes(768, 384), 492 s to factor): **6/6 alive**, one survivor each (the shadow), bound rises from 10^(10^239) to 10^(10^441). Crossing Cairn's two tables: of the 182 CLOSED-sandwich patterns at 384 (shadow1335.tsv), 181 are CLOSED-sandwich at 480 as well (x4_480_1335.tsv; the other is the NOTAPPL case), and 480 cuts nothing 384 does not (359 ⊂ 1153).

**Mechanism (theorem, X16 sharpened).** For a wrap-0 representation V = y, the anchor's own exponent vector (b_y, c_y) satisfies 2^a 3^b 7^c ≡ y modulo *every* prime, so the modular coset at every level L is (b_y, c_y) + Λ_L and is never empty: the prime cuts, at any level, with any primes, cannot kill the shadow. The shadow's other constraint is the window: ones up to K, fixed digits at copy 0, unplaced digits beyond K, i.e. 2^a 3^b 7^c ≡ W_K (mod 10^K), a class v_w + K_K with K_K = {(b, c): 3^b 7^c ≡ 1 (mod 10^K)}. The shadow survives level L (K = L) iff the two classes meet:

  δ := v_w(L) − (b_y, c_y) ∈ Λ_L + K_L.

So every shadow kill is a 2,5-adic incompatibility between the anchor and the ones-extension, measured in the finite group G_L := Z²/(Λ_L + K_L), and a level kills shadows only through |G_L|. Equivalently: 9·2^a 3^b 7^c − 10^n = c₀ (c₀ = 9Σ(d_j − 1)10^{e_j} − 1) is the shadow's limit equation; the levels test it modulo every m = (10-adic) × (primes of 10^L − 1); "cut to extinction" is Skolem's local–global principle for this 3-term exponential equation, open in general (known cases: Schinzel 1975 for one product term; Bartolome–Bilu–Luca 2013 for rank 1; Bérczes–Hajdu–Tijdeman for x^n − b·Π y_i^{k_i} = ±1 only). Baker (the sandwich) is the effective substitute.

**Depth map (gtable.py; |G_L| = 2^α 5^β, exact).**
| L | 96 | 192 | 288 | 384 | 480 | 576 | 768 |
|---|---|---|---|---|---|---|---|
| |G_L| | 2^9·5^4 | 2^9·5^4 | 2^9·5^6 | 2^13·5^4 | 2^10·5^4 | 2^9·5^6 | 2^13·5^4 |
Reading: 192 kills no wrap-0 shadow (G unchanged — matches 256/256 shadows alive at 192 in Cairn's data); 384 is the 2-adic killer (2^13; 1153/1335 cut); 480 adds one bit (2^10; 359 cut); 288 is a different, 5-adic killer (5^6, from 999999000001 = Φ_36(10) combined with the level-96 lattice); 768 adds nothing — hence 6/6 alive. Per prime (align.py): no prime adds more than 2^5 alone; the depth is a property of the whole lattice (saturation), bounded by the 2-, 5-parts of |⟨3,7⟩ mod p| (418725889: 2^13; Φ_48(10) = 9999999900000001 has 5^8 but the cumulative 5-part stays 5^4 at level 96 — misalignment of the modular and 5-adic logarithms).

**Witness test vs pipeline (witness.py on the 43; levels 192/384/768).** Per word: 'A' = δ ∈ Λ_L + K_L, 'x' = not. Every pattern checked so far agrees with the pipeline and with Cairn's per-word fields: cut patterns are 'Axx' on every word (alive at 192, dead at 384 — sh192dead = 0, n384 = k/0), the sandwich pattern 14336 227888 is 'AAA'. (Run still going; the full 43 will be in WITNESS-run.txt.)

**Level 288/480 on the six sandwich patterns (WITNESS-sand6-288.txt).** 288 (5^6) kills two of them outright — 28672 2244788 0 330812181 (word ν=8, r=3: x at 288) and 28672 22224788 0 330812181 (ν=9, r=4: x) — and one word of 28672 2227888 0 78121827 and of 42336 22334677 1 3281116734 (which also loses a word at 480); 14336 227888 and 28672 2244788 0 78121827 survive 288 on every word.

**Registered predictions (step 3).**
(P1) The witness test reproduces Cairn's per-word level-384 verdicts on all 14,325 words: shadow alive at 384 ⟺ δ ∈ Λ_384 + K_384; 0 exceptions.
(P2) A ×3 lift 384 → 1152 (primes of levels 36, 72, 144, 288, 576, 1152 ∤ 384: 19, 3169, 8929, 13249, 52579, 98641, 333667, 1067329, 999999000001, 577, 317752351489, 1153, 23041; trivial image for the additive filter: 19, 577, 1153, 3169, 23041, product ≈ 9.2·10^14 against 3^{r+1} children) closes exactly 28672 2244788 0 330812181 and 28672 22224788 0 330812181 of my six as CLOSED-cut and leaves the other four CLOSED-sandwich; on the 181 robust patterns it converts a fraction near 1/3 (2/6 observed; interval wide) to CLOSED-cut, and no pattern moves toward open. Because G_1152 = 2^13·5^6 is the product of the 384 and 288 depths, the 1152 verdict is predicted by the 288 witness test alone on 384-survivors.
(P3) No level whose |G_L| does not exceed 2^13·5^6 in either part closes any of the remaining ones; cut-to-extinction needs primes with larger aligned 2- or 5-parts of |⟨3,7⟩ mod p| at a usable order of 10 — none among the PH-feasible primes of the levels 96–1152 (align.py), so the sandwich stays for those, with the margin 110+ orders.

**Status.** Mechanism exact (lattice identity, checked on 10/43 + 6 at 288); |G_L| table exact; P1–P3 open for Cairn's 1,335 run and a C ×3 lift.

**P2 tested (extinct1152.py, EXTINCT1152-run.txt; 02:30–03:30 EDT).** The ×3 step 384 → 1152 run on the six: the two predicted patterns — 28672 2244788 0 330812181 and 28672 22224788 0 330812181 — are **CLOSED-cut at 1152** (the shadow passes the five trivial-image primes as the unique Δ′ ≡ 0 child of 81 resp. 243, then dies at the nontrivial primes/window), the other four stay sandwich with exactly one survivor each and bound 10^(10^633.1) (U″ 10^52.6–10^66). 6/6 as predicted, pattern for pattern, from the 288 witness test alone — P2 holds on this set. The prediction was registered before the run (ledger 02:10). A per-pattern cost of ~8 min in Python here (dlogs for the 13 primes once, 498 s); the C port would be seconds.

**Depth map completed (GTABLE-run.txt, 03:30 EDT):** |G_672| = 2^9·5^4, |G_960| = |G_1056| = 2^10·5^4, **|G_1152| = 2^13·5^6** — exactly the product of the 384 (2^13) and 288 (5^6) depths, as P2 assumed; 672 and 1056 (the additive-kill ladder levels) add no depth at all, so they can kill non-shadow children only, never a wrap-0 shadow.

**P1 on the 43 (WITNESS-run.txt complete, 04:05 EDT):** per pattern, the number of words with δ ∈ Λ_384 + K_384 equals the pipeline's number of level-384 survivors (SHADOWCERT-run-v2.txt) on **43/43 patterns, 74/74 words**; every word is 'A' at 192 (192 never kills a shadow) and 384/768 agree on every word (G_384 = G_768). The witness test is therefore an exact, lift-free predictor of the shadow's fate on this set; P1 on Cairn's 14,325 words stays open.

## X18 continued — base 8, the full final stage (wordlift_b.py on all 1,058 patterns, WORDLIFTB8-full-part{1,2}.txt; wordlift_b2.py 96 → 192 → 384 on the survivors, WORDLIFTB8-384.txt; 2026-10-23 01:00–09:00 EDT, chat box, one reboot survived by --skip)

Level 192 (additive filter at 3457, exact test on the 4,066 of 511,608 children that pass it, 11,779 words): **918 of 1,058
patterns closed outright**, 140 keep level-192 survivors (1,690 cosets, bound 10^(10^78.7–79.7) digits), spread over all
k = 2 … 10. Second doubling 192 → 384 (new PH-feasible primes 769, 274177, 17047297, 628582818817; the words' lattice has
trivial image at 769 only, so the filter is Δ ≡ 0 mod 769 — the shadow and ≈ 1/769 of the rest): of the 174 (key, entry)
cases re-run, 46 close at 384 and **94 keep shadow-type survivors, 491 cosets, bound 10^(10^141.2–142.8) digits** (the rest
closed at 96/192 as before). Same picture as base 10 (X20): the base-8 window is 2-adic only, so the compatibility group
is a 2-group and the shadows that pass 384 are the ones whose δ is 2-adically compatible; the kills at 384 are
2-adic. What closes the 94 is the base-8 sandwich: the lower bound 10^(10^141) against the base-8 U″(k ≤ 10) table
(Cairn's Mac base-8 sandwich; base-10 U″(10, a) ≈ 10^80 for comparison) — to be read off, not computed here. Status:
base 8 final stage = 918 cut at 192 + 46 cut at 384 + 94 sandwich at 10^141 (one key may carry several entries; counts
are per log line).

**τ test complete (HSHADOW §7 addendum, 08:15 EDT):** 1,335 patterns / 15,050 representations / 14,325 words, 0 mismatches of
τ ≡ −w/9; τ ≠ 0 on exactly the 16 words of the 5 wrap-1 representations in Cairn's 4 patterns; wraps 9, 10, 18 (1,272
representations) never have words.
