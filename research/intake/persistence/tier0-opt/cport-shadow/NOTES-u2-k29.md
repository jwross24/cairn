# U-double-prime table extended to k = 29

Status: PROVEN-ON-PAPER at most, conditional on Matveev (BMS Thm 9.4) and Yu 2007 Theorem II exactly as in `cport/NOTES-u2.md`; the code path is
`cport/tools/mk_utable_u2.py` run unchanged with `--kmax 29`. The output goes to a new path; `cport/data/utable_u2.txt` is untouched.
No-Claim: two typings of one derivation are not an independent proof; nothing here is a vertex result.

## Command and output

```
cd research/intake/persistence/tier0-opt/cport-shadow
nice -n 10 uv run --no-project --with mpmath --with sympy --with gmpy2 python ../cport/tools/mk_utable_u2.py --kmax 29 --amax 24 \
  --out data/utable_u2_k29.txt --log logs/utable_u2_k29.log --prime ../cport/data/utable_prime.txt
```

725 rows (k = 1..29, a = 0..24), wall about 40 s. md5 of `data/utable_u2_k29.txt` is 21675a9d; the log has the per-row m (meeting index), log10 U'', log10 U.
Every entry is an integer N rounded up and certified with 256-bit mpmath interval arithmetic (Phi_m(N) < N and N > e^(k+1)), as in NOTES-u2.md.
Entries are min(U'', U); the clamp to U did not fire (U'' < U at all 725 rows; U' exists only for k <= 24).

## Certification (`tools/cert_table.py`, `tools/neg_table.py`, logs in `logs/`)

| Check | Result |
|---|---|
| rows k <= 24 equal `cport/data/utable_u2.txt` (integers) | 600 of 600 identical |
| U'' <= U' at every k <= 24 entry | 600 of 600 |
| U'' nondecreasing in k at every a | holds |
| second typing (`cross_utable_u2.py`, fixed-point iteration, constants retyped) at k = 25..29, a = 0..24 | 125 points, 0 mismatches, max abs diff 1.18e-6 in log10 |
| planted negative: 0.99 of the certified N refused by the interval check | refused at (25,0), (27,1), (29,0), (29,1), (29,24) and at the four points of `mk_utable_u2.py --selftest` ((6,0), (11,1), (31,0), (31,40)) |
| monotonicity grid check of NOTES-u2.md (`monotone_u2.txt`) | not re-run for k = 26..29; the analytic lemma (Codex retype, COORDINATION.md) covers all k, and the grid script is not among the tools |

## Values (log10 of the digit bound; a = 0 / a = 1 / a = 24)

| k | a = 0 | a = 1 | a = 24 |
|---|---|---|---|
| 25 | 196.1246 | 190.6745 | 191.2995 |
| 26 | 203.9475 | 198.0557 | 198.0557 |
| 27 | 213.1364 | 204.6426 | 205.2676 |
| 28 | 217.9444 | 215.0673 | 215.0673 |
| 29 | 230.1824 | 218.6397 | 219.2646 |

TIERB-FINAL.md planned with the interpolated 230.0 / 218.0 at k = 29: the certified 230.18 / 218.64 agree to 0.2 and 0.6 orders.
The level-384 depth-1 bounds observed on the 1,335 patterns lie in 10^238.1 to 10^239.4 (RESULT.md), so they exceed every entry above by at least 7.9 orders at k = 29, a = 0 and by at least 18 orders at a >= 1.

md5: utable_u2_k29.txt 21675a9d, utable_u2_k29.log 7d989706, cert_table_k29.txt 9d6014a0, utable_selftest.txt 1025c24c, utable_k29_negative.txt 03398fb8.
