# dpcount — exact level-12 survivor counting by DP over residues: feasibility, validation, Tier-C forecast

Scout directory: `/home/claude/scouts/dpcount/` (2026-10-20). Machine: 2 cores, 7 GB RAM, 30 GB free disk, ≤ 2 CPU-h.

## 0. Verdict in three lines

1. **An exact count without enumerating patterns is possible, and the algorithm is written and validated** (sparse form reproduces the engine's recorded `c_stats` exactly on 12 recorded equations up to 5.4×10^7 patterns, including 11-fold digit multiplicities). Its cost is independent of the number of patterns: ≈ 12·k streaming passes over an array indexed by Z/P, P = 5 291 005 291.
2. **For the Tier-C vertices it is a big-memory job, not a big-CPU job:** the dense state needs `max_d min(m_d+1, 12)` ≈ 12–13 arrays of P cells. With 8-bit cells and CRT over ~10 moduli that is **64 GB of RAM per pass, ≈ 70 TB of memory traffic (≈ 20 min at 50 GB/s) per equation, ≈ 100 node-days for all 6 251 Tier-C equations** (≈ 5 node-days for the smallest vertex, 306 equations). On the 1-TB scale asked about it is feasible (128-bit cells, one pass: 85 GB per array, 1.1 TB total). On this 7 GB machine it is not: the smallest possible full-P state (two 8-bit arrays, 10.6 GB) does not fit.
3. **There is no cheaper exact route**: counting mod each prime separately, character sums, Fourier/CRT splitting and meet-in-the-middle all fail for the same reason (the test is multiplicative, the pattern sum is additive; §1). So for planning, the **Monte-Carlo forecast (§4) is the right tool**: 6.2×10^8 exact-test samples give every Tier-C vertex's survivor count to ±0.1–0.3 % (95 %).

## 1. Feasibility analysis

### 1.1 What the survival test is, as a function of V mod P

P = 11·13·37·101·9901 = 5 291 005 291, ∏(p−1) = 4 276 800 000. the tier0 `FastLevel` over the five level-12 primes gives:

| ℓ | ∏ Z/ℓ^k over the primes | H_ℓ = image of (log 2, log 3, log 7) | index |
|---|---|---|---|
| 2 | Z/2 × (Z/4)^4 (size 512) | 64 | **8** |
| 3 | Z/3 × Z/9 × Z/9 (243) | 243 | 1 |
| 5 | Z/5 × Z/25 × Z/25 (3125) | 625 | **5** |
| 11 | Z/11 | 11 | 1 |

So S = ⟨2,3,7⟩ ⊂ (Z/P)^* has index 40 = 8·5, the 40 characters of (Z/P)^*/S are the 8 characters of the 2-part quotient times the 5 of the 5-part quotient, and 2 is a primitive root mod every one of the five primes (log 2 = 1 everywhere). The a-split is the further quotient by ⟨2^12, 3, 7⟩ (G = 12, N = 9900): a is determined mod 12, and the engine's `(a,pattern)` count is Σ_survivors #{a0 ∈ [0, A] : a0 ≡ v0 (mod 12)} — v0 is empirically uniform mod 12 (§2), so (a,pattern) ≈ survivors·(A+1)/12. The survival set is therefore a union of cosets of a subgroup of index 40 (480 with the a-class) in (Z/P)^*, plus the zero divisors are excluded (V ≡ 0 mod some p happens for ≈ 1/11+1/13+1/37+1/101 ≈ 19–21 % of patterns — the engine's `zero` counts).

Restricted to the four small primes (Q = 534 391) the same construction has index only **2** (ℓ=2 part 128 → 64, ℓ=5 part 125 → 125): almost all of the index-40 selectivity lives in 9901 jointly with the others. This is why no sub-product of the primes gives a useful exact count, and why a DP mod Q is cheap (dp4.c, 8.5 MB per array) but only an upper bound ≈ 20× the truth.

### 1.2 Why nothing factors

The count is ⟨F, f⟩ = Σ_v F(v) f(v) with F = Σ_patterns δ_V (an additive convolution of sparse factors in the group ring Z[Z/P]) and f = indicator of the survival cosets (a function on (Z/P)^*).

