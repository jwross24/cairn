# What the open patterns are: every one is an exact improper representation of a small S-unit

*2026-10-20 00:20 EDT, chat session. Computation: `classify_open.py` over `runall_final.jsonl`,
`trees_c.jsonl` (34 cloud vertices), `trees_mac.jsonl` (33 Mac vertices, 20:30 snapshot). Calibration:
STRONG-EMPIRICAL for the sweep so far (exact check on every recorded open pattern), with a precise
statement that can be re-checked by anyone from the jsonl files.*

## Statement

Let P = (ν, {(d_j, e_j)}) be a residue pattern at level L = 96 (ν = n mod L, e_j = positions mod L).
Call an integer y an **exact anchor** of P if

    y = R_ν + Σ_j (d_j − 1)·10^{e_j}   over the integers, with 0 ≤ ν, e_j < 96,   (†)

where the positions are the pattern's residues taken as integers in [0, 96). (†) is a *representation*
of y that may be **improper**: a position e_j ≥ ν ("a digit above the top"; it acts as extra leading
1s), or repeated positions whose (d−1) contributions carry. A proper representation (all e_j < ν
distinct, ν = number of digits of y) is y itself written with its digits.

**Finding (00:45 EDT, all results to date: 53 cloud-v1 vertices, 34 cloud-C vertices, 43 Mac vertices as of
00:05).** 299 distinct open (vertex, multiset, anchor) triples over 47 vertices. **Every one has an exact
anchor y = 2^a 3^b 7^c with y ≤ 1134213192**, the pattern's own exceptional coset point (the Babai-nearest
lattice point the engine already computes), with (†) holding over Z — in one case (vertex 14336,
anchor 71442, ν = 95 with a 2 at position 95) with the pattern value equal to y + R_96, i.e. the digits
above the top wrap a full period; (†) is therefore stated as pattern value ∈ y + {0, R_96}. Breakdown:
33 SELF (the vertex's own known child; a = t silences Lemma B), 243 anchored on a zero-free S-unit of
the 10^4000 corpus, 23 anchored on an S-unit with a 0 digit (e.g. 1067311728 = 2⁴3⁴7⁷ for vertex 32928
— a genuine S-unit the residues cannot tell from a zero-free one). 73 distinct anchors; 111132 = 2²3⁴7³
carries 63 patterns, 13122 = 2·3⁸ 31, 1417176 and 413343 13 each. Base 6 (20 open patterns over 5
vertices, `classify_base.py`): 3 SELF, 17 anchored, 0 unexplained.

## Why this explains the method's failures completely

If (†) holds then for every candidate y′ of the pattern — n ≡ ν, E_j ≡ e_j (mod 96) — we have
y′ − y = 10^ν R_{n−ν} + Σ (d_j − 1)(10^{E_j} − 10^{e_j}), every term divisible by R_96 = (10^96 − 1)/9.
So y′ ≡ y (mod R_96): no prime of any level ≤ 96 can separate y′ from y, the lattice coset of the
pattern is exactly (b_y, c_y) + Λ_96 with Λ_96 = {(Δb, Δc) : 3^{Δb}7^{Δc} ≡ 1 mod R_96/gcd}, and
10-adic pinning and descent see the digits of y, which are consistent by construction. The pattern
is open at level 96 *because y exists*. Lifting to level 192 keeps one child alive (the one whose
positions keep the identity), so the pattern is open at every level: the method converges to
{y} only at level ∞. Modular methods cannot close an anchored pattern; this is now a theorem about
the method, not an observation.

Conversely every open pattern we have IS anchored. So the sweep's open set is exactly
"shadows of real small S-units", and the single residual question for the ⟨N_open⟩ bounded vertices is:

> **(Impersonation problem.)** Let y = 2^a 3^b 7^c < 10^10 and let (†) be an improper representation
> of y with positions < 96. Is there an S-unit y′ = y·3^{Δb}7^{Δc} ≠ y, (Δb, Δc) ∈ Λ_96, whose decimal
> digits realize the pattern properly (n ≡ ν, n > max E_j, positions distinct)? The lattice gives
> |(Δb, Δc)| ≥ 10^27, i.e. y′ has ≥ 1.3×10^27 digits; the claim is that there is none at all.

This is sharper than OPEN-PROBLEM.md's middle-gap question: y′/y is a unit ≡ 1 mod R_96, so the
question is about the digits of y·u for u in a fixed rank-2 subgroup of ⟨3,7⟩, the kind of statement
(digits of S-units in a multiplicative subgroup) where Stewart/Bugeaud-type results live — still
log-log effective there, but the object is now a single explicit lattice per pattern.

## Consequences for the program

1. The "closed below 10^27 digits" vertices need no further enumeration at any level: each open
   pattern's residual set is one explicit coset of Λ_96 around a listed anchor. Table B of the paper
   should list the anchor per open pattern (`classify_open.py` prints it).
2. The same classifier runs on bases 6 and 8 (`run_base.py` records the exceptional point); if every
   open pattern there is anchored too, the base-6/8 theorems have the identical residual statement.
3. A planted-child red-team now has a precise target: an impersonator y′ of an anchor y. Any y′ with
   < 10^27 digits is excluded by the lattice; the adversary must beat the lattice, not the residues.
4. Nothing here touches target 0.

## Check it yourself

    python3 classify_open.py runall_final.jsonl trees_c.jsonl trees_mac.jsonl      # classes + anchors
    python3 classify_base.py 6 base6.jsonl 12,24,48                               # same for base 6 / 8
    python3 -c "import classify_open as C; print(C.exact_identity((2,2,3), 111132))"   # -> (5, (1, 0, 5))

(5, (1, 0, 5)) is for M sorted descending (3, 2, 2): 2·10^1 + 1·10^0 + 1·10^5 + R_5 = 20 + 1 + 100000 + 11111 = 111132 ✓
— a 5-digit pattern with a 2 above the top at position 5, which the residues read as a sixth leading 1.
