# Theorem U-double-prime (candidate, not adopted): Yu 2007 Theorem II replaces the 5-adic step

Status: PROVEN-ON-PAPER at most, conditional on Matveev (BMS Thm 9.4) and on Yu, Forum Math. 19 (2007), Theorem II and
Theorem 1 as printed. Not Lean-checked. Nothing here edits tier0/ or the adopted U-prime.

## Theorem quote (Yu 2007, printed p.260, PDF page 74)

"Theorem II. Under the hypotheses of the Main Theorem, we have ord_p(Xi - 1) < C_2(n, d, p) h_0(a_1) ... h_0(a_n) h^(2)."

Main Theorem (p.190): n >= 2 and (1.5); a_1..a_n multiplicatively independent; b_j in Z, not all zero;
(1.15) ord_p a_j = 0; (1.16) ord_p b_n <= ord_p b_j for all j. (1.5), p.188: ord_q(p^f - 1) = 1 or zeta_4 in K when q = 2.
C_2 is (1.7), p.189:
C_2 = c^(2)/p^kappa * (a^(2) e p^kappa)^n * (n+1)^(n+1)/(n-1)! * p^f/q^u * d^(n+2)/(f log p)^3 * log max(d,e) * max(log(e^4 (n+1) d), e_p, f log p),
where e is Euler's number (confirmed by (13.1), p.260, which carries 1/e^n in C_1/C_2). h^(2) is (1.10), p.189, with
B-circ = min over nonzero |b_j| (1.11) and G_2 (1.9). Case III values (p.194-195): c^(2) = 394(p-1)/(p-2), a^(2) = 8, a_0^(2) = 1 + log 8, a_1^(2) = 2.4, a_2^(2) = 6.44.
Part II applies when n/(f log p) > e_p*theta + 0.6 (p.188, (13.2)); otherwise Lemma 13.1 (p.260) reduces to Theorem I.

## Hypothesis check (p = 5, K = Q(i), d = 2, prime (2+i): e = f = 1, N = 5, kappa = 0, q = 2, q^u = 4, case III)

