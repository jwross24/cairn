import os, sys, time, json, math
from collections import Counter
py = '/private/tmp/persist-cport/py'
os.chdir(py); sys.path.insert(0, py)
import deepcut as DC
import classify_open as C
from lattice import Coset
from baker_chain import baker_upper_bound

mode, shard, nshard, listfile, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4], sys.argv[5]
maxdepth = 5
NN = []
_orig = DC.nearest_norm
def rec(co):
    r = _orig(co); NN.append(r[0]); return r
DC.nearest_norm = rec
want = [tuple(l.split()[:4]) for l in open(listfile) if l.strip()]
wantset = set(want)
Lam = DC.kernel_lattice()
seen = set(); idx = 0
fo = open(out, 'w')
for f in ['runall_final.jsonl', 'trees_c.jsonl', 'trees_mac.jsonl']:
    for (s, M, a, nu, eps, y, sol) in C.entries(f):
        key = (s, M, a, y)
        k2 = (str(s), ''.join(map(str, M)), str(a), str(y))
        if k2 not in wantset or key in seen: continue
        seen.add(key); i = idx; idx += 1
        if i % nshard != shard: continue
        fct = C.factor237(y); assert fct and fct[0] == a
        co0 = Coset((fct[1], fct[2]), Lam.u1, Lam.u2)
        reps = DC.all_representations(M, y)
        if nu is not None:
            reps = [r for r in reps if r[0] == nu and Counter(e for _, e in r[1]) == Counter(e % 96 for e in eps)] or reps
        rec_out = dict(key=list(k2), nreps=len(reps), reps=[])
        k = len(M)
        t_pat = time.process_time()
        if mode == 'deepcut':
            for rep in reps:
                NN.clear(); t0 = time.process_time()
                closed, bound, cases, stats = DC.deep_cut(co0, a, rep, 1, 200000)
                dt = time.process_time() - t0
                rec_out['reps'].append(dict(closed=closed, bound=bound, cases=cases, stats=stats, nn=(str(min(NN)) if NN else None), t=dt))
        else:
            U = baker_upper_bound(k, a); logU = math.log10(U)
            rec_out['U'] = str(U)
            for (nu0, De) in reps:
                dl = []
                for D in range(1, maxdepth + 1):
                    NN.clear(); t0 = time.process_time()
                    closed, bound, cases, stats = DC.deep_cut(co0, a, (nu0, list(De)), D, 2000000)
                    dt = time.process_time() - t0
                    nn = str(min(NN)) if NN else None
                    if closed is None: res = 'BUDGET'
                    elif closed: res = 'CLOSED-cut'
                    elif bound > logU: res = 'CLOSED-sandwich'
                    else: res = 'open'
                    dl.append(dict(D=D, res=res, cases=cases, stats=stats, bound=bound, nn=nn, t=dt))
                    if res != 'open': break
                rec_out['reps'].append(dict(depths=dl))
        rec_out['t'] = time.process_time() - t_pat
        fo.write(json.dumps(rec_out) + '\n'); fo.flush()
fo.close()
