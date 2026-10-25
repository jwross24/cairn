import sys, json, math, functools
from fractions import Fraction
from collections import Counter
import sympy

@functools.lru_cache(maxsize=None)
def level_primes(L):
    return tuple(sorted(int(p) for p in sympy.factorint(10 ** L - 1) if int(p) not in (2, 3, 5, 7)))

def pattern_residue(p, nu, M, eps):
    y = (pow(10, nu, p) - 1) * pow(9, -1, p) % p
    for d, e in zip(M, eps):
        y = (y + (d - 1) * pow(10, e, p)) % p
    return y

def coset_consistent(it, level, M):
    a, nu, eps = it['a'], it['nu'], it['eps']
    if len(eps) != len(M) or not 0 <= nu < level or any(not 0 <= e < level for e in eps):
        return 'shape'
    for p in level_primes(level):
        y = pattern_residue(p, nu, M, eps)
        b, c = it['v0']
        if y == 0 or pow(2, a, p) * pow(3, b, p) * pow(7, c, p) % p != y:
            return f'v0 mod {p}'
        for u in (it['u1'], it['u2']):
            if pow(3, u[0], p) * pow(7, u[1], p) % p != 1:
                return f'kernel mod {p}'
    return None

def exceptional_of(it, M):
    a = it['a']; u1, u2, v0 = it['u1'], it['u2'], it['v0']
    norm = math.hypot(u1[0], u1[1])
    digits = int(norm / (2 * math.sqrt(2)) * math.log10(3))
    det = u1[0] * u2[1] - u1[1] * u2[0]
    x = round(Fraction(-v0[0] * u2[1] + v0[1] * u2[0], det)); y = round(Fraction(v0[0] * u1[1] - v0[1] * u1[0], det))
    best = None
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            bb = v0[0] + (x + dx) * u1[0] + (y + dy) * u2[0]; cc = v0[1] + (x + dx) * u1[1] + (y + dy) * u2[1]
            nn = bb * bb + cc * cc
            if best is None or nn < best[0]: best = (nn, bb, cc)
    b0, c0 = best[1], best[2]
    exc = None
    if b0 >= 0 and c0 >= 0 and max(b0, c0) < norm / 2:
        yy = 2 ** a * 3 ** b0 * 7 ** c0; sY = str(yy)
        ok = '0' not in sY and Counter(ch for ch in sY if ch != '1') == Counter(str(d) for d in M) and len(sY) % 12 == it['nu'] % 12
        exc = [a, yy if yy < 10 ** 40 else f"~10^{len(sY)}", ok]
    return digits, exc

def check_row(r):
    op = r.get('open_patterns')
    if op is None:
        return 'legacy', []
    bad = []
    M = r['M']; items = op['items']
    if op['M'] != list(M): bad.append('M')
    if len(items) != r['open']: bad.append(f"count {len(items)} vs {r['open']}")
    if len(items) != len(r['bounds']): bad.append('bounds length')
    if op['level'] != r['levels'][-1][0]: bad.append('level')
    digs = []; excs = []
    for i, it in enumerate(items):
        w = coset_consistent(it, op['level'], M)
        if w: bad.append(f'item {i} {w}')
        dg, ex = exceptional_of(it, M)
        digs.append(dg)
        if ex is not None: excs.append(ex)
    if digs != r['bounds']: bad.append('bounds differ')
    if json.loads(json.dumps(excs)) != r['exceptional']: bad.append('exceptional differ')
    if len({json.dumps([it['a'], it['nu'], it['eps']]) for it in items}) != len(items): bad.append('duplicate pattern')
    return 'checked', bad

if __name__ == '__main__':
    nchk = nleg = nopen = nbad = 0
    for f in sys.argv[1:]:
        for ln in open(f):
            if not ln.startswith('{'): continue
            r = json.loads(ln)
            rows = r['eqs'] if 'eqs' in r else [r]
            for e in rows:
                if 'M' not in e: continue
                st, bad = check_row(e)
                if st == 'legacy': nleg += 1; continue
                nchk += 1; nopen += e['open']
                if bad: nbad += 1; print('BAD', e['s'], e['M'], bad[:3])
    print(f"equations checked {nchk} legacy {nleg} open patterns {nopen} bad {nbad}")
    sys.exit(1 if nbad or not nchk else 0)
