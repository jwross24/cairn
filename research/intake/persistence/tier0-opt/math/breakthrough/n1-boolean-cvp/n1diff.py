import sys, os, json, math, time, glob
from collections import Counter

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from n1lib import *
from n1solve import *

TIER0_OPT = os.path.normpath(os.path.join(HERE, '..', '..', '..'))
CPORT = os.path.join(TIER0_OPT, 'cport')
sys.path.insert(0, os.path.join(CPORT, 'tools'))
from stage_io import entries, full_key

FROZEN = os.environ.get('N1_FROZEN', '/private/tmp/n1work')
ORACLE = os.environ.get('N1_ORACLE', '/private/tmp/n1work/oracle')
LAMCACHE = os.path.join(FROZEN, 'lam96.json')


def load_lam():
    if os.path.exists(LAMCACHE):
        j = json.load(open(LAMCACHE))
        return Coset(tuple(j['v0']), tuple(j['u1']), tuple(j['u2']))
    lam = DC.kernel_lattice()
    json.dump({'v0': lam.v0, 'u1': lam.u1, 'u2': lam.u2}, open(LAMCACHE, 'w'))
    return lam


def class_count_labeled(types, E, D):
    """number of labeled placements of the free digits into blocks E..D-1 (distinct positions)."""
    byclass = {}
    for (d, e), c in types.items():
        byclass.setdefault(e, []).append(((d, e), c))
    total = 1
    for e, lst in byclass.items():
        keys = [k for k, _ in lst]
        caps = tuple(c for _, c in lst)
        from functools import lru_cache

        @lru_cache(None)
        def f(t, rem):
            if t == D:
                return 1
            s = f(t + 1, rem)
            for i, r in enumerate(rem):
                if r > 0:
                    nr = list(rem)
                    nr[i] -= 1
                    s += r * f(t + 1, tuple(nr))
            return s
        total *= f(E, caps)
    return total


def load_oracle_tsv():
    out = {}
    for p in glob.glob(os.path.join(ORACLE, 'sw', '*.tsv')):
        for l in open(p):
            f = l.rstrip('\n').split('\t')
            s, M, a, y, ri, D, res, cases, stats, nn, t = f[1:12]
            key = (s, M, a, y)
            out.setdefault(key, {}).setdefault(int(ri), {})[int(D)] = (res, int(cases), stats, nn)
    return out


def reps_for(key_rec):
    s, M, a, nu, eps, y = key_rec
    reps = DC.all_representations(M, y)
    if nu is not None:
        reps = [r for r in reps if r[0] == nu and Counter(e for _, e in r[1]) == Counter(e % LMAX for e in eps)]
    return reps


def run_rep(co0, a, rep, D, E=None, bkz=0, verbose=False):
    nu, De = rep
    De = list(De)
    if E is None:
        E = exact_E(D, a)
    t0 = time.time()
    surv = survivors_to(co0, a, (nu, De), E)
    t_enum = time.time() - t0
    labeled_base = len(surv)
    groups = {}
    for co, assigned in surv:
        key = tuple(sorted((De[j][0], De[j][1], t) for j, t in assigned))
        if key in groups:
            groups[key][1] += 1
        else:
            groups[key] = [(co, assigned), 1]
    best = None
    labeled_total = 0
    tot_nodes = 0
    tot_inexact = 0
    all_complete = True
    exact_sys = True
    t1 = time.time()
    for key, ((co, assigned), mult) in groups.items():
        sysd = build_system(co, assigned, a, De, E, D)
        exact_sys &= sysd['exact']
        K = sysd['K']
        co_x0 = cut_coset(co, a, sysd['Tbase'], K)
        assert co_x0 is not None
        nn0, _ = DC.nearest_norm(co_x0)
        res = solve_min(sysd, a, nn0, bkz=bkz)
        tot_nodes += res['nodes']
        tot_inexact += res['inexact']
        all_complete &= res['complete']
        if best is None or res['nn'] < best:
            best = res['nn']
        labeled_total += mult * class_count_labeled(sysd['types'], E, D)
    return dict(E=E, D=D, bases_labeled=labeled_base, bases_unique=len(groups), labeled_total=labeled_total, nn=best,
                nodes=tot_nodes, inexact=tot_inexact, complete=all_complete, exact_system=exact_sys,
                t_enum=t_enum, t_lattice=time.time() - t1)


if __name__ == '__main__':
    want = set()
    for l in open(os.path.join(CPORT, 'data', 'survivors.txt')):
        want.add(tuple(l.split()[:4]))
    lam = load_lam()
    recs = {}
    for fn in ('runall_final.jsonl', 'trees_c.jsonl', 'trees_mac.jsonl'):
        for (s, M, a, nu, eps, y, sol) in entries(os.path.join(FROZEN, fn)):
            key = (str(s), ''.join(map(str, M)), str(a), str(y))
            if key in want:
                recs.setdefault(key, {})[full_key(s, M, a, nu, eps, y)] = (s, M, a, nu, eps, y)
    orc = load_oracle_tsv()
    only = sys.argv[1] if len(sys.argv) > 1 else None
    maxk = int(os.environ.get('N1_MAXK', '8'))
    nbad = 0
    nchk = 0
    donefile = os.environ.get('N1_DONE')
    done = set()
    if donefile and os.path.exists(donefile):
        for l in open(donefile):
            if l.startswith('DONE '):
                done.add(l[5:].strip())
    for key in sorted(recs, key=lambda k: (len(k[1]), k)):
        if only and ' '.join(key) != only:
            continue
        if len(key[1]) > maxk:
            continue
        if ' '.join(key) in done:
            continue
        for fk, rec in recs[key].items():
            s, M, a, nu, eps, y = rec
            reps = reps_for(rec)
            from descent import factor237
            f = factor237(y)
            co0 = Coset((f[1], f[2]), lam.u1, lam.u2)
            otab = None
            for tk in orc:
                if tk == key:
                    otab = orc[tk]
            for ri, rep in enumerate(reps):
                ods = otab.get(ri, {}) if otab else {}
                for D in sorted(ods):
                    res, cases, stats, nn = ods[D]
                    if res == 'CLOSED-cut':
                        continue
                    out = run_rep(co0, int(a), rep, D)
                    onn = int(nn)
                    ostats = json.loads(stats)
                    ok_nn = out['nn'] == onn
                    ok_cnt = out['labeled_total'] == ostats[-1]
                    nchk += 1
                    if not (ok_nn and ok_cnt and out['complete'] and out['inexact'] == 0):
                        nbad += 1
                    print(' '.join(key), 'rep', ri, 'D', D, 'E', out['E'], 'bases', out['bases_unique'], 'sub', out['labeled_total'], ostats[-1],
                          'nn_eq', ok_nn, 'cnt_eq', ok_cnt, 'nodes', out['nodes'], 'inexact', out['inexact'], 'exactsys', out['exact_system'],
                          f"t={out['t_enum']:.1f}+{out['t_lattice']:.1f}", flush=True)
        print('DONE', ' '.join(key), flush=True)
    print('checked', nchk, 'mismatches', nbad)
