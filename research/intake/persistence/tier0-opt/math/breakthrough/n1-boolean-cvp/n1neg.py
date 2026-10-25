import sys, os, json, math, time
from collections import Counter

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from n1lib import *
import n1diff as ND
from stage_io import entries, full_key
from descent import factor237

CASES = [("32928 446777 1 57177414", 2), ("28672 78888 2 1411788", 2), ("14336 47888 0 7411887", 3), ("28672 444788 0 7411887", 3), ("32928 446777 1 57177414", 3), ("28672 2227888 0 78121827", 4)]

if __name__ == '__main__':
    lam = ND.load_lam()
    recs = {}
    for fn in ('runall_final.jsonl', 'trees_c.jsonl', 'trees_mac.jsonl'):
        for (s, M, a, nu, eps, y, sol) in entries(os.path.join(ND.FROZEN, fn)):
            key = (str(s), ''.join(map(str, M)), str(a), str(y))
            recs.setdefault(key, {})[full_key(s, M, a, nu, eps, y)] = (s, M, a, nu, eps, y)
    for ks, D in CASES:
        key = tuple(ks.split())
        for fk, rec in recs[key].items():
            s, M, a, nu, eps, y = rec
            a = int(a)
            f = factor237(y)
            co0 = Coset((f[1], f[2]), lam.u1, lam.u2)
            for ri, rep in enumerate(ND.reps_for(rec)):
                E_ex = exact_E(D, a)
                res = {}
                for E in range(max(1, E_ex - 1), E_ex + 1):
                    res[E] = ND.run_rep(co0, a, rep, D, E=E)
                print(ks, 'rep', ri, 'D', D, {E: dict(nn_eq_exact=(r['nn'] == res[E_ex]['nn']), nodes=r['nodes'], inexact=r['inexact'],
                                                    exact_system=r['exact_system'], sub=r['labeled_total']) for E, r in res.items()}, flush=True)
