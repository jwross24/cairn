# Affine targets and exact Boolean lattice feasibility

**The target can be made exactly affine. High-copy feasibility admits rank $q+3$ with a sparse-integer domain filter, but I do not establish a computational improvement over fiber enumeration. Low-position branching remains exponential.**

**Calibration: HIGH, paper proofs and finite computations distinguished below.** These are ordinary proofs, without Lean verification or Cairn’s PROVEN status. No conjecture is assumed. Read grounding: the permitted deep attempt, DEEPCUT.md, SANDWICH.md, sandwich.py, and deepcut.py. The parallel lane was not accessed.

## 1. Exact affine target

**Theorem 1. HIGH, proved here.** Put $K=96D$, assume $K\ge a+3$, and fix
\[
T(x)=T_0+\sum_{i=1}^r\Delta_i x_i,\qquad x_i\in\{0,1\},
\]
with $v_2(T_0)=a$, $5\nmid T_0$, and every free position at least
\[
H=\max\{a+2,\lceil(K+a)/2\rceil\}.
\]
Thus $10^H\mid\Delta_i$. Write $U_0=T_0/2^a$, $N_2=K-a$, $N_5=K$, and
\[
\rho_i=(\Delta_i/2^a)/U_0.
\]
The fractions have unit denominators at both primes. For $p=2,5$, exactly
\[
\log_p(T(x)/(2^aU_0))
\equiv\sum_i x_i\log_p(1+\rho_i)\pmod{p^{N_p}}.
\]

**Proof.** We have $v_2(\rho_i)\ge H-a\ge2$, $v_5(\rho_i)\ge H\ge1$, and
\[
v_2(\rho_i\rho_j)\ge K-a,\qquad
v_5(\rho_i\rho_j)\ge K.
\]
Consequently every mixed product vanishes and
\[
1+\sum_i\rho_ix_i\equiv\prod_i(1+\rho_i)^{x_i}\pmod{p^{N_p}}.
\]
Apply the logarithm homomorphism. Its convergent series is additive by the formal identity for the logarithm of a product. On $1+4\mathbb Z_2$, respectively $1+5\mathbb Z_5$, its first term has strictly smaller valuation than every later term. Hence $v_p(\log(1+w))=v_p(w)$, proving both congruence preservation and injectivity at the stated precision. This proves the assertion. □

Only pairs allowed to occur together need the mixed-product condition. Forbidden pairs, including two copies of one digit, have $x_ix_j=0$.

**Critical boundary. HIGH, computed and explained by the series.** Keep the exact coefficients $\log(1+\rho_i)$. Replacing them by $\rho_i$ can lose a 2-adic bit: $K=8,a=0,T_0=1111,\Delta=10^4$ gives $\rho=112$ but $\log_2(1+\rho)=240\pmod{256}$. Boolean idempotence absorbs each variable’s self-powers; it does not authorize dropping them.

## 2. Complete exponent congruences

**Theorem 2. HIGH, proved here.** Define
\[
\ell_2(u)=\log_2(\epsilon(u)u),\quad
\epsilon(u)\in\{1,-1\},\quad\epsilon(u)u\equiv1\pmod4,
\]
\[
\ell_5(u)=\tfrac14\log_5(u^4),\qquad
\tau(u)=\log_{2\bmod5}(u\bmod5)\in\mathbb Z/4.
\]
The condition $3^b7^c\equiv T(x)/2^a$ at both normalized precisions is equivalent to
\[
b+c\equiv\log_{-1}(U_0\bmod4)\pmod2,
\quad3b+c\equiv\tau(U_0)\pmod4,
\]
\[
b\ell_p(3)+c\ell_p(7)
-\sum_i x_i\log_p(1+\rho_i)
\equiv\ell_p(U_0)\pmod{p^{N_p}}.
\]

**Proof.** Theorem 1 gives the principal-unit equations. Every target ratio is 1 modulo 4 and modulo 5, so its torsion coordinates are fixed. The displayed torsion rows retain the sign at 2 and the residue at 5. The logarithm’s valuation identity then makes its remaining kernel trivial modulo the required prime power. Both directions follow. □

Divide the 2-adic log row by 4 and its modulus accordingly; divide the 5-adic row by 5. Add the original exponent coset $C=p+B\mathbb Z^2$ through
\[
\operatorname{adj}(B)((b,c)^T-p)\equiv0\pmod{|\det B|}.
\]
All equations are affine integer congruences in $y=(x,b,c)$. Successive extended-gcd intersections construct their solution set as either empty or a full-rank affine lattice $y_0+\Lambda\subset\mathbb Z^{r+2}$. No target fiber is listed.

For construction, restrict one modular row to the current lattice basis. Unimodular Euclidean operations reduce its coefficient row to $(g,0,\ldots,0)$. Solving $gk\equiv d\pmod m$ either proves inconsistency or shifts the origin and scales the first basis vector by $m/\gcd(g,m)$. Thus each intersection preserves exactly all solutions.

