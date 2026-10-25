#!/usr/bin/env python3
"""N(k) under explicit abc-type hypotheses for the digit chain of 9y'+1 = 10^n + sum c_j 10^{E_j}.

General lemma (CONDITIONAL.md, Thm A): under ABC_f (c <= R f(R) for coprime a+b=c, R = rad(abc)),
every solution with k >= 1 non-1 digits satisfies
    n <= (k+1) * ( log10(16800) + Phi_f(n)/log 10 ),   Phi_f(n) = sup_{N <= 16800*10^n} log f(N).
N_f(k) := largest n satisfying this (computed by scanning upward until the inequality fails and
verifying it keeps failing; all functions used have Phi(n)/n decreasing eventually).
"""
import math
from math import log, exp, sqrt

L10 = log(10.0)
C0 = log(16800.0)            # 210*80
c0 = C0 / L10                # 4.2253...

def log2(x): return log(log(x))
def log3(x): return log(log(log(x)))

# ---------- f-functions (return log f(N) as a function of L = log N) ----------
def logf_rst_bare(L, kappa=4*sqrt(3)):
    """exp(kappa sqrt(L/log L)) for L >= log 16, constant below."""
    L = max(L, log(16.0))
    return kappa*sqrt(L/log(L))

def logf_rst(L, C1):
    """RST Conjecture A, (1.5), with explicit C1; N >= 16 (log3 N defined for N > e^e = 15.15)."""
    L = max(L, log(16.0))
    l2 = log(L); l3 = log(l2)
    return 4*sqrt(3*L/l2)*(1 + l3/(2*l2) + C1/l2)

def logf_abc(L, eps, logK):
    return logK + eps*L

# ---------- Phi(n) = sup over N <= 16800*10^n ----------
def Phi(logf, n, grid=None):
    Lmax = C0 + n*L10
    # sup over a grid in L from log16 to Lmax (functions are increasing for L large; grid guards small-L bumps)
    best = -1e300
    m = 400
    for i in range(m+1):
        L = log(16.0) + (Lmax-log(16.0))*i/m
        best = max(best, logf(L))
    best = max(best, logf(Lmax))
    return best

def N_of_k(logf, k, nmax=10**7):
    """largest n with n <= (k+1)(c0 + Phi(n)/log10). Scan: find first n0 where it fails, then confirm
    failure persists on a sparse grid up to nmax (sanity; the functions are sublinear)."""
    n = 1
    last_ok = 0
    while n <= nmax:
        rhs = (k+1)*(c0 + Phi(logf, n)/L10)
        if n <= rhs:
            last_ok = n
            n = max(n+1, int(rhs*0.995))   # jump (rhs is an upper bound candidate; keep monotone scan safe)
        else:
            # verify no larger n satisfies it: check a few multiples
            for m in (1.05, 1.2, 1.5, 2, 4, 10, 100):
                nn = int(n*m)+1
                assert nn > (k+1)*(c0 + Phi(logf, nn)/L10), (k, nn)
            break
    # refine: scan from last_ok upward one by one
    n = last_ok
    while True:
        rhs = (k+1)*(c0 + Phi(logf, n+1)/L10)
        if n+1 <= rhs: n += 1
        else: break
    return n

# ---------- Baker explicit abc via Chim-Shorey-Sinha ----------
def G1_of_lambda(lam):
    """G_1(N) with lam = log N (N >= 297856)."""
    A = log(lam) - log(log(lam))
    A1 = A + log(A) - 1.076869
    return (1 + log(A1))/A1

def N_baker(k):
    """n <= (k+1)(c0 + (log(6/5) + G1(R*) (C0 + n log10))/log10) + 1.72 log R*/log 5, minimised over R*."""
    best = None
    # scan lam = log R* on a log grid
    for i in range(0, 80000):
        u = 2.5 + i*0.005          # u = log lam = log log R*
        lam = exp(u)
        if lam < log(297856): continue
        if u > 400: break
        g = G1_of_lambda(lam)
        if (k+1)*g >= 1: continue
        num = (k+1)*(c0 + (log(1.2) + g*C0)/L10) + 1.72*lam/log(5.0)
        n = num/(1 - (k+1)*g)
        if best is None or n < best[0]: best = (n, lam, g)
    return best

# ---------- plain abc(eps, K) ----------
def N_abc(k, eps, log10K):
    if (k+1)*eps >= 1: return math.inf
    return (k+1)*(c0*(1+eps) + log10K)/(1-(k+1)*eps)

def best_abc(k, log10K_of_eps):
    """minimise over eps."""
    best = None
    for i in range(1, 100000):
        eps = i*1e-6
        if (k+1)*eps >= 1: break
        v = N_abc(k, eps, log10K_of_eps(eps))
        if best is None or v < best[0]: best = (v, eps)
    return best

