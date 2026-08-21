# Distributed collision search (rho/kangaroo, distinguished points, certificates) — Tier-1/2 skill + ladder design only

Scope guard: nothing here targets the 254-bit instance. Certicom's status page and the SHARCS'09 ECC2-X slides list ECC2K-130, ECC2-131 and ECCp-131 as open (last solved: 109-bit, 2002/2004).

## Per source

### 1. van Oorschot–Wiener, "Parallel collision search with cryptanalytic applications", J. Cryptology 12 (1999) — preprint read in full (§4.1, §5.1)
- Mechanism: each processor walks from x_0 = g^{a0} y^{b0}, tracking (a_i,b_i); at a distinguished point (probability θ) it sends (x_i,a_i,b_i) to a central list and restarts. Two triples (x,a,b),(x,c,d) give log_g y ≡ (a−c)(d−b)^{-1} mod p "provided b ≢ d" (§5.1); for DLP "collisions merely need to be detected, not located". T_ρ = (√(πp/2)/m + 1/θ)·t (eq. 5); parallel kangaroo T_λ = (2√b/m + 1/θ)·t (eq. 6); kangaroo is 1.60× slower than rho at b=p, faster only when b < 0.39p. Trail abort at 20/θ wastes <5×10^-8 of work (§4.1).
- Candidate home: SUBSTRATE succinct certificate (§3) and the Tier-2 rho skill's cost profile (§5).
- Certificate schema that follows from §5.1 (fields): curve (p,a,b), n, P, Q; walk definition (r, the r multipliers (m_i,n_i) or the PRNG seed generating them, the index function, the DP predicate θ); the two colliding DP triples (X,a,b), (X,c,d). Verifier: check aP+bQ == X == cP+dQ (four scalar multiplications, i.e. O(log n) group ops — not O(1); the "O(1)" in the brief should read "a constant number of scalar mults"), then x=(a−c)(d−b)^{-1} mod n and xP==Q. Size at 60 bits ≈ 2×(120+120) bits ≈ 60 bytes plus walk definition. Storing seeds instead of (a,b) (sources 3,4 below) shrinks DP reports but makes verification cost O(1/θ) iterations.
- Cost: none beyond the fields above. Evidence: the certificate algebra is a theorem (PROVEN-in-source); the run-time formulas are heuristic random-walk estimates (STRONG-EMPIRICAL via sources 2–3).
- Epistemics risk: low. The only trap is "b ≡ d" useless collisions — the verifier must reject them, never "retry silently".

### 2. Bernstein–Lange–Schwabe, "On the correct use of the negation map in the Pollard rho method", PKC 2011 (eprint 2011/003) — §§2,3,6 read
- Mechanism: negating additive walk f(W)=|W|+R_{h(W)} halves the class count (√2 fewer iterations) but enters fruitless 2-cycles with probability ≈1/(2r) per step; fix = check W_{i−1}=W_{i−3} every w≈2√r steps, escape by doubling the lexicographic min; longer cycles checked geometrically less often; total overhead 1+Θ(1/√r) (§3). Their PS3 software: r=2048, 2-cycle check every 48 iterations, 12-cycle check every 49152.
- The ladder-relevant part is §6: they scaled the *same* software "without changing the prime" by varying b in y²=x³−3x+b to get prime-order subgroups of 2^50, 2^55, 2^60, ran 32237 / 257241 / 33791 independent DLP experiments with DP probability 2^-20, sorted DPs back into seed order "to avoid bias favoring short walks", aborted walks after 47·2^18 steps, and verified "a large random sample" of logs against the planted scalar. Measured mean DP count = 1.0789 / 1.0074 / 0.9996 × √(πℓ/4)/2^20, sd ≈ 0.53–0.56 × that.
- Candidate home: SMALL-SCALE LADDER (§6) protocol — the published template for "measured scaling matching claimed asymptotic" on 50–60-bit prime-order toy curves, including the variance to expect (sd ≈ 0.5×mean: single runs prove nothing).
- Cost: the negation map is optional at Tier-1; the *protocol* costs only many repeats. Evidence: STRONG-EMPIRICAL (§6 figures). Epistemics risk: none; it gives the calibration layer an empirical distribution to test a claimed speedup against.

