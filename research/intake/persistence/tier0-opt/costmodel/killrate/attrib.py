import json,glob
exec(open('analyze.py').read().split("res={}")[0])
agg={}
for f in glob.glob('cfg_*.kr'):
    H,n=load(f)
    for h,c in H.items(): agg[h]=agg.get(h,0)+c
N=sum(agg.values())
def attrib(order):
    cnt={}
    for h,c in agg.items():
        for k,i in order:
            bit=(1<<i) if k=='P' else (1<<(5+i))
            if h&bit: cnt[(k,i)]=cnt.get((k,i),0)+c; break
        else: cnt['pass']=cnt.get('pass',0)+c
    return {(f"{k[0]}{k[1]}" if k!='pass' else 'pass'):round(v/N,5) for k,v in cnt.items()}
cur=[('P',i) for i in range(5)]+[('C',c) for c in range(4)]
best=[('P',0),('P',3),('P',4),('C',2),('P',1),('P',2),('C',0),('C',1),('C',3)]
out=dict(N=N,current=attrib(cur),best=attrib(best))
print(json.dumps(out,indent=1)); json.dump(out,open('attrib.json','w'))
