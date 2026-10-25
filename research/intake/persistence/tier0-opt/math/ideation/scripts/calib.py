import json, collections, math
from math import comb, log10
base='/Users/jwross/Documents/cairn/research/intake/persistence/tier0/'
H37={12:10**6.950,24:10**13.527,48:10**30.319,96:10**56.449}
G={12:10**9.631,24:10**21.622,48:10**45.596,96:10**93.588}
def N(M,L):
    from collections import Counter
    r=L
    for d,m in Counter(M).items(): r*=comb(L-1+m,m)
    return r
acc=collections.defaultdict(lambda: collections.defaultdict(lambda:[0.0,0.0,0]))
for f in ['trees_mac.jsonl','trees_c.jsonl','runall_final.jsonl']:
    for l in open(base+f):
        try: r=json.loads(l)
        except Exception: continue
        eqs=r.get('eqs',[])
        if not isinstance(eqs,list): continue
        for e in eqs:
            if not isinstance(e,dict): continue
            lv=e.get('levels')
            if not lv: continue
            k=len(e['M'])
            sv={x[0]:x[2] for x in lv}
            s96=sv.get(96,0)
            for L in (12,24,48):
                if L not in sv: continue
                nxt={12:24,24:48,48:96}[L]
                # survivors at L that die later: s_L - s_next (if next recorded) else skip for 48 if no 96
                if L==48 and 96 not in sv: continue
                die = sv[L] - (sv.get(nxt,0) if nxt in sv else 0)
                if L==12 and nxt not in sv: die=sv[L]
                model=N(e['M'],L)*H37[L]/G[L]
                a=acc[k][L]; a[0]+=die; a[1]+=model; a[2]+=1
for k in sorted(acc):
    s=f"k={k:2d} "
    for L in (12,24,48):
        if L in acc[k]:
            d,m,n=acc[k][L]
            s+=f"| L{L}: n={n} obs_die={d:.3g} model(no A, no tail)={m:.3g} f={d/m if m else 0:.2e} "
    print(s)
