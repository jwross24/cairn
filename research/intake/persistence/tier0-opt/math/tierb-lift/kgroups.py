import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, '..', '..', '..', 'tier0')))
sys.dont_write_bytecode = True
from math import gcd
from tier0v2 import chain_step

def egcd(a, b):
    if b == 0:
        return (abs(a), (1 if a >= 0 else -1), 0)
    g, x, y = egcd(b, a % b)
    return g, y, x - (a // b) * y

def restrict(basis, f, n):
    f1 = sum(basis[0][i] * f[i] for i in range(2)) % n
    f2 = sum(basis[1][i] * f[i] for i in range(2)) % n
    rows = [[f1, 1, 0], [f2, 0, 1], [n, 0, 0]]
    while sum(1 for r in rows if r[0] != 0) > 1:
        rows = sorted(rows, key=lambda r: (r[0] == 0, abs(r[0])))
        piv = rows[0]
        for r in rows[1:]:
            if r[0] != 0:
                q = r[0] // piv[0]
                for j in range(3):
                    r[j] -= q * piv[j]
    ker = [r for r in rows if r[0] == 0]
    assert len(ker) == 2, rows
    out = []
    for r in ker:
        out.append((r[1] * basis[0][0] + r[2] * basis[1][0], r[1] * basis[0][1] + r[2] * basis[1][1]))
    return out

def det(b):
    return abs(b[0][0] * b[1][1] - b[0][1] * b[1][0])

def kernel(basis, prs):
    for (l3, l7, n) in prs:
        basis = restrict(basis, (l3, l7), n)
    return basis

def prs_of(pdata):
    return [(pd.l3, pd.l7, pd.p - 1) for pd in pdata]

if __name__ == '__main__':
    top = int(sys.argv[1]) if len(sys.argv) > 1 else 24
    levels = (12, 24, 48)
    I = [(1, 0), (0, 1)]
    steps = {}
    kers = {}
    cur = I
    for i, L in enumerate(levels):
        if L > top: break
        st = chain_step(levels, i, True)
        steps[L] = st
        cur = kernel(cur, prs_of(st['pdata']))
        kers[L] = cur
        print(L, 'primes', [pd.p for pd in st['pdata']], '|<3,7>_L| =', det(cur), 'basis', cur, flush=True)
    res = {}
    for i, L in enumerate(levels):
        if L > top or i == 0: continue
        Lp = levels[i - 1]
        new = steps[L]['pdata']
        subsets = {}
        for r in range(1, len(new) + 1):
            import itertools
            for sub in itertools.combinations(range(len(new)), r):
                k2 = kernel(kers[Lp], prs_of([new[j] for j in sub]))
                subsets[','.join(str(new[j].p) for j in sub)] = dict(K=det(k2) // det(kers[Lp]), G=1)
                g = 1
                for j in sub: g *= new[j].p - 1
                subsets[','.join(str(new[j].p) for j in sub)]['G'] = g
        res[L] = subsets
        for k, v in subsets.items():
            print(L, k, 'K', v['K'], 'G', v['G'], 'accept %.3e' % (v['K'] / v['G']), flush=True)
    json.dump(res, open(os.path.join(HERE, 'logs', 'kgroups_%d.json' % top), 'w'), indent=1)
