# Bonuccelli, Colucci, de Faria: Erdős–Sloane and shifted Sloane persistence

Source: G. Bonuccelli, L. Colucci, E. de Faria, "On the Erdős–Sloane and Shifted Sloane Persistence
Problems", J. Integer Sequences 23 (2020), Article 20.10.7, 30 pp.
https://cs.uwaterloo.ca/journals/JIS/VOL23/Colucci/col4.pdf. Read: full text via pdftotext of the
journal PDF, 2026-10-29. Cited in cairn only as background reference [1] of Fonga arXiv:2608.27802.

## What it proves (documented: paper §5)

- Maps: S_{t,b}(n) = Π(d_i + t) (Wagstaff's shift) and S*_b(n) = product of nonzero digits (Erdős).
- **Unconditional.** Theorem 7: under S_{1,b} every n reaches the cycle (2, …, b−1, 10_b) or the fixed
  point 1(b−2)_b. Theorems 6 and 13: lim sup ν(n)/log log n ≤ 1/log(1/α), resp. 2/log(1/α), with
  α = log_b(b−1), from the digit-count recursion k_{j+1} ≤ 1 + α k_j.
- **Theorem 8 (b = 3, t = 1), the one complete backward-orbit classification.** n reaches (2, 10_3) iff
  n or 2^{#1(n)} has no ternary digit 1, otherwise (11_3). It works because S_{1,3}(n) = 2^{#1}3^{#2},
  the 3-part only appends zeros, so the dynamics collapse to powers of 2, plus the invariant
  n ≡ #1(n) (mod 2) (3 ≡ 1 mod 2).
- **Conditional on de Faria–Tresser (Conjecture 1) or its uniform version (Conjecture 4):** unbounded
  persistence for S*_b and S_{1,b} (Theorems 5, 10), matching lower bounds in Theorems 6 and 13,
  stabilization for S_{2,b} (Theorem 15), and divergence for larger shifts (Theorems 17–23).
- Conjecture 11: every large even number 2n is #1(2^{2m})_3 for some m (OEIS A036461, even-indexed terms).

## Carry-over to even targets (verified where marked)

- **The parity invariant does not transfer as a filter.** The base-10 analog is y ≡ digit sum (mod 9),
  i.e. y ≡ n + Σ(d_j − 1) (mod 9) for E(s, M). It would prune only if S missed residues mod 3^k, but
  {2^a 3^b 7^c mod m} covers every residue for m = 9, 27, 81 (verified 2026-10-29, exhaustive over
  a, c < 60, b < 8). The congruence couples n to b and removes no candidate unless b is tracked jointly,
  and cairn's ladder already keeps all three exponents.
- **Theorem 8's collapse has no base-10 counterpart for t = 0.** It needs the product map to land in a
  one-generator family after one step; S_{0,10} lands in the three-generator S.
- Unconditional bounds are log log growth bounds, far weaker than the finite-tree statement the program
  targets.

## Verdict

Low yield for even targets: no method that prunes or settles an equation. Worth one line in sources.md
for the shifted-problem landscape and the A036461 conjecture. Confidence HIGH on "no transferable
method" for the results read (Theorems 5–15); Theorems 17–23 skimmed by statement only.

Leads: forward citations of this paper (2020–2026 persistence work cairn may lack); Wagstaff, "Iterating
the product of shifted digits", Fibonacci Quart. 19 (1981) 340–347 (low priority, recreational);
Herzberg–Murty, Resonance 19 (2014) (survey, low priority).
