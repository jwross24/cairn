import sys,json,math,heapq,collections,copy
import os
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,HERE)
import costmodel as cm
from costmodel import *
V=json.load(open(os.path.join(HERE,'tierA_eqs.json')))
CF=1/6
SPEEDS=[1.0]*4+[cm.E_SPEED]*6
CAP=sum(SPEEDS)

def eq_rows(open_mode='registered',sand_slope=None):
    rows=[]
    for v in V:
        for e in v['eqs']:
            if e['done']: continue
            w=eq_work(tuple(e['M']),e['npat'],open_mode=open_mode)
            rows.append((v['s'],e,w))
    return rows

def stage_table(rows,sc):
    """per-eq stage P-core seconds under scenario sc"""
    u=dict(UNIT); 
    out=[]
    for s,e,w in rows:
        k=w['q']
        st=eq_stage_seconds(w,u,t12=sc.get('t12',UNIT['t12_ref']))
        if sc.get('gpu'): st['gpu']=w['npat']/sc['gpu']; st['lvl12']=0.0
        hx=sc.get('q14_x',1.0) if k>=14 else 1.0
        for l in ('lvl24','lvl48','lvl96'): st[l]=st[l]*hx/sc.get('lvlN_x',1)
        st['lemmaC']/=sc.get('post_x',1); 
        sw=st['sandwich']
        if sc.get('sand_slope') is not None:
            a,b,c=POST['sandwich_lnsec']; k0=11; D=cm.sand_depth(k)
            ref11=math.exp(a+b*k0+c*cm.sand_depth(k0)); sw=sw/ sand_secs(k)*(ref11*math.exp(sc['sand_slope']*(k-k0)+c*(D-cm.sand_depth(k0))))
        st['sandwich']=sw/sc.get('post_x',1)
        out.append((s,e,w,st))
    return out

def sweep_driver(tab,sc):
    """current driver: vertices sequential, equations sequential, lvl12 over 10 procs (6x), lift+python serial, post serial after"""
    t=0;post=0
    for s,e,w,st in tab:
        t+=st['lvl12']*CF+st['lvl24']+st['lvl48']+st['lvl96']+st['py']; post+=st['lemmaC']+st['sandwich']
    return t,post

def pool_sim(tab,sc,chunk=None):
    gpu=sc.get('gpu')
    byv=collections.defaultdict(list)
    for r in tab: byv[r[0]].append(r)
    keys=('lvl12','lvl24','lvl48','lvl96','py','lemmaC','sandwich')
    tot=sum(sum(st[k] for k in keys) for _,_,_,st in tab)
    chunk=chunk or max(300.0,tot/CAP/300)
    vwork={s:sum(sum(st[k] for k in keys) for _,_,_,st in byv[s]) for s in byv}
    vorder=sorted(byv,key=lambda s:-vwork[s])
    ready=[]; cnt=0
    def add(kind,s,work):
        nonlocal cnt
        cnt+=1; heapq.heappush(ready,(-work,cnt,kind,s))
    rem={s:0 for s in byv}; post={s:[] for s in byv}; prem={s:0 for s in byv}; vfin={}
    for s in vorder:
        for _,e,w,st in byv[s]:
            if st['lvl12']>0:
                for _ in range(12): add('p1',s,st['lvl12']/12); rem[s]+=1
            lift=st['lvl24']+st['lvl48']+st['lvl96']
            n=max(1,math.ceil(lift/chunk))
            for _ in range(n): add('p1',s,lift/n); rem[s]+=1
            add('p1',s,st['py']); rem[s]+=1
            pc=st['lemmaC']+st['sandwich']
            if pc>0:
                n=max(1,math.ceil(pc/chunk)); post[s]+=[pc/n]*n
    events=[]  # (time, seq, kind, worker, vertex)
    seq=0; gtot=0.0
    if gpu:
        g=0.0
        for s in vorder:
            g+=sum(st['gpu'] for _,_,_,st in byv[s]); rem[s]+=1
            seq+=1; heapq.heappush(events,(g,seq,'gpu',-1,s))
        gtot=g
    free=sorted(range(len(SPEEDS)),key=lambda i:-SPEEDS[i]); t=0.0; fin=0.0; busy=0.0
    while ready or events:
        while ready and free:
            negw,_,kind,s=heapq.heappop(ready); wk=-negw
            i=free.pop(0)
            seq+=1; heapq.heappush(events,(t+wk/SPEEDS[i],seq,kind,i,s)); busy+=wk
        if not events: break
        t,_,kind,i,s=heapq.heappop(events)
        fin=max(fin,t)
        if i>=0:
            free.append(i); free.sort(key=lambda j:-SPEEDS[j])
        if kind in ('p1','gpu'):
            rem[s]-=1
            if rem[s]==0:
                for x in post[s]: add('post',s,x)
                prem[s]=len(post[s])
                if prem[s]==0: vfin[s]=t
        elif kind=='post':
            prem[s]-=1
            if prem[s]==0: vfin[s]=t
    pool_sim.vfin=vfin; pool_sim.vwork=vwork
    return fin,busy,tot,gtot
