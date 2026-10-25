import pickle, time
from common import *
from tree import Pat, solve_direct, leaves_at
from strings_lib import count_objects, count_feasible

def ref_strings(De, final, D):
    out = set()
    for ent in final:
        assigned = ent[6]
        out.add(frozenset((De[j][1] + LMAX * t, De[j][0]) for j, t in assigned))
    return out

def my_strings(pat, K, leaves):
    out = set()
    for L, co in leaves:
        s = []
        p = 0; x = L
        digs = {}
        while x:
            d = x % 10
            if d != 1: s.append((p, d))
            x //= 10; p += 1
        out.add(frozenset(s))
    return out

def main():
    t0 = time.time(); Lam = DC.kernel_lattice()
    recs = pickle.load(open(os.path.join(HERE, 'ref_run.pkl'), 'rb'))
    pats = {p['key'] + (p['nu'], None if p['eps'] is None else tuple(p['eps'])): p for p in load_patterns()}
    bykey = defaultdict(list)
    for p in pats.values(): bykey[p['key']].append(p)
    res = []
    for r in recs:
        if r.get('budget'): continue
        cands = [p for p in bykey[r['key']] if p['nu'] == r['nu']]
        p = cands[0]
        rep = reps_of(p)[r['rep']]
        assert rep[0] == r['repnu'] and rep[1] == r['De']
        co0 = anchor_coset(p, Lam)
        pat = Pat(r['De'], p['y'], p['a'], co0)
        D = r['D']; K = LMAX * D
        t = time.time()
        leaves = solve_direct(pat, K)
        dt = time.time() - t
        closed = not leaves
        bound = min(DC.digits_bound(co) for _, co in leaves) if leaves else None
        ms = my_strings(pat, K, leaves)
        rs = ref_strings(r['De'], r['final'], D)
        refpts = sorted(DC.nearest_norm(Coset((int(f[0]), int(f[1])), (int(f[2]), int(f[3])), (int(f[4]), int(f[5]))))[1] for f in r['final'])
        mypts = sorted(DC.nearest_norm(co)[1] for _, co in leaves)
        refpts_d = sorted(set(refpts))
        objs = count_objects(r['De'], p['y'], p['a'], D)
        rec = dict(key=r['key'], rep=r['rep'], D=D, closed_eq=closed == r['closed'], bound_eq=(bound == r['bound']),
                   strings_eq=(ms == rs), pts_eq=(sorted(set(mypts)) == refpts_d), nleaf=len(leaves), nref=len(r['final']),
                   nref_distinct=len(rs), objs_formula=objs, objs_eq=(objs == (r['stats'][-1] if r['stats'] else 0)),
                   t_direct=dt, bound=bound, k=r['k'])
        res.append(rec)
        print(rec, flush=True)
    pickle.dump(res, open(os.path.join(HERE, 'differential.pkl'), 'wb'))
    ok = all(x['closed_eq'] and x['bound_eq'] and x['strings_eq'] and x['pts_eq'] and x['objs_eq'] for x in res)
    print('ALL EXACT' if ok else 'MISMATCH', len(res), time.time() - t0)

main()
