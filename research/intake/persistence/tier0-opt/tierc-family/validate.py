import sys
sys.dont_write_bytecode = True
sys.path.insert(0, '/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/tierc-family')
import time, json
from famlib import *

COND = {96: (9, 5), 192: (9, 5), 384: (13, 5), 480: (10, 5)}
LEVELS = (96, 192, 384, 480)


def low_profile(De, q):
    groups = {}
    for d, e in De:
        groups.setdefault(e, []).append((d - 1) * 10 ** e)
    low = {e: v for e, v in groups.items() if e < q}
    mult = 1
    for e, v in groups.items():
        if e >= q:
            mult *= len(v) + 1
    return low, mult


def subset_sums(low):
    sums = [0]
    for e in sorted(low):
        opts = [0] + low[e]
        sums = [s + o for s in sums for o in opts]
    return sums


def pattern_family_alive(a, y, nu, De, compress=True):
    qmax = a + max(c[0] for c in COND.values())
    if compress:
        low, mult = low_profile(De, qmax)
    else:
        groups = {}
        for d, e in De:
            groups.setdefault(e, []).append((d - 1) * 10 ** e)
        low, mult = groups, 1
    sums = subset_sums(low)
    base = R(96) - y
    res = {}
    for L in LEVELS:
        c2, c5 = COND[L]
        mod = (1 << (a + c2)) * 5 ** c5
        res[L] = sum(1 for s in sums if (base + s) % mod == 0) * mult
    return res, len(sums), mult


def load_cases():
    out = []
    for line in open(DATA + 'cases_1335.txt'):
        t = line.split()
        out.append((t[0], tuple(int(ch) for ch in t[1]), int(t[2]), int(t[3])))
    return out


def load_recorded():
    rec = {}
    for line in open(DATA + 'shadow1335.tsv'):
        t = line.rstrip('\n').split('\t')
        if len(t) < 10 or t[0].startswith('pattern'):
            continue
        key = tuple(t[0].split()[:4])
        rec[key] = dict(reps=int(t[5]), words=int(t[6]), verdict=t[7], bound=t[8], alive=int(t[9]))
    return rec


if __name__ == '__main__':
    cases = load_cases()
    rec = load_recorded()
    t0 = time.time()
    rows = []
    nrep_tot = 0
    for (s, M, a, y) in cases:
        t1 = time.time()
        reps = reps_wrap0(M, y)
        tot = {L: 0 for L in LEVELS}
        nsum = 0
        mult = 0
        for nu, De in reps:
            r, ns, mu = pattern_family_alive(a, y, nu, De)
            for L in LEVELS:
                tot[L] += r[L]
            nsum += ns
            mult += mu
        rows.append(dict(key=(s, ''.join(map(str, M)), str(a), str(y)), k=len(M), a=a, nreps=len(reps), alive=tot, profiles=nsum, mult=mult, sec=time.time() - t1))
        nrep_tot += len(reps)
    json.dump(rows, open(OUT + 'validate_rows.json', 'w'))
    print('patterns', len(rows), 'wrap0 reps', nrep_tot, 'seconds', round(time.time() - t0, 1))
