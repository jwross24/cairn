import sys
sys.dont_write_bytecode = True
sys.path.insert(0, '/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/tierc-family')
import random, time, json
from collections import Counter, defaultdict
from famlib import *
from famtest import *
from validate import load_cases, load_recorded


def key_of(c):
    return (c[0], ''.join(map(str, c[1])), str(c[2]), str(c[3]))


def words_of(a, y, De, limit):
    g = groups_of(De)
    n = 1
    for v in g.values():
        n *= len(v) + 1
    if n > limit:
        return None
    return subset_sums(g)


if __name__ == '__main__':
    t0 = time.time()
    lam = build_lambdas()
    cases = load_cases()
    rec = load_recorded()
    rng = random.Random(1)
    surv = [c for c in cases if rec[key_of(c)]['verdict'] == 'CLOSED-sandwich']
    cut = [c for c in cases if rec[key_of(c)]['verdict'] == 'CLOSED-cut']
    sample = rng.sample(surv, 30) + rng.sample(cut, 30)
    agree = Counter()
    disagree = []
    ref_time = Counter()
    ref_calls = Counter()
    cat_seen = Counter()
    zform_checked = 0
    for (s, M, a, y) in sample:
        reps = reps_wrap0(M, y)
        for nu, De in reps[:3]:
            sums = words_of(a, y, De, 4096)
            if sums is None:
                continue
            base = R(96) - y
            m96, m384, m480 = modulus(a, 96), modulus(a, 384), modulus(a, 480)
            cats = defaultdict(list)
            for sm in sums:
                z = base + sm
                if z % m96:
                    cats['dead96'].append(sm)
                elif z % m384:
                    cats['alive96_dead384'].append(sm)
                elif z % m480:
                    cats['alive384_dead480'].append(sm)
                else:
                    cats['alive480'].append(sm)
            for cat, lst in cats.items():
                for sm in rng.sample(lst, min(3, len(lst))):
                    cat_seen[cat] += 1
                    z = base + sm
                    SU = (y - R(nu)) - sm
                    zform = (R(96) - R(nu) - SU) == z
                    zform_checked += zform
                    flags_c = {96: z % m96 == 0}
                    flags_r = {}
                    for L in LEVELS:
                        W = R(L) + sm
                        t1 = time.time()
                        flags_r[L] = ref_alive(a, y, W, L, lam)
                        ref_time[L] += time.time() - t1
                        ref_calls[L] += 1
                    c = {96: z % m96 == 0}
                    for L in (192, 384, 480):
                        c[L] = c[96] and z % modulus(a, L) == 0
                    r = {96: flags_r[96]}
                    for L in (192, 384, 480):
                        r[L] = flags_r[96] and flags_r[L]
                    for L in LEVELS:
                        agree[(L, c[L] == r[L])] += 1
                        if c[L] != r[L]:
                            disagree.append((key_of((s, M, a, y)), nu, cat, L, c[L], r[L]))
    print('words checked by category', dict(cat_seen))
    print('agreement (level, same?) ->', dict(agree))
    print('disagreements', len(disagree), disagree[:5])
    print('z-form identity held on', zform_checked, 'words')
    print('reference seconds per call', {L: round(ref_time[L] / max(1, ref_calls[L]), 5) for L in LEVELS}, 'calls', dict(ref_calls))
    print('seconds', round(time.time() - t0, 1))
