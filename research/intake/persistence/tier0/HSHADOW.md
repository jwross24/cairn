# H-shadow explained: why the lift kills, and the final stage without any children enumeration

*2026-10-21 19:10 EDT, chat session. Code `hshadow.py` (measurement), `shadowcert.py` (the final stage with the
certificate); logs `HSHADOW-run.txt` (256 words), `SHADOWCERT-run.txt` (the 43). Builds on WORDLIFT.md.
Calibration: §2 facts are exact computations on the stated samples; §3 is an exact, finite certificate per pattern
(ordinary proof, machine-executed, not Lean-checked); §4 is the cost consequence (forecast). No vertex changes
status: SHADOWCERT-run.txt reproduces WORDLIFT-run.txt verdict for verdict (37 CLOSED-cut, 6 CLOSED-sandwich at
10^238–239 digits).*

## 1. The observation (WORDLIFT.md §5)

Every level-96 depth-1 word W has exactly one level-192 child on 54/54 patterns. `hshadow.py` on 256 words of 200
anchored patterns (k = 8–14): **256/256 have exactly one child, and it is always the same one** — ν unchanged, every
unplaced digit at an even copy (t ≡ 0 mod 2, hence position ≥ 192), nothing newly fixed. Its level-192 pattern
value is V = R_ν + Σ_all (d_j − 1)10^{e_j}, the same number as the level-96 pattern value: the *shadow*.

## 2. The mechanism — three exact facts

1. **Lattice content.** Λ_96 ⊆ m·Z² with m = 2^7·3^2·5^4·7·11·41·59·101 (gcd of the basis coordinates; exact).
   The words' sub-lattice Λ'_a = Λ_96 ∩ {3^b7^c ≡ 1 mod 5^96·2^(96−a)} (the same lattice for every word of a
   pattern with exponent a) has content 2500·m for a = 0 — in particular 2^9·3^2 | content.
2. **Trivial images at 193 and 769.** The level-192 primes are 193, 769, 19841, 976193, 6187457,
   834427406578561, 1253224535459902849. Since 192 = 2^6·3 and 768 = 2^8·3 divide the content, every (b, c) ∈ Λ'_a
   has 3^b7^c ≡ 1 (mod 193) and (mod 769): the image of the word lattice is TRIVIAL there (measured index p − 1 on
   31/31 words; indices 640, 448, 704, 1920, 1152 at the other five — small images there too, orders 31, 2179,
   8789, 4.3×10^11, 1.1×10^15). Consequence: the cut of a word's coset at p ∈ {193, 769} is a pure congruence on
   the child's value, V_child ≡ V_W (mod p) for one fixed residue V_W; the shadow (V_child = V) satisfies it
   because the anchor's exact identity does. Any other child has V_child = V + (10^96 − 1)·Δ with
   Δ(S, sn) = Σ_{j∈S} (d_j − 1)10^{e_j} + sn·10^ν/9 (S = unplaced digits moved to odd copies, sn = ν-shift), and
   10^96 − 1 is a unit mod p, so **it survives 193 and 769 iff Δ ≡ 0 (mod 193·769 = 148417)**.
3. **Where the kills happen.** On 2464 non-shadow children of 31 words: 2433 died at the prime cut, 0 at the
   K = 192 window (`fate` measurement); the 31 survivors are the shadows. On 10 words checked exhaustively, no
   non-shadow child had Δ ≡ 0 mod 148417. At level 384 (new primes 3457, 12289, 418725889, 1265011073; images of
   the level-192 shadow lattices have indices 1152, 3072, 21504, 2176) the shadows die at the prime cut too
   (10/10 and 23/24 and 9/12 in the k = 14–16 sample), never at the window; the survivors are the 0–3 per pattern
   that WORDLIFT.md reported, bound 10^239.

So H-shadow is not a conjecture about accidents: the kill is an additive subset-sum congruence, and the shadow is
the empty subset.

## 3. The shadow certificate (`shadowcert.py`) — exact, per pattern, no children enumeration

For a pattern with k digits, exponent a, representation (ν, (d_j, e_j)) and depth-1 words W_1..W_w:
1. Check the trivial image: the basis of each word's lattice maps to 1 mod 193 and mod 769 (two modexps per
   vector; asserted — if it ever failed, the certificate would not apply and the word lift would be used).
