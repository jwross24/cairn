# H2: per-anchor closure of Lemma C (depth 1)

Calibration labels follow RULE 2. Nothing here is PROVEN (no Lean, no statement review).

## Setting

An anchor is (y, a) with y = 2^a 3^b 7^c, coset C_y = (b, c) + Lambda_96, and a family of open patterns
P = (M, nu, {(d_j, e_j)}) with positions e_j in [0, 96) and y + k R_96 = R_nu + sum (d_j - 1) 10^(e_j).
Lemma C at depth 1 (deepcut.py, D = 1) closes P when for every case S (a set of pattern digits placed at their own
position e_j, at most one per residue class e) the number
L_S = R_96 + sum_{j in S} (d_j - 1) 10^(e_j) fails the test "v2(L_S) = a, 5 does not divide L_S, and
cut_coset(C_y, a, L_S, 96) is nonempty".

## Step 1 (no carries at depth 1)  [PROVEN-ON-PAPER]

At most one digit per class sits at copy 0, so the digit of L_S at position e is
l_e = 1 + (d - 1) = d if class e contributes digit d, and 1 otherwise. Every l_e lies in 0..9 (digits of M are at
least 2), so L_S = sum_e l_e 10^e has no carries. A depth-1 case is therefore a digit string
l in prod_e ({1} union D_e), where D_e is the set of digits of the pattern in class e. Its multiplicity
(number of cases of deepcut that produce it) is prod over non-1 positions of m(e, l_e), the number of pattern
digits equal to l_e in class e. The carries of the pattern (two digits in one class summing past 9) matter only for
the integer identity that defines the anchor, and for depth 2 and beyond, not for depth-1 closure.

## Step 2 (the acceptance test is a congruence)  [PROVEN-ON-PAPER given the group fact; STRONG-EMPIRICAL for the fact]

Group fact (DEEPCUT.md, blind audit): the image S of Lambda_96 in G = (Z/5^96)^* x (Z/2^(96-a))^* is the kernel of
reduction G -> (Z/5^5)^* x (Z/2^9)^*; equivalently S has index 2500 * 256 = 640000 and is contained in that kernel.
Containment is a check on two basis vectors. The index is the audited 2500 and 2^8 for the two projections plus
the joint index 640000 quoted in DEEPCUT.md. The check of the fact here is `equiv_check.py`: cut_coset against the
predicate below on random targets, positive and negative.

Given the fact, the cut congruences 2^a 3^b 7^c = L (mod 5^96 and 2^96) with (b, c) in C_y are solvable iff
L / 2^a is in (y / 2^a) S, i.e.

    Acc_y(L)  <=>  L == y (mod 5^5 * 2^(a+9)).

Acc_y implies v2(L) = a and 5 does not divide L. Let N_a = 5^5 2^(a+9) and w = a + 9; N_a divides 10^w, so Acc_y
reads only the digits l_0 .. l_(w-1).

## Step 3 (the automaton)

Let q_e = y - sum_(i<e) l_i 10^i. Acc_y holds iff q_w == 0 (mod 2^w) and q_5 == 0 (mod 5^5).
Since 10^e = 2^e 5^e, q_e == 0 (mod 2^e) holds inductively and the next digit is forced in parity:
l_e == (q_e / 2^e) (mod 2). So the digit-level automaton A_y reads positions 0..w-1, its state is
(q_e mod 2^w, q_e mod 5^5 while e < 5), it has at most 5 outgoing digits per state (those of the right parity),
and the 5-part is a filter at e = 5. A_y depends on (y, a) only; the pattern enters only through its masks
D_e for e < w.

## Per-anchor closure

Compile once per anchor: the lazily memoized transition table of A_y (and, when a is small, the witness list
W_y = all accepting strings, each recorded by its non-1 entries {(e, l_e)}).
A pattern is OPEN iff some witness has all its entries in the pattern's low profile {(e, d) : e < w, d in D_e};
the number of surviving depth-1 cases is sum over witnesses contained in the profile of the product of
multiplicities, times prod over classes e >= w of (1 + n_e), where n_e is the number of pattern digits in class e
(those digits can sit at copy 0 or not without touching Acc_y). The verdict of a rep is zero survivors.
A pattern is closed iff all its representations are. A signature cache (low profile -> count) shares work among
patterns and representations of one anchor.

This is DEEPCUT's "depends only on the lowest nine digits" made exact: positions below max(5, a + 9), and the
digits of the anchor y modulo 5^5 2^(a+9), nothing else.

## Equivalence claim

For every anchor (y, a) and every representation (nu, De) of a pattern on it, the per-anchor count of surviving
depth-1 cases equals len(stats[0]) of deepcut.deep_cut(C_y, a, rep, 1), and the CLOSED/OPEN verdicts agree.
Argument: Step 1 gives a bijection between deepcut's depth-1 cases (subsets of free digits with at most one per
class) and (string, choice of digits) pairs; Step 2 replaces its per-case test by the congruence; Step 3 counts
accepted strings. Status: PROVEN-ON-PAPER conditional on the group fact; checked (STRONG-EMPIRICAL) by
`diff_run.py` against deepcut.py's own outputs, and by `equiv_check.py`.
Not covered: depth 2 and beyond (not needed; DEEPCUT.md: depth 2 never kills), and cases deepcut abandons at
maxcases (the per-anchor method has no case budget).

## What is and is not reduced

Per pattern the cost falls from 2^(free digits) discrete-logarithm cuts to a pass over at most w layers of a
memoized automaton. The number of patterns per anchor is not reduced by this method: a Tier-C anchor carries
10^6 to 10^9 patterns by the anchor-first census, and testing each costs microseconds. A count of open
patterns without listing them would need a product of A_y (determinized over the masks D_e) with the
representation DP of RESULT-anchorfirst.md (carry and remaining-multiset state). That product is a design,
not prototyped, and its state count is CONJECTURE.
