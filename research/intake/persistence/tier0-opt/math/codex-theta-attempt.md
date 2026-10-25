# Second attempt: sublinear gap bounds from affine exponent cosets

**No unconditional sublinear-in-height gap bound was obtained for the full family.** The results are a cofactor-sensitive bound, a height-free special case, an exact bounded-coordinate rejection test, and a constructive limitation of local congruence arguments. No hardest case closes; no generic Baker constant improves.

All theorem claims below are **proved on paper, confidence HIGH**, with numerical tests distinguished explicitly. Nothing has Cairn's **PROVEN** status: there is no Lean check, statement-level review, or substrate admission. The numerical experiments are standalone reproducible computations.

Grounding: I read `codex-deep-attempt.md`, `codex-brainstorm.md`, `breakthrough/b3-archimedean/REPORT.md`, and `breakthrough/b1-obstruction/MAP.md`. I did not read the excluded parallel lane. No conjecture is assumed.

## Theorem 1: the relevant height is the nonsmooth cofactor

Consider consecutive exceptional positions \(e>f\), with gap \(g=e-f\) and fixed-prefix length \(h=n-e\). All logarithms are natural unless marked otherwise. Write
\[
9y=10^eN+T,\qquad N=9\lfloor y/10^e\rfloor+1.
\]
The fixed upper digits determine \(N\); the lower exceptional digits determine \(T\). With digits at most 9 and distinct positions,
\[
0<T<80\,10^f.\tag{U: tail bound}
\]
Factor \(N=2^r7^tR\), removing every factor of 2 and 7. There is no factor of 3 because \(N\equiv1\pmod9\). Set
\[
H_R=\max(1,\log R),\quad
B=\max(3,|a-r|,b+2,|c-t|,e),
\]
\[
C_m=8\,30^{m+3}m^{9/2}\log3\log7\log10.
\]
Then
\[
g\log10+\log N
<\log80+C_mH_R\log(\mathrm eB),\tag{G: cofactor gap}
\]
where \(m=5\) when \(R>1\), and \(m=4,H_R=1\) when \(R=1\). Also
\[
B<4n+4.\tag{B: coefficient bound}
\]

