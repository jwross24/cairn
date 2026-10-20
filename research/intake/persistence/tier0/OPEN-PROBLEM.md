# An effective gap bound for the decimal digits of 2^a 3^b 7^c

*Draft of the question that would finish the even-target case of Sloane's persistence
conjecture. Written to be posted (MathOverflow / sent to a specialist) once the sweep's final
numbers are in. Owner's call whether and where.*

## Context

Sloane's multiplicative persistence conjecture (base 10, bound 11) is known for odd digital
roots (Brier–Clavier–Gutsche–Naccache 2021). For even digital roots 2, 4, 6, 8 it reduces to the
finiteness and explicit form of trees whose vertices are integers y = 2^a 3^b 7^c and whose edges
are y → p(y), p = product of digits. A vertex s has children y ∈ S = {2^a 3^b 7^c} with p(y) = s;
such y has at most log₂ s non-1 digits, so

  y = R_n + Σ_{j=1}^{q} (d_j − 1)·10^{e_j},   R_n = (10^n − 1)/9,   d_j ∈ {2,…,9},   e_1 > … > e_q.   (★)

We have a computer-assisted method (residue patterns modulo the primes of 10^L − 1, lattice
cosets in (b,c), 10-adic pinning, a 2-adic descent) that closes an equation (★) when it
terminates, and we have closed it for ⟨N⟩ vertices across the four trees; ⟨18⟩ vertices remain
whose enumeration would need 10^15–10^22 residue patterns. For every pattern the method leaves
open, the solutions other than one known small one have more than 10^27 digits.

## What is known

For a solution of (★):
- the **top gap** n − e_1 is bounded effectively: |a log 2 + b log 3 + c log 7 + log 9 − n log 10|
  < 72·10^{e_1 − n}, a linear form in four logarithms (Matveev), reducible by LLL;
- the **bottom gap** e_q is bounded effectively: 5^{e_q} | 9·2^a 3^b 7^c + 1, a 5-adic linear
  form with the constant 1 (Yu), reducible likewise;
- each equation (★) has finitely many solutions (Subspace Theorem; ineffective);
- the number of nonzero digits of an S-unit tends to infinity effectively but only at rate
  log log (Stewart 1980; Bugeaud 2018).

## The question

**Is there an effective C (depending on q, or even on S = {2,3,7} alone) such that every
solution of (★) satisfies e_j − e_{j+1} ≤ C·log max(a,b,c) for every interior gap
1 ≤ j < q?**

The obstruction to the obvious attack: 5^{e_j} divides 9·2^a 3^b 7^c + 1 − (the lower part
Σ_{i>j} 9(d_i − 1)10^{e_i}), i.e. v₅(2^a 3^b 7^c − L_j) ≥ e_j for an integer L_j with about
e_{j+1} digits. Yu's theorem bounds this by a constant times the height of L_j times
log max(a,b,c), and the height of L_j is ≈ e_{j+1}·log 10, so the bound is e_j ≤ C·e_{j+1}·log B:
gaps may grow geometrically and the chain only yields B ≤ (C log B)^{q+1}, far beyond
computation even after reduction. A bound whose constant does not carry the height of L_j —
exploiting that L_j is itself of the sparse form (★) — would make each remaining equation
decidable by LLL reduction and, combined with the lattice method, would very likely close all
⟨18⟩ vertices and hence the even-target case of the conjecture.

Partial credit: the same question for two gaps (q = 2), or for the special case where the lower
part is a repunit (L_j = R_{e_{j+1}}, all lower digits equal to 1), would already resolve a
large class of the open patterns, which are exactly of that shape (the "carry coincidence"
patterns, anchored on 111132 = 2²3⁴7³ and 13122 = 2·3⁸).