* **Character sum.** f = (1/40) Σ_χ χ on units (0 on non-units), χ multiplicative. Σ_patterns χ(R_ν + Σ(d_j−1)10^{e_j}) does not split over digits because χ is not additive — confirmed; the Fourier transform (additive characters of Z/P) of f is a Gauss-sum-type object with full support, so there is no sparse spectral shortcut either.
* **Mod each prime separately.** F mod p for each p is a 5-tuple of small distributions, but f is a joint condition (the 2-part couples all five primes, the 5-part couples 11, 101, 9901); the joint distribution of (V mod 11, …, V mod 9901) is F itself.
* **Meet in the middle / adjoint.** ⟨F_A * F_B, f⟩ = Σ_u F_A(u)·(F_B^− * f)(u): both factors are dense on Z/P. Pushing the convolutions onto f ((F^− * f)(0)) costs the same as building F.
* **Sparse-to-dense transition.** The support of F grows to Θ(P) quickly; the sparse DP's support was already 2.9×10^7 at 5×10^7 patterns (§2) and would saturate P (5.3×10^9) far below Tier-A sizes.

Hence the exact count is exactly one dense DP over Z/P per equation, and its cost is memory.

### 1.3 The DP and its true cost

For digit value d with multiplicity m the m copies form a **multiset** of classes. Two equivalent formulations (both implemented; the Python one is the classes-outer form):

* classes outer, copies inner: arrays A_0..A_m; for r = 0..11, for j = 1..m (increasing, in place): `A_j += shift(A_{j-1}, (d-1)·10^r)` — the geometric series in class r, i.e. the complete homogeneous symmetric polynomial h_m(x^{c_0},…,x^{c_11});
* copies outer, "last class" inner: 12 arrays Q_r (prefix sums), `Q'_r = Q'_{r-1} + shift(Q_r, c_r)`.

Memory = `max_d min(m_d+1, 12) + 1` arrays of P cells; every Tier-C equation has a digit with m ≥ 11, so 12–13 arrays. Work = 12·k shift-add passes (k = number of digits, 17–44), each a cyclic rotation of a P-array by a constant — sequential memory streaming, no random access; ≈ 3 P-byte reads/writes per shift-add in 8-bit cells. Per equation and per 8-bit modulus pass: ≈ 36·k·P ≈ 7 TB of traffic; survivor counts per equation reach 10^20 > 2^64, so ~10 coprime 8-bit moduli (or 5 × 16-bit, 3 × 32-bit, 1 × 128-bit) are needed to reconstruct the count by CRT. Rough totals:

| | RAM | traffic per equation | time per equation @50 GB/s | all Tier C (6 251 eqs) |
|---|---|---|---|---|
| 8-bit cells, 10 CRT passes | 64 GB | 70 TB | ≈ 23 min | ≈ 100 node-days |
| 128-bit cells, 1 pass | 1.1 TB | 110 TB | ≈ 37 min | ≈ 160 node-days |

(The final classification pass — membership class of every residue by five log-table lookups — is 5×10^9 cheap operations, negligible. The symmetric-function alternative h_m = Σ_{λ⊢m} p_λ/z_λ needs only two arrays but ≈ p(m)·ℓ(λ) ≈ 10^3–10^5 × more passes; not attractive.)

A GPU helps little here (the job is bandwidth-bound at ~1 byte/op, ~1 TB/s HBM ⇒ ≈ 1 min per equation but the state does not fit in GPU memory without tiling the rotations). The honest statement: **the exact Tier-C survivor count is a ~100-node-day job on 128-GB-class nodes** (or a few days on a dozen of them), per-vertex ≈ 5 (s=3.4e15), 15, 15, 14, 40, 14 node-days — and it would still only tell the planners the same number the Monte Carlo below gives to 0.1–0.3 %.

### 1.4 A side finding: the engine's 2-adic bound A does not scale to Tier C

`tier0v2.two_adic_bound(M)` (used by `export_cfg.py` for every multiset) tries every digit at every tail position; it did not finish in 2 min for k = 36. The parity of each successive tail digit is forced (d_i ≡ u_i mod 2 with t_i = 2^i u_i, u_{i+1} = (u_i + d_i 5^i)/2), which gives an exact DFS (`twoadic.c`, validated against the Python on all recorded cases and 40 random multisets). But for the 2-heavy Tier-C multisets A itself is ≥ 100–160: the 1's are free and any spare odd digit (3, 7, 9) lets the chain of odd-forced positions be steered, so the number of valid tails explodes (> 10^8 nodes at depth 120–157 without exhausting). **The exact A for most Tier-C multisets is out of reach of this DFS; the forecasts below use the lower bound reached by a 2×10^6-node search (10^8 nodes for the 8 largest multisets per vertex), and report the A-dependent quantities separately from the A-independent ones.** The engine will need a smarter A (e.g. a bound from the lift levels, or a per-a treatment) before it can even configure a Tier-C run.