2. One DP over Z/148417 across ALL k digits lists every (S, sn) ≠ (∅, 0) with Δ(S, sn) ≡ 0 mod 148417 — cost
   k·148417 word operations, independent of the number of words. Expected number of candidates 2^(k+1)/148417.
   Each candidate is tested, for each word with S ⊆ unplaced(W), at the five remaining level-192 primes
   (exact `child_coset`). If none survives, **every word has exactly its shadow at level 192** — a theorem for
   that pattern.
3. For each word, the shadow's level-192 coset is cut by the four level-384 primes (4 discrete-log cuts; the shadow's
   V is the same number at every level) and, when it passes, by Lemma C depth 1 at K = 384 (copy 2 of each
   unplaced digit is in the window). Survivors: exact nearest-point bound vs U″.

Result on the 43: **43/43, verdicts identical to the word lift and to the sandwich** (37 CLOSED-cut, 6
CLOSED-sandwich with bound 10^238.2–239.1 against U″ ≤ 10^66); the DP produced 0 candidates on all 43; 574 s
in Python, ≈ 150 s of it setup. On the k = 14–16 sample the DP gave 0 candidates on 17 of 19 patterns, 3 and 2
on the other two (none of which survived the remaining primes — the asserted single child held on every word).

## 4. What this does to the Tier-B final stage (TIERB-FINAL.md §3, WORDLIFT.md §5)

Per surviving pattern the cost was Σ_words 2^(r+1) children (≈ 3^(k−9) at k = 20–29: dead). It is now
k·148417 (one DP) + #words × (4 modexps + a rare window test). The words are the depth-1 survivors of Lemma C,
which the C port already enumerates (its depth-1 DP); for a Tier-B anchor with ≈ 20 digits above position 9 that
is up to ≈ 2^20 words × 4 modexps ≈ 10^7 operations ≈ 10 ms in C per pattern. With ≈ 2×10^9 surviving patterns:
≈ 2×10^7 s ≈ **230 core-days, against 2.7×10^4 core-days for the enumeration — the final stage becomes ≈ 1 % of
Tier B instead of a second wall.** (Forecast; the words count at k = 29 is extrapolated, and the Lemma C depth-1
rate from TIERB-FINAL.md §2 is used.) For k ≥ 31 the same certificate runs to level 768 (new primes to be
PH-checked); 10^239 at level 384 already exceeds U″ for k ≤ 30.

The same mechanism (small image ⇒ additive congruence) is the right lens on the sweep's own lifts 12 → 24 → 48 → 96:
there the lattice is the full ⟨2, 3, 7⟩ image with small index (40 at level 12), so the congruence sets are large
and the kill is weak (1/40) — which is exactly why the enumeration, not the final stage, is Tier B's wall.

## 5. Verification and residuals

- Exact facts: content of Λ_96 (basis gcd, factored), image indices (orders of the basis images, exact via
  `n_order`), child fates (exhaustive per word on the stated samples), DP candidate counts (exhaustive).
- Cross-check: SHADOWCERT-run.txt ≡ WORDLIFT-run.txt ≡ SANDWICH verdicts on the 43 (three different final-stage
  algorithms, same 37 + 6 split, same six sandwich patterns).
- Open: (i) a one-line lemma that content(Λ'_a) is always divisible by 768 (it is a computed property of Λ_96 plus
  the 2-adic and 5-adic cut kernels; the code asserts it rather than assuming it); (ii) the DP with explicit mask
  lists is fine to k ≈ 20 — for k = 29 use the counting DP with backtracking (noted in the code); (iii) a blind
  re-implementation of §3 (the (S, sn) ↔ child correspondence and the ν-shift term 10^ν/9) is the right next check;
  (iv) port into the C final stage and re-run the 1335 patterns.

## 6. The lemma, stated (added 21:40 EDT; Lean candidate)

