# Grounding: PARI/Sage backend for the M0 toy-curve skill and Tier-0 verifier

Scratch (all scripts runnable): `/private/tmp/claude-502/-Users-jr843u-Documents-cairn/9cf1d827-93dc-467a-8101-c39c1c16857b/scratchpad/grounding/pari-sage-toy-curve-backend/` (`bench.gp`, `bench_cypari2.py`, `verify.gp`, `verify_driver.py`, `.venv/`). Probes run 2026-08-21 on arm64 macOS.

## 1. What is installed

- **PARI/GP**: was absent; `brew install pari` (bottled 2.17.4, deps gmp 6.3.0 already present) took 12.5 s wall. `/opt/homebrew/bin/gp --version` → `GP/PARI CALCULATOR Version 2.17.4 (released)`. Shell has `alias gp='git push'` — always call `/opt/homebrew/bin/gp`. `pari-seadata` is a separate brew formula, not installed (`default(datadir)` = `/opt/homebrew/share/pari`, no `seadata` dir). STRONG-EMPIRICAL.
- **Sage**: not installed (`sage: command not found`). PROVEN (probe).
- **cypari2 / gmpy2**: not in the user env; `uv venv && uv pip install cypari2 gmpy2` into scratch `.venv` took 7.2 s (prebuilt wheels, Python 3.14.0): cypari2 2.2.4 bundling libpari **2.17.2** (`pari.version()` → `(2,17,2)`), gmpy2 2.3.1. STRONG-EMPIRICAL.

## 2. Measured: prime-order toy curve search (b = 30/40/50/60)

Algorithm (`bench.gp`): `setrand(seed); p = randomprime([2^(b-1),2^b])` (proven prime below 2^64, usersch3.tex:10248-10254), loop `a,b = random(p)`, skip singular, `N = ellcard(ellinit([a,b],p))` (mode 0) or `ellsea(E,1)` (mode 1, early abort), accept `isprime(N)`.
Command: `/opt/homebrew/bin/gp -q -f -D parisizemax=256M bench.gp` (gp 2.17.4); `.venv/bin/python bench_cypari2.py` (cypari2, libpari 2.17.2) gave **bit-identical p,a,b,N and tries** for every row — same PRNG/algorithms across the two builds. STRONG-EMPIRICAL.

| b | seed | ellcard tries / ms | ellsea(E,1) tries / ms |
|---|---|---|---|
| 30 | 1,2,3 | 48/2, 148/4, 20/1 | 19/76, 18/102, 11/32 |
| 40 | 1,2,3 | 40/9, 52/10, 57/10 | 13/165, 3/77, 92/468 |
| 50 | 1,2,3 | 36/52, 11/13, 220/288 | 46/379, 20/80, 7/71 |
| 60 | 1,2,3 | 7/543, 31/2359, **344/25429** | 45/274, 72/869, 140/696 |

