import math, time
from collections import Counter, defaultdict
from fractions import Fraction
import gmpy2
from gmpy2 import mpq
from fpylll import IntegerMatrix, LLL, BKZ, FPLLL
from .env import *

FPLLL.set_precision(400)


def system_from_node(node, D):
    a = node['a']
    s = node['s']
    E = s // LMAX
    K = LMAX * D
    assert s % LMAX == 0 and K >= s
    Y = int(node['Y'])
    co = coset_from_json(node['coset'])
    rem = [tuple(x) for x in node['remaining']]
    Tbase = Y + 10 ** s * R(K - s)
    types = Counter(rem)
    vars_ = [(d, e, t) for (d, e), cnt in sorted(types.items()) for t in range(E, D)]
    W2 = 2 ** (K - a)
    W5 = 5 ** K
    v0, u1, u2 = co.v0, co.u1, co.u2

    def G(b, c, mod):
        return pow(3, b, mod) * pow(7, c, mod) % mod

    G02, G05 = G(v0[0], v0[1], W2), G(v0[0], v0[1], W5)
    gu2, gu5 = G(u1[0], u1[1], W2), G(u1[0], u1[1], W5)
    gv2, gv5 = G(u2[0], u2[1], W2), G(u2[0], u2[1], W5)
    s2, s5 = s - a, s
    assert (gu2 - 1) % 2 ** s2 == 0 and (gv2 - 1) % 2 ** s2 == 0
    assert (gu5 - 1) % 5 ** s5 == 0 and (gv5 - 1) % 5 ** s5 == 0
    assert Tbase % 2 ** a == 0 and (Tbase >> a) % 2 == 1
    tau2 = (Tbase >> a) % W2
    tau5 = Tbase * pow(2 ** a, -1, W5) % W5
    rho2_ = (G02 - tau2) % W2
    rho5_ = (G05 - tau5) % W5
    assert rho2_ % 2 ** s2 == 0 and rho5_ % 5 ** s5 == 0
    m2 = min(K - a, 2 * s2)
    m5 = min(K, 2 * s5)
    h2, h5 = m2 - s2, m5 - s5
    mod2, mod5 = 2 ** h2, 5 ** h5
    al2 = [G02 * (gu2 - 1) // 2 ** s2 % mod2, G02 * (gv2 - 1) // 2 ** s2 % mod2]
    al5 = [G05 * (gu5 - 1) // 5 ** s5 % mod5, G05 * (gv5 - 1) // 5 ** s5 % mod5]
    inv2a5 = pow(2 ** a, -1, mod5) if h5 > 0 else 0
    om2, om5 = [], []
    for (d, e, t) in vars_:
        w = (d - 1) * 10 ** (e + LMAX * t)
        om2.append(-((w >> a) // 2 ** s2) % mod2)
        om5.append(-(w // 5 ** s5 * inv2a5) % mod5)
    be2 = -(rho2_ // 2 ** s2) % mod2
    be5 = -(rho5_ // 5 ** s5) % mod5
    M = mod2 * mod5
    c2 = mod5 * pow(mod5, -1, mod2) if mod2 > 1 else 0
    c5 = mod2 * pow(mod2, -1, mod5) if mod5 > 1 else 0

    def crt(x2, x5):
        return (x2 * c2 + x5 * c5) % M

    return dict(K=K, s=s, a=a, D=D, E=E, h2=h2, h5=h5, M=M, alpha=[crt(al2[i], al5[i]) for i in range(2)],
                omega=[crt(om2[i], om5[i]) for i in range(len(vars_))], beta=crt(be2, be5), vars=vars_,
                types=types, Tbase=Tbase, exact=(h2 == K - s and h5 == K - s), co=co)


def z_box(co, rho2):
    u1, u2, v0 = co.u1, co.u2, co.v0
    det = u1[0] * u2[1] - u2[0] * u1[1]
    ad = abs(det)
    rho = math.isqrt(rho2) + 1
    n1 = math.isqrt(u1[0] ** 2 + u1[1] ** 2) + 1
    n2 = math.isqrt(u2[0] ** 2 + u2[1] ** 2) + 1
    c1 = Fraction(-(u2[1] * v0[0] - u2[0] * v0[1]), det)
    c2 = Fraction(-(-u1[1] * v0[0] + u1[0] * v0[1]), det)
    r1 = Fraction(rho * n2, ad)
    r2 = Fraction(rho * n1, ad)
    return (math.ceil(c1 - r1), math.floor(c1 + r1)), (math.ceil(c2 - r2), math.floor(c2 + r2))


def cent(x, M):
    x %= M
    return x - M if 2 * x > M else x


def check_mu(mu, M, alpha, omega, beta, vars_, zb):
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
    return klo > khi, hi - lo


def reduce_rows(rows, bkz=0):
    A = IntegerMatrix.from_matrix(rows)
    LLL.reduction(A, delta=0.99)
    if bkz and len(rows) > bkz:
        BKZ.reduction(A, BKZ.Param(block_size=bkz, flags=BKZ.AUTO_ABORT | BKZ.MAX_LOOPS, max_loops=6),
                      float_type="mpfr", precision=400)
    return [[int(A[i, j]) for j in range(A.ncols)] for i in range(A.nrows)]


def find_certificate(M, alpha, omega, beta, vars_, zb, bkz=0):
    w = [max(1, zb[0][1] - zb[0][0]), max(1, zb[1][1] - zb[1][0])] + [1] * len(omega)
    a_all = alpha + omega
    n = len(a_all)
    rows = [[1] + [w[j] * a_all[j] for j in range(n)]]
    for j in range(n):
        r = [0] * (n + 1)
        r[1 + j] = w[j] * M
        rows.append(r)
    B = reduce_rows(rows, bkz)
    cands = [row[0] for row in B if row[0] % M != 0]
    best = None
    for c in cands:
        for sg in (1, -1):
            ok, wid = check_mu(sg * c, M, alpha, omega, beta, vars_, zb)
            if ok:
                return True, sg * c, wid
            if best is None or wid < best:
                best = wid
    for i in range(min(len(cands), 6)):
        for j in range(i + 1, min(len(cands), 6)):
            for sg in (1, -1):
                mu = cands[i] + sg * cands[j]
                if mu % M == 0:
                    continue
                ok, wid = check_mu(mu, M, alpha, omega, beta, vars_, zb)
                if ok:
                    return True, mu, wid
    return False, None, best


def certify_tree(sysd, rho2, node_cap=5000, bkz=0):
    zb = z_box(sysd['co'], rho2)
    stats = {'nodes': 0, 'leaves': 0, 'max_depth': 0}
    if zb[0][0] > zb[0][1] or zb[1][0] > zb[1][1]:
        return {'empty_box': True}, stats, zb
    M, alpha = sysd['M'], sysd['alpha']

    def rec(vars_, omega, beta, depth):
        stats['nodes'] += 1
        stats['max_depth'] = max(stats['max_depth'], depth)
        if stats['nodes'] > node_cap:
            return None
        ok, mu, wid = find_certificate(M, alpha, omega, beta, vars_, zb, bkz)
        if ok:
            stats['leaves'] += 1
            return {'mu': mu}
        if not vars_:
            return False
        groups = defaultdict(list)
        for i, (d, e, t) in enumerate(vars_):
            groups[(e, t)].append(i)
        gk = max(groups, key=lambda k: len(groups[k]))
        gi = groups[gk]
        gs = set(gi)
        keep = [i for i in range(len(vars_)) if i not in gs]
        nv = [vars_[i] for i in keep]
        no = [omega[i] for i in keep]
        children = []
        for choice in [None] + gi:
            nb = beta if choice is None else (beta - omega[choice]) % M
            r = rec(nv, no, nb, depth + 1)
            if r is None or r is False:
                return r
            children.append({'choice': None if choice is None else list(vars_[choice]), 'tree': r})
        return {'group': list(gk), 'children': children}

    tree = rec(sysd['vars'], sysd['omega'], sysd['beta'], 0)
    return tree, stats, zb


def replay_tree(tree, vars_, omega, beta, M, alpha, zb):
    if 'mu' in tree:
        ok, _ = check_mu(tree['mu'], M, alpha, omega, beta, vars_, zb)
        return ok
    gk = tuple(tree['group'])
    gidx = [i for i, (d, e, t) in enumerate(vars_) if (e, t) == gk]
    if not gidx:
        return False
    keep = [i for i in range(len(vars_)) if i not in set(gidx)]
    nv = [vars_[i] for i in keep]
    no = [omega[i] for i in keep]
    want = [None] + [list(vars_[i]) for i in gidx]
    got = [ch['choice'] for ch in tree['children']]
    if got != want:
        return False
    for ch in tree['children']:
        if ch['choice'] is None:
            nb = beta
        else:
            i = [list(v) for v in vars_].index(ch['choice'])
            nb = (beta - omega[i]) % M
        if not replay_tree(ch['tree'], nv, no, nb, M, alpha, zb):
            return False
    return True


def nearest_certificate(node, rho2):
    co = coset_from_json(node['coset'])
    nn, pt = DC.nearest_norm(co)
    return {'kind': 'nearest', 'nn': nn, 'point': list(pt)}, nn > rho2


def certify_node(node, D, rho2, node_cap=5000, bkz=0):
    t0 = time.time()
    base = {'format': 'ucert-record-v1', 'backend': 'dual', 'node': node_id(node), 'D': D, 'rho2': str(rho2)}
    if LMAX * D == node['s']:
        rec, ok = nearest_certificate(node, rho2)
        rec['nn'] = str(rec['nn'])
        base.update(kind='nearest', nearest=rec, certified=ok, t=time.time() - t0)
        return base
    sysd = system_from_node(node, D)
    if not sysd['vars']:
        c2 = cut_coset(sysd['co'], node['a'], sysd['Tbase'], sysd['K'])
        nn = None if c2 is None else DC.nearest_norm(c2)[0]
        base.update(kind='novars', nn=None if nn is None else str(nn), certified=(nn is None or nn > rho2), t=time.time() - t0)
        return base
    tree, stats, zb = certify_tree(sysd, rho2, node_cap, bkz)
    ok = isinstance(tree, dict)
    base.update(kind='dual', exact_system=sysd['exact'], M=str(sysd['M']), zbox=[list(zb[0]), list(zb[1])],
                tree=tree if ok else None, stats=stats, certified=ok and True, cap_hit=(tree is None), t=time.time() - t0)
    return base


def verify_record(node, rec, rho2):
    from . import cert_cvp
    D = rec['D']
    co = coset_from_json(node['coset'])
    if rec['kind'] == 'nearest':
        b, c = rec['nearest']['point']
        nn = b * b + c * c
        return (co.contains(b, c) and str(nn) == rec['nearest']['nn'] and cert_cvp.nearest2d(co) == nn
                and (nn > rho2) == rec['certified'] and rec['certified'])
    if rec['kind'] == 'novars':
        K = LMAX * D
        c2 = cert_cvp.extend_exact(co, node['a'], node['s'], int(node['Y']) + 10 ** node['s'] * R(K - node['s']), K)
        nn = None if c2 is None else cert_cvp.nearest2d(c2)
        return (nn is None and rec['nn'] is None) or (nn is not None and str(nn) == rec['nn'] and nn > rho2)
    sysd = system_from_node(node, D)
    zb = z_box(sysd['co'], rho2)
    if [list(zb[0]), list(zb[1])] != rec['zbox']:
        return False
    if zb[0][0] > zb[0][1] or zb[1][0] > zb[1][1]:
        return True
    return rec['tree'] is not None and replay_tree(rec['tree'], sysd['vars'], sysd['omega'], sysd['beta'], sysd['M'], sysd['alpha'], zb)


def kernel_basis_and_particular(a_vec, beta, M):
    n = len(a_vec)
    piv = None
    for i, x in enumerate(a_vec):
        if math.gcd(x, M) == 1:
            piv = i
            break
    if piv is None:
        raise ValueError("no unit coefficient")
    inv = pow(a_vec[piv], -1, M)
    rows = []
    for j in range(n):
        if j == piv:
            continue
        r = [0] * n
        r[j] = 1
        r[piv] = (-a_vec[j] * inv) % M
        rows.append(r)
    r = [0] * n
    r[piv] = M
    rows.append(r)
    part = [0] * n
    part[piv] = beta * inv % M
    return rows, part


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


def lattice_point_value(b, c, a, K):
    return 2 ** a * pow(3, b, 10 ** K) * pow(7, c, 10 ** K) % 10 ** K


def target_value(Tbase, vars_, x, K):
    L = Tbase
    for (d, e, t), xi in zip(vars_, x):
        if xi:
            L += (d - 1) * 10 ** (e + LMAX * t)
    return L % 10 ** K


def solve_min(sysd, nn0, nodes_cap=50_000_000, bkz=0):
    a = sysd['a']
    vars_ = sysd['vars']
    m = len(vars_)
    M = sysd['M']
    K = sysd['K']
    types = sysd['types']
    co = sysd['co']
    u1, u2, v0 = co.u1, co.u2, co.v0
    avec = sysd['alpha'] + sysd['omega']
    rows_k, part = kernel_basis_and_particular(avec, sysd['beta'], M)
    L = math.isqrt(nn0) + 2
    n = 2 + m

    def emb(v):
        z1, z2 = v[0], v[1]
        return [2 * (z1 * u1[0] + z2 * u2[0]), 2 * (z1 * u1[1] + z2 * u2[1])] + [2 * L * xi for xi in v[2:]]

    B = reduce_rows([emb(r) for r in rows_k], bkz)
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
    best = {'nn': nn0, 'x': [0] * m}
    stats = {'nodes': 0, 'valid': 0, 'inexact': 0}
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
        if lattice_point_value(b, cc, a, K) != target_value(sysd['Tbase'], vars_, xfull, K):
            stats['inexact'] += 1
            return
        nnv = b * b + cc * cc
        if nnv < best['nn']:
            best['nn'] = nnv
            best['x'] = xfull
            best['pt'] = (b, cc)
            radius[0] = float(mpq(4 * nnv + L * L * m) / scale) * (1.0 + 1e-7)

    import sys
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
                leaf()
            elif rec(i - 1, pc) is False:
                d[i] = 0
                return False
            k += 1
        d[i] = 0
        return True

    ok = rec(n - 1, 0.0)
    return dict(nn=best['nn'], x=best['x'], pt=best.get('pt'), nodes=stats['nodes'], valid=stats['valid'], inexact=stats['inexact'], complete=bool(ok))


def min_node(node, D, **kw):
    t0 = time.time()
    co = coset_from_json(node['coset'])
    if LMAX * D == node['s']:
        nn, pt = DC.nearest_norm(co)
        return dict(nn=nn, pt=pt, complete=True, nodes=0, inexact=0, t=time.time() - t0)
    sysd = system_from_node(node, D)
    c0 = cut_coset(sysd['co'], node['a'], sysd['Tbase'], sysd['K'])
    nn0 = DC.nearest_norm(c0)[0]
    if not sysd['vars']:
        return dict(nn=nn0, complete=True, nodes=0, inexact=0, t=time.time() - t0)
    res = solve_min(sysd, nn0, **kw)
    res['t'] = time.time() - t0
    return res


def expand_nodes(pattern, rep, E):
    """own enumeration of the depth-E nodes by the deep-cut recursion (one cut per 96-digit block)."""
    import itertools
    a = pattern['a']
    lam = coset_from_json(pattern['lam'])
    co0 = Coset((pattern['b'], pattern['c']), lam.u1, lam.u2)
    De = [tuple(x) for x in rep['De']]
    survivors = [(co0, ())]
    for D in range(1, E + 1):
        K = LMAX * D
        RK = R(K)
        new = []
        for co, assigned in survivors:
            fixed = dict(assigned)
            free = [j for j in range(len(De)) if j not in fixed]
            for choice in itertools.product((0, 1), repeat=len(free)):
                taken = Counter(De[j][1] for j, c in zip(free, choice) if c)
                if any(cnt > 1 for cnt in taken.values()):
                    continue
                L = RK
                for j, t in fixed.items():
                    L += (De[j][0] - 1) * 10 ** (De[j][1] + LMAX * t)
                for j, c in zip(free, choice):
                    if c:
                        L += (De[j][0] - 1) * 10 ** (De[j][1] + LMAX * (D - 1))
                if v2(L) != a or L % 5 == 0:
                    continue
                co2 = cut_coset(co, a, L, K)
                if co2 is None:
                    continue
                new.append((co2, assigned + tuple((j, D - 1) for j, c in zip(free, choice) if c)))
        survivors = new
    s = LMAX * E
    groups = {}
    for co, assigned in survivors:
        key = tuple(sorted((De[j][0], De[j][1], t) for j, t in assigned))
        if key in groups:
            groups[key]['mult'] += 1
            continue
        fixed = dict(assigned)
        Y = R(s) + sum((De[j][0] - 1) * 10 ** (De[j][1] + LMAX * t) for j, t in fixed.items())
        groups[key] = {'format': 'ucert-node-v1', 'a': a, 's': s, 'Y': str(Y), 'coset': coset_to_json(co),
                       'remaining': sorted([list(De[j]) for j in range(len(De)) if j not in fixed]), 'mult': 1}
    return list(groups.values())
