# Prediction, registered before any computation (2026-10-24)

Question: can the witness-lemma membership delta in Lambda_L + K_L be decided for a whole family of wrap-0 shadows at once?

Reading of the sources, before computing (no number below comes from a run in this directory):

- HSHADOW section 8 and PAPER 3.10': for a wrap-0 representation V = y the shadow survives level L iff delta = v_w(L) - (b_y, c_y) lies in Lambda_L + K_L, a finite {2,5}-group G_L with |G_L| = 2^9 5^4 (L = 96, 192), 2^13 5^4 (384, 768), 2^10 5^4 (480), 2^9 5^6 (288, 576), 2^13 5^6 (1152).
- Any character of G_L pulls back to a Dirichlet character mod 10^L of 2-power times 5-power order, so its conductor divides 2^(alpha+2) 5^(beta+1) where |G_L| = 2^alpha 5^beta. Hence the membership should reduce to a lookup in a small subgroup T_L of (Z/m)^* with m = 2^c2 5^c5, c2 <= alpha + 2 + a, c5 <= beta + 1.
- Because the shadow differs from y only by X = S_U + 10^nu / 9 (S_U the unplaced digits, nu the leading ones), the verdict depends on the anchor only through y mod m, and a word with X = 0 mod m is alive at every level by construction.

Predictions (each falsifiable by the runs named):

P1. Conductor. The exact minimal modulus equals the bound: (c2, c5) = (11, 5) at 192 (with a = 0), (15, 5) at 384, (12, 5) at 480, (11, 7) at 288. Falsified if any minimal exponent is larger than the bound.
P2. Exactness. The lookup test and the full lattice test agree on 100 percent of wrap-0 words of the 1335 patterns at 192, 384, 480; zero disagreements.
P3. Validation against recorded verdicts (shadow1335.tsv, 1335 patterns): the family verdict never kills a key whose recorded verdict is CLOSED-sandwich at 384 with a wrap-0 shadow survivor; whole-key kill fractions at 192 / 384 / 480 / 1152 are about 0 / 86 / 27 / 91 percent (recorded cut rates 0, 1152 of 1335, 359 of 1335, and about 1/3 of the 181 robust). Allowed deviation: 3 points, from keys whose recorded survivor is a wrap >= 1 accident rather than the shadow.
P4. Structure. At least 95 percent of alive wrap-0 words have X = 0 mod m (structural, independent of y); the rest are accidents with probability near |T_L| / |(Z/m)^*|, about 1e-7 per word.
P5. Compression. Words per key divided by distinct (nu, low-position) profile classes is at least 100 for k >= 14 and below 10 for k <= 8.
P6. Tier C domain. Zero of the Tier C anchors (every S-unit 2^a 3^b 7^c with y < 10^97 in the box) admit a wrap-0 representation for any multiset of the six Tier C vertices, because a wrap-0 representation needs digit sum of (y - R_nu) <= sum(d_j - 1) while a random 97-digit y gives about 430. So the fraction of Tier C families killed whole at levels 192-1152 by the witness test is undefined (coverage 0), and the measured reduction in cost per covered pattern is below 100x (coverage 0 counts as below).
P7. Wrap >= 1 analog. For a Tier C pattern of wrap w >= 1 the number of (S, sn) children passing 193 and 769 is about 2^(k+1) / 148417 (29,000 at k = 31; 2.4e8 at k = 44), position-independent within Poisson noise, so no family of free-position patterns is killed whole at level 192 by the trivial-image primes.

Verdict rule: if P6 or P7 holds, the kill criterion (below 100x per pattern on the Tier C sample) fires and the result is reported as negative, "do not retry without new data". Probability that the criterion fires: 0.85.
