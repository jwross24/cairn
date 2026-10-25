import glob,itertools,json,re,sys
comps={0:[0,1,2,3,4],1:[1,2,4],2:[0,3,4],3:[4]}
P=[11,13,37,101,9901]
steps=[('P',i) for i in range(5)]+[('C',c) for c in range(4)]
def load(f):
    H={};n=0
    for l in open(f):
        if l.startswith('H '): _,h,c=l.split(); H[int(h)]=int(c)
        if l.startswith('patterns'): n=int(l.split()[1])
    return H,n
def cost_order(order,H,cp,cc):
    # order: list of steps; returns expected cost per pattern and expected number of tests
    tot=0;N=sum(H.values())
    for h,cnt in H.items():
        zm=h&31; cm=h>>5; spent=0; ev=set()
        for st in order:
            kind,i=st
            if kind=='P':
                if not all(True for _ in [0]): pass
                spent+=cp; ev.add(i)
                if zm>>i&1: break
            else:
                if not all(j in ev for j in comps[i]): raise Exception('infeasible')
                spent+=cc
                if cm>>i&1: break
        tot+=spent*cnt
    return tot/N
def feasible(order):
    ev=set()
    for k,i in order:
        if k=='P': ev.add(i)
        elif not all(j in ev for j in comps[i]): return False
    return True
def best(H,cp,cc):
    b=None
    # primes order x comp placement: enumerate permutations of primes, comps tested asap in each fixed ordering of comps by greedy availability -> enumerate all feasible perms of 9 steps
    for perm in itertools.permutations(steps):
        if not feasible(perm): continue
        c=cost_order(perm,H,cp,cc)
        if b is None or c<b[0]: b=(c,perm)
    return b
res={}
agg={}
for f in sorted(glob.glob('cfg_*.kr')):
    H,n=load(f)
    for h,c in H.items(): agg[h]=agg.get(h,0)+c
    res[f]=(H,n)
def marg(H):
    N=sum(H.values()); out={}
    for i in range(5): out['Z%d(p=%d)'%(i,P[i])]=sum(c for h,c in H.items() if h>>i&1)/N
    for c_ in range(4): out['C%d'%c_]=sum(c for h,c in H.items() if (h>>(5+c_))&1)/N
    out['any']=sum(c for h,c in H.items() if h)/N
    out['onlyC_only(no zero)']=sum(c for h,c in H.items() if h and not (h&31))/N
    return out
cur=[('P',i) for i in range(5)]+[('C',c) for c in range(4)]
out={}
for name,H in list(res.items())+[('AGG',(agg,0))]:
    H=H[0] if isinstance(H,tuple) else H
    m=marg(H)
    r={}
    for tag,cp,cc in (('cp1.5_cc1',1.5,1.0),('cp1_cc1',1.0,1.0),('count',1.0,1.0)):
        base=cost_order(cur,H,cp,cc); b=best(H,cp,cc); br=5*cp+4*cc
        r[tag]=dict(branchless=br,current_order=round(base,3),best=round(b[0],3),best_order=[f"{k}{i}" for k,i in b[1]])
    out[name]=dict(marg={k:round(v,5) for k,v in m.items()},cost=r,N=sum(H.values()))
json.dump(out,open('killrates.json','w'),indent=1)
for k,v in out.items():
    print(k,v['N'],v['marg']); print('  ',v['cost']['cp1.5_cc1'])

H=agg;N=sum(H.values())
order=[('P',0),('P',3),('P',4),('C',2),('P',1),('P',2),('C',0),('C',1),('C',3)]
alive=N;ev=set();print('cumulative survivors in best order')
mask=0
for k,i in order:
    mask|= (1<<i) if k=='P' else (1<<(5+i))
    alive=sum(c for h,c in H.items() if not (h&mask))
    print(k,i,round(alive/N,5))
for tag in ('cp1.5_cc1','cp1_cc1'):
    print(tag,{k:v['cost'][tag] for k,v in out.items() if k=='AGG'})
