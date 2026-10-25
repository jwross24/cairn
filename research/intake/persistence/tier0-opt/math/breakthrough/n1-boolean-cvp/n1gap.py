import sys, os, json, math, time
from collections import Counter

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from n1lib import *
from n1solve import *
from n1cert import *
import n1diff as ND
from stage_io import entries, full_key
from descent import factor237


def gaps_for(key_str, Ds=(2, 3), maxbases=6):
    lam = ND.load_lam()
    want = tuple(key_str.split())
    recs = {}
    for fn in ('runall_final.jsonl', 'trees_c.jsonl', 'trees_mac.jsonl'):
        for (s, M, a, nu, eps, y, sol) in entries(os.path.join(ND.FROZEN, fn)):
            key = (str(s), ''.join(map(str, M)), str(a), str(y))
            if key == want:
                recs[full_key(s, M, a, nu, eps, y)] = (s, M, a, nu, eps, y)
    rows = []
    for fk, rec in recs.items():
        s, M, a, nu, eps, y = rec
        a = int(a)
        f = factor237(y)
        co0 = Coset((f[1], f[2]), lam.u1, lam.u2)
        for ri, rep in enumerate(ND.reps_for(rec)):
            nu_, De = rep
            De = list(De)
            for D in Ds:
                E = exact_E(D, a)
                if E >= D:
                    continue
                surv = survivors_to(co0, a, rep, E)
                seen = set()
                nb = 0
                for co, assigned in surv:
                    k2 = tuple(sorted((De[j][0], De[j][1], t) for j, t in assigned))
                    if k2 in seen:
                        continue
                    seen.add(k2)
                    nb += 1
                    if nb > maxbases:
                        break
                    sysd = build_system(co, assigned, a, De, E, D)
                    co_x0 = cut_coset(co, a, sysd['Tbase'], sysd['K'])
                    nn0, _ = DC.nearest_norm(co_x0)
                    res = solve_min(sysd, a, nn0)
                    t0 = time.time()
                    j = cert_gap(sysd, res['nn'])
                    dt = time.time() - t0
                    rows.append((key_str, ri, D, E, len(sysd['vars']), len(str(res['nn'])), j, None if j is None else j * math.log10(2) / 2, dt))
                    print(rows[-1], flush=True)
    return rows


if __name__ == '__main__':
    for k in sys.argv[1:]:
        gaps_for(k)
