import sys, itertools
from collections import Counter, defaultdict
from fractions import Fraction

sys.dont_write_bytecode = True
T0 = '/Users/jwross/Documents/cairn/research/intake/persistence/tier0'
sys.path.insert(0, T0)
from lattice import Coset
from descent import cut_coset, v2
import math

LMAX = 96


def factor237(y):
    e = []
    for p in (2, 3, 7):
        c = 0
        while y % p == 0:
            y //= p
            c += 1
        e.append(c)
    return tuple(e) if y == 1 else None


def nearest(co):
    u1, u2 = co.u1, co.u2
    v0 = co.v0
    det = u1[0] * u2[1] - u1[1] * u2[0]
    x = round(Fraction(-v0[0] * u2[1] + v0[1] * u2[0], det))
    y = round(Fraction(v0[0] * u1[1] - v0[1] * u1[0], det))
    best = None
    for dx in (-2, -1, 0, 1, 2):
        for dy in (-2, -1, 0, 1, 2):
            b = v0[0] + (x + dx) * u1[0] + (y + dy) * u2[0]
            c = v0[1] + (x + dx) * u1[1] + (y + dy) * u2[1]
            nn = b * b + c * c
            if best is None or nn < best[0]:
                best = (nn, b, c)
    return best


def digits_bound_log10(co):
    nn = nearest(co)[0]
    if nn == 0:
        return -1.0
    return 0.5 * math.log10(nn) - 0.5 * math.log10(2) + math.log10(math.log10(3))


def rep_from_record(M, nu, eps):
    return nu, [(d, e) for d, e in zip(sorted(M), eps)]


def pattern_value(M, nu, eps):
    return (10 ** nu - 1) // 9 + sum((d - 1) * 10 ** e for d, e in zip(sorted(M), eps))


def deep_cut(co0, a, rep, depth, maxcases):
    nu, De = rep
    survivors = [(co0, ())]
    stats = []
    cases = 0
    for D in range(1, depth + 1):
        K = LMAX * D
        RK = (10 ** K - 1) // 9
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
                cases += 1
                if cases > maxcases:
                    return None, None, cases, stats
                if v2(L) != a or L % 5 == 0:
                    continue
                co2 = cut_coset(co, a, L, K)
                if co2 is None:
                    continue
                new.append((co2, assigned + tuple((j, D - 1) for j, c in zip(free, choice) if c)))
        survivors = new
        stats.append(len(new))
        if not survivors:
            return True, None, cases, stats
    bound = min(digits_bound_log10(co) for co, _ in survivors)
    return False, bound, cases, stats


def all_representations(M, y):
    M = tuple(sorted(M))
    out = []
    RL = (10 ** LMAX - 1) // 9
    for k in range(0, 8 * len(M) + 2):
        for nu in range(LMAX):
            target = y + k * RL - (10 ** nu - 1) // 9
            if target < 0:
                continue
            emax = len(str(target))
            sols = []

            def rec(e, rem_ms, rem, acc):
                if not rem_ms:
                    if rem == 0:
                        sols.append(tuple(acc))
                    return
                if e > emax or e >= LMAX or rem < 0:
                    return
                need = (rem // 10 ** e) % 10
                ms = list(rem_ms)
                tried = set()
                for kk in range(0, len(ms) + 1):
                    for sub in itertools.combinations(range(len(ms)), kk):
                        ds = tuple(ms[i] for i in sub)
                        if ds in tried:
                            continue
                        tried.add(ds)
                        tot = sum(d - 1 for d in ds)
                        if tot % 10 != need:
                            continue
                        rest = tuple(ms[i] for i in range(len(ms)) if i not in sub)
                        rec(e + 1, rest, rem - tot * 10 ** e, acc + [(d, e) for d in ds])

            rec(0, M, target, [])
            for s in sols:
                out.append((nu, s))
    return out


def load_items(vertices):
    import json
    rows = []
    for l in open(T0 + '/trees_mac.jsonl'):
        r = json.loads(l)
        if r['s'] not in vertices:
            continue
        for eq in r['eqs']:
            M = tuple(eq['M'])
            for i, it in enumerate(eq['open_patterns']['items']):
                co = Coset(tuple(it['v0']), tuple(it['u1']), tuple(it['u2']))
                nn, b0, c0 = nearest(co)
                norm = math.hypot(*it['u1'])
                adm = b0 >= 0 and c0 >= 0 and max(b0, c0) < norm / 2
                rows.append(dict(s=r['s'], M=M, i=i, a=it['a'], nu=it['nu'], eps=tuple(it['eps']), co=co, nn=nn, b0=b0, c0=c0, adm=adm))
    return rows