**Lemma (additive kill).** Let Λ ⊆ Z² be a lattice, p a prime ∤ 30·7 with Λ ⊆ Ker_p := {(b, c) : 3^b 7^c ≡ 1 (mod p)},
and C = w + Λ a coset. For V ∈ Z with V ≢ 0 (mod p), write C ∩ cut_p(V) := {(b, c) ∈ C : 2^a 3^b 7^c ≡ V (mod p)}.
Then C ∩ cut_p(V) is either empty or all of C, and it is all of C iff V ≡ 2^a 3^{w_b} 7^{w_c} (mod p). In particular,
if V₀ satisfies it and V = V₀ + u·Δ with p ∤ u, then C ∩ cut_p(V) ≠ ∅ iff Δ ≡ 0 (mod p).
*Proof.* For (b, c) = w + λ with λ ∈ Λ ⊆ Ker_p, 3^b 7^c ≡ 3^{w_b} 7^{w_c} (mod p), a constant on C. ∎

**Lemma (content).** If ⟨3,7⟩ ⊂ (Z/Q)^* ≅ Z/d₁ × Z/d₂ with d₁ | d₂ and Λ = Ker_Q, then every vector of Λ is
divisible by d₁, and Λ ⊆ Ker_p whenever (p − 1) | d₁ (Fermat). *Proof.* Z²/Λ ≅ Z/d₁ × Z/d₂; the Smith normal form of
a basis matrix of Λ is diag(d₁, d₂), and the gcd of the entries of any basis matrix equals its first elementary
divisor d₁; then Λ ⊆ d₁Z² ⊆ (p−1)Z² ⊆ Ker_p. ∎