### 3. Bernstein, Engels, Lange, Niederhagen, Paar, Schwabe, Zimmermann, "Faster elliptic-curve discrete logarithms on FPGAs" (eprint 2016/382, v. 2016-12-12) — §§1.4, 3, 4.9, 5 read
- Mechanism: walks store no (a,b) counters; the server stores (seed, DP) and on collision recomputes both 2^30-step walks in software (NTL, "on the scale of an hour") to recover the coefficients (§3). DP property = top 30 bits of x zero. Record: 117.35-bit prime-order subgroup over F_{2^127}; expected √(π·2^117.35/4)/2^30 ≈ 3.80×10^8 DPs, actually needed 9.69×10^8 (unlucky by 2.55×), ~2^60 iterations over six months (§4.9, §1.4).
- Verification methodology (§5): a single DL time is "inadequate as a verification tool"; they ran 1024 DLs on a 2^60.69 subgroup (same field, b changed) — 1173 walks/DL vs predicted 1153 — and 1024 on a 2^61.93 subgroup (1751 vs 1771), compared the sorted distribution against −(4/π)log(1−x/1024) from rho theory (Fig. 5.1), used AES-postprocessed consecutive seeds so seed assignment to experiments is retroactive, and spot-checked walks against an independent software implementation.
- Candidate home: SUBSTRATE certificate variant (report = seed + DP; certificate = two seeds + walk def; verification = replay 2/θ iterations) and the CALIBRATION layer (distribution-shape check, not mean-only).
- Cost: storage traded for O(1/θ) verification work; fine if θ ≥ 2^-20. Evidence: STRONG-EMPIRICAL. Epistemics risk: the "unlucky 2.55×" shows a single expensive run never calibrates a cost model — gate on distributions.

### 4. Bailey et al., "Breaking ECC2K-130" (eprint 2009/541) — §2 read
- Mechanism: 64-bit seed → AES → starting coefficients; DP report = 64-bit seed + 64-bit hash of the normalized DP (128 bits total vs "4·112 bits" per DP in the 2009 112-bit prime-field break); walks are deterministic so the server recomputes only colliding seeds. Expected 2^60.9 iterations, DP probability 2^-25.27, ~2^35.63 DPs.
- Candidate home: SUBSTRATE — the minimal DP record format. Cost: recompute on collision. Evidence: STRONG-EMPIRICAL (running project design; the Frobenius-orbit normalization is Koblitz-specific and does not transfer to prime-field toys). Epistemics risk: none.

### 5. Galbraith–Pollard–Ruprai, "Computing discrete logarithms in an interval", Math. Comp. 82 (2013) / eprint 2010/617 — abstract, §1, §3.2, §5 read
- Mechanism/constants: vOW kangaroo (2+o(1))√N; 4-kangaroo (1.715+o(1))√N; Gaudry–Schost variant (1.661+o(1))√N; BSGS interval variant 4/3·√N avg (Pollard); rho in a group of order N ≈ 1.25√N. Experiments (>1000 runs, N=2^40 and ≈2^47): measured 1.733±0.044 (4-kangaroo), 1.851±0.067 (3-kangaroo), 1.686 (GS, N≈2^47).
- Candidate home: Tier-1 interval-DLP skill cost profile + known-answer expectations; also the calibration layer's idea of publishing a 95% CI on ops/√N.
- Cost: the 4-kangaroo trick is a ~15% constant — not worth complexity at Tier-1. Evidence: STRONG-EMPIRICAL. Epistemics risk: none.