# ---------- Lang-Waldschmidt shape LW(eps, c0) ----------
def N_LW(k, eps, cc):
    """n(1 - k eps/(1+eps)) <= Ctop + k Cint/(1+eps), log B = log(3.33 n + 2); solve by iteration."""
    if k*eps/(1+eps) >= 1: return math.inf
    n = 10.0
    for _ in range(200):
        lB = log(3.33*n + 2)
        Ctop = (log(80) + (1+eps)*(log(420) + 4*lB) + 4*cc)/L10
        Cint = (log(80) + eps*log(9) + (1+eps)*(log(420) + 5*lB) + 5*cc)/((1+eps)*L10)
        n_new = (Ctop + k*Cint)/(1 - k*eps/(1+eps))
        if abs(n_new - n) < 1e-6: break
        n = n_new
    # the fixed point is the largest solution since RHS grows like log n
    return n

def best_LW(k, cc):
    best = None
    for i in range(1, 20000):
        eps = i*1e-5
        if k*eps/(1+eps) >= 1: break
        v = N_LW(k, eps, cc)
        if best is None or v < best[0]: best = (v, eps)
    return best

if __name__ == "__main__":
    beta = 1 + log(3) - 13/6*log(2)
    print("beta =", beta)
    ks = [16, 20, 22, 25, 26, 27, 28, 29, 31, 34, 35, 36, 42, 44]
    # monotonicity check of f_RST on [16, 10^20000]
    for C1 in (0.0, beta, 1.0, 2.0, 5.0, 10.0):
        Ls = [log(16)*(1.001**i) for i in range(0, 20000) if log(16)*(1.001**i) < 60000]
        vals = [logf_rst(L, C1) for L in Ls]
        mono = all(vals[i] <= vals[i+1] + 1e-12 for i in range(len(vals)-1))
        print(f"C1={C1:.4f}: log f_RST increasing on [16,e^60000]? {mono}")
    print()
    hdr = ["k", "bare 4sqrt3", "RST[0]", "RST[beta]", "RST[1]", "RST[2]", "RST[5]", "RST[10]", "bare k=8", "bare k=10"]
    print(" | ".join(hdr))
    rows = {}
    for k in ks:
        r = [k]
        r.append(N_of_k(lambda L: logf_rst_bare(L), k))
        for C1 in (0.0, beta, 1.0, 2.0, 5.0, 10.0):
            r.append(N_of_k(lambda L, C1=C1: logf_rst(L, C1), k))
        r.append(N_of_k(lambda L: logf_rst_bare(L, 8.0), k))
        r.append(N_of_k(lambda L: logf_rst_bare(L, 10.0), k))
        rows[k] = r
        print(" | ".join(str(x) for x in r))
    print()
    print("Baker explicit abc (CSS 2019 form): k, log10 N(k) [digits], log10 log R*, G1(R*)")
    for k in ks:
        n, lam, g = N_baker(k)
        print(k, f"{math.log10(n):.2f}", f"{math.log10(lam):.3f}", f"{g:.5f}")
    print()
    print("endpoint check: Phi attained at right endpoint for n = N(k)?")
    for C1 in (0.0, beta, 1.0, 2.0, 5.0, 10.0):
        for k in (16, 44):
            n = N_of_k(lambda L, C1=C1: logf_rst(L, C1), k)
            Lmax = C0 + n*L10
            sup = max(logf_rst(log(16)+(Lmax-log(16))*i/100000, C1) for i in range(100001))
            print(f"C1={C1:.3f} k={k} n={n} endpoint={logf_rst(Lmax,C1):.6f} sup={sup:.6f} ok={logf_rst(Lmax,C1)>=sup-1e-9}")
    print()
    print("plain abc(eps,K): max log10 K so that N(k;eps=1/(2(k+1)),K) <= 4000, and <= 8000")
    for k in ks:
        eps = 1/(2*(k+1))
        # N = (k+1)(c0(1+eps)+x)/(1-(k+1)eps) <= T  => x <= T(1-(k+1)eps)/(k+1) - c0(1+eps)
        for T in (4000, 8000):
            x = T*(1-(k+1)*eps)/(k+1) - c0*(1+eps)
            print(k, T, f"eps=1/{2*(k+1)} log10K<= {x:.1f}", end="; ")
        print()
    print()
    print("abc(eps,K) with K from RST-bare (log K(eps) = sup_L [kappa sqrt(L/logL) - eps L]), best eps:")
    def logK_from_rst(eps, kappa=4*sqrt(3)):
        best = 0.0
        L = log(16.0)
        while L < 1e7:
            best = max(best, kappa*sqrt(L/log(L)) - eps*L)
            L *= 1.01
        return best/L10
    for k in (29, 44):
        v, eps = best_abc(k, logK_from_rst)
        print(k, f"N={v:.0f} at eps={eps:.5f}, log10K={logK_from_rst(eps):.1f}")
    print()
    print("LW(eps, c0) hypothetical (Lang-Waldschmidt shape), best eps; c0 in {0, 10, 50}:")
    for k in ks:
        out = []
        for cc in (0.0, 10.0, 50.0):
            v, eps = best_LW(k, cc)
            out.append(f"c0={cc:.0f}: N={v:.0f} (eps={eps:.4f})")
        print(k, "; ".join(out))