## 2. Exact reproduction of recorded counts (the "small analogue")

`dp_exact.py` — sparse DP over the full P (numpy sorted-key merge), classification by the engine's own `FastLevel` tables; `dense_dp` mod 5291 and mod 534391 cross-checked against the sparse distribution binned mod those moduli (same patterns, same counts); brute-force enumeration cross-checked on the five smallest. Engine numbers from `/tmp/trees_c.jsonl` `c_stats` (`zero`, `prefilter-dead`, `(a,pattern)`); survivors = patterns − zero − prefilter-dead.

| s | M | patterns | support of F | A | zero | prefilter-dead | survivors | (a,pattern) | engine (zero, pre, (a,pat)) | match | DP + classify time |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 128 | 2·8·8 | 11 232 | 11 232 | 9 | 2 352 | 8 629 | 251 | 213 | (2352, 8629, 213) | exact | 0.02 s |
| 128 | 4·4·8 | 11 232 | 11 232 | 7 | 1 674 | 9 293 | 265 | 172 | (1674, 9293, 172) | exact | 0.02 s |
| 2187 | 3·9^3 | 52 416 | 52 416 | 0 | 14 391 | 37 010 | 1 015 | 80 | (14391, 37010, 80) | exact | 0.1 s |
| 128 | 2·4^3 | 52 416 | 52 416 | 16 | 10 280 | 41 071 | 1 065 | 1 535 | (10280, 41071, 1535) | exact | 0.1 s |
| 128 | 2^4·8 | 196 560 | 195 768 | 19 | 31 301 | 160 973 | 4 286 | 7 166 | (31301, 160973, 7166) | exact | 0.3 s |
| 1792 | 2^2·7·8^2 | 876 096 | 791 892 | 24 | 155 376 | 702 518 | 18 202 | 38 107 | (155376, 702518, 38107) | exact | 1.5 s |
| 1728 | 3^3·4^3 | 1 589 952 | 1 578 012 | 18 | 338 145 | 1 220 630 | 31 177 | 49 274 | (338145, 1220630, 49274) | exact | 2.6 s |
| 941192 | 7^6·8 | 1 782 144 | 1 780 764 | 3 | 211 383 | 1 531 318 | 39 443 | 13 087 | (211383, 1531318, 13087) | exact | 2.9 s |
| 972 | 2^2·3^5 | 4 088 448 | 3 600 252 | 16 | 823 921 | 3 182 709 | 81 818 | 115 777 | (823921, 3182709, 115777) | exact | 5.8 s |
| 177147 | 3^11 | 8 465 184 | 8 459 664 | 0 | 1 328 951 | 6 957 498 | 178 735 | 15 260 | (1328951, 6957498, 15260) | exact | 14 s |
| 413343 | 3^10·7 | 50 791 104 | 29 027 890 | 0 | 8 545 543 | 41 187 593 | 1 057 968 | 87 717 | (8545543, 41187593, 87717) | exact | 56 s |
| 1728 | 2^6·3^3 | 54 058 368 | 15 714 000 | 26 | 10 614 743 | 42 357 665 | 1 085 960 | 2 442 550 | (10614743, 42357665, 2442550) | exact | 28 s |

All twelve agree to the last digit, in all three recorded statistics (and the five tiny ones also agree with brute force). The by-v0 histogram of survivors is flat (e.g. 3^10·7: 86 568–89 538 per class of 12), confirming (a,pattern) ≈ survivors·(A+1)/12. The C 4-prime DP (`dp4.c`, 128-bit counts) agrees with the Python dense DP + restricted test on 2^4·8, 3^3·4^3, 2^2·7·8^2; the Monte-Carlo sampler (`mc.c`) agrees with the exact numbers on 2^4·8 at 4×10^6 samples (survival 0.02179/0.02195 vs 0.021805; (a,pattern)/pattern 0.03640/0.03668 vs 0.036457; mean lift multiplicity 52.43 vs 52.46 exact).