Per-curve cost (`gp -s 64M`, loops): ellcard ≈ 1.3 ms @50b (generic) vs ellsea(,0) 61 ms; @60b ellcard 75 ms ≈ ellsea(,0) 74 ms (ellcard is SEA there — consistent with usersch3.tex:31112-31113 "below about 2^50 the generic algorithm will be faster"), ellsea(,1) 0.3 ms per rejected curve. STRONG-EMPIRICAL. Consequence for PLAN.md:437 ("milliseconds below 60 bits"): true through 50 bits; at 60 bits use `ellsea(E,1)` for the search (PARI's own `cryptocurve` recipe, usersch3.tex:31084-31102) then confirm with `ellcard` — at 60 bits that confirm is SEA again, so the two-algorithm agreement (BSGS vs SEA) is only independent for b ≤ 50. Tries at 30/40/50 from 3 seeds each (20–220) are too few to pin the PLAN.md:439 "10/25/130" means — sample variance is large. STRONG-EMPIRICAL on samples, CONJECTURE on means.
**Stack:** default `parisize=8000000`, `parisizemax=0`; 60-bit `ellcard` overflows the default stack in gp *and* in cypari2 (`PariError: the PARI stack overflows (current size: 8011776…)`). Pass `-s 64M` or `--default parisizemax=256M` to gp (`gp --help` lists `-s stacksize`, `--default key=val`, `-f` fast start, `-q` quiet) and `pari.allocatemem(64_000_000)` in cypari2. PROVEN (probe).

## 3. Tier-0 verifier: exact calls and subprocess shape

PARI calls (usersch3.tex, 2.17.4): `ellinit([a,b],p)` (se:ellinit:29556), `ellisoncurve(E,z)` → 1/0 (29871-29876), `ellmul(E,z,n)` → `[0]` is the point at infinity (30225-30231), `ellorder(E,z)` (30274), `elllog(E,P,G,o)` "assumes that P is a multiple of G" (30003-30015). Sage 10.6 `ell_point.py:4342-4345` states verbatim that `elllog()` does not guarantee termination if Q is not a multiple of P and checks membership first — PROVEN-in-source for PLAN.md:444-445.
`verify.gp` defines `verify(p,a,b,n,Px,Py,Qx,Qy,x)`: ispseudoprime(p) → nonsingular → `ellisoncurve(E,P)`,`(E,Q)` → `ellmul(E,Q,n)==[0]` → `ellmul(E,P,x)==Q`; prints one line `OK` / `FAIL [reasons]`, `quit(0|1)`. Driver (`verify_driver.py`) validates all nine fields as nonnegative ints, pipes one line `verify(p,a,b,...)` to stdin of `/opt/homebrew/bin/gp -q -f -D parisizemax=256M verify.gp`, accepts only `rc==0 and stdout=="OK"`. Probe at 60 bits: good → `(0,'OK')` 17 ms; `-Q` → `FAIL ["xP-ne-Q"]`; off-curve → `FAIL ["Q-off-curve"]`; wrong n → `FAIL ["nQ-not-O"]`; cypari2 in-process same checks 0.1 ms. Two gotchas, both PROVEN by probe: (i) gp exits **0** on a fatal error (`1/0` and the 8 MB stack overflow both gave rc=0, empty stdout, message on stderr) — never trust rc alone; (ii) gp fills missing args with 0 (`verify(1,2)` ran and FAILed) — arity is the driver's job. Run: `.venv/bin/python verify_driver.py`.

## 4. Known-answer seeds (pinned)

1. PARI 2.17.4 `usersch3.tex:29031-29032`: `E = ellinit([-3,1], 5); ellcard(E)` → `7` (prime). Local gp enumeration: affine points (0,1),(0,4),(1,2),(1,3),(3,2),(3,3); P=(0,1) has order 7, `[k]P` for k=1..6 = (0,1),(1,3),(3,3),(3,2),(1,2),(0,4) → vendor triple **(p=5,a=-3,b=1,n=7,P=(0,1),Q=(3,3),x=3)**. Curve+N PROVEN-in-source; P,Q,x STRONG-EMPIRICAL (hand-checkable).
2. Sage 10.6 `ell_point.py:4529-4537` (commit of tag `10.6` — `api.github.com/.../tags/10.6` returned no sha field; OPEN) with `constructor.py:790-791` (j≠0,1728 over a general field → `[0,0,0,-3j(j-1728),-2j(j-1728)^2]`): `E = EllipticCurve(j=GF(101)(5))` = y²=x³+90x+44 over GF(101); `(2*P).log(P)` → `2`, `P.discrete_log(2*P)` → `45` (=2⁻¹ mod 89). gp: ellcard=89, prime. Vendor (p=101,a=90,b=44,n=89, x=2, Q=2P) with P any nonzero point — P is `E.gens()[0]`, not explicit in the doctest. PROVEN-in-source for curve/x/order; P is OPEN.
3. Sage 10.6 `ell_point.py:4666-4672`: p=next_prime(2^150)=1427247692705959881058285969449495136382746771, E=[1,1], P=(831623307675610677632782670796608848711856078, 42295786042873366706573292533588638217232964), `P.order()` = `E.cardinality()` = 1427247692705959881058262545272474300628281448 (composite — even). gp confirms oncurve, ellorder, `[n]P==[0]`. Membership/cardinality/big-int path only, no x. PROVEN-in-source.
4. Sage 10.6 `ell_point.py:~822-827` (`has_order`): E=[1,0]/GF(419), P=(-33,8), order 21; gp: card 420. Negative-control seed for `nQ-not-O`. PROVEN-in-source.
PARI's `elllog` doc example (usersch3.tex:30017-30027) is over F_{2^8} — not vendorable by an F_p verifier.

## OPEN
- Exact commit SHA for Sage tag 10.6 (API call returned no `sha`; files were fetched from `raw.githubusercontent.com/sagemath/sage/10.6/...`).
- PARI's own test vectors (`src/test/in/elllog`) — gitweb blob_plain returned an HTML error page; doc examples used instead.
- No explicit F_p (P,Q,x) triple exists in Sage/PARI docs beyond seed 1; seeds 2–3 need a locally computed P or Q.
- Mean tries at each bit size (PLAN.md:439) — 3 seeds is too few; run ≥50 seeds before quoting a cost profile.
