import sys, os, json, math, time
from collections import Counter

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from n1lib import *
from n1solve import *
from n1cert import *
from n1tierc import info_budget
import n1diff as ND
from stage_io import entries, full_key
from descent import factor237


def load_utable(path):
    U = {}
    for l in open(path):
        t = l.split()
        if len(t) == 3:
            U[(int(t[0]), int(t[1]))] = int(t[2])
    return U


def cert_rep(co0, a, rep, D, Ub, rho2):
    E = exact_E(D, a)
    nu_, De = rep
    De = list(De)
    surv = survivors_to(co0, a, rep, E)
    seen = set()
    nb = ncert = nodes = 0
    minslack = None
    t0 = time.time()
    for co, assigned in surv:
        k2 = tuple(sorted((De[j][0], De[j][1], t) for j, t in assigned))
        if k2 in seen:
            continue
        seen.add(k2)
        sysd = build_system(co, assigned, a, De, E, D)
        nb += 1
        if not sysd['vars']:
            nn = DC.nearest_norm(cut_coset(co, a, sysd['Tbase'], sysd['K']))[0]
            ncert += closes(nn, Ub)
            continue
        b = info_budget(sysd, rho2)
        minslack = b['predicted_slack'] if minslack is None else min(minslack, b['predicted_slack'])
        res, st = certify_branching(sysd, rho2, node_cap=5000)
        nodes += st['nodes']
        ncert += (res is True)
    return nb, ncert, nodes, minslack, E, time.time() - t0


below_false_closure = []

if __name__ == '__main__':
    lam = ND.load_lam()
    U = load_utable(os.path.join(ND.ORACLE, 'utable.txt'))
    orc = ND.load_oracle_tsv()
    want = set()
    for l in open(os.path.join(ND.CPORT, 'data', 'survivors.txt')):
        want.add(tuple(l.split()[:4]))
    recs = {}
    for fn in ('runall_final.jsonl', 'trees_c.jsonl', 'trees_mac.jsonl'):
        for (s, M, a, nu, eps, y, sol) in entries(os.path.join(ND.FROZEN, fn)):
            key = (str(s), ''.join(map(str, M)), str(a), str(y))
            if key in want:
                recs.setdefault(key, {})[full_key(s, M, a, nu, eps, y)] = (s, M, a, nu, eps, y)
    maxk = int(os.environ.get('N1_MAXK', '9'))
    only = sys.argv[1] if len(sys.argv) > 1 else None
    npat = nclosed = 0
    for key in sorted(recs, key=lambda k: (len(k[1]), k)):
        if only and ' '.join(key) != only:
            continue
        if len(key[1]) > maxk:
            continue
        k = len(key[1])
        a_ = int(key[2])
        Ub = U[(k, a_)]
        rho2 = disc_radius2(Ub)
        for fk, rec in recs[key].items():
            s, M, a, nu, eps, y = rec
            a = int(a)
            f = factor237(y)
            co0 = Coset((f[1], f[2]), lam.u1, lam.u2)
            reps = ND.reps_for(rec)
            all_closed = True
            info = []
            for ri, rep in enumerate(reps):
                ods = orc[key].get(ri, {})
                dstar = None
                for D in sorted(ods):
                    if ods[D][0] in ('CLOSED-sandwich', 'CLOSED-cut'):
                        dstar = D
                        break
                if dstar is None or ods[dstar][0] == 'CLOSED-cut':
                    info.append((ri, dstar, 'cut', 0, 0, None))
                    continue
                D = dstar
                nb, ncert, nodes, minslack, E, dt = cert_rep(co0, a, rep, D, Ub, rho2)
                below = None
                if D > 1 and ods.get(D - 1, ('?',))[0] == 'open':
                    nb2, nc2, nodes2, ms2, E2, dt2 = cert_rep(co0, a, rep, D - 1, Ub, rho2)
                    below = (D - 1, nb2, nc2)
                    if nc2 == nb2:
                        below_false_closure.append((key, ri, D - 1))
                closed_r = ncert == nb
                all_closed &= closed_r
                info.append((ri, D, E, nb, ncert, nodes, None if minslack is None else round(minslack, 1), round(dt, 1), 'below', below))
            npat += 1
            nclosed += all_closed
            print(' '.join(key), 'k', k, 'CERT-CLOSED' if all_closed else 'NOT-CERTIFIED', info, flush=True)
    print('patterns', npat, 'closed by certificates alone', nclosed)
    print('false closures at the depth below the first closing depth:', len(below_false_closure), below_false_closure)
