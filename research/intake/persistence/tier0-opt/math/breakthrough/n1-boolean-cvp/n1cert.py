import sys, math, time
from collections import defaultdict
from fractions import Fraction

sys.dont_write_bytecode = True
from n1lib import *
from n1solve import reduce_rows


def disc_radius2(U):
    """largest squared norm that the sandwich excludes: closes(nn, U) <=> nn > rho2."""
    return (2 * U * U * 10 ** 20) // ELL_LO ** 2


def z_box(co, rho2):
    """integer box containing every z with ||v0 + U z||^2 <= rho2 (superset of the disc)."""
    u1, u2 = co.u1, co.u2
    v0 = co.v0
    det = u1[0] * u2[1] - u2[0] * u1[1]
    ad = abs(det)
    rho = math.isqrt(rho2) + 1
    n1 = math.isqrt(u1[0] ** 2 + u1[1] ** 2) + 1
    n2 = math.isqrt(u2[0] ** 2 + u2[1] ** 2) + 1
    c1 = Fraction(-(u2[1] * v0[0] - u2[0] * v0[1]), det)
    c2 = Fraction(-(-u1[1] * v0[0] + u1[0] * v0[1]), det)
    r1 = Fraction(rho * n2, ad)
    r2 = Fraction(rho * n1, ad)
    lo1 = math.ceil(c1 - r1)
    hi1 = math.floor(c1 + r1)
    lo2 = math.ceil(c2 - r2)
    hi2 = math.floor(c2 + r2)
    return (lo1, hi1), (lo2, hi2)


def cent(x, M):
    x %= M
    return x - M if 2 * x > M else x


def check_mu(mu, M, alpha, omega, beta, vars_, zb):
    """exact interval test for one multiplier. returns (certified, slack)"""
    r = [cent(mu * al, M) for al in alpha]
    lo = hi = 0
    for rr, (zl, zh) in zip(r, zb):
        if rr >= 0:
            lo += rr * zl
            hi += rr * zh
        else:
            lo += rr * zh
            hi += rr * zl
    groups = defaultdict(list)
    for (d, e, t), om in zip(vars_, omega):
        groups[(e, t)].append(cent(mu * om, M))
    for g in groups.values():
        lo += min(0, min(g))
        hi += max(0, max(g))
    b = (mu * beta) % M
    klo = -((b - lo) // M)
    khi = (hi - b) // M
    return klo > khi, (hi - lo)


def find_certificate(M, alpha, omega, beta, vars_, zb, bkz=0, extra=1):
    """lattice reduction over the multiplier: coordinates weighted by the box widths."""
    w = [max(1, zb[0][1] - zb[0][0]), max(1, zb[1][1] - zb[1][0])] + [1] * len(omega)
    a_all = alpha + omega
    n = len(a_all)
    rows = [[1] + [w[j] * a_all[j] if j == i else 0 for j in range(n)] for i in range(0)]
    rows = [[extra] + [w[j] * a_all[j] for j in range(n)]]
    for j in range(n):
        r = [0] * (n + 1)
        r[1 + j] = w[j] * M
        rows.append(r)
    B = reduce_rows(rows, bkz)
    best = None
    cands = []
    for row in B:
        mu = row[0] // extra if row[0] % extra == 0 else None
        if mu is None or mu % M == 0:
            continue
        cands.append(mu)
    for i in range(len(cands)):
        for s in (1, -1):
            ok, wid = check_mu(s * cands[i], M, alpha, omega, beta, vars_, zb)
            if ok:
                return True, s * cands[i], wid
            if best is None or wid < best:
                best = wid
    for i in range(min(len(cands), 6)):
        for j in range(i + 1, min(len(cands), 6)):
            for sgn in (1, -1):
                mu = cands[i] + sgn * cands[j]
                if mu % M == 0:
                    continue
                ok, wid = check_mu(mu, M, alpha, omega, beta, vars_, zb)
                if ok:
                    return True, mu, wid
    return False, None, best


def certify_branching(sysd, rho2, node_cap=100000, bkz=0, stats=None):
    """sound branch and bound: True iff every admissible (z, x) is excluded from the disc of squared radius rho2."""
    if stats is None:
        stats = {'nodes': 0, 'certs': 0, 'max_depth': 0}
    zb = z_box(sysd['co'], rho2)
    if zb[0][0] > zb[0][1] or zb[1][0] > zb[1][1]:
        return True, stats
    M = sysd['M']
    alpha = sysd['alpha']

    def rec(vars_, omega, beta, depth):
        stats['nodes'] += 1
        stats['max_depth'] = max(stats['max_depth'], depth)
        if stats['nodes'] > node_cap:
            return None
        ok, mu, wid = find_certificate(M, alpha, omega, beta, vars_, zb, bkz)
        if ok:
            stats['certs'] += 1
            return True
        if not vars_:
            return False
        groups = defaultdict(list)
        for i, (d, e, t) in enumerate(vars_):
            groups[(e, t)].append(i)
        gk = max(groups, key=lambda k: len(groups[k]))
        gi = groups[gk]
        keep = [i for i in range(len(vars_)) if i not in set(gi)]
        nv = [vars_[i] for i in keep]
        no = [omega[i] for i in keep]
        for choice in [None] + gi:
            nb = beta if choice is None else (beta - omega[choice]) % M
            r = rec(nv, no, nb, depth + 1)
            if r is None:
                return None
            if r is False:
                return False
        return True

    res = rec(sysd['vars'], sysd['omega'], sysd['beta'], 0)
    return res, stats


def cert_gap(sysd, nn_exact, node_cap=2000, bkz=0):
    """largest j with certify(rho2 = nn_exact >> j) failing... returned as the smallest j >= 0 for which the
    certificate succeeds (monotone in rho2). The certified lower bound on the true minimum is nn_exact >> j."""
    lo, hi = 0, 2 * len(str(nn_exact)) * 4
    res, _ = certify_branching(sysd, nn_exact >> hi, node_cap=node_cap, bkz=bkz)
    if res is not True:
        return None
    while hi - lo > 1:
        mid = (lo + hi) // 2
        res, _ = certify_branching(sysd, nn_exact >> mid, node_cap=node_cap, bkz=bkz)
        if res is True:
            hi = mid
        else:
            lo = mid
    res, _ = certify_branching(sysd, nn_exact >> lo, node_cap=node_cap, bkz=bkz)
    return lo if res is True else hi