### 6. JeanLucPons/Kangaroo @ 37576c82 (cloned) — README, HashTable.h, Kangaroo.cpp read
- Mechanism: secp256k1-only (SECPK1/, `ModAddK1order`); DP entry = 128-bit x LSBs + 128-bit distance with sign/type bits (HashTable.h:51-56); expected-ops model `op = Z0·(N·(k·θ+√N))^{1/3}`, Z0 = 2(2−√2)·gainS·√π (Kangaroo.cpp:836-862) — DP overhead vs herd size k and DP rarity θ (README table); `CheckKey` recomputes k·G and compares to the target before printing (Kangaroo.cpp:216-253).
- Candidate home: Tier-1/2 kangaroo skill — borrow the DP-overhead cost model and the verify-before-output pattern. Reject as a dependency: curve hard-coded, GPU/CUDA build, no certificate export.
- Evidence: formulas STRONG-EMPIRICAL (README claims solved 109/114-bit secp256k1 puzzles; not verified by me). Epistemics risk: none if only the formulas are borrowed.

### 7. Sage `sage/groups/generic.py` (develop, fetched 2026-08-21) — `discrete_log_rho` L658-818, `bsgs` L510-656, `discrete_log` L821-1125, `discrete_log_lambda` L1134-1240
- Mechanism: rho = r=20 additive walk with Python `hash()` partition, Brent-style memory of 4 points (geometric `nextsigma = 3*sigma`), `reset_bound = 8·isqrt(ord)`, up to 10 restarts, **verifies `power(base,res)==a` before returning** (L807-809); no negation map, no DPs, serial. `bsgs` m=isqrt(range)+1 baby table (dict). `discrete_log(..., verify=True)` re-checks the CRT result (L1117). Doctests = ready known-answer seeds (e.g. GF(37^5) curve, point of order 46591, log 12345; prime-order-required error path).
- Candidate home: SKILL INTERFACE self-tests (known-answer seeds) and the Tier-0 verifier pattern. Cost: none. Evidence: PROVEN-in-source. Epistemics risk: none.

### 8. Sage `ell_finite_field.py` (`cardinality` L318-508, `cardinality_pari` L840-875) + `ell_point.py` (`log` L4558-4751) + PARI docs (`ellcard`, `elllog`, `znlog`)
- Mechanism: `cardinality()` → PARI `ellcard` (Shanks–Mestre BSGS Õ(q^{1/4}) "unreasonable when q has about 30 digits", SEA above); `algorithm='all'` cross-checks PARI vs Sage's own BSGS and raises on disagreement. `P.log(Q)` checks subgroup membership (n·Q==O, then gcd/Weil pairing) before calling `pari.elllog`, because PARI's generic DL "may enter an infinite loop" if no solution exists; znlog uses Pohlig–Hellman, BSGS for q<2^32, rho for q>2^32.
- Candidate home: exemplar M0 skill "generate prime-order toy curve of b bits": random p, random (a,b), `cardinality()` (ms at ≤60 bits), accept if prime. Acceptance ≈ c/ln p: in my session script (gmpy2, Hasse-interval BSGS order-finding instead of SEA) 10/25/130 curve tries at 30/40/50 bits, 0.00/0.06/1.52 s. Also the Tier-0 "two independent implementations must agree" pattern (`algorithm='all'`).
- Evidence: PROVEN-in-source for code paths; counts STRONG-EMPIRICAL (one seed). Epistemics risk: none.

### 9. Session measurement — `scratchpad/adjacent/toy_ladder_bench.py` (Python 3.14 + gmpy2, one core, Apple laptop)
- 30-bit: rho 25k–45k ops (0.05–0.08 s), BSGS 33k–58k ops, 31k-entry table (0.02–0.03 s). 40-bit: rho 0.95M–1.47M ops (0.97–1.46 s), BSGS 1.5M–1.8M ops, 0.92M-entry table (1.24–1.27 s). 50-bit: rho 4.2M and 30.3M ops (2.9 s, 20.7 s; ≈0.7 µs/iteration); BSGS not run (2^25 Python dict entries ≈ several GB). Every run verified xP==Q.
- Derived ladder bar (CONJECTURE beyond 50 bits): rho 1.25√n ops (0.886√n with negation), BSGS ≈1.5√n ops and √n memory. 50-bit: rho 42M ops ≈30 s Python / seconds in C; BSGS ≈50M ops, 33.5M entries (≈0.4–0.8 GB in C, several GB in Python). 60-bit: rho 1.35G ops ≈15 min Python, ≈2–3 min in C (BLS: 362 cycles/iteration at 3.2 GHz ≈ 0.11 µs); BSGS needs 2^30 entries (≥12 GB). So "beats BSGS at 50 bits" = < ~5×10^7 group ops and <1 GB at 50 bits, and *completes* at 60 bits; measured scaling must be compared against √n (60/50-bit ratio ≈32×), reported in ops not seconds.
- Evidence: STRONG-EMPIRICAL for ≤50 bits (few trials; sd ≈ 0.5×mean per BLS §6, so Tier-1 needs ≥10² trials before quoting a mean).