Why the sparse DP stops here: at 5×10^7 patterns the support is already 1.6–2.9×10^7 residues and the per-digit merges sort ~10^8 keys; a Tier-A equation (10^9–10^11 patterns) saturates Z/P, i.e. needs the dense arrays of §1.3 (≥ 10.6 GB for the simplest multiset), which this machine does not have. The full-P dense code path is the same algorithm as `dp4.c` with Q replaced by P.

### New exact counts for frontier (Tier-A) vertices: the multisets small enough for this machine (sparse DP, full P)

These vertices (1778112, 3779136, 131712) are not in the result files; the counts are new and exact. They cover only ≈ 10^-4 of each vertex's patterns (the rest needs the dense 64-GB DP), but they are the exact numbers an engine run must reproduce.

| s | M | patterns | support | A | zero | prefilter-dead | survivors | survivors/patterns | (a,pattern) | wall |
|---|---|---|---|---|---|---|---|---|---|---|
| 1778112 | 7^3·8^2·9^2 | 26,574,912 | 25,146,096 | 3 | 5,003,628 | 21,030,777 | 540,507 | 1/49.2 | 180,694 | 41 s |
| 1778112 | 4·6^4·7^3 | 71,547,840 | 56,274,564 | 33 | 13,261,895 | 56,824,324 | 1,461,621 | 1/49.0 | 4,141,075 | 91 s |
| 3779136 | 8^2·9^5 | 4,088,448 | 4,076,136 | 3 | 831,710 | 3,174,798 | 81,940 | 1/49.9 | 27,400 | 6 s |
| 3779136 | 6^6·9^2 | 11,583,936 | 11,483,517 | 24 | 2,459,905 | 8,896,453 | 227,578 | 1/50.9 | 474,052 | 18 s |
| 3779136 | 4^3·9^5 | 19,079,424 | 18,907,492 | 9 | 5,174,132 | 13,555,405 | 349,887 | 1/54.5 | 291,582 | 28 s |
| 3779136 | 4·6^4·9^3 | 71,547,840 | 56,697,202 | 33 | 16,439,708 | 53,729,254 | 1,378,878 | 1/51.9 | 3,908,147 | 88 s |
| 131712 | 6·7^3·8^2 | 4,088,448 | 3,947,004 | 20 | 992,780 | 3,018,109 | 77,559 | 1/52.7 | 135,773 | 6 s |
| 131712 | 4^3·6·7^3 | 19,079,424 | 13,844,136 | 33 | 2,849,727 | 15,823,964 | 405,733 | 1/47.0 | 1,149,548 | 23 s |
| 131712 | 2·3·7^3·8^2 | 49,061,376 | 38,923,508 | 32 | 8,424,187 | 39,622,801 | 1,014,388 | 1/48.4 | 2,787,197 | 63 s |
| 131712 | 3·4^2·7^3·8 | 49,061,376 | 41,248,892 | 27 | 9,477,962 | 38,595,053 | 988,361 | 1/49.6 | 2,306,444 | 68 s |


## 3. Code

| file | what |
|---|---|
| `dp_exact.py` | exact DP (sparse over Z/P; dense mod Q), brute force, classification via tier0 `FastLevel`; `run(M)` reproduces `c_stats` |
| `mkcfg.py` → `l12.cfg` | pattern-independent tables for the C tools (log tables, ℓ-component membership with a-representatives, 4-prime projection) |
| `dp4.c` | exact dense DP mod 534391 (primes 11,13,37,101), 128-bit counts — the full-P algorithm at 1/9901 of the memory; rigorous upper bound |
| `mc.c` | Monte Carlo: uniform patterns (uniform multiset of classes per digit value by stars-and-bars), exact 5-prime test, a-split, exact lift multiplicity 2·∏(j_{d,r}+1), 4-prime test |
| `twoadic.c` | 2-adic bound A by forced-parity DFS, 384-bit, node budget (exact when not capped) |
| `tierc_mc.py` | driver: per-equation allocation n_M ∝ N_M (2×10^4 … 10^6), aggregation with 95 % intervals → `tierc_eqs.jsonl`, `tierc_summary.json` |
| `tiera_exact.py` | exact sparse-DP counts for the small multisets of Tier-A vertices → `tiera_exact.jsonl` |
| `report_tables.py` | renders the tables of §4 from the JSON |

## 4. Tier-C Monte-Carlo forecast