# ---------- Baker explicit, one-regime version with G(N) (CSS Thm 1.3 (1.8)), f_B(N) = (6/5) N^{G(N)} ----------
def G_of_lambda(lam):
    A = log(lam) - log(log(lam))
    return (1 + log(A))/A

def N_baker_G(k, useG1=False):
    """largest n with n <= (k+1)(c0 + (log 1.2 + G(Rmax) log Rmax)/log10), Rmax = 16800*10^n; lam = log Rmax.
    Solve in u = log lam by bisection on phi(u) = (k+1)(c0+log1.2/log10 + G lam/log10) - (lam - C0)/log10."""
    Gf = G1_of_lambda if useG1 else G_of_lambda
    def phi(u):
        lam = exp(u)
        # divide by lam to keep it finite: sign unchanged
        return ((k+1)*(c0 + log(1.2)/L10) + C0/L10)/lam + (k+1)*Gf(lam)/L10 - 1/L10
    lo, hi = 5.0, 600.0
    assert phi(lo) > 0 and phi(hi) < 0
    for _ in range(200):
        mid = (lo+hi)/2
        if phi(mid) > 0: lo = mid
        else: hi = mid
    # n = (exp(hi) - C0)/log10 ; report log10 n = hi/log10 - log10(log10)
    log10n = hi/L10 - math.log10(L10)
    return log10n, hi, Gf(exp(hi))

if __name__ == "__main__":
    print()
    print("Baker explicit, one-regime: k, log10 N(k) with G, with G1, (k+1)G at the root")
    for k in ks:
        nG, uG, gG = N_baker_G(k)
        n1, u1, g1 = N_baker_G(k, True)
        print(k, f"G: log10 N = {nG:.3f}  (k+1)G={(k+1)*gG:.6f} | G1: log10 N = {n1:.3f}")
    print()
    print("LW(eps,c0) at eps = 1/(2(k+1)):")
    for k in ks:
        eps = 1/(2*(k+1))
        print(k, " ".join(f"c0={cc}: {N_LW(k, eps, cc):.0f}" for cc in (0, 10, 50, 100)))
    print()
    print("Matveev (Theorem U) ceilings for comparison: BAKER-CHAIN table log10 G(k,0): 29: 506.2, 31: 541.1, 44: 768.7 (TABLES D)")

if __name__ == "__main__":
    print()
    print("VERIFICATION of headline columns: n=N(k) satisfies n <= rho(n), n=N(k)+1 violates; Phi = sup on 20000-grid")
    def Phi_fine(logf, n):
        Lmax = C0 + n*L10
        return max(logf(log(16.0)+(Lmax-log(16.0))*i/20000) for i in range(20001))
    for name, logf in (("bare", lambda L: logf_rst_bare(L)), ("RST[beta]", lambda L: logf_rst(L, beta)),
                       ("RST[1]", lambda L: logf_rst(L, 1.0)), ("RST[2]", lambda L: logf_rst(L, 2.0))):
        for k in ks:
            n = N_of_k(logf, k)
            r0 = (k+1)*(c0 + Phi_fine(logf, n)/L10); r1 = (k+1)*(c0 + Phi_fine(logf, n+1)/L10)
            assert n <= r0 and n+1 > r1
            print(f"{name:10s} k={k:2d} N(k)={n:5d}  rho(N)={r0:9.3f}  rho(N+1)={r1:9.3f}")
    print()
    print("non-monotone region of log f_RST(C1): first L0 beyond which log f(L) >= max_{L'<=L0} log f and increasing")
    for C1 in (beta, 1.0, 2.0, 5.0, 10.0):
        Ls = [log(16)*(1.0005**i) for i in range(0, 40000)]
        vals = [logf_rst(L, C1) for L in Ls]
        m = max(vals[:1])
        # find first index i such that vals[j] is increasing for all j>=i and vals[i] >= max(vals[:i])
        idx=None
        for i in range(len(vals)-1):
            if vals[i] >= max(vals[:i+1]) and all(vals[j] <= vals[j+1] for j in range(i, len(vals)-1)):
                idx=i; break
        print(f"C1={C1:.3f}: endpoint rule valid for log N >= {Ls[idx]:.1f} (i.e. N >= 10^{Ls[idx]/L10:.1f})")
