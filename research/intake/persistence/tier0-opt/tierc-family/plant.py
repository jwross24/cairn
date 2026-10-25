import sys
sys.dont_write_bytecode = True
sys.path.insert(0, '/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/tierc-family')
import random, time, json
from collections import Counter, defaultdict
from famlib import *
from famtest import *
from validate import load_cases, load_recorded
from refcheck import key_of

SIX = [('14336', '227888', '0', '78121827'), ('28672', '2244788', '0', '78121827'), ('28672', '2244788', '0', '330812181'),
       ('28672', '22224788', '0', '330812181'), ('28672', '2227888', '0', '78121827'), ('42336', '22334677', '1', '3281116734')]


def planted_delta(lam, key, rng, trials):
    s, Ms, a, y = key
    a, y = int(a), int(y)
    f = factor237(y)
    res = Counter()
    for L in (192, 384, 480):
        rows = lam[L].rows()
        K = klat(L, L)
        for _ in range(trials):
            x1, x2 = rng.randrange(-40, 41), rng.randrange(-40, 41)
            k1, k2 = rng.randrange(-40, 41), rng.randrange(-40, 41)
            p = (f[1] + x1 * rows[0][0] + x2 * rows[1][0] + k1 * K.a, f[2] + x1 * rows[0][1] + x2 * rows[1][1] + k1 * K.b + k2 * K.d)
            m = 10 ** L
            W = (2 ** a * pow(3, p[0], m) * pow(7, p[1], m)) % m
            member = (lam[L].plus(K)).contains(p[0] - f[1], p[1] - f[2])
            res[(L, 'member', member, 'family-test', alive_from_W(a, y, W, L), 'reference', ref_alive(a, y, W, L, lam))] += 1
        for _ in range(trials):
            dx, dy = rng.randrange(-30, 31), rng.randrange(-30, 31)
            p = (f[1] + dx, f[2] + dy)
            m = 10 ** L
            W = (2 ** a * pow(3, p[0], m) * pow(7, p[1], m)) % m
            member = (lam[L].plus(K)).contains(dx, dy)
            res[(L, 'member', member, 'family-test', alive_from_W(a, y, W, L), 'reference', ref_alive(a, y, W, L, lam))] += 1
    return res


if __name__ == '__main__':
    t0 = time.time()
    lam = build_lambdas()
    rng = random.Random(24)
    cases = load_cases()
    rec = load_recorded()
    survkey = ('14336', '227888', '0', '78121827')
    print('PLANTED DELTA on', survkey)
    for k, v in sorted(planted_delta(lam, survkey, rng, 25).items(), key=str):
        print(k, v)
    print('seconds', round(time.time() - t0, 1), flush=True)

    survivors = [c for c in cases if rec[key_of(c)]['verdict'] == 'CLOSED-sandwich']
    cutters = [c for c in cases if rec[key_of(c)]['verdict'] == 'CLOSED-cut']
    sample_cut = rng.sample(cutters, 300)
    reps_cache = {}
    for c in survivors + sample_cut:
        reps_cache[key_of(c)] = reps_wrap0(c[1], c[3])
    print('reps cached', len(reps_cache), round(time.time() - t0), flush=True)

    def counts(c, cond):
        a, y = c[2], c[3]
        tot = {L: 0 for L in cond}
        for nu, De in reps_cache[key_of(c)]:
            r, _, _ = family_counts(a, y, De, cond)
            for L in cond:
                tot[L] += r[L]
        return tot

    variants = {
        'true (9,5)(13,5)(10,5)': COND,
        'strict 5-adic: 5^6 at 384,480': {96: (9, 5), 192: (9, 5), 384: (13, 6), 480: (10, 6)},
        'loose 2-adic: 2^12 at 384': {96: (9, 5), 192: (9, 5), 384: (12, 5), 480: (10, 5)},
        'loose 5-adic: 5^4 at 384': {96: (9, 5), 192: (9, 5), 384: (13, 4), 480: (10, 5)},
        'strict 2-adic: 2^14 at 384': {96: (9, 5), 192: (9, 5), 384: (14, 5), 480: (10, 5)},
    }
    for name, cond in variants.items():
        false_kill = sum(1 for c in survivors if counts(c, cond)[384] == 0)
        false_alive = sum(1 for c in sample_cut if counts(c, cond)[384] > 0)
        print(f"MUTANT {name}: survivors falsely killed {false_kill}/{len(survivors)}; cut keys falsely alive {false_alive}/{len(sample_cut)}", flush=True)

    print('SIX recorded sandwich patterns at levels 192, 288, 384, 480, 768, 1152 (conductor (alpha, beta+1) inferred for 288, 768, 1152)')
    cond6 = {192: (9, 5), 288: (9, 7), 384: (13, 5), 480: (10, 5), 768: (13, 5), 1152: (13, 7), 96: (9, 5)}
    six_rows = []
    for key in SIX:
        a, y = int(key[2]), int(key[3])
        M = tuple(int(ch) for ch in key[1])
        reps = reps_wrap0(M, y)
        tot = Counter()
        for nu, De in reps:
            r, _, _ = family_counts(a, y, De, cond6)
            for L in r:
                tot[L] += r[L]
        six_rows.append((key, len(reps), dict(tot)))
        print(key, 'wrap0 reps', len(reps), {L: tot[L] for L in (192, 288, 384, 480, 768, 1152)}, flush=True)
    print('seconds', round(time.time() - t0, 1))