Method: for each of the 6 251 equations (s, M) of `tierC.txt`, N_M = 12·∏_d C(11+m_d, m_d) exact; n_M uniformly random patterns with n_M = clamp(10^8·N_M/Σ_M N_M, 2×10^4, 10^6) (Neyman allocation; the per-vertex total is what matters, and the largest equation is ≤ 3 % of a vertex); the exact level-12 test per sample; survivors = Σ_M N_M·(surv_M/n_M), variance Σ N_M² p(1−p)/n_M; the same for the lift multiplicity (level-24 children per survivor, counted exactly with the multiset symmetry: 2·∏_{(d,r)}(j_{d,r}+1), **not** 2^{k+1}) and for the a-split. "Hybrid" = exact 4-prime count (dp4, all 306 multisets of the first vertex, the 20 largest of each other vertex) × MC conditional pass rate of the remaining test. Intervals are normal 95 % (binomial counts are ≥ 10^5 per vertex).

### Per-vertex Monte-Carlo estimates (95% intervals)

| vertex s | 2^a3^b7^c | multisets | k | patterns (exact) | samples | survivors (patterns) | survivors / patterns | level-24 children of survivors (exact symmetry) | mean lifts per survivor | 4-prime exact upper bound* |
|---|---|---|---|---|---|---|---|---|---|---|
| 3416267673274176 | 2^6·3^27·7^1 | 306 | 17–34 | 1.724e+19 | 7.59e+07 | 3.485e+17 [3.479e+17, 3.491e+17] (±0.17%) | 1/49.5 | 2.333e+24 [2.327e+24, 2.339e+24] (±0.26%) | 6.694e+06 = 2^22.7 | 6.968e+18 |
| 128421199872 | 2^23·3^7·7^1 | 925 | 13–31 | 2.566e+19 | 1.06e+08 | 5.185e+17 [5.178e+17, 5.192e+17] (±0.14%) | 1/49.5 | 1.009e+24 [1.007e+24, 1.011e+24] (±0.21%) | 1.947e+06 = 2^20.9 | 2.016e+18 (top 20 multisets, 19% of patterns) |
| 913217421312 | 2^29·3^5·7^1 | 911 | 14–35 | 8.595e+19 | 1.06e+08 | 1.735e+18 [1.733e+18, 1.738e+18] (±0.14%) | 1/49.5 | 8.482e+24 [8.463e+24, 8.500e+24] (±0.21%) | 4.888e+06 = 2^22.2 | 7.028e+18 (top 20 multisets, 20% of patterns) |
| 727326941773824 | 2^39·3^3·7^2 | 834 | 17–44 | 5.531e+21 | 1.04e+08 | 1.119e+20 [1.118e+20, 1.121e+20] (±0.14%) | 1/49.4 | 6.623e+27 [6.608e+27, 6.638e+27] (±0.23%) | 5.916e+07 = 2^25.8 | 4.922e+20 (top 20 multisets, 22% of patterns) |
| 112717121716224 | 2^34·3^8·7^0 | 2446 | 16–42 | 9.864e+21 | 1.28e+08 | 1.992e+20 [1.989e+20, 1.995e+20] (±0.13%) | 1/49.5 | 8.375e+27 [8.356e+27, 8.394e+27] (±0.23%) | 4.204e+07 = 2^25.3 | 4.283e+20 (top 20 multisets, 11% of patterns) |
| 1438916737499136 | 2^24·3^6·7^6 | 829 | 17–36 | 1.380e+22 | 1.05e+08 | 2.786e+20 [2.782e+20, 2.790e+20] (±0.14%) | 1/49.5 | 9.045e+27 [9.025e+27, 9.064e+27] (±0.22%) | 3.246e+07 = 2^25.0 | 1.179e+21 (top 20 multisets, 21% of patterns) |

### The a-split (A from the 2-adic search; lower bounds where the search was capped)

