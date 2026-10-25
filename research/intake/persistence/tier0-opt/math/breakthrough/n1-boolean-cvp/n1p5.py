import sys, os, json, math, time
from collections import Counter

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from n1lib import *
from n1tier import count_blocks
import n1diff as ND
from stage_io import entries, full_key
from descent import factor237


def free_types_of(De, assigned):
    fixed = {j for j, t in assigned}
    return Counter(De[j] for j in range(len(De)) if j not in fixed)


if __name__ == '__main__':
    maxk = int(os.environ.get('N1_MAXK', '9'))
    lam = ND.load_lam()
    orc = ND.load_oracle_tsv()
    want = set(tuple(l.split()[:4]) for l in open(os.path.join(ND.CPORT, 'data', 'survivors.txt')))
    recs = {}
    for fn in ('runall_final.jsonl', 'trees_c.jsonl', 'trees_mac.jsonl'):
        for (s, M, a, nu, eps, y, sol) in entries(os.path.join(ND.FROZEN, fn)):
            key = (str(s), ''.join(map(str, M)), str(a), str(y))
            if key in want:
                recs.setdefault(key, {})[full_key(s, M, a, nu, eps, y)] = (s, M, a, nu, eps, y)
    out = []
    for key in sorted(recs, key=lambda k: (len(k[1]), k)):
        if len(key[1]) > maxk:
            continue
        for fk, rec in recs[key].items():
            s, M, a, nu, eps, y = rec
            a = int(a)
            f = factor237(y)
            co0 = Coset((f[1], f[2]), lam.u1, lam.u2)
            for ri, rep in enumerate(ND.reps_for(rec)):
                nu_, De = rep
                De = list(De)
                ods = orc[key].get(ri, {})
                cache = {}
                for D in sorted(ods):
                    res, cases, stats, nn = ods[D]
                    if res == 'CLOSED-cut':
                        continue
                    E = exact_E(D, a)
                    if E not in cache:
                        cache[E] = survivors_to(co0, a, rep, E)
                    seen = set()
                    Nunl = 0
                    V = None
                    for co, assigned in cache[E]:
                        k2 = tuple(sorted((De[j][0], De[j][1], t) for j, t in assigned))
                        if k2 in seen:
                            continue
                        seen.add(k2)
                        ft = free_types_of(De, assigned)
                        Nunl += count_blocks(ft, D - E)
                        if V is None:
                            Tb = (10 ** (LMAX * D) - 1) // 9 + sum((De[j][0] - 1) * 10 ** (De[j][1] + LMAX * t) for j, t in assigned)
                            c2 = cut_coset(co, a, Tb, LMAX * D)
                            V = c2.index()
                    nnv = int(nn)
                    r = log10_big(nnv) - (log10_big(V) - math.log10(math.pi * Nunl))
                    out.append(dict(key=' '.join(key), ri=ri, D=D, a=a, k=len(key[1]), N=Nunl, Nlab=json.loads(stats)[-1], logV=log10_big(V), lognn=log10_big(nnv), resid=r))
                    print(json.dumps(out[-1]), flush=True)
    rs = [o['resid'] for o in out if o['N'] >= 2]
    if rs:
        m = sum(rs) / len(rs)
        sd = (sum((x - m) ** 2 for x in rs) / len(rs)) ** 0.5
        inb = sum(abs(x) <= 0.7 for x in rs) / len(rs)
        print('rows with N>=2', len(rs), 'mean resid', round(m, 3), 'sd', round(sd, 3), 'fraction within +-0.7', round(inb, 3))
