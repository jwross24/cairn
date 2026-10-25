import os, sys, time, json, math
from collections import Counter
sys.dont_write_bytecode = True
PY = os.environ['CPORT_PYREF_DIR']
os.chdir(PY)
sys.path.insert(0, PY)
sys.path.insert(1, os.path.dirname(os.path.abspath(__file__)))
import deepcut as DC
import classify_open as C
from lattice import Coset
from baker_chain import baker_upper_bound
from stage_io import records

mode, shard, nshard, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
wantfile = sys.argv[5] if len(sys.argv) > 5 and sys.argv[5] != '-' else None
files = sys.argv[6:]
maxdepth = 5

NN = []
_orig = DC.nearest_norm


def rec(co):
    r = _orig(co)
    NN.append(r[0])
    return r


DC.nearest_norm = rec

want = None
if wantfile:
    want = set(tuple(l.split()[:4]) for l in open(wantfile) if l.strip())
Lam = DC.kernel_lattice()
seen = set()
if os.environ.get('CPORT_SKIP_GLOB'):
    import glob
    for f in glob.glob(os.environ['CPORT_SKIP_GLOB']):
        for l in open(f):
            seen.add(json.loads(l)['key'])
todo = []
for rec_, fk in records(files):
    (s, M, a, nu, eps, y) = rec_
    k2 = (str(s), ''.join(map(str, M)), str(a), str(y))
    if fk in seen:
        continue
    if want is not None and k2 not in want:
        continue
    seen.add(fk)
    todo.append((rec_, fk))
todo.sort(key=lambda t: len(t[0][1]))
fo = open(out, 'w')
for idx, ((s, M, a, nu, eps, y), fk) in enumerate(todo):
    if idx % nshard != shard:
        continue
    t_pat = time.process_time()
    fct = C.factor237(y)
    assert fct and fct[0] == a, (s, M, a, y, fct)
    co0 = Coset((fct[1], fct[2]), Lam.u1, Lam.u2)
    reps = DC.all_representations(M, y)
    assert reps, ("no representation of the anchor", s, M, a, y)
    if nu is not None:
        reps = [r for r in reps if r[0] == nu and Counter(e for _, e in r[1]) == Counter(e % DC.LMAX for e in eps)]
        assert reps, ("recorded pattern not among the representations", s, M, a, y, nu, eps)
    k = len(M)
    R = dict(key=fk, reps=[])
    Ms = ''.join(map(str, M))
    if mode == 'deepcut':
        worst = None
        closed_all = True
        tcase = 0
        for rep in reps:
            NN.clear()
            t0 = time.process_time()
            closed, bound, cases, stats = DC.deep_cut(co0, a, rep, 1, 200000)
            dt = time.process_time() - t0
            R['reps'].append(dict(closed=closed, bound=bound, cases=cases, stats=stats, nn=(str(min(NN)) if NN else None), t=dt))
            tcase += cases
            if closed is None:
                closed_all = False
                worst = -1
                break
            if not closed:
                closed_all = False
                worst = bound if worst is None or bound < worst else worst
        R['closed_all'] = bool(closed_all)
        R['line'] = (f"s={s:<10} M={Ms:<12} a={a:<2} y={y:<12} reps={len(reps):<3} cases={tcase:<7} "
                     f"{'CLOSED' if closed_all else ('BUDGET' if worst == -1 else f'bound 10^(10^{worst:.2f}) digits')}")
    else:
        U = baker_upper_bound(k, a)
        logU = math.log10(U)
        verdict = []
        allclosed = True
        for (nu0, De) in reps:
            res = None
            dl = []
            for D in range(1, maxdepth + 1):
                NN.clear()
                t0 = time.process_time()
                closed, bound, cases, stats = DC.deep_cut(co0, a, (nu0, list(De)), D, 2000000)
                dt = time.process_time() - t0
                nn = str(min(NN)) if NN else None
                if closed is None:
                    res = ('BUDGET', D, cases)
                    dl.append(dict(D=D, res='BUDGET', cases=cases, stats=stats, nn=nn, t=dt))
                    break
                if closed:
                    res = ('CLOSED-cut', D, cases)
                    dl.append(dict(D=D, res='CLOSED-cut', cases=cases, stats=stats, nn=nn, t=dt))
                    break
                if bound > logU:
                    res = ('CLOSED-sandwich', D, cases, round(bound, 2), stats)
                    dl.append(dict(D=D, res='CLOSED-sandwich', cases=cases, stats=stats, nn=nn, t=dt))
                    break
                res = ('open', D, cases, round(bound, 2), stats)
                dl.append(dict(D=D, res='open', cases=cases, stats=stats, nn=nn, t=dt))
            verdict.append(res)
            R['reps'].append(dict(depths=dl))
            if res[0] not in ('CLOSED-cut', 'CLOSED-sandwich'):
                allclosed = False
        R['closed_all'] = bool(allclosed)
        R['line'] = (f"s={s:<8} M={Ms:<12} a={a} y={y:<11} k={k} log10 U={logU:.1f} reps={len(reps)} -> "
                     f"{'CLOSED' if allclosed else 'OPEN'} {verdict}")
    R['t'] = time.process_time() - t_pat
    fo.write(json.dumps(R) + '\n')
    fo.flush()
fo.close()
