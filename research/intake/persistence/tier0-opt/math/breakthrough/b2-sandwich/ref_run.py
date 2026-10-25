import time, pickle
from common import *

def main():
    t0 = time.time(); Lam = DC.kernel_lattice()
    pats = sorted(load_patterns(), key=lambda p: len(p['M']))
    pk = os.path.join(HERE, 'ref_run.pkl')
    out = pickle.load(open(pk, 'rb')) if os.path.exists(pk) else []
    done = {(x['key'], x['nu']) for x in out}
    for p in pats:
        if (p['key'], p['nu']) in done: continue
        k = len(p['M']); a = p['a']; U = baker_upper_bound(k, a); logU = math.log10(U)
        co0 = anchor_coset(p, Lam)
        for ri, rep in enumerate(reps_of(p)):
            nu, De = rep
            for D in range(1, 7):
                closed, bound, cases, stats, levels = deep_cut_inst(co0, a, rep, D, maxcuts=250)
                rec = dict(key=p['key'], nu=p['nu'], rep=ri, repnu=nu, De=De, k=k, a=a, logU=logU, D=D,
                           closed=closed, bound=bound, cases=cases, stats=stats,
                           final=[[str(x) for x in (co.v0 + co.u1 + co.u2)] + [list(assigned)] for co, assigned in (levels[-1] if levels else [])])
                out.append(rec)
                if closed == 'BUDGET':
                    print(p['key'], ri, D, 'BUDGET', cases, stats, round(time.time() - t0), flush=True)
                    out.append(dict(key=p['key'], nu=p['nu'], rep=ri, repnu=nu, De=De, k=k, a=a, logU=logU, D=D, budget=True, cases=cases, stats=stats))
                    break
                print(p['key'], ri, D, closed, bound, cases, stats, round(time.time() - t0), flush=True)
                if closed or bound > logU: break
        pickle.dump(out, open(os.path.join(HERE, 'ref_run.pkl'), 'wb'))
    print('done', time.time() - t0)

main()