| Hypothesis | Status |
|---|---|
| (1.5): ord_2(5-1) = 2, so zeta_4 in K needed | holds for K = Q(i) (Q alone fails; the 2013 paper's weaker condition is not used) |
| n >= 2 | n = 3 |
| a_j in K, ord_p a_j = 0 | 3, 7 yes. a_3 = 2^a/T_j: T_j = sum_{i>j} c_i 10^E_i - 1 with c_i = 9(d_i - 1); mod 5 it is -1 (E_k > 0) or 4 d_k (E_k = 0), nonzero for d_k != 5. Re-derived here; the exclusion of digit 5 is the adopted U-prime premise |
| b_3 = 1, so (1.16) | holds (ord_5 1 = 0) |
| Xi != 1 | M - T_j = N_j 10^E_j > 0 |
| multiplicative independence of (3, 7, 2^a/T_j) | holds iff T_j is not +-2^a 3^u 7^v. In the dependent case Theorem II does not apply; see below |
| B-circ = 1 | log term 0 |
| heights | h_0(a_3) <= a log 2 + log T_j <= H; the bound C_2 h_0 h_0 h_0 h^(2) is increasing in h_0(a_3) (derivative argument), so an upper bound H is valid |
| exponents bounded by B = 2.1 nu + 2 | b + 2 <= 2.0959 n + 2, c smaller; used as in U-prime |

Dependent case (T_j = +-2^a 3^u 7^v, so Xi = +-3^x 7^y or -1 times that): handled with Yu Theorem 1 (p.193, proof in section 11, no independence
needed, units and (1.5) only) with n = 1, 2 for the + sign (exponent bound |x|,|y| <= B, so B' = 2B) and n = 3 with the third number -1
(modified height L/(k_1 (n+4) d) = log5/140) for T_k = -1. The chain takes F = max(Theorem II branch, dependent branch) at every stage.
The dependent branch is height-free. This is the same structure as `main_rig` in math/yu-audit/yu_chain.py.

Not verified, stated gaps:
1. Yu's Part II prints 12 "we omit the details" statements (pp.261-279, first at Lemma 13.2, last at the end of section 19). Theorem II is stated and proved modulo those; I did not reconstruct them.
2. Matveev's theorem and the U-prime top-down chain are reused unchanged (not re-audited).
3. The new monotonicity lemma below is a paper argument plus a grid check, not a certified computation.
4. The application identities (M, T_j, N_j, a >= 1 forces E_k = 0) are taken from the adopted U-prime text.
5. Slip in the earlier audit: math/yu-audit/yu_consts.py and math/codex-yu-check.md omit the factor e^n in (1.7); Theorem II's constant is 10^(9.3028 + 1.3029) = 10^10.606, not 10^9.3028. Predicted 230.2 / 324.3 (k = 31 / 44, a = 0) were understated; correct values are 246.02 / 344.98.
6. Pre-existing, not mine: math/codex-yu/yu2007.txt and yu2013.txt are text extractions of the owner-supplied PDFs inside the repo.

## Monotonicity lemma (replaces BAKER-CHAIN section 5.1 for the non-polynomial Z side)

Claim: for nu >= e^(k+1), Phi_m(nu)/nu is strictly decreasing, Phi_m = X_m + Z_m. X_m is a polynomial in T = 1 + log(2.1 nu + 2 + a) with
nonnegative coefficients (section 5.1 argument). For Z_m, write F(H, B) = max(c H max(G, g), D log 2B), g = log(w(B/H + 1/log 3)).
With r = (B/H)/(B/H + 1/log 3) in (0,1), the elasticity of F in H is 1 - r/g in [0,1] (g > G > 1 where g is selected) and in B is r/g.
If the elasticity of H in B is at most 1, the elasticity of F(H(B), B) is at most eps_H + (r/g)(1 - eps_H) <= 1. H_j = a log 2 + q_{j+1} log 10 + log 80
has elasticity at most that of q_{j+1}; the innermost H is constant; the dependent branch has elasticity 1/log 2B < 1; a max of such functions keeps the bound.
So Z_m/B is nonincreasing and, since B = 2.1 nu + 2, Z_m/nu is strictly decreasing. Grid check (logs/finalstage/monotone_u2.txt): 717,931 points over
(k, a) in {(3,0),(6,0),(6,1),(11,1),(24,0),(24,24),(31,0),(31,40),(44,0),(44,1)}, all m, nu up to 10^1200: 0 violations.

## Table and checks

`tools/mk_utable_u2.py` (new; mk_utable_prime.py untouched): X chain as in U-prime, Z chain with F above, one bisection on min_m Phi_m(nu)/nu, then
integer N rounded up and certified with mpmath intervals at 256 bits (Phi(N) < N and N > e^(k+1)). Entries are min(U-double-prime, U); no entry needed the clamp.

```
cd research/intake/persistence/tier0-opt/cport
nice -n 10 uv run --no-project --with mpmath python tools/mk_utable_u2.py --out data/utable_u2.txt --log logs/finalstage/utable_u2.log --prime data/utable_prime.txt
nice -n 10 uv run --no-project --with mpmath python tools/mk_utable_u2.py --selftest
nice -n 10 uv run --no-project --with mpmath python tools/cross_utable_u2.py 31,0 31,1 31,40 44,0 44,1 44,40
```

| k | a | log10 U-prime | log10 U-double-prime (certified) | second typing |
|---|---|---|---|---|
| 31 | 0 | 281.50 | 246.0183 | 246.0183 |
| 31 | 1 | 279.23 | 232.7809 | 232.7809 |
| 31 | 40 | 280.06 | 233.4949 | 233.4949 |
| 44 | 0 | 402.11 | 344.9831 | 344.9831 |
| 44 | 1 | 393.93 | 334.9920 | 334.9920 |
| 44 | 40 | 394.75 | 334.9932 | 334.9932 |

U-double-prime <= U-prime at 600 of 600 entries (strictly less at 576; the 24 equal entries are k = 1, a >= 1, where the Z side is empty). 0 entries exceed U.
Second typing (`tools/cross_utable_u2.py`, fixed-point iteration instead of bisection, constants retyped from the theorem) agrees on all 600 points, max |diff| 1.2e-6
(`logs/finalstage/cross_utable_u2.txt`). Pipeline check: with the e^n factor dropped the tool reproduces yu_chain.py main_rig (230.18, 324.26, 222.53, 317.78).
No-Claim: two typings of one derivation are not an independent proof. Sandwich depth needed: 5 at k = 31 and 7 at k = 44 (lower bound 10^(72+48(D-1))).
Planted negative: `--selftest` shows N at 0.99 of the certified value refused at (6,0), (11,1), (31,0), (31,40).

## Gate and final stage

43 survivors under the new table (`SANDWICH-full-U2.txt`): 43/43 CLOSED, 33 at depth 1 and 10 at depth 2 (U-prime: 16 and 27), smallest margin +4.93 (U-prime: +0.33).
Planted negative: a table with every entry 10^400 closes 0 of 43 (`SANDWICH-full-U2-negative-inflated-table.txt`).
`cport selftest --lattice data/lattice96.txt` PASSED (`logs/finalstage/selftest_u2.txt`; it does not read the table, so it is independent of U).

Final stage, fresh snapshot (`logs/finalstage/manifest-u2.json`, trees_mac 6,664,709 bytes, md5 a6911e81), no reuse, 2 processes, nice 10:
138 vertices, all 138 CLOSED; 8027 open patterns: 6692 Lemma C depth 1, 1335 sandwich, 0 left; wall 4079 s (`FINAL-STAGE-run-U2.txt`).
Against the U-prime run (137 vertices, 7645 patterns, 6426 / 1219): no vertex has fewer patterns or fewer sandwich closures; the only new vertex is 3211264 from the larger snapshot.
Lemma C depth 1 does not read the table, so every pattern the sandwich closed under U-prime is a depth-1 survivor here and is closed here; U-prime per-pattern status files were not found, so this is a per-vertex comparison.

## Commands for the gate

```
nice -n 10 uv run --no-project --with sympy --with gmpy2 --with mpmath python tools/sandwich_full.py --out <dir> --jobs 2 --timeout 600 --utable-file data/utable_u2.txt
nice -n 10 uv run --no-project --with sympy --with gmpy2 --with mpmath python tools/final_stage.py --out <dir> --jobs 2 --pattern-timeout 3600 --deadline-epoch <t> --utable-file data/utable_u2.txt
```

## md5

```
cd1e4f5092b5b53896d84a214e5cdf04  data/utable_u2.txt
a60a2b05d44e1a2c25c15e2949288ffb  SANDWICH-full-U2.txt
8198f45204b6f92066748e4e1ae08494  FINAL-STAGE-run-U2.txt
56de0756e983049e8377eb99ac7d3019  logs/finalstage/utable_u2.log
09ee9b936da06086998e7eb3e37341a9  logs/finalstage/cross_utable_u2.txt
7ba16fdb00307d9dc6a7bfbd8d0c139e  logs/finalstage/monotone_u2.txt
742a50aa6e7e83f11b6efe5fe72af2e7  logs/finalstage/selftest_u2.txt
236bf7452d2a802451b39052d2d409ff  SANDWICH-full-U2-negative-inflated-table.txt
3415053b8942e3d036d9a99e1296da8b  tools/mk_utable_u2.py
cdbd8b32cf782e96ed104df18ed367db  tools/cross_utable_u2.py
b95707a1983b6fc6e5c330d90dcfbdbc  cport (binary; differs from the 8c0335e9 recorded in SANDWICH-full-Uprime.txt, rebuilt since)
29105783f886919f0b4cada75a62c8c5  cport.c
```