## 3. Exact bounded search

**Theorem 3. HIGH, proved here.** For an integer $G\ge1$, scale coordinates by
\[
S=\operatorname{diag}(2,\ldots,2,G^{-1},G^{-1}),
\quad t=(1,\ldots,1,0,0).
\]
Enumerate every point of $S(y_0+\Lambda)$ within squared distance $r+2$ of $t$. Retain points with $|b|,|c|\le G$ and all digit/position constraints. The retained set is exactly the requested Boolean box intersection.

**Proof.** Every valid point contributes $r$ from its Boolean coordinates and at most 2 from its exponents, so is enumerated. Conversely each integer Boolean coordinate contributes at least 1; any coordinate outside $\{0,1\}$ contributes at least 9. Such a point has total at least $r+8>r+2$. Thus every enumerated point is Boolean, and the final filters impose precisely the remaining conditions. □

This gives rank $r+2$, independent of the number of congruence rows. Exact rational LLL preserves the lattice; complete Fincke–Pohst enumeration certifies exhaustion. LLL/BKZ or Babai alone cannot certify a negative answer. Enumeration background: [Galbraith, Chapter 18](https://www.math.auckland.ac.nz/~sgal018/crypto-book/ch18.pdf), read.

Kannan embedding adds one coordinate: use generators $(S\Lambda,0)$ and $(Sy_0-t,\eta)$, with $\eta>0$. Enumerating through squared radius $r+2+\eta^2$ and retaining last coordinate $\pm\eta$, with the corresponding sign, gives the same search in rank $r+3$. Vectors in the zero layer are irrelevant. This embedding was proved here but not implemented.

Binary search on $G$ minimizes integer exponent height $\max(|b|,|c|)$. Handle $G=0$ directly. For physical exponents additionally require $b,c\ge0$. A certified digit bound $n<G_{\rm digits}$ permits the conservative exponent box $G=3\lceil G_{\rm digits}\rceil$, since $3^3>10$ and $7^3>10$. Baker digit bounds must not be used unchanged as exponent bounds.

## 4. Full copy family and cost

**Theorem 4. HIGH, proved here.** Let
\[
\ell_j=\#\{0\le t<D:e_j+96t<H\}.
\]
Branch for digit $j$ over its $\ell_j$ low copies or “no low copy.” Reject physical collisions. In each branch set
\[
T_0=R_K+\sum_{\text{fixed low copies}}(d_j-1)10^{e_j+96t_j}.
\]
Reject wrong valuation or divisibility by 5. For each unfixed digit introduce one Boolean selector per remaining visible copy, with sum at most 1. All-zero means $t_j\ge D$. Apply Theorems 1–3.

**Proof.** Every genuine assignment determines exactly one labeled low branch and one admissible selector vector. Its target is the displayed affine target, so survives every equivalence and lies in the enumerated ball whenever its exponents meet the box. Conversely each retained vector reconstructs such an assignment. Repeated digits retain separate labels; collisions concern physical positions. □

The construction costs
\[
\prod_j(\ell_j+1)\left[\operatorname{poly}(qD,L)+E(r+2,L)\right],
\qquad r\le\sum_j(D-\ell_j),
\]
as an upper bound using the largest branch dimension. Here $L$ includes $96D$, coset bit lengths, and $\log(G+1)$; $E$ is complete enumeration cost, dependent on reduced-basis geometry. It is not a polynomial-time oracle.

For fixed $a$, $\ell_j=D/2+O(1)$, so low branching remains approximately $(D/2+1)^q$, and Boolean rank can be approximately $qD/2+2$. Exactly, if $a=0,D=2d$, every $\ell_j=d$: there are $(d+1)^q$ low branches before filtering and Boolean rank at most $qd+2$. One optional copy per digit gives the desired $q+3$ embedding rank **per low branch**.

**HIGH, proved obstruction to ordinary index-bit linearization.** Write four high copy contributions as $\alpha B^t$, $B=10^{96}$, $t=u+2v$, with $v_5(\alpha)=H$, $2H\ge K$, and $H+288<K$. Modulo $5^K$ each log increment equals $\alpha B^t$, because its quadratic and higher terms vanish. Their mixed Boolean difference is
\[
\alpha(B^3-B^2-B+1)
=\alpha(B-1)(B^2-1)\not\equiv0\pmod{5^K}.
\]
Its valuation is $H<K$. Thus even entirely high copies are not affine in the usual binary digits of their index. This does not exclude another encoding or algorithm.

## 5. Recovering rank $q+3$, with a sparse domain

**Theorem 5. HIGH, proved here.** In one low branch, let digit $j$ have first remaining high position $m_j$ and $h_j$ visible high copies. Put $B=10^{96}$ and
\[
u_j\in\{0,1,B,\ldots,B^{h_j-1}\},\qquad
\Delta_j=(d_j-1)10^{m_j}.
\]
The target logs are exactly affine in these integer coordinates. Theorem 2 therefore gives rank $f+2$, where $f\le q$ counts unfixed digits with visible high copies. Kannan embedding has rank $f+3$.

**Proof.** Each normalized $\rho_j$ satisfies $\rho_j^2=0$ modulo both prime-power precisions. The integer binomial identity gives $(1+\rho_j)^{u_j}\equiv1+u_j\rho_j$. Mixed products also vanish. Taking logarithms yields the same equations with $x_i$ replaced by $u_j$. The sparse alphabet encodes exactly one high copy or absence. □

For complete search, scale coordinate $u_j$ by $2/W_j$, $W_j=B^{h_j-1}$, and center it at 1. Every allowed value contributes at most 1 to squared distance, so radius squared $f+2$ still covers every solution. Enumerate completely, then filter the sparse alphabets and physical collisions. This decides the branch without explicitly constructing its exponent fibers.

**HIGH, proved cost limitation.** The cost law becomes the same low-branch factor times $\operatorname{poly}(qD,L)+E(f+2,L)$, but the interval relaxation can be disastrous. In a rank-3 toy lattice, impose $u\equiv2\pmod3$, $b,c\equiv0\pmod T$, with $T>\sqrt3G$. Alphabet $\{0,1,B\}$ has no allowed residue, since $B\equiv1\pmod3$. Nevertheless the search ball contains at least $\lfloor B/3\rfloor$ points with $0\le u\le B$, $b=c=0$. Thus low rank alone supplies no useful enumeration bound. This is an algorithmic counterexample, not a claim about survivor data.

## 6. Prototype and differential plan

**HIGH, computed.** `codex-n1/prototype.py` implements finite p-adic logs, congruence intersection, exact rational LLL, complete sphere enumeration, low branching, and one-hot/collision filters. It also implements the sparse-alphabet high-position solver. `results.json` records PASS under Python 3.14.7 in 37.1 seconds:

- 13,524 comparisons with direct modular exponentiation.
- 60 random lattice systems versus exhaustive search: 49 feasible, 11 infeasible.
- 12 combined parent/target systems and three planted precision-96/192 systems, including $a=40$.
- Four complete toy copy families versus exhaustive search, preserving both repeated-label realizations of $6561=3^8$.
- A planted rank-4 sparse-alphabet case matched exhaustive search; a rank-3 negative required filtering 57 sphere points.
- Planted nonaffinity and 2-adic truncation failures; budget exhaustion returns UNKNOWN.

From the requested working directory, after checking the clock:
```bash
date '+%Y-%m-%d %H:%M:%S %Z'
UV_CACHE_DIR="$PWD/tier0-opt/math/codex-n1/uv-cache" \
PYTHONDONTWRITEBYTECODE=1 uv run --no-project --offline --python 3.14 \
python tier0-opt/math/codex-n1/prototype.py --self-test
```
The script refuses computation during 01:45–05:30 Eastern time and checks during enumeration/reduction.

**MEDIUM, planned, not executed on the 43 survivors.** Pin inputs and the recorded source hashes; preserve full $(s,M,a,y,\nu,\epsilon)$ keys. Recover every permitted representation using deepcut’s corrected wrap bound and multiplicities. At depths 1–4, compare symbolic feasibility against the union of every enumerated sandwich fiber using the **same exponent box** and exact two-dimensional box tests. Separately compare minimum squared Euclidean norms when reproducing sandwich’s norm objective; a Euclidean norm threshold and a box threshold are different tests.

Include repeated $(d,e)$, class collisions, the absent-copy sentinel, $a$ near the precision limit, genuine long S-units, corrupted targets, and resource limits. Budget-limited references yield UNKNOWN. Verify the actual input census rather than forcing 43 by merging records. Log every mismatch with its assignment and exponent witness.

## where this breaks

**HIGH, established limitations.** Low-copy branching remains exponential. Boolean one-hot dimension grows with $qD$; sparse-domain compression retains low rank but can require far more enumeration. A nearest point outside the box does not prove that every point misses it. Neither lattice density heuristics nor observed exhaustion of a different search establishes rejection.

The suffix model requires the candidate length to reach $K$; short exceptional anchors require separate treatment. Precisions $K<a+3$ need another exact unit-group treatment. The prototype’s small planted boxes do not establish performance on Baker-sized boxes. No survivor closure, general speedup, or conjectural local-to-global inference is claimed.

File: `tier0-opt/math/codex-n1-attempt.md`. Ran the prototype three times before 01:45 EDT; the final expanded suite passed. Did not run the 43-survivor differential, BKZ, Kannan embedding, Lean, or production closure computations.