**Proof.** The nonzero form is
\[
\Lambda=2^{a-r}3^{b+2}7^{c-t}10^{-e}R^{-1}-1
=T/(10^eN).
\]
By (U),
\[
\log\Lambda<\log80-g\log10-\log N.\tag{A: archimedean upper bound}
\]
[Bugeaud–Kaneko, Theorem 2.1, (2.1)](https://arxiv.org/html/1704.00432v1) applied to these fixed rational bases gives
\[
\log\Lambda>-C_mH_R\log(\mathrm eB).\tag{L: logarithmic lower bound}
\]
For base 2 its permitted height factor is 1; the other three factors are their logarithms. Delete \(R\) when it equals 1. Combining (A) and (L) proves (G). Finally \(y<10^n\) and \(N<10^{n+1}\) bound each prime exponent and give (B).

Thus **\(R=1\) gives a genuine height-free bound**, with the usual logarithmic dependence on \(B\). **CONDITIONAL subclass conclusion:** sublinear growth of \(\log R\) with \(h\) would give sublinear height dependence in (G). That condition is not established for the full family.

**Numerically tested, confidence HIGH.** \(C_4\approx4.40952343891222\times10^{14}\), \(C_5\approx3.61083770426747\times10^{16}\). For actual solutions \(y=32,72,1323\), respectively:

| Quantity | 32 | 72 | 1323 |
|---|---:|---:|---:|
| \(N,R,B\) | 28,1,3 | 64,1,4 | 118,59,5 |
| \(T<80\,10^f\) | 8<80 | 8<80 | 107<800 |
| \(\log\Lambda\), upper (A) | −3.55535, −1.25276 | −4.38203, −2.07944 | −4.70303, −2.69124 |
| Left, right of (G) | 5.63479, \(9.25388\times10^{14}\) | 6.46147, \(1.05224\times10^{15}\) | 7.07327, \(3.84196\times10^{17}\) |

For (L), negate the last-row right sides after subtracting \(\log80\); all pass. Bounds (B) read \(3<12,4<12,5<20\). These examples establish no useful interior improvement at Tier C.

## Theorem 2: stripping smooth factors cannot guarantee sublinearity

For every integer \(h\ge2\) with \(h\equiv2\pmod6\), the admissible decimal prefix
\[
P_h=2\,10^{h-1}+(10^{h-1}-1)/9+1
\]
contains exactly two 2s and otherwise 1s. Its associated numerator is
\[
N_h=9P_h+1=19\,10^{h-1}+9.
\]
It is coprime to 42, so its cofactor is the entire numerator. In particular,
\[
\log R_h>(h-1)\log10.\tag{H: linear residual height}
\]

**Proof.** \(N_h\) is odd, is 1 modulo 3, and is 3 modulo 7, since \(10^{h-1}\equiv3\pmod7\). Inequality (H) follows directly from its displayed value.

**Numerically tested, confidence HIGH.** At \(h=2,8,32,98\), all four gcds are 1, and \((\log R_h)/h\) is respectively \(2.646652412362,2.382816834687,2.322643026937,2.309134622445\), exceeding the corresponding right sides of (H) divided by \(h\): \(1.151292546497,2.014761956370,2.230629308838,2.279089326739\).

These are admissible prefixes with a fixed two-digit exceptional multiset, **not completed S-unit solutions**. They refute automatic cofactor shrinkage from prefix sparsity alone.

## Theorem 3: affine lifting gives a finite certificate, not a gap estimate

Fix \(v_2(Y_0)=a,v_5(Y_0)=0\), a parent suffix of length \(s\ge a+3\), and generators \(g_i=3^{u_i}7^{v_i}\) preserving it. For a block length \(L\), require
\[
1\le L\le s-a.\tag{P: affine precision}
\]
Set \(M=10^L\), \(A_i=Y_0(g_i-1)/10^s\pmod M\), using modular representatives for the quotients. For a desired suffix \(Q\equiv Y_0\pmod{10^s}\), put \(\beta=(Q-Y_0)/10^s\pmod M\). Then extension is exactly
\[
A_1z_1+A_2z_2\equiv\beta\pmod M.
\]
If \(|z_i|\le Z_i\), any integer \(\mu\) satisfying
\[
|[\mu\beta]_M|>Z_1|[\mu A_1]_M|+Z_2|[\mu A_2]_M|\tag{D: separation certificate}
\]
excludes the extension; brackets denote centered residues.

**Proof.** Quadratic terms vanish because
\[
2s-a\ge s+L,\qquad2s\ge s+L.\tag{V: quadratic valuations}
\]
Inversion preserves the expansion for negative coordinates. This proves the congruence; the triangle inequality proves (D).

**Numerically tested, confidence HIGH.** With \(a=2,s=6,Y_0=588\), use \(g_1=3^{12500},g_2=7^{12500}\). All 196 comparisons for \(L=1,\ldots,4\), \(z_i=-3,\ldots,3\), agree. At \(L=4\), (V) reads \(10\ge10,12\ge10\). The coefficient row is \((867,2410)\). For \(\beta=1111,Z_i=2,\mu=12\), (D) is **3332>2968**; exhaustive enumeration of 25 points confirms rejection. The feasible target \(\beta=867\) receives zero rejections across all 9,999 nonzero multipliers.

**Planted negative:** at forbidden \(L=5,z=(2,0)\), direct and affine residues are **31734000588** and **81734000588**. Precision cannot be extended merely by treating the coset affinely again.

## Theorem 4: long runs survive the specified lattice locally

Let \(\Lambda\) be the recorded lattice from `codex-deep-attempt.md`, with covolume \(2.809995097495096\times10^{56}\). It contains
\[
w=(5834300434592217394015440000,
5252227908597256497593760000).
\]
Put \(G=3^{w_1}7^{w_2}\). Exact modular arithmetic gives \(v_2(G-1)=9,v_5(G-1)=5\). Thus, modulo \(10^K\), its order is
\[
O_K=2^{K-9}5^{K-5}\quad(K\ge9).
\]
Its powers cover every unit congruent to 1 modulo \(2^9\) and \(5^5\): lifting the exponent gives the two component orders, which are coprime.

Take \(y_0=3^3\,7^{10}=7626831723\), \(q=1113231723\), and
\[
Q_r=q+10^{10}(10^r-1)/9,\qquad K=10+r.
\]
Since \(q-y_0\) is divisible by \(2^9\,5^5=1600000\), some
\[
0<t<O_K\tag{T: exponent representative}
\]
gives \(y_0G^t\equiv Q_r\pmod{10^K}\), for every positive \(r\). These S-units lie in the same exponent coset and have the fixed low word \(q\), followed upward by \(r\) ones. They also have digit length
\[
n>w_1/4>10^{27},\tag{N: length floor}
\]
because \(3^{tw_1}>2^{w_1}>10^{w_1/4}\).

**Numerically tested, confidence HIGH.** Exact modular lifting at \(r=4,32,128\) verifies these suffixes. Representatives for the first two are \(44120481<62500000\) and \(501557290997134973664141940794120481<625\times10^{33}\). Approximate \(\log_{10}n\) values are **35.503316740107, 63.558997049659, 159.397499792258**. Inequality (N) follows from the exact integer check \(w_1>4\times10^{27}\).

Reproduce the numerical checks; printed logarithms use floating-point approximations:

```bash
UV_CACHE_DIR=/private/tmp/uv-cache PYTHONDONTWRITEBYTECODE=1 uv run --no-project --offline python - <<'PY'
from math import gcd, log, log10
from fractions import Fraction
C={m:8*30**(m+3)*m**4.5*log(3)*log(7)*log(10) for m in (4,5)}
for y,a,b,c,e,f in ((32,5,0,0,1,0),(72,3,2,0,1,0),(1323,0,3,2,2,1)):
    assert y==2**a*3**b*7**c
    n=len(str(y)); N=9*(y//10**e)+1; R=N
    ex=[]
    for p in (2,7):
        j=0
        while R%p==0:
            R//=p; j+=1
        ex.append(j)
    rr,tt=ex; B=max(3,abs(a-rr),b+2,abs(c-tt),e)
    T=9*y-10**e*N; lam=log(float(Fraction(T,10**e*N)))
    upper=log(80)-(e-f)*log(10)-log(N)
    loss=C[4 if R==1 else 5]*max(1,log(R))*(1+log(B))
    assert 0<T<80*10**f and B<4*n+4
    assert -loss<lam<upper
    assert (e-f)*log(10)+log(N)<log(80)+loss
    print('G',y,log(10*N),log(80)+loss)
for h in (2,8,32,98):
    P=2*10**(h-1)+(10**(h-1)-1)//9+1
    N=9*P+1
    assert str(P).count('2')==2 and str(P).count('1')==h-2
    assert gcd(N,42)==1 and log(N)>(h-1)*log(10)
    print('H',h,log(N)/h)
def row(L):
    return [588*(pow(p,12500,10**(6+L))-1)//10**6%10**L for p in (3,7)]
checks=0
for L in range(1,5):
    assert 12-2>=6+L and 12>=6+L
    Q=10**(6+L); A=row(L)
    for z in range(-3,4):
        for v in range(-3,4):
            assert 588*pow(3,12500*z,Q)*pow(7,12500*v,Q)%Q==(588+10**6*(A[0]*z+A[1]*v))%Q
            checks+=1
A=row(4); center=lambda x:(x+5000)%10000-5000
assert A==[867,2410]
assert abs(center(12*1111))==3332>2*sum(abs(center(12*x)) for x in A)==2968
assert not any((A[0]*z+A[1]*v-1111)%10000==0 for z in range(-2,3) for v in range(-2,3))
assert not any(abs(center(mu*867))>2*sum(abs(center(mu*x)) for x in A) for mu in range(1,10000))
actual=588*pow(3,25000,10**11)%10**11
predicted=(588+2*10**6*row(5)[0])%10**11
assert (actual,predicted)==(31734000588,81734000588)
print('affine',checks,'negative',actual!=predicted)
w=(5834300434592217394015440000,5252227908597256497593760000)
v=(24550795595028192589139040000,-26061931100684490688131840000)
print('covolume',abs(w[0]*v[1]-w[1]*v[0]))
y0=7626831723
assert w[0]>4*10**27
assert (1113231723-y0)%1600000==0
for r in (4,32,128):
    K=10+r; Q=10**K
    target=1113231723+10**10*((10**r-1)//9)
    rho=target*pow(y0,-1,Q)%Q
    parts=[]
    for p,v in ((2,9),(5,5)):
        M=p**(v+1)
        g=pow(3,w[0],M)*pow(7,w[1],M)%M
        assert (g-1)%p**v==0 and (g-1)%M!=0
        t=0; step=1
        for j in range(v,K):
            M=p**(j+1)
            g=pow(3,w[0],M)*pow(7,w[1],M)%M
            ds=[d for d in range(p) if pow(g,t+d*step,M)==rho%M]
            assert len(ds)==1
            t+=ds[0]*step; step*=p
        parts.append((t,step))
    (t2,m2),(t5,m5)=parts
    t=t2+m2*((t5-t2)*pow(m2,-1,m5)%m5)
    assert 0<t<m2*m5
    assert pow(3,3+t*w[0],Q)*pow(7,10+t*w[1],Q)%Q==target
    logn=log10((3+t*w[0])*log10(3)+(10+t*w[1])*log10(7))
    print(r,'PASS',t,logn)
PY
```

## Where this breaks

**Confidence HIGH:** Theorem 4 does not control digits above the tested suffix. It is not a counterexample with the full fixed multiset, nor does it contradict a bound containing \(\log B\): its exponents grow rapidly with \(r\).

**Confidence HIGH:** Differences between two candidates sharing a target remove the inhomogeneous target; a gap theorem must also exclude a single candidate. Neither covolume nor affine surjectivity supplies that exclusion. Theorem 3 needs actual bounded-coordinate separation, whose uniform strength remains unproved.

**Hypothesis, confidence LOW:** simultaneous control of the high prefix and low affine fiber might force such separation uniformly. No inequality establishing this was found. The smooth-prefix special case and local certificates therefore do not justify \(\theta<1\), even \(\theta=0.99\), for the requested family.