**Application.** Λ = Λ′_a (the words' lattice), p ∈ {193, 769}: the first lemma's hypothesis Λ′_a ⊆ Ker_p is verified
exactly for every a ≤ 160 (EXPERIMENTS-X §X8; for a ≤ 85 it also follows from the content lemma, d₁ ⊇ 2^9·3^2), V₀ = the
word's shadow value, u = 10^96 − 1 (a unit mod p since ord_p(10) ∤ 96), Δ = Δ(S, sn). Hence the child (S, sn) passes
193 and 769 iff Δ(S, sn) ≡ 0 (mod 148417) — the certificate's DP condition — with no reference to the particular word
beyond its lattice. The same two lemmas give the level-480 statement with the seven primes and Δ′ (EXPERIMENTS-X §X4).

## 7. The target τ is the wrap (added 2026-10-22, from Cairn's G2 finding)

Cairn's port found 16 words (4 patterns) whose shadow fails 193 and 769, all with the DP target τ = 65963. Explanation
and lemma: for a representation y + w·R_96 = V = R_ν + Σ (d_j − 1)10^{e_j} with wrap w, every word's coset base point
w′ lies in the anchor's Λ_96-coset, and Λ_96 ⊆ Ker_p for a trivial-image prime p, so 2^a 3^{w′_b} 7^{w′_c} ≡ y (mod p);
hence τ_W = (2^a 3^{w′_b} 7^{w′_c} − V)/(10^96 − 1) ≡ (y − V)/(10^96 − 1) = −w·R_96/(10^96 − 1) = **−w/9 (mod p)** — the
same for every word of the representation, and −1/9 ≡ 65963 (mod 148417) exactly (checked: the two 3211264
patterns have wrap 1; the 393216 patterns have wrap-0 and wrap-1 representations, Cairn's τ = 65963 words come from
the latter). So: a wrap-0 representation's level-192 survivor at the trivial primes is the shadow (Δ = 0); a wrap-w
representation's is whichever child has Δ(S, sn) ≡ −w/9 — never the shadow when p ∤ w. The DP target is a property of
the representation, not of the word; shadowcert.py (v2) computes it per word anyway, which costs nothing and asserts
nothing. Prediction for Cairn's data: every τ ≠ 0 word has τ ≡ −w/9 with w its representation's wrap (65963 ↔ w = 1,
131926 ↔ w = 2, …).

*Hypotheses, stated explicitly (Codex blind retype P10, 2026-10-23 00:39, found each necessary with an L = 96
counterexample when dropped):* (i) the word's base point w′ lies in the anchor's Λ_96-coset (true for every Lemma C
word: the cut only intersects with sub-lattices of the anchor coset); (ii) the word lattice Λ_W has trivial image at p —
Λ_W ⊆ Λ_96 ⊆ Ker_p suffices, and for 769 this needs the word lattice, not Λ_96 (content(Λ_96) = 2^7·3^2·5^4·7·11·41·59·101
has 2-part 2^7, so the content lemma does not give 769 for Λ_96; 769 is trivial for Λ_96 by the orders ord 3 = 48,
ord 7 = 256, and for Λ′_a by its content 2^9·3^2·5^8·7·11·41·59·101, which 768 divides); (iii) p ∤ 10^96 − 1, so the
division by 10^96 − 1 is legitimate; (iv) for the claim "Δ = 0 never passes", p ∤ w. Chat-side test on Cairn's
1,335 patterns (`tautest.py`, run 2026-10-23): per word, τ from the base point against −w/9 with w = (V − y)/R_96 of
the word's representation; the 6-pattern pilot (incl. two G2 patterns) gives 46 words, 0 mismatches, the τ ≠ 0 words
exactly the words of the wrap-1 representations (2 and 4 — Cairn's sh192dead counts).

**Corollary (wrap ≥ 1 representations die at level 192).** Since V_child ≡ y (mod p) is forced at a trivial-image
prime and y = V − w·R_96, a wrap-w representation has a level-192 survivor only if some (S, sn) has
Δ(S, sn) ≡ −w/9 (mod 148417) — for w ≥ 1 that is never the shadow and never structural: it happens with the
accidental rate 2^{r+1}/148417 (then the other five primes and the window apply). So the only structural level-192
survivors are the shadows of wrap-0 representations; everything else closes at 192 outright or by an accident that
is tested exactly. Consistent with the data: 256/256 words of wrap-0 representations had exactly the shadow; the 16
τ = 65963 words (wrap 1) had accidental single-digit hits, all killed at 384.

## 8. The witness lemma and the compatibility group (added 2026-10-23, 03:15; EXPERIMENTS-X §X20)

**Lemma (anchor witness).** Let V = y be a wrap-0 representation of the anchor y = 2^a 3^{b_y} 7^{c_y}, and let p ∤ 10 be any
prime. The shadow's modular condition at p — 2^a 3^b 7^c ≡ V_shadow (mod p) with V_shadow = V — is satisfied by (b_y, c_y).
Hence for every level L the shadow's modular coset is (b_y, c_y) + Λ_L, never empty, and no prime cut at any level kills a
wrap-0 shadow. More generally every *local* condition that the integer y itself satisfies (its 3-adic and 7-adic
valuations included) is witnessed by y; the only condition y does not satisfy is the length: N has more than K digits,
expressed by the window 2^a 3^b 7^c ≡ W_K := R_K + Σ_fixed (d_j − 1)10^{e_j} (mod 10^K), whose class is v_w(K) + K_K with
K_K := {(b, c): 3^b 7^c ≡ 1 (mod 10^K)}.

**Proposition (survival criterion).** With K = L, the shadow survives level L iff
  δ := v_w(L) − (b_y, c_y) ∈ Λ_L + K_L,
i.e. iff δ maps to 0 in the finite abelian group G_L := Z²/(Λ_L + K_L), whose order is a {2,5}-number (K_L has index
2^{L−a−2}·4·5^{L−1}-type in Z², and Λ_L + K_L ⊇ K_L). Proof: the modular coset and the window class are cosets of Λ_L and
K_L through (b_y, c_y) and v_w; two cosets meet iff the difference of base points lies in the sum of the lattices. ∎
Computed (gtable.py): |G_96| = |G_192| = 2^9·5^4, |G_288| = |G_576| = 2^9·5^6, |G_384| = |G_768| = 2^13·5^4, |G_480| = 2^10·5^4,
and G_1152 ⊇ both 2^13 and 5^6. A level kills wrap-0 shadows only through G_L: 192 kills none (Cairn: 256/256 shadows alive),
384 is the 2-adic killer, 288 the 5-adic one, 768 adds nothing (6/6 alive), and the ×3 step 384 → 1152 closes exactly the
patterns whose δ fails the 5-adic test at 288 (predicted and confirmed on the six, EXPERIMENTS-X §X20 P2).

**What this says about the sandwich.** The shadow is the finite-level image of the limit equation 9·2^a 3^b 7^c − 10^n = c₀
(c₀ = 9Σ(d_j − 1)10^{e_j} − 1), tested modulo every m = 10^K · (primes of 10^L − 1); a shadow that survives all levels is an
adelic solution of a 3-term exponential equation, and "the cut eventually closes every pattern" is Skolem's local–global
principle for it (open in this generality; proved cases: Schinzel 1975, Bartolome–Bilu–Luca 2013 rank one,
Bérczes–Hajdu–Tijdeman x^n − bΠy_i^{k_i} = ±1). The depth available from PH-feasible primes of levels ≤ 1152 is 2^13·5^6
(align.py: no prime adds more than 2^5 alone; depth is a saturation property of the whole lattice, bounded by the 2,5-parts
of |⟨3,7⟩ mod p| and cut by the misalignment of modular and q-adic logarithms), so for the robust survivors the sandwich
(archimedean Matveev + Yu, margin ≥ 110 orders) is not a convenience but the needed effective substitute. (A two-log
p-adic form — v_7(10^n + c₀) = c forces 10^n ≡ −c₀ (mod 7^c) — does not shortcut it: c₀ carries the unplaced digits'
positions, so h(c₀) is not bounded independently of n; U″(k, a) is precisely the k-term iterated-gap bound that handles this,
which is why it grows with k.)

Hypotheses as in §7: wrap 0 (for wrap w the witness is absent and the τ-corollary applies); Λ_W ⊆ Λ_L; the window at K = L
with the shadow's placements (fixed digits at copy 0, unplaced beyond K); nothing else.

**τ-lemma test on Cairn's 1,335 patterns — COMPLETE (tautest.py, 2026-10-23 00:45 → 10-24 08:12 EDT, two reboots survived
by --resume; TAUTEST-all.txt).** 1,335 patterns, 15,050 representations (wrap 0: 13,724; wrap 1: 54; wrap 9: 1,257; wrap 10: 8;
wrap 18: 7), 14,325 words — the port's count exactly. Per word τ from the coset base point against −w/9 mod 148417:
**0 mismatches on 14,325 words.** τ ≠ 0 on exactly 16 words, all from the 5 wrap-1 representations that have words, in
exactly Cairn's four G2 patterns (393216 2222222223488: 8; 393216 222222244468: 4; 3211264 222222277888 a=2: 2;
3211264 2222222247788: 2); every wrap-0 word has τ = 0; no representation of wrap ≥ 2 has a word at all. The §7
prediction holds on the whole set.