| vertex s | A found (max over multisets) | multisets with A capped | (a,pattern) pairs, A as found | level-24 children of (a,pattern) pairs | a-values per survivor |
|---|---|---|---|---|---|
| 3416267673274176 | 118 | 281/306 | 2.771e+18 [2.766e+18, 2.775e+18] (±0.17%) | 1.910e+25 [1.905e+25, 1.916e+25] (±0.27%) | 7.95 |
| 128421199872 | 118 | 916/925 | 3.970e+18 [3.965e+18, 3.976e+18] (±0.14%) | 8.047e+24 [8.030e+24, 8.064e+24] (±0.21%) | 7.66 |
| 913217421312 | 122 | 901/911 | 1.408e+19 [1.406e+19, 1.409e+19] (±0.14%) | 7.168e+25 [7.153e+25, 7.184e+25] (±0.22%) | 8.11 |
| 727326941773824 | 144 | 830/834 | 1.030e+21 [1.028e+21, 1.031e+21] (±0.14%) | 6.346e+28 [6.331e+28, 6.361e+28] (±0.23%) | 9.20 |
| 112717121716224 | 135 | 2433/2446 | 1.764e+21 [1.761e+21, 1.766e+21] (±0.14%) | 7.741e+28 [7.723e+28, 7.759e+28] (±0.24%) | 8.85 |
| 1438916737499136 | 125 | 828/829 | 2.385e+21 [2.381e+21, 2.388e+21] (±0.14%) | 8.069e+28 [8.050e+28, 8.087e+28] (±0.23%) | 8.56 |

### Hybrid estimator (exact 4-prime count × MC conditional pass rate of the 9901 part), where dp4 ran

| vertex s | plain MC survivors | hybrid survivors | zero-residue patterns (MC) |
|---|---|---|---|
| 3416267673274176 | 3.485e+17 [3.479e+17, 3.491e+17] (±0.17%) | 3.486e+17 [3.480e+17, 3.492e+17] (±0.17%) | 3.305e+18 (19.2%) |
| 128421199872 | 5.185e+17 [5.178e+17, 5.192e+17] (±0.14%) | 5.185e+17 [5.178e+17, 5.192e+17] (±0.14%) | 4.919e+18 (19.2%) |
| 913217421312 | 1.735e+18 [1.733e+18, 1.738e+18] (±0.14%) | 1.735e+18 [1.733e+18, 1.738e+18] (±0.14%) | 1.648e+19 (19.2%) |
| 727326941773824 | 1.119e+20 [1.118e+20, 1.121e+20] (±0.14%) | 1.119e+20 [1.118e+20, 1.121e+20] (±0.14%) | 1.060e+21 (19.2%) |
| 112717121716224 | 1.992e+20 [1.989e+20, 1.995e+20] (±0.13%) | 1.992e+20 [1.989e+20, 1.995e+20] (±0.13%) | 1.890e+21 (19.2%) |
| 1438916737499136 | 2.786e+20 [2.782e+20, 2.790e+20] (±0.14%) | 2.786e+20 [2.782e+20, 2.790e+20] (±0.14%) | 2.644e+21 (19.2%) |

### Largest equations per vertex (top 3 by pattern count)

| s | M | k | patterns | n | surv/n | mean lifts | A (capped?) |
|---|---|---|---|---|---|---|---|
| 3416267673274176 | 2^4·3^15·6^2·7^1·9^5 | 27 | 5.174e+17 | 1e+06 | 0.0200 | 8.93e+06 | 104+ |
| 3416267673274176 | 2^4·3^13·6^2·7^1·9^6 | 26 | 4.736e+17 | 1e+06 | 0.0203 | 7.05e+06 | 102+ |
| 3416267673274176 | 2^4·3^17·6^2·7^1·9^4 | 28 | 4.494e+17 | 1e+06 | 0.0205 | 1.05e+07 | 107+ |
| 128421199872 | 2^11·3^4·4^4·6^1·7^1·8^1·9^1 | 23 | 3.271e+17 | 1e+06 | 0.0202 | 2.14e+06 | 101+ |
| 128421199872 | 2^13·3^4·4^3·6^1·7^1·8^1·9^1 | 24 | 3.086e+17 | 1e+06 | 0.0199 | 2.72e+06 | 103+ |
| 128421199872 | 2^12·3^5·4^3·6^2·7^1·8^1 | 24 | 2.898e+17 | 1e+06 | 0.0202 | 3.06e+06 | 107+ |
| 913217421312 | 2^14·3^4·4^4·6^1·7^1·8^2 | 26 | 1.119e+18 | 1e+06 | 0.0200 | 6.99e+06 | 106+ |
| 913217421312 | 2^13·3^3·4^4·6^2·7^1·8^2 | 25 | 1.087e+18 | 1e+06 | 0.0203 | 5.03e+06 | 105+ |
| 913217421312 | 2^12·3^4·4^5·6^1·7^1·8^2 | 25 | 1.087e+18 | 1e+06 | 0.0202 | 5.51e+06 | 106+ |
| 727326941773824 | 2^17·3^2·4^6·6^1·7^2·8^3 | 31 | 8.475e+19 | 1e+06 | 0.0202 | 6.78e+07 | 119+ |
| 727326941773824 | 2^15·3^2·4^7·6^1·7^2·8^3 | 30 | 7.841e+19 | 1e+06 | 0.0205 | 5.42e+07 | 115+ |
| 727326941773824 | 2^19·3^2·4^5·6^1·7^2·8^3 | 32 | 7.609e+19 | 1e+06 | 0.0203 | 7.77e+07 | 122+ |
| 112717121716224 | 2^16·3^4·4^5·6^2·8^2·9^1 | 30 | 6.810e+19 | 7e+05 | 0.0201 | 4.93e+07 | 117+ |
| 112717121716224 | 2^14·3^4·4^6·6^2·8^2·9^1 | 29 | 6.597e+19 | 7e+05 | 0.0203 | 3.94e+07 | 116+ |
| 112717121716224 | 2^13·3^4·4^5·6^2·8^3·9^1 | 28 | 6.085e+19 | 6e+05 | 0.0203 | 2.93e+07 | 112+ |
| 1438916737499136 | 2^11·3^4·4^4·6^2·7^6·8^1 | 28 | 1.827e+20 | 1e+06 | 0.0202 | 3.95e+07 | 117+ |
| 1438916737499136 | 2^13·3^4·4^3·6^2·7^6·8^1 | 29 | 1.724e+20 | 1e+06 | 0.0204 | 5.01e+07 | 117+ |
| 1438916737499136 | 2^12·3^5·4^4·6^1·7^6·8^1 | 29 | 1.724e+20 | 1e+06 | 0.0203 | 5.55e+07 | 115+ |


