import sys, os, json, math, time
from collections import Counter

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from n1lib import *
import n1diff as ND
from stage_io import entries, full_key
from descent import factor237

TIER0 = '/Users/jwross/Documents/cairn/research/intake/persistence/tier0'


def depth2_cases():
    out = []
    for l in open(os.path.join(TIER0, 'DEEPCUT-run.txt')):
        if l.startswith('s=') and 'bound' in l and 'CLOSED' not in l:
            t = l.split()
            s = t[0][2:]
            M = t[1][2:]
            a = t[2][2:]
            y = t[3][2:]
            out.append((s, M, a, y, l.split('bound')[1].strip()))
    return out


if __name__ == '__main__':
    lam = ND.load_lam()
    recs = {}
    for fn in ('runall_final.jsonl', 'trees_c.jsonl', 'trees_mac.jsonl'):
        for (s, M, a, nu, eps, y, sol) in entries(os.path.join(ND.FROZEN, fn)):
            key = (str(s), ''.join(map(str, M)), str(a), str(y))
            recs.setdefault(key, {})[full_key(s, M, a, nu, eps, y)] = (s, M, a, nu, eps, y)
    nbad = 0
    ntot = 0
    for (s, M, a, y, old) in depth2_cases():
        key = (s, M, a, y)
        for fk, rec in recs[key].items():
            reps = ND.reps_for(rec)
            f = factor237(int(y))
            co0 = Coset((f[1], f[2]), lam.u1, lam.u2)
            for ri, rep in enumerate(reps):
                closed, bound, cases, stats = DC.deep_cut(co0, int(a), rep, 2, 10 ** 7)
                mine = ND.run_rep(co0, int(a), rep, 2)
                if closed:
                    ok = mine['nn'] is None and mine['labeled_total'] == 0
                    ntot += 1
                    nbad += (not ok)
                    print(' '.join(key), 'rep', ri, 'deepcut CLOSED', 'lattice nn', mine['nn'], 'OK' if ok else 'MISMATCH', flush=True)
                    continue
                b_mine = bound_digits_log(mine['nn']) if mine['nn'] is not None else None
                ok = b_mine is not None and abs(b_mine - bound) < 1e-9 and stats[-1] == mine['labeled_total']
                ntot += 1
                nbad += (not ok)
                print(' '.join(key), 'rep', ri, 'deepcut bound', f'{bound:.6f}', 'lattice bound', f'{b_mine:.6f}', 'stats', stats,
                      'mine', mine['labeled_total'], 'OK' if ok else 'MISMATCH', 'old-file', old, flush=True)
    print('depth-2 cases compared', ntot, 'mismatches', nbad)
