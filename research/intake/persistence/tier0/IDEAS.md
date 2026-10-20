# Breaking the even-target frontier: ideas, tested against the numbers (2026-10-19 evening)

The frontier after the current sweep: 18 vertices at 10^15–10^22 residue patterns. Enumeration
cost is ~12^q / symmetry; the observed level-12 survival is a stable 1/40 of patterns (then the
a-split and tail test kill 99.98% of those). Any idea must either shrink 12^q by orders of
magnitude or replace enumeration. Verdicts below are from arithmetic, not optimism.

## A. Restrict the enumeration by linear congruences (RETRACTED 21:15 EDT — the 3-adic half fails)

The idea: b ≥ 3 ⇒ y ≡ 0 (mod 27) and c ≥ 1 ⇒ y ≡ 0 (mod 7), both linear in the residue pattern,
so prune the enumeration to patterns with 7 | y or 27 | y and handle the rest (y = 2^a 3^b, b ≤ 2,
a ≤ A: finite) directly. Checked: R_n mod 27 is NOT a function of n mod 12 — 10 has order 27 modulo
243, so R_n mod 27 takes 9 values on each class of n mod 12 — and the pruning would need n mod 108,
nine times more n-residues, which eats the gain: kept fraction (1/7 + 1/27 − 1/189)·9 ≈ 1.6 > 1.
With mod 9 instead of 27 (n mod 36, ×3) the kept fraction is (1/7 + 1/9 − 1/63)·3 ≈ 0.71: a 1.4×
gain for real complexity. Not worth it. The mod-7 half alone is sound (R_n mod 7 depends on n mod 6)
but leaves y = 2^a 3^b with b free, which is not finite. Retracted; do not port.

## A′. The actual bottleneck is the lift, not level 12 (measured 21:15 EDT from trees_mac.jsonl)

After Cairn's C work the level-12 pass costs ~8 ns/pattern. Lifting an OPEN pattern to level 24
costs 2^{q+1} children (deduped by digit symmetry: observed ~50–100 per pattern at q = 9), each a
Python lattice/DLog step (~150 µs). Measured: single equations at q = 9 already produce ~9×10^5
level-24 children (vertices 1411788, 268912, 1728), i.e. minutes of Python per equation while C
takes seconds. OPEN-at-12 counts scale with the pattern count (~1 per 7,000 patterns), children
per pattern as 2^{q+1}: the 10^12–10^13 region would need 10^10–10^11 Python lattice steps. The
sweep will stall there within hours. Fix: a C lift pass (`lvlN.c`): read parent OPEN patterns with
their coset representatives, enumerate deduped children by Gray code, compute residues for the new
primes incrementally, Pohlig–Hellman for p up to 10^16 (p − 1 is smooth for every cyclotomic prime
in use), the ℓ-component prefilter and representative CRT relative to the parent lattice, the tail
test at the new K. Python keeps only descent and exact verification. Expected ≥ 300× on the lift.
Owner: chat (algorithmic + reference C); constant-factor pass: Cairn, after golden checks.

## B. Meet-in-the-middle (tested twice: does not apply in base 10)

*Addendum 23:50 EDT.* The literature scout found the closest relative of our engine: Dimitrov–Howe,
"Powers of 3 with few nonzero bits" (arXiv:2105.06440), who solved 3^x = (sum of ≤ 22 powers of 2)
by modular lifting *with* meet-in-the-middle. Their MITM works because they choose primes where the
multiplicative side ⟨3⟩ has small order relative to p, so the target set is small. For us the primes
are forced (ord_p(10) | L) and the multiplicative side is ⟨3,7⟩ (a pinned mod 12). Measured over all
108 primes dividing 10^L − 1, L ≤ 60: the smallest |⟨3,7⟩|/p is 5.6×10^−2 (p = 999999000001, L = 36);
MITM needs ~10^−6. Dead, quantitatively. Their Lemma 3.1 on "extraneous modular solutions" is the
right language for our carry coincidences.

The additive side (patterns ↔ sums of (d−1)10^e) and the multiplicative side (2^a⟨3,7⟩) do not
share a group operation, so a split of the digits gives "P + v ∈ T" with T a multiplicative
subgroup of density ~2.5% in Z/m (m ≈ 5.4×10^9). With T as a 675 MB bitmap the per-pattern test
is one lookup — no better than now. MITM needs a collision condition; subgroup membership of a
sum is not one. The carry-coincidence structure is a collision structure, but it describes why
patterns *survive*, not how to enumerate fewer of them.

## C. A different first level (tested: level 12 is special)

