import math, time
from collections import Counter, defaultdict
import gmpy2
from gmpy2 import mpz, mpq
from .env import *
from lattice import _kernel_and_particular, _reduce


def unit_at(co, a, mod):
    return int(gmpy2.powmod(2, a, mod) * gmpy2.powmod(3, co.v0[0], mod) * gmpy2.powmod(7, co.v0[1], mod) % mod)


def gen_unit(u, mod):
    return int(gmpy2.powmod(3, u[0], mod) * gmpy2.powmod(7, u[1], mod) % mod)


def v5(x):
    n = 0
    while x and x % 5 == 0:
        x //= 5
        n += 1
    return n


def intersect_z(co, Au, Av, r, mod):
    sol = _kernel_and_particular(Au % mod, Av % mod, mod, r % mod)
    if sol is None:
        return None
    x0, y0, k1, k2 = sol
    u1, u2, v0 = co.u1, co.u2, co.v0
    nv0 = (v0[0] + x0 * u1[0] + y0 * u2[0], v0[1] + x0 * u1[1] + y0 * u2[1])
    nu1 = (k1[0] * u1[0] + k1[1] * u2[0], k1[0] * u1[1] + k1[1] * u2[1])
    nu2 = (k2[0] * u1[0] + k2[1] * u2[0], k2[0] * u1[1] + k2[1] * u2[1])
    nu1, nu2 = _reduce(nu1, nu2)
    return Coset(nv0, nu1, nu2)


