import sys,json,math,collections
import os; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from load import *
E_=[e for e in eqs(('trees_mac.jsonl.eqs.jsonl',)) if e['npat']>2e6]
# trees_c.jsonl holds eqs inside vertex rows
for l in open(T+'trees_c.jsonl'):
    r=json.loads(l)
    for e in r.get('eqs',[]):
        if isinstance(e,dict) and e.get('npat',0)>2e6 and 'levels' in e: E_.append(e)
g=collections.defaultdict(lambda: collections.defaultdict(float))
for e in E_:
    q=len(e['M']); d=g[q]
    L={l[0]:l for l in e['levels']}
    d['npat']+=e['npat']; d['pass']+=e['c_stats']['(a,pattern)']; d['sv12']+=L[12][2]
    for lv in (24,48,96):
        if lv in L: d['n%d'%lv]+=L[lv][1]; d['sv%d'%lv]+=L[lv][2]
    d['open']+=e['open']; d['neq']+=1
# ratios: name -> (num, den)
R={'pass':('pass','npat'),'sv12':('sv12','npat'),'n24':('n24','sv12'),'s24':('sv24','n24'),'n48':('n48','sv24'),'s48':('sv48','n48'),'n96':('n96','sv48'),'s96':('sv96','n96'),'open':('open','npat')}
fits={}
QLO=7
for name,(a,b) in R.items():
    pts=[(q,g[q][a],g[q][b]) for q in sorted(g) if q>=QLO and g[q][a]>0 and g[q][b]>0]
    # weighted LS of ln(num/den) on q, weight = num
    W=sum(p[1] for p in pts); sq=sum(p[1]*p[0] for p in pts)/W
    sy=sum(p[1]*math.log(p[1]/p[2]) for p in pts)/W
    sxx=sum(p[1]*(p[0]-sq)**2 for p in pts); sxy=sum(p[1]*(p[0]-sq)*(math.log(p[1]/p[2])-sy) for p in pts)
    slope=sxy/sxx if sxx>0 else 0
    fits[name]=dict(slope=slope,intercept_at_q=sq,ln_at_q=sy,npts=len(pts),obs={q:(g[q][a]/g[q][b] if g[q][b] else None) for q in sorted(g)})
json.dump(dict(fits=fits,counts={q:dict(v) for q,v in g.items()}),open('rates.json','w'),indent=1)
for n,f in fits.items(): print(n,'slope %.3f'%f['slope'],'rate@q=13 %.3e'%math.exp(f['ln_at_q']+f['slope']*(13-f['intercept_at_q'])),'rate@q=18 %.3e'%math.exp(f['ln_at_q']+f['slope']*(18-f['intercept_at_q'])))
print(len(E_),{q:int(v['neq']) for q,v in g.items()})