Smaller L means fewer patterns (8^q vs 12^q is 25,000× fewer at q = 25) but the kill must come
from rank deficiency of ⟨2,3,7⟩ in ∏(Z/p)^*. At L = 8 (primes 11, 73, 101, 137) the 3-, 5- and
17-parts have rank ≤ 3 so only the 2-part kills: survival ≈ 1/2. L = 6 (13 only) and L = 4 (101)
kill nothing; L = 9 (37, 333667) barely. Level 12 works because 9901 (p−1 = 4·9·25·11) and 37
and 13 add rank in the 3- and 5-parts simultaneously. There is no cheaper level with teeth.

## D. Effective bounds for the gaps (tested: works at the ends, fails in the middle)

Baker–Matveev on a·log2 + b·log3 + c·log7 + log9 − n·log10 bounds the top gap n − e_1; Yu's
p-adic theorem on v_5(9·2^a3^b7^c + 1) (constant +1, height 0) bounds the bottom gap e_q. Both
reduce by LLL to double digits. The middle gaps need v_5(2^a3^b7^c − L_j/9) with L_j the lower
part of the number, whose height grows with its position; Yu's bound then reads e_j ≤ C·e_{j+1}·log B
— gaps may grow geometrically, and the chain gives B ≤ (C log B)^{q+1}, effective but ~10^90 for
q = 31 after reduction. Combined with the lattice (b, c pinned mod ~10^28 at level 96) that still
leaves 10^60 candidates. So: Baker turns "open with a 10^27 bound" into "open with a 10^90
ceiling" — a real theorem (every equation becomes decidable in principle) but not a computation.

## E. Digit-by-digit descent with coset cuts (tested: the all-ones branch never dies)

Building y from the bottom and cutting the (b,c) coset at every digit is exact and cheap, but the
digit 1 always leaves exactly one sub-coset alive (⟨3,7⟩ is the full unit group mod 10^k for
k ≥ 3), so the branch "…1111" is infinite. Only the prime filters can prune it, and they need
the residues of the *remaining* digits — which is the enumeration we were trying to avoid.

## F. Leading-digit sieve per open pattern (real, extends bounds, not closure)

For an open pattern the coset is explicit; frac(a·log2 + b·log3 + c·log7) must put the top W
digits in the pattern's allowed set, a width-10^{−W} window. Fincke–Pohst on the 4-D lattice
(coset × the real linear form) enumerates every coset point with ≤ B digits meeting the window.
Gives "no solution in this pattern below 10^6 digits" cheaply — but the lattice bound is already
10^27, so this only matters for Tier-2 vertices where no coset exists yet, and there it is a
heuristic search, not a certificate.

## G′. Literature verdict (scout, 23:45 EDT)

Nothing in print bounds an interior digit gap of an S-unit with a constant free of the lower part's
height. The state of the art is the Bugeaud–Kaneko chain (Math. Proc. Camb. Phil. Soc. 2018,
arXiv:1704.00432, Lemma 3.1): Matveev for the top, Yu's p-adic bound — whose dependence on each
height is linear and multiplicative — for the rest, with a balancing choice of the gap index that
gives exponent k − 2; the resulting bounds are log log in the size, far beyond computation. Effective
multi-term S-unit equations (Vojta 1983; Bajpai–Bennett, Acta Arith. 2024) stop at 4–5 terms over
≤ 3 places; ours have q + 3 terms over 5 places. Bertók–Hajdu–Luca–Sharma (Publ. Math. Debrecen
2017) close 4-term {2,3,5} problems by modular obstructions exactly as we do and say no effective
tool reaches them directly. So OPEN-PROBLEM.md is genuinely open, including its repunit special
case (the all-ones lower part is already covered by the bottom-gap argument; one non-1 digit below
makes it a 5-term, 5-place equation).

## G. What would actually close the 18 (honest)

A middle-gap bound. Equivalently: a theorem that an S-unit (S = {2,3,7}) cannot have two
consecutive non-1 decimal digits separated by a gap that is super-logarithmic in its size, with
an *effective* constant that does not depend on the height of the lower part. Nothing in the
Baker/Yu toolkit gives this; the closest results (Stewart 1980, Bugeaud 2018 on nonzero digits
of S-units) are log-log effective and vastly too weak. This is the research problem. It is a
sharp, well-posed question in Diophantine approximation, and it is the right thing to put in
front of a number theorist — with the 18 vertices as the concrete payoff.

## Verification work done tonight

Mutation testing of the engine against the control corpus: 8 planted defects, 6 caught by the
positive controls (descent exact case, descent valuation, pinning K, lattice sign, prime log,
2-adic bound). The two escapes were diagnostic, not defects: one mutated Python code the C pass
makes dead (the live check in lvl12.c is being mutated separately), the other — dropping the
n-residue lift to level 24 — escaped because **no control in those vertices has ≥ 12 digits**.
Fix: the 14-digit element 11519532122112 (product 10800) as a synthetic lifting control; result
recorded with the mutant runs in this folder.
