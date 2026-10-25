import sys, json, os
from math import gcd
from fractions import Fraction
from collections import Counter, defaultdict
import branchsplit
from tier0v2 import chain_step, PrimeData

LEVELS = (12, 24, 48, 96)


def load(path):
    out = {}
    for l in open(path):
        d = json.loads(l)
        out[(d['s'], tuple(d['M']))] = d
    return out


def egcd(a, b):
    if b == 0:
        return (abs(a), (1 if a >= 0 else -1), 0)
    g, x, y = egcd(b, a % b)
    return g, y, x - (a // b) * y


def solve_1d(eqs):
    r0, m0 = 0, 1
    for A, r, m in eqs:
        g = gcd(A, m)
        if r % g:
            return None
        mm = m // g
        c = (r // g) * pow((A // g) % mm, -1, mm) % mm if mm > 1 else 0
        g2 = gcd(m0, mm)
        if (c - r0) % g2:
            return None
        l = m0 // g2 * mm
        if mm > 1:
            t = ((c - r0) // g2) * pow((m0 // g2) % (mm // g2), -1, mm // g2) % (mm // g2) if mm // g2 > 1 else 0
            r0 = (r0 + m0 * t) % l
        m0 = l
    return r0, m0


_PD = None


def all_pdata():
    global _PD
    if _PD is None:
        _PD = []
        for i, L in enumerate(LEVELS):
            _PD += [(L, pd) for pd in chain_step(LEVELS, i)['pdata']]
    return _PD


def indep_impossible(M, item, level):
    a, nu, eps = item['a'], item['nu'], tuple(item['eps'])
    three, seven = branchsplit.branch_of(tuple(sorted(M)), nu, eps)
    nb, nc = not three, not seven
    eqs = []
    for L, pd in all_pdata():
        if L > level:
            continue
        y = pd.R[nu % L]
        for d, e in zip(sorted(M), eps):
            y = (y + (d - 1) * pd.pow10[e % L]) % pd.p
        if y == 0:
            return 'ydiv', (three, seven)
        r = (pd.log(y) - a * pd.l2) % (pd.p - 1)
        eqs.append((pd, r))
    if nb and nc:
        feasible = all(0 == r for pd, r in eqs)
        return ('inconsistent' if not feasible else 'FEASIBLE'), (three, seven)
    if nb:
        sol = solve_1d([(pd.l7, r, pd.p - 1) for pd, r in eqs])
    elif nc:
        sol = solve_1d([(pd.l3, r, pd.p - 1) for pd, r in eqs])
    else:
        return 'NOT-REMOVABLE', (three, seven)
    return ('inconsistent' if sol is None else 'FEASIBLE'), (three, seven)


def anchor(item):
    u1, u2, v0 = item['u1'], item['u2'], item['v0']
    det = u1[0] * u2[1] - u1[1] * u2[0]
    x = round(Fraction(-v0[0] * u2[1] + v0[1] * u2[0], det))
    yy = round(Fraction(v0[0] * u1[1] - v0[1] * u1[0], det))
    best = None
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            bb = v0[0] + (x + dx) * u1[0] + (yy + dy) * u2[0]
            cc = v0[1] + (x + dx) * u1[1] + (yy + dy) * u2[1]
            nn = bb * bb + cc * cc
            if best is None or nn < best[0]:
                best = (nn, bb, cc)
    return best[1], best[2]


def key(it):
    return (it['a'], it['nu'], tuple(it['eps']))


def compare(base, new, verbose=True):
    rep = dict(equations=0, sols_identical=0, sols_diff=[], refused=[], missing=[], open_subset=0, open_not_subset=[],
               coset_diff=[], removed=0, removed_checks=Counter(), removed_anchor=Counter(), levels_prod=Counter(),
               levels_new=Counter(), nin_prod=Counter(), nin_new=Counter(), c12=[0, 0])
    for k, n in new.items():
        if k not in base:
            rep['missing'].append(k)
            continue
        b = base[k]
        rep['equations'] += 1
        if 'refused' in n:
            rep['refused'].append((k, n['refused']))
            continue
        if b['sols'] == n['sols']:
            rep['sols_identical'] += 1
        else:
            rep['sols_diff'].append((k, b['sols'], n['sols']))
        if 'open_patterns' not in b:
            rep.setdefault('count_only', []).append(k)
            rep['open_subset'] += 1 if n['open'] <= b['open'] else 0
            if n['open'] > b['open']:
                rep['open_not_subset'].append((k, 'count'))
            for L, nn, sv, cls in b['levels']:
                rep['levels_prod'][L] += sv
                rep['nin_prod'][L] += nn
            for L, nn, sv, cls in n['levels']:
                rep['levels_new'][L] += sv
                rep['nin_new'][L] += nn
            continue
        bo = {key(i): i for i in b['open_patterns']['items']}
        no = {key(i): i for i in n['open_patterns']['items']}
        if b['open_patterns']['level'] != n['open_patterns']['level'] and no:
            pass
        if set(no) <= set(bo):
            rep['open_subset'] += 1
        else:
            rep['open_not_subset'].append((k, sorted(set(no) - set(bo))[:3]))
        for kk in set(no) & set(bo):
            if (no[kk]['v0'], no[kk]['u1'], no[kk]['u2']) != (bo[kk]['v0'], bo[kk]['u1'], bo[kk]['u2']):
                rep['coset_diff'].append((k, kk))
        lvl = b['open_patterns']['level']
        for kk in sorted(set(bo) - set(no)):
            rep['removed'] += 1
            verdict, cls = indep_impossible(k[1], bo[kk], lvl)
            rep['removed_checks'][verdict] += 1
            ab, ac = anchor(bo[kk])
            need_b0, need_c0 = not cls[0], not cls[1]
            forbids = (need_b0 and ab > 0) or (need_c0 and ac > 0)
            rep['removed_anchor']['anchor-needs-forbidden-factor' if forbids else 'anchor-compatible-but-no-lattice-point'] += 1
        for L, nn, sv, cls in b['levels']:
            rep['levels_prod'][L] += sv
            rep['nin_prod'][L] += nn
        for L, nn, sv, cls in n['levels']:
            rep['levels_new'][L] += sv
            rep['nin_new'][L] += nn
    return rep


if __name__ == '__main__':
    base = load(sys.argv[1])
    new = load(sys.argv[2])
    rep = compare(base, new)
    out = {k: (dict(v) if isinstance(v, Counter) else v) for k, v in rep.items()}
    print(json.dumps(out, default=str))
