import pickle, time
from common import *
from tree import Pat, solve_direct, solve_pruned, leaves_at

def verdict_at(pat, K, logU):
    leaves = solve_direct(pat, K)
    if not leaves: return True, None, 0
    b = min(DC.digits_bound(co) for _, co in leaves)
    return b > logU, b, len(leaves)

def minimal_K(pat, logU, Kmax):
    lo, hi = 1, Kmax
    best = None
    while lo < hi:
        mid = (lo + hi) // 2
        if mid < 40: lo = mid + 1; continue
        ok, b, n = verdict_at(pat, mid, logU)
        if ok: hi = mid
        else: lo = mid + 1
    ok, b, n = verdict_at(pat, lo, logU)
    return lo, ok, b, n

def main():
    Lam = DC.kernel_lattice()
    recs = pickle.load(open(os.path.join(HERE, 'ref_run.pkl'), 'rb'))
    pats = {}
    for p in load_patterns(): pats[(p['key'], p['nu'])] = p
    last = {}
    for r in recs:
        last[(r['key'], r['nu'], r['rep'])] = r
    out = []
    t0 = time.time()
    for (key, nu, ri), r in sorted(last.items()):
        if r["k"] > 7: continue
        p = pats[(key, nu)]
        rep = reps_of(p)[ri]
        co0 = anchor_coset(p, Lam)
        pat = Pat(rep[1], p['y'], p['a'], co0)
        logU = r['logU']; Dstop = r['D']
        if r['closed']:
            out.append(dict(key=key, rep=ri, kind='cut', D=Dstop, Kmin=96, ok=True, nleaf=0, cases=r['cases'], k=r['k'])); continue
        Kmin, ok, b, n = minimal_K(pat, logU, 96 * Dstop)
        res = dict(key=key, rep=ri, kind='sandwich', D=Dstop, Kmin=Kmin, ok=ok, bound=b, nleaf=n, cases=r['cases'], k=r['k'], logU=logU)
        for step in (96, 48):
            sched = list(range(step, 96 * Dstop + 1, step))
            closed, cuts, stages, pruned, fr = solve_pruned(pat, sched, logU)
            res[f'pruned{step}'] = dict(closed=closed, cuts=cuts, stages=stages, pruned=pruned)
        out.append(res)
        print(res, round(time.time() - t0), flush=True)
        pickle.dump(out, open(os.path.join(HERE, 'fractional.pkl'), 'wb'))

main()