### 10. Galbraith–Gebregiyorgis, "Summation polynomial algorithms for elliptic curves in characteristic two", INDOCRYPT 2014 (eprint 2014/806) — §6, conclusions read
- Mechanism (reporting template): binary Edwards curves, n ∈ {17,…,53}, m=3/4, l ∈ {3,…,7}; 100 trials averaged, 200 s patience threshold; columns n, l, #Var, #Pequ, D_reg, T_GB/T_SAT, Mem, P_succ; closing bound trials ≥ 2^{n−lm} ≥ 2^{n−40} ≥ 2^{n/2} for n>100 ⇒ "worse than Pollard rho".
- Candidate home: LADDER result format + NEGATIVE-RESULTS MAP (the bound is exactly a no-go entry). Evidence: STRONG-EMPIRICAL. Epistemics risk: none.

## Rejected
- JeanLucPons/Kangaroo (and BitCrack-genre tools) as a dependency: secp256k1 hard-coded, no curve parameterization, no certificate export; borrow the cost model only. BitCrack itself not read.
- Negation-map + fruitless-cycle machinery at Tier-1: a √2 constant for Θ(1/√r) bookkeeping; ladder verdicts are about exponents, not constants.
- 4-kangaroo / Gaudry–Schost constants: 15% — same reason.
- ECC2K-130 Frobenius-orbit normalization: Koblitz-specific, does not apply to prime-field toy curves.
- Seed-only DP reports as the *primary* certificate: verification is O(1/θ) iterations, not a constant number of scalar mults; keep (a,b) in the stored certificate at Tier-1/2 and use seed-only only as a storage optimization at Tier-3.
- Anything framed as progress on ECCp-131/ECC2K-130: out of scope by construction.

## Recommend /research-software next on
- PARI/GP `ellcard`/`ellsea`/`elllog` via cypari2 (the engine under Sage) as the Tier-0/1 backend: read `src/modules/ellsea.c` and the generic DL code for the 2^32 BSGS→rho switch.
- Sage `discrete_log_lambda` L1134-1240 for a bounded-interval Tier-1 skill (no DPs, one tame endpoint).

## Sources
vOW preprint https://people.scs.carleton.ca/~paulv/papers/JoC97.pdf · BLS eprint 2011/003 · Bernstein et al. eprint 2016/382 · ECC2K-130 eprint 2009/541 and https://ecc-challenge.info/ · GPR eprint 2010/617 / doi:10.1090/S0025-5718-2012-02641-X · Kangaroo https://github.com/JeanLucPons/Kangaroo @37576c82 · Sage develop `src/sage/groups/generic.py`, `src/sage/schemes/elliptic_curves/ell_finite_field.py`, `ell_point.py` · PARI docs https://pari.math.u-bordeaux.fr/dochtml/ref-stable/Elliptic_curves.html and Arithmetic_functions.html · GG14 eprint 2014/806 · Certicom https://www.certicom.com/en/the-certicom-ecc-challenge and SHARCS'09 slides http://www.hyperelliptic.org/tanja/SHARCS/slides09/04-ECC2-X.pdf · session script `scratchpad/adjacent/toy_ladder_bench.py`, logs `bench40.log`, `bench50.log`.
