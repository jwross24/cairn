import sys, os, math, time
from collections import Counter, defaultdict
from fractions import Fraction
import gmpy2
from gmpy2 import mpq

sys.dont_write_bytecode = True
from n1lib import *
from fpylll import IntegerMatrix, LLL, BKZ, FPLLL

FPLLL.set_precision(400)


def reduce_rows(rows, bkz=0):
    A = IntegerMatrix.from_matrix(rows)
    LLL.reduction(A, delta=0.99)
    if bkz and len(rows) > bkz:
        BKZ.reduction(A, BKZ.Param(block_size=bkz, flags=BKZ.AUTO_ABORT | BKZ.MAX_LOOPS, max_loops=6),
                      float_type="mpfr", precision=400)
    return [[int(A[i, j]) for j in range(A.ncols)] for i in range(A.nrows)]


def gso_q(B):
    n = len(B)
    G = [[sum(x * y for x, y in zip(B[i], B[j])) for j in range(n)] for i in range(n)]
    mu = [[mpq(0)] * n for _ in range(n)]
    r = [mpq(0)] * n
    for i in range(n):
        for j in range(i):
            s = mpq(G[i][j])
            for k in range(j):
                s -= mu[i][k] * mu[j][k] * r[k]
            mu[i][j] = s / r[j]
        s = mpq(G[i][i])
        for k in range(i):
            s -= mu[i][k] ** 2 * r[k]
        r[i] = s
    return G, mu, r


def valid_x(x, vars_, types):
    cnt = Counter()
    pos = Counter()
    for (d, e, t), xi in zip(vars_, x):
        if xi:
            cnt[(d, e)] += 1
            pos[(e, t)] += 1
            if pos[(e, t)] > 1:
                return False
    return all(cnt[k] <= types[k] for k in cnt)


def solve_min(sysd, a, nn0, nodes_cap=int(os.environ.get('N1_EXACT_NODECAP', 50_000_000)), bkz=0, exact_leaf=True):
    """exact minimum, over every admissible high-block placement and every lattice point of the linear
    system, of the squared (b, c) norm; leaves are verified by exact modular exponentiation."""
    co = sysd['co']
    vars_ = sysd['vars']
    m = len(vars_)
    M = sysd['M']
    K = sysd['K']
    types = sysd['types']
    u1, u2 = co.u1, co.u2
    v0 = co.v0
    avec = sysd['alpha'] + sysd['omega']
    rows_k, part = kernel_basis_and_particular(avec, sysd['beta'], M)
    L = math.isqrt(nn0) + 2
    n = 2 + m

    def emb(v):
        z1, z2 = v[0], v[1]
        return [2 * (z1 * u1[0] + z2 * u2[0]), 2 * (z1 * u1[1] + z2 * u2[1])] + [2 * L * xi for xi in v[2:]]

    B0 = [emb(r) for r in rows_k]
    t0 = time.time()
    B = reduce_rows(B0, bkz)
    t_red = time.time() - t0
    xp = part[2:]
    pe = emb(part)
    target = [-(pe[0] + 2 * v0[0]), -(pe[1] + 2 * v0[1])] + [L - 2 * L * xi for xi in xp]
    G, mu, r = gso_q(B)
    T = [sum(x * y for x, y in zip(B[j], target)) for j in range(n)]
    g = [mpq(0)] * n
    for j in range(n):
        s = mpq(T[j])
        for k in range(j):
            s -= mu[j][k] * g[k]
        g[j] = s
    tau = [g[j] / r[j] for j in range(n)]
    c0 = [0] * n
    for j in range(n - 1, -1, -1):
        s = tau[j]
        for i in range(j + 1, n):
            s -= mu[i][j] * c0[i]
        t_ = s + mpq(1, 2)
        c0[j] = int(t_.numerator // t_.denominator)
    cen0 = []
    for j in range(n):
        s = tau[j]
        for i in range(j + 1, n):
            s -= mu[i][j] * c0[i]
        cen0.append(float(s - c0[j]))
    R2 = 4 * nn0 + L * L * m
    scale = mpq(R2)
    rf = [float(r[j] / scale) for j in range(n)]
    muf = [[float(mu[i][j]) for j in range(n)] for i in range(n)]
    best = {'nn': nn0, 'x': [0] * m, 'found': 0}
    stats = {'nodes': 0, 'leaves': 0, 'valid': 0, 'inexact': 0}
    radius = [1.0 + 1e-7]
    d = [0] * n

    def leaf():
        c = [c0[i] + d[i] for i in range(n)]
        v = [sum(c[i] * B[i][j] for i in range(n)) for j in range(n)]
        pt = [v[j] - target[j] for j in range(n)]
        xfull = []
        for j in range(2, n):
            val = pt[j]
            if (val + L) % (2 * L) != 0:
                return
            xv = (val + L) // (2 * L)
            if xv not in (0, 1):
                return
            xfull.append(xv)
        if pt[0] % 2 or pt[1] % 2:
            return
        if not valid_x(xfull, vars_, types):
            return
        b, cc = pt[0] // 2, pt[1] // 2
        stats['valid'] += 1
        if exact_leaf:
            if lattice_point_value(b, cc, a, K) != target_value(sysd['Tbase'], vars_, xfull, K):
                stats['inexact'] += 1
                return
        nnv = b * b + cc * cc
        if nnv < best['nn']:
            best['nn'] = nnv
            best['x'] = xfull
            best['found'] += 1
            radius[0] = float(mpq(4 * nnv + L * L * m) / scale) * (1.0 + 1e-7)

    sys.setrecursionlimit(10000)

    def rec(i, partial):
        center = cen0[i]
        for k in range(i + 1, n):
            if d[k]:
                center -= muf[k][i] * d[k]
        ci = math.floor(center + 0.5)
        s = 1 if center >= ci else -1
        k = 0
        while True:
            if k == 0:
                cur = ci
            elif k % 2:
                cur = ci + s * ((k + 1) // 2)
            else:
                cur = ci - s * (k // 2)
            dist = cur - center
            pc = partial + rf[i] * dist * dist
            if pc > radius[0]:
                break
            stats['nodes'] += 1
            if stats['nodes'] > nodes_cap:
                d[i] = 0
                return False
            d[i] = cur
            if i == 0:
                stats['leaves'] += 1
                leaf()
            elif rec(i - 1, pc) is False:
                d[i] = 0
                return False
            k += 1
        d[i] = 0
        return True

    ok = rec(n - 1, 0.0)
    return dict(nn=best['nn'], x=best['x'], improved=best['found'], nodes=stats['nodes'], leaves=stats['leaves'],
                valid=stats['valid'], inexact=stats['inexact'], complete=bool(ok), t_reduce=t_red,
                t_total=time.time() - t0, L=L, dim=n)