def linear_coeffs(co, a, m, h):
    assert 1 <= h <= m - a, (h, m, a)
    mod = 10 ** (m + h)
    y0 = unit_at(co, a, mod)
    coeffs = []
    for u in (co.u1, co.u2):
        t = (gen_unit(u, mod) - 1) % mod
        if t:
            assert v5(t) >= m and v2(t) >= m - a, "units of the coset do not agree mod 10^m"
        coeffs.append(((y0 * t) % mod) // 10 ** m % 10 ** h)
    return y0, coeffs[0], coeffs[1]


def extend_exact(co, a, m, Y, m2):
    if m - a < 1 or m < 3:
        return cut_coset(co, a, Y % 10 ** m2, m2)
    while m < m2:
        h = min(m2 - m, m - a)
        y0, Au, Av = linear_coeffs(co, a, m, h)
        if (Y - y0) % 10 ** m:
            return None
        beta = ((Y - y0) % 10 ** (m + h)) // 10 ** m
        co = intersect_z(co, Au, Av, beta, 10 ** h)
        if co is None:
            return None
        m += h
    return co


def expand_nodes(pattern, rep, E, first_lin=12):
    """own enumeration of the depth-E nodes: digit-ordered, one cut per branch position, identical digits merged."""
    a = pattern['a']
    lam = coset_from_json(pattern['lam'])
    co0 = Coset((pattern['b'], pattern['c']), lam.u1, lam.u2)
    De = [tuple(x) for x in rep['De']]
    s = LMAX * E
    classes = {e % LMAX for _, e in De}
    out = []

    def cut(co, mc, Y, m2):
        if Y % 5 == 0:
            return None
        if m2 > a and v2(Y % 10 ** m2) != a:
            return None
        if mc >= first_lin and mc - a >= 1:
            return extend_exact(co, a, mc, Y, m2)
        return cut_coset(co, a, Y, m2)

    def next_branch(m):
        p = m
        while p < s and p % LMAX not in classes:
            p += 1
        return p

    def rec(co, mc, mf, Y, remaining):
        if mf >= 3 and mf > mc:
            co = cut(co, mc, Y, mf)
            if co is None:
                return
            mc = mf
        if mf >= s:
            out.append((co, Y, tuple(remaining)))
            return
        p = next_branch(mf)
        if p >= s:
            rec(co, mc, s, Y + (10 ** s - 10 ** mf) // 9, remaining)
            return
        opts = [None]
        seen = set()
        for j in remaining:
            if De[j][1] % LMAX == p % LMAX and De[j][0] not in seen:
                seen.add(De[j][0])
                opts.append(j)
        for j in opts:
            Y2 = Y + (10 ** (p + 1) - 10 ** mf) // 9 + ((De[j][0] - 1) * 10 ** p if j is not None else 0)
            rec(co, mc, p + 1, Y2, [i for i in remaining if i != j])

    rec(co0, 0, 0, 0, list(range(len(De))))
    nodes = []
    for co, Y, rem in out:
        nodes.append({'format': 'ucert-node-v1', 'a': a, 's': s, 'Y': str(Y % 10 ** s), 'coset': coset_to_json(co),
                      'remaining': sorted([list(De[j]) for j in rem])})
    return nodes


def _egcd_full(a, b):
    x0, y0, x1, y1 = 1, 0, 0, 1
    while b:
        q, a, b = a // b, b, a % b
        x0, x1 = x1, x0 - q * x1
        y0, y1 = y1, y0 - q * y1
    if a < 0:
        a, x0, y0 = -a, -x0, -y0
    return a, x0, y0


def kernel_basis_and_particular(coeffs, M, r):
    d = len(coeffs)
    c = [int(x) for x in coeffs] + [int(M)]
    n = d + 1
    U = [[1 if i == j else 0 for j in range(n)] for i in range(n)]

    def colcomb(i, j, a, b, cc, dd):
        for row in U:
            x, y = row[i], row[j]
            row[i], row[j] = a * x + b * y, cc * x + dd * y
        c[i], c[j] = a * c[i] + b * c[j], cc * c[i] + dd * c[j]

    for i in range(1, n):
        if c[i] == 0:
            continue
        if c[0] == 0:
            colcomb(0, i, 0, 1, 1, 0)
            continue
        g, s, t = _egcd_full(c[0], c[i])
        colcomb(0, i, s, t, -c[i] // g, c[0] // g)
    g = c[0]
    assert all(x == 0 for x in c[1:])
    if r % g:
        return None, None
    basis = [[U[row][col] for row in range(d)] for col in range(1, n)]
    part = [U[row][0] * (r // g) for row in range(d)]
    assert (sum(ci * vi for ci, vi in zip(coeffs, part)) - r) % M == 0
    return basis, part


def dot(u, v):
    return sum(a * b for a, b in zip(u, v))


def lll_integral(B, delta_num=99, delta_den=100, carry=None):
    B = [[mpz(x) for x in v] for v in B]
    n = len(B)
    C = [list(v) for v in carry] if carry is not None else None
    lam = [[mpz(0)] * n for _ in range(n)]
    d = [mpz(0)] * (n + 1)
    d[0] = mpz(1)
    d[1] = dot(B[0], B[0])

    def RED(k, l):
        if 2 * abs(lam[k][l]) > d[l + 1]:
            q = (2 * lam[k][l] + d[l + 1]) // (2 * d[l + 1])
            B[k] = [x - q * y for x, y in zip(B[k], B[l])]
            if C is not None:
                C[k] = [x - q * y for x, y in zip(C[k], C[l])]
            lam[k][l] -= q * d[l + 1]
            for i in range(l):
                lam[k][i] -= q * lam[l][i]

    def SWAP(k, kmax):
        B[k], B[k - 1] = B[k - 1], B[k]
        if C is not None:
            C[k], C[k - 1] = C[k - 1], C[k]
        for j in range(k - 1):
            lam[k][j], lam[k - 1][j] = lam[k - 1][j], lam[k][j]
        L = lam[k][k - 1]
        Bv = (d[k - 1] * d[k + 1] + L * L) // d[k]
        for i in range(k + 1, kmax + 1):
            t = lam[i][k]
            lam[i][k] = (d[k + 1] * lam[i][k - 1] - L * t) // d[k]
            lam[i][k - 1] = (Bv * t + L * lam[i][k]) // d[k + 1]
        d[k] = Bv

    k = 1
    kmax = 0
    while k < n:
        if k > kmax:
            kmax = k
            for j in range(k + 1):
                u = dot(B[k], B[j])
                for i in range(j):
                    u = (d[i + 1] * u - lam[k][i] * lam[j][i]) // d[i]
                if j < k:
                    lam[k][j] = u
                else:
                    d[k + 1] = u
                    assert u > 0, "dependent vectors"
        RED(k, k - 1)
        if delta_den * d[k + 1] * d[k - 1] < delta_num * d[k] * d[k] - delta_den * lam[k][k - 1] ** 2:
            SWAP(k, kmax)
            k = max(1, k - 1)
        else:
            for l in range(k - 2, -1, -1):
                RED(k, l)
            k += 1
    out = [[int(x) for x in v] for v in B]
    return (out, [[int(x) for x in v] for v in C]) if carry is not None else out


def gram_schmidt_q(B):
    n = len(B)
    Bq = [[mpq(x) for x in v] for v in B]
    Bs, Bn = [], []
    mu = [[mpq(0)] * n for _ in range(n)]
    for i in range(n):
        v = list(Bq[i])
        for j in range(i):
            mu[i][j] = sum(a * b for a, b in zip(Bq[i], Bs[j])) / Bn[j]
            v = [a - mu[i][j] * b for a, b in zip(v, Bs[j])]
        Bs.append(v)
        Bn.append(sum(a * a for a in v))
    return mu, Bn, Bs


def _outward(ci):
    x0 = (2 * ci.numerator + ci.denominator) // (2 * ci.denominator)
    yield x0
    lo, hi = x0 - 1, x0 + 1
    while True:
        if abs(lo - ci) <= abs(hi - ci):
            yield lo
            lo -= 1
        else:
            yield hi
            hi += 1


def cvp_enumerate(B, target, R2, shrink=False, max_nodes=10 ** 7, first=False):
    n = len(B)
    mu, Bn, Bs = gram_schmidt_q(B)
    tq = [mpq(x) for x in target]
    tau = [sum(a * b for a, b in zip(tq, Bs[j])) / Bn[j] for j in range(n)]
    tperp2 = sum(a * a for a in tq) - sum(tau[j] * tau[j] * Bn[j] for j in range(n))
    assert tperp2 >= 0
    R2 = mpq(R2) - tperp2
    if R2 < 0:
        return None, None, 0, True
    c = [0] * n
    pd = [mpq(0)] * (n + 1)
    best = [None, None]
    nodes = 0

    def center(i):
        s = tau[i]
        for j in range(i + 1, n):
            s -= c[j] * mu[j][i]
        return s

    ci = center(n - 1)
    stack = [(ci, _outward(ci))]
    while stack:
        i = n - len(stack)
        ci, gen = stack[-1]
        x = next(gen)
        d2 = (x - ci) * (x - ci) * Bn[i]
        if pd[i + 1] + d2 > R2:
            stack.pop()
            continue
        nodes += 1
        if nodes > max_nodes:
            return best[0], best[1], nodes, False
        c[i] = x
        pd[i] = pd[i + 1] + d2
        if i == 0:
            if best[0] is None or pd[0] < best[0]:
                best[0] = pd[0]
                best[1] = [int(v) for v in c]
                if first:
                    return best[0] + tperp2, best[1], nodes, True
                if shrink:
                    R2 = pd[0]
            continue
        cj = center(i - 1)
        stack.append((cj, _outward(cj)))
    return (best[0] + tperp2 if best[0] is not None else None), best[1], nodes, True


def nearest2d(co):
    """exact minimum of ||(b, c)||^2 over the coset: LLL-reduce, take the four rounding neighbours as the start
    radius, then exact Schnorr-Euchner enumeration at that radius."""
    B = [[co.u1[0], co.u1[1]], [co.u2[0], co.u2[1]]]
    B, _ = lll_integral(B, carry=[[1, 0], [0, 1]])
    target = [-co.v0[0], -co.v0[1]]
    mu, Bn, Bs = gram_schmidt_q(B)
    tq = [mpq(x) for x in target]
    tau = [sum(a * b for a, b in zip(tq, Bs[j])) / Bn[j] for j in range(2)]
    c1 = tau[1]
    best = None
    for x1 in (c1.numerator // c1.denominator, c1.numerator // c1.denominator + 1):
        c0_ = tau[0] - x1 * mu[1][0]
        for x0 in (c0_.numerator // c0_.denominator, c0_.numerator // c0_.denominator + 1):
            d = [target[k] - x0 * B[0][k] - x1 * B[1][k] for k in range(2)]
            n2 = d[0] ** 2 + d[1] ** 2
            if best is None or n2 < best:
                best = n2
    d2, cb, nodes, complete = cvp_enumerate(B, target, best, shrink=True)
    assert complete and d2 is not None
    return int(d2)


def block_problem(node, D, N2, exact_groups=True):
    a = node['a']
    s = node['s']
    K = LMAX * D
    h = K - s
    assert 1 <= h <= s - a
    co = coset_from_json(node['coset'])
    Yfix = int(node['Y'])
    De_rem = [tuple(x) for x in node['remaining']]
    y0, Au, Av = linear_coeffs(co, a, s, h)
    assert (y0 - Yfix) % 10 ** s == 0
    T = Yfix % 10 ** s + (10 ** (s + h) - 10 ** s) // 9
    beta = ((T - y0) % 10 ** (s + h)) // 10 ** s
    vars_ = []
    for j, (d, e) in enumerate(De_rem):
        for p in range(s, s + h):
            if p % LMAX == e % LMAX:
                vars_.append((j, p, (d - 1) * 10 ** (p - s)))
    f = len(vars_)
    groups = []
    if exact_groups:
        byj, byp = defaultdict(list), defaultdict(list)
        for idx, (j, p, w) in enumerate(vars_):
            byj[j].append(idx)
            byp[p].append(idx)
        groups = [g for g in list(byj.values()) + list(byp.values()) if len(g) >= 2]
    coeffs = [Au, Av] + [-w for (_, _, w) in vars_]
    M = 10 ** h
    basis, part = kernel_basis_and_particular(coeffs, M, beta)
    return dict(co=co, a=a, s=s, h=h, K=K, T=T, vars=vars_, groups=groups, coeffs=coeffs, M=M, basis=basis, part=part,
                f=f, G=len(groups), beta=beta)


def embed_fn(prob, lam):
    co = prob['co']
    u1, u2 = co.u1, co.u2
    groups = prob['groups']

    def embed(v):
        z1, z2 = v[0], v[1]
        x = v[2:]
        out = [2 * (z1 * u1[0] + z2 * u2[0]), 2 * (z1 * u1[1] + z2 * u2[1])]
        out += [2 * lam * xj for xj in x]
        out += [2 * lam * sum(x[i] for i in g) for g in groups]
        return out
    return embed


def solve_block(node, D, N2, shrink=False, max_nodes=10 ** 7, exact_groups=True):
    t0 = time.time()
    prob = block_problem(node, D, N2, exact_groups)
    f, G = prob['f'], prob['G']
    if prob['basis'] is None:
        return dict(empty=True, min2=None, complete=True, nodes=0, f=f, G=G, dim=2 + f), prob, None
    co = prob['co']
    v0 = co.v0
    lam = gmpy2.isqrt(N2) + 1
    embed = embed_fn(prob, lam)
    EB = [embed(v) for v in prob['basis']]
    Ep = embed(prob['part'])
    target = [-2 * v0[0] - Ep[0], -2 * v0[1] - Ep[1]] + [lam - Ep[2 + i] for i in range(f + G)]
    R2 = 4 * N2 + lam * lam * (f + G)
    EBr, basis_r = lll_integral(EB, carry=prob['basis'])
    assert all(embed(v) == w for v, w in zip(basis_r, EBr))
    t2 = time.time()
    dist2, cbest, nodes, complete = cvp_enumerate(EBr, target, R2, shrink=shrink, max_nodes=max_nodes, first=not shrink)
    res = dict(empty=False, min2=None, complete=complete, nodes=nodes, f=f, G=G, dim=2 + f, t_lll=t2 - t0, t_enum=time.time() - t2)
    pack = dict(lam=int(lam), R2=str(R2), target=[str(x) for x in target], EB=EBr, basis=basis_r, part=prob['part'])
    if dist2 is not None:
        y = [sum(cc * b[i] for cc, b in zip(cbest, basis_r)) for i in range(2 + f)]
        P = [p + yy for p, yy in zip(prob['part'], y)]
        x = P[2:]
        ok = all(xj in (0, 1) for xj in x) and all(sum(x[i] for i in g) <= 1 for g in prob['groups'])
        b = v0[0] + P[0] * co.u1[0] + P[1] * co.u2[0]
        c = v0[1] + P[0] * co.u1[1] + P[1] * co.u2[1]
        n2 = b * b + c * c
        assert ok, "enumeration returned a non-box point"
        assert 4 * n2 + lam * lam * (f + G) == dist2
        Yw = prob['T'] + sum(w for (j, p, w), xj in zip(prob['vars'], x) if xj) * 10 ** prob['s']
        assert unit_at(Coset((b, c), co.u1, co.u2), prob['a'], 10 ** prob['K']) == Yw % 10 ** prob['K'], "found point is not a union point"
        res.update(min2=n2, point=[b, c], word=[(prob['vars'][i][0], prob['vars'][i][1]) for i in range(f) if x[i]])
    return res, prob, pack


def certify_node(node, D, rho2, max_nodes=10 ** 7):
    t0 = time.time()
    base = {'format': 'ucert-record-v1', 'backend': 'cvp', 'node': node_id(node), 'D': D, 'rho2': str(rho2)}
    if LMAX * D == node['s']:
        co = coset_from_json(node['coset'])
        nn = nearest2d(co)
        base.update(kind='nearest', nn=str(nn), certified=nn > rho2, t=time.time() - t0)
        return base
    res, prob, pack = solve_block(node, D, rho2, shrink=False, max_nodes=max_nodes)
    cert = res['complete'] and res['min2'] is None
    base.update(kind='cvp', f=res['f'], G=res['G'], dim=res['dim'], empty=res['empty'], nodes=res['nodes'], complete=res['complete'],
                certified=cert, t=time.time() - t0)
    if res['min2'] is not None:
        base['refused_point'] = res['point']
        base['refused_norm2'] = str(res['min2'])
    if pack is not None:
        base['pack'] = pack
    return base


def min_node(node, D, max_nodes=10 ** 7):
    t0 = time.time()
    co = coset_from_json(node['coset'])
    if LMAX * D == node['s']:
        return dict(nn=nearest2d(co), complete=True, nodes=0, t=time.time() - t0)
    a, s, K = node['a'], node['s'], LMAX * D
    Y = int(node['Y'])
    c0 = extend_exact(co, a, s, Y + 10 ** s * R(K - s), K)
    nn0 = nearest2d(c0)
    res, prob, pack = solve_block(node, D, nn0, shrink=True, max_nodes=max_nodes)
    nn = nn0 if res['min2'] is None else min(nn0, res['min2'])
    return dict(nn=nn, complete=res['complete'], nodes=res['nodes'], word=res.get('word'), f=res['f'], G=res['G'], t=time.time() - t0)


def verify_record(node, rec, rho2):
    D = rec['D']
    co = coset_from_json(node['coset'])
    if rec['kind'] == 'nearest':
        return rec['certified'] and nearest2d(co) == int(rec['nn']) and int(rec['nn']) > rho2
    if not rec['certified']:
        return False
    prob = block_problem(node, D, rho2)
    if prob['basis'] is None:
        return rec['empty']
    pack = rec['pack']
    lam = pack['lam']
    if lam != math.isqrt(rho2) + 1:
        return False
    d = 2 + prob['f']
    M = prob['M']
    for row in pack['basis']:
        if sum(c * v for c, v in zip(prob['coeffs'], row)) % M:
            return False
    emb = embed_fn(prob, lam)
    if any(emb(v) != w for v, w in zip(pack['basis'], pack['EB'])):
        return False
    dd = _det_int(pack['basis'])
    g = 0
    for cf in prob['coeffs']:
        g = math.gcd(g, cf)
    if abs(dd) != M // math.gcd(M, g):
        return False
    part = pack['part']
    if (sum(c * v for c, v in zip(prob['coeffs'], part)) - prob['beta']) % M:
        return False
    Ep = emb(part)
    v0 = co.v0
    target = [-2 * v0[0] - Ep[0], -2 * v0[1] - Ep[1]] + [lam - Ep[2 + i] for i in range(prob['f'] + prob['G'])]
    if [str(x) for x in target] != pack['target']:
        return False
    R2 = 4 * rho2 + lam * lam * (prob['f'] + prob['G'])
    if str(R2) != pack['R2']:
        return False
    dist2, cb, nodes, complete = cvp_enumerate(pack['EB'], target, R2, shrink=False)
    return complete and dist2 is None


def _det_int(rows):
    n = len(rows)
    A = [[mpq(x) for x in r] for r in rows]
    det = mpq(1)
    for i in range(n):
        piv = next((r for r in range(i, n) if A[r][i] != 0), None)
        if piv is None:
            return 0
        if piv != i:
            A[i], A[piv] = A[piv], A[i]
            det = -det
        det *= A[i][i]
        for r in range(i + 1, n):
            if A[r][i] != 0:
                fct = A[r][i] / A[i][i]
                A[r] = [x - fct * y for x, y in zip(A[r], A[i])]
    return int(det)
