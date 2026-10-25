import sys, json, multiprocessing as mp
from collections import defaultdict
from tier0 import solve_equation, multisets, arrangements
KNOWN=[98,189,294,1161216]
def work(D):
    r=solve_equation(72, D, KNOWN, verbose=False, time_budget=5400)
    return (D, len(r['open']), sorted(y for y in r['solutions'] if y>=10),
            [(L, n_in, n_surv, cls, round(el)) for (L,ps,n_in,n_surv,cls,el) in r['levels']])
if __name__=="__main__":
    eqs=[D for M in multisets(72) for D in arrangements(M)]
    eqs.sort(key=lambda D:(len(D),D))
    out=[]
    with mp.Pool(2) as pool:
        for res in pool.imap_unordered(work, eqs):
            print(json.dumps(res), flush=True); out.append(res)
    byM=defaultdict(lambda:[0,set(),0])
    for D,nopen,sols,lv in out:
        M=tuple(sorted(D)); byM[M][0]+=nopen; byM[M][1]|=set(sols); byM[M][2]+=1
    print("\nPER MULTISET:")
    allclosed=True
    for M,(nopen,sols,neq) in sorted(byM.items()):
        print(f"  M={M}: {neq} arrangements, open patterns {nopen}, children {sorted(sols)} -> {'CLOSED' if nopen==0 else 'OPEN'}")
        allclosed &= (nopen==0)
    found=set().union(*(v[1] for v in byM.values()))
    print(f"VERTEX 72: {'CLOSED' if allclosed else 'OPEN'}; children found {sorted(found)}; known {sorted(KNOWN)}; match={found==set(KNOWN)}")
