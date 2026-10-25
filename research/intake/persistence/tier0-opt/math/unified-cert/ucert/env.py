import os, sys, math, json, hashlib
from collections import Counter

sys.dont_write_bytecode = True
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PERSIST = os.path.normpath(os.path.join(ROOT, '..', '..', '..'))
TIER0 = os.path.join(PERSIST, 'tier0')
if TIER0 not in sys.path:
    sys.path.append(TIER0)

_cwd = os.getcwd()
os.chdir(TIER0)
try:
    import deepcut as DC
    from descent import cut_coset, v2, factor237
    from lattice import Coset
finally:
    os.chdir(_cwd)

LMAX = 96
ELL_LO = 4771212547


def disc_radius2(U):
    return (2 * U * U * 10 ** 20) // ELL_LO ** 2


def closes(nn, U):
    return nn * ELL_LO ** 2 > 2 * U * U * 10 ** 20


def exact_E(D, a):
    for E in range(1, D + 1):
        if 2 * LMAX * E - a >= LMAX * D:
            return E
    return D


def log10_big(n):
    return math.log10(n) if n < 10 ** 300 else (len(str(n)) - 1) + math.log10(int(str(n)[:15]) / 1e14)


def digits_bound_log10(nn):
    return 0.5 * log10_big(nn) - 0.5 * math.log10(2) + math.log10(math.log10(3))


def load_utable(path):
    U = {}
    for l in open(path):
        t = l.split()
        if len(t) == 3:
            U[(int(t[0]), int(t[1]))] = int(t[2])
    return U


def coset_to_json(co):
    return {'v0': list(co.v0), 'u1': list(co.u1), 'u2': list(co.u2)}


def coset_from_json(j):
    return Coset(tuple(j['v0']), tuple(j['u1']), tuple(j['u2']))


def sha(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def R(n):
    return (10 ** n - 1) // 9


def class_count_labeled(types, E, D):
    from functools import lru_cache
    byclass = {}
    for (d, e), c in types.items():
        byclass.setdefault(e, []).append(((d, e), c))
    total = 1
    for e, lst in byclass.items():
        caps = tuple(c for _, c in lst)

        @lru_cache(None)
        def f(t, rem):
            if t == D:
                return 1
            s = f(t + 1, rem)
            for i, r in enumerate(rem):
                if r > 0:
                    nr = list(rem)
                    nr[i] -= 1
                    s += r * f(t + 1, tuple(nr))
            return s
        total *= f(E, caps)
    return total


def node_id(node):
    return sha({k: v for k, v in node.items() if k != 'mult'})


def canon_coset(co):
    (a1, b1), (a2, b2) = co.u1, co.u2
    if a1 == 0 and a2 == 0:
        g, r1, r2 = 0, (0, abs(b1)), (0, abs(b2))
        raise ValueError('degenerate coset')
    x0, y0, x1, y1 = 1, 0, 0, 1
    p, q = a1, a2
    while q:
        t = p // q
        p, q = q, p - t * q
        x0, x1 = x1, x0 - t * x1
        y0, y1 = y1, y0 - t * y1
    if p < 0:
        p, x0, y0 = -p, -x0, -y0
    g = p
    row1 = (g, x0 * b1 + y0 * b2)
    h22 = abs((a1 // g) * b2 - (a2 // g) * b1)
    r12 = row1[1] % h22
    qv = co.v0[0] // g
    vx = co.v0[0] - qv * g
    vy = co.v0[1] - qv * r12
    vy %= h22
    return (g, r12, h22, vx, vy)


def node_digest(node):
    co = coset_from_json(node['coset'])
    return sha([node['a'], node['s'], node['Y'], [list(x) for x in node['remaining']], list(canon_coset(co))])