### Reading the numbers

* **Level-12 survival is generic to 0.2 %.** Under uniform residues the zero fraction is 1 − ∏(1−1/p) = 0.1915 and the survival rate (1 − 0.1915)/40 = 0.02021 = 1/49.5; every vertex's MC gives 1/49.4–1/49.5 (zero fraction 19.2 %), i.e. survivors = 0.02021·N to within the 0.15 % intervals. So for Tier C the exact DP would only confirm `N/49.5`; the pattern structure that makes small equations deviate (1/47–1/55 in the exact Tier-A table above) averages out over the 10^2–10^3 multisets and 10^19–10^22 patterns of a Tier-C vertex. The informative MC outputs are the lift multiplicity and the a-split, which are not generic.
* Level-24 children: the multiset symmetry cuts 2^{k+1} by 10^2–10^4 at these k (classes get reused heavily when m_d ≫ 12), but the children still number 10^24–10^27 per vertex — the 12→24 lift is 10^6–10^7 × the level-12 survivor count, i.e. the lift, not level 12, is the wall for Tier C (as FRONTIER.md already says for Tier B).
* The a-split multiplies by (A+1)/12 ≈ 7.7–9.2 with the A lower bounds found; the true A for the 2-heavy multisets is larger (the DFS was still finding longer tails when capped), so the (a,pattern) and children-of-(a,pattern) rows are **lower bounds**.
* Compared with FRONTIER.md's "2^{k+1} children per survivor": the exact multiset-symmetry lift multiplicity is 2^{20.9}–2^{25.8} per survivor against 2^{k+1} = 2^{14}–2^{45}; for the large equations that dominate a vertex (k = 23–32) the symmetry saves 10^2–10^4. Per vertex the level-24 inputs are 1.0×10^24, 2.3×10^24, 8.5×10^24, 6.6×10^27, 8.4×10^27, 9.0×10^27 (× 8–9 for the a-split): still 10^22–10^26 above anything enumerable, which is the quantitative form of "new mathematics or nothing" for Tier C — and it confirms that for Tier B too the 12→24 lift (not level 12) is the wall.
* The hybrid estimator (exact 4-prime count × MC conditional rate) changes nothing, because the 4-prime test has index 2 only: all the selectivity (and all the sampling variance) sits in the joint condition with 9901. This is also the quantitative reason an exact count cannot avoid the full P.

## 5. Budget

CPU used ≈ 1 h 35 min of the 2 h: validation runs ≈ 6 min, Tier-C run 1 564 s (6.24×10^8 MC samples, 6 251 × twoadic, 406 × dp4), Tier-A exact sparse DPs ≈ 8 min, the rest tooling and tests. Peak RSS ≈ 4 GB (the 7×10^7-pattern sparse DPs). One worker process at a time.