**Theorem F with wrap (checked 2026-10-24 14:40–15:10 EDT, check_wplus.py, CHECK-WPLUS.txt).** For a representation of wrap w
(V = y + w·R_96) the depth-1 word (fixed set F, unplaced S_U = Σ_{j∉F}(d_j − 1)10^{e_j}) survives the K = 96 window iff
  10^ν + 9·S_U + w ≡ 0 (mod 2^{a + v₂(d₁) + 2} · 5^{v₅(d₁) + 1}),   d₁ = content(Λ_96) = 2^7·3^2·5^4·7·11·41·59·101,
(with v₂(L) = a and 5 ∤ L for L = R_96 + Σ_F): the congruence set equals the exact `depth1_words` set on 99/99
representations of five patterns (wrap 0: 74 representations, wrap 1: 25 — including the five wrap-1 representations
that carry the 16 τ ≠ 0 words: 4, 4, 2, 2 … exactly), 0 disagreements. Derivation: W_96 − y = (R_96 − R_ν) − S_U + w·R_96,
so 9(W_96 − y) ≡ −(10^ν + 9 S_U + w) (mod 10^96), and the witness criterion is W_96 ≡ y modulo the image of Λ_96 in the
2,5-adic units, which is trivial exactly modulo 2^{v₂(d₁)+2}·5^{v₅(d₁)+1} on the odd part. For w ≥ 1 the term w must be
balanced by the digits at positions < 5 (5-adically) and < a + 9 (2-adically), which is why wrap ≥ 1 representations
almost never survive depth 1 (Tier-B census samples: 0/80,489).
