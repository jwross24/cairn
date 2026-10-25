# B3: special-family archimedean bounds (2026-10-20)

Written by the Cairn orchestrator from the B3 lane's final report; the lane's own write was refused by the harness.
Scripts beside this file: b3_chain.py, b3_cert.py, b3_neg.py, b3_sens.py, b3_theta.py, b3_lp.py. Nothing is
Lean-checked.

## Best unconditional bound (PROVEN-ON-PAPER, interval-certified numerics)

| k | a = 0 | a = 1 | a = 40 | current table | Codex H5 (unaudited) |
|---|---|---|---|---|---|
| 31 | log10 G′ = 281.51 | 279.23 | 280.06 | 541 / 599 | 332 |
| 44 | 402.12 | 393.93 | 394.76 | ≈ 775 | 465 |

Sandwich depth needed (lower bound 10^(72+48(D−1)) digits): D = 6 at k = 31, D = 8 at k = 44. Not shallow.

Method: two-ended chain, Matveev (BMS 9.4) top-down and Bugeaud–Kaneko Thm 2.1 (2.2) 5-adic bottom-up. BK was read
(page image); Yu's original was not, so BK's printed constant is an assumption. New step: for fixed a ≤ 40, fold
2^a into the one varying rational (2^a/N_j or 2^a/T_j), so Matveev uses 4 logarithms instead of 5 and Yu 3 instead of
4. Per-gap constants at k = 31, a = 0: K0 = 10^14.7, K1 = 10^16.7, Y = 10^18.2. Proved along the way: a ≥ 1 forces
E_k = 0 (M + 1 is odd); 5 ∤ T_j when digit 5 is excluded. Planted negative: N at 0.99 of the fixed point is refused.
The gain is lost if a is unbounded.

## What could not work

1. Hypergeometric / Padé / Thue–Siegel: negative (HEURISTIC; Padé denominators not built). Bennett 1997 Thm 1.1,
   Cor 1.2 read for the form of the result: an effective measure for one fixed (A/B)^(1/m) with λ ≥ 2.2. On the top
   gap it gives g0 ≤ λn/m, linear in n; height-free needs m ≳ n/log n while validity needs m ≲ √n.
2. Gap structure: negative, with a matching construction. Only archimedean prefix and 5-adic suffix constraints exist;
   the LP maximum equals min_m [K0(1+K)^(m−1) + Z0(1+Y)^(k−m)] exactly (checked k = 6, 10, 14), so meet-in-the-middle
   is optimal in this class, about 8.7 digits per gap. Pigeonhole (Bugeaud–Kaneko) has the one-sided exponent. p-adic
   information at 3 or 7 gives n ≲ C·E_{j+1}·s_j, vacuous. Joint p = 2 and p = 5 see the same E_j; the 2-adic form
   fails for a ≥ 1.
3. Bugeaud–Laurent two-log p-adic bounds: inapplicable; our p-adic forms have 3 logarithms.
4. End reduction (Baker–Davenport LLL/CVP): small. Top gap 10^14.7 → about 10^3; with a ≥ 1 the last gap's T lies in a
   7-element set; combined about 10^12. Each further enumerated level trades 10^14 for about 10^4 nodes, worse than one
   more sandwich depth (CONJECTURE; lattice bounds not computed).

## The precise target for a breakthrough

A gap bound "gap ≤ C·h^θ" with S_{j+1} = S_j + C·S_j^θ gives log10 S_k:

| θ | k = 31 | k = 44 |
|---|---|---|
| 0 | 17.8 | 17.9 |
| 0.5 | 34.8 | 35.2 |
| 0.75 | 67.8 | 68.7 |
| 0.9 | 158 | 163 |
| 1 (Baker) | 520 | 732 |

θ ≤ 0.75 would close Tier C at depth 1; height-free (θ = 0) closes below the lattice's 10^27. Every known theorem has
θ = 1. Sensitivity: scaling K and Y by 10^-3 gives 232 / 329; by 10^-6, 186 / 264; D = 3 needs about 10^-8 at
k = 31 and 10^-12 at k = 44.

## Next

1. Audit Bugeaud–Kaneko (2.2) against Yu's original: the largest constant driver; a 10^3 error moves log10 G′ by
   about 15.
2. Per sub-coset, replace k by k − m_known using the known low blocks (E_j < 96D). Cheap; CONJECTURE, not computed;
   no worst-case gain.
3. Drop hypergeometric methods and interior-gap reduction.
4. A step change needs θ < 1 for this family or Baker constants about 10^8 smaller; neither exists unconditionally.
