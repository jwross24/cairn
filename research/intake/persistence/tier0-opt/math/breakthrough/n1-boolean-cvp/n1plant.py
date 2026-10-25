import sys, os, json, math, random, time, itertools
from collections import Counter

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from n1lib import *
from n1solve import *
from n1cert import *
from n1tier import *
import n1diff as ND


def exact_subcoset_nn(co, a, Tbase, vars_, x, K):
    L = Tbase
    for (d, e, t), xi in zip(vars_, x):
        if xi:
            L += (d - 1) * 10 ** (e + LMAX * t)
    c2 = cut_coset(co, a, L, K)
    if c2 is None:
        return None
    return DC.nearest_norm(c2)[0]


def planted_small(key_str, ntrials=40, seed=1):
    """planted genuine points on real patterns: radius^2 = nearest norm of a chosen sub-coset must never certify."""
    rng = random.Random(seed)
    lam = ND.load_lam()
    want = tuple(key_str.split())
    recs = {}
    from stage_io import entries, full_key
    for fn in ('runall_final.jsonl', 'trees_c.jsonl', 'trees_mac.jsonl'):
        for (s, M, a, nu, eps, y, sol) in entries(os.path.join(ND.FROZEN, fn)):
            key = (str(s), ''.join(map(str, M)), str(a), str(y))
            if key == want:
                recs[full_key(s, M, a, nu, eps, y)] = (s, M, a, nu, eps, y)
    out = Counter()
    from descent import factor237
    for fk, rec in recs.items():
        s, M, a, nu, eps, y = rec
        a = int(a)
        f = factor237(y)
        co0 = Coset((f[1], f[2]), lam.u1, lam.u2)
        for rep in ND.reps_for(rec):
            nu_, De = rep
            De = list(De)
            for D in (2, 3):
                E = exact_E(D, a)
                if E >= D:
                    continue
                surv = survivors_to(co0, a, rep, E)
                seen = set()
                for co, assigned in surv:
                    key2 = tuple(sorted((De[j][0], De[j][1], t) for j, t in assigned))
                    if key2 in seen:
                        continue
                    seen.add(key2)
                    sysd = build_system(co, assigned, a, De, E, D)
                    vars_ = sysd['vars']
                    m = len(vars_)
                    xs = [x for x in itertools.product((0, 1), repeat=m) if valid_x(x, vars_, sysd['types'])]
                    nns = [(exact_subcoset_nn(co, a, sysd['Tbase'], vars_, x, sysd['K']), x) for x in xs]
                    nns = [(n, x) for n, x in nns if n is not None]
                    nmin = min(n for n, _ in nns)
                    rng.shuffle(nns)
                    for n, x in nns[:ntrials]:
                        res, st = certify_branching(sysd, n, node_cap=2000)
                        out['planted_at_nn'] += 1
                        if res is True:
                            out['FALSE_CLOSURE'] += 1
                    res, st = certify_branching(sysd, nmin - 1, node_cap=2000)
                    out['below_min_total'] += 1
                    out['below_min_certified'] += (res is True)
                    res, st = certify_branching(sysd, 4 * nmin, node_cap=2000)
                    out['above_min_total'] += 1
                    out['above_min_certified'] += (res is True)
    return out


if __name__ == '__main__':
    keys = sys.argv[1:]
    tot = Counter()
    for k in keys:
        r = planted_small(k)
        print(k, dict(r), flush=True)
        tot.update(r)
    print('TOTAL', dict(tot))
