import gzip, json, sys, os
H=os.path.dirname(os.path.abspath(__file__))
def stream(p):
    with gzip.open(p,'rb') as g:
        for l in g: yield l
def diff(pa, pb):
    ia, ib = stream(pa), stream(pb)
    a=next(ia,None); b=next(ib,None)
    only_a=only_b=0; a_lo_a=a_hi_a=a_lo_b=a_hi_b=0; same=0
    def hi(l): return int(l.split()[1])>=64
    while a is not None or b is not None:
        if b is None or (a is not None and a<b):
            only_a+=1
            if hi(a): a_hi_a+=1
            else: a_lo_a+=1
            a=next(ia,None)
        elif a is None or b<a:
            only_b+=1
            if hi(b): a_hi_b+=1
            else: a_lo_b+=1
            b=next(ib,None)
        else:
            same+=1; a=next(ia,None); b=next(ib,None)
    return dict(only_first=only_a,only_second=only_b,first_only_a_ge64=a_hi_a,first_only_a_lt64=a_lo_a,second_only_a_ge64=a_hi_b,second_only_a_lt64=a_lo_b,common=same)
if __name__=='__main__':
    recs={}
    for l in open(f'{H}/runs.jsonl'):
        r=json.loads(l)
        if r['rc']==0: recs[(r['tag'],r['which'])]=r
    tags=json.load(open(f'{H}/queue_tags.json'))
    out=[]
    for t in tags:
        if not all((t,w) in recs for w in ('prod','fix1','fix2')): continue
        row=dict(tag=t,A=int(open(f'{H}/cfgs/cfg_{t}.txt').readline().split()[1]),
                 lines={w:recs[(t,w)]['lines'] for w in ('prod','fix1','fix2')},
                 sha={w:recs[(t,w)]['sha256'][:12] for w in ('prod','fix1','fix2')},
                 secs=sum(recs[(t,w)]['secs'] for w in ('prod','fix1','fix2')))
        for x,y in (('prod','fix1'),('prod','fix2'),('fix1','fix2')):
            if recs[(t,x)]['sha256']==recs[(t,y)]['sha256']: row[f'{x}_vs_{y}']='IDENTICAL'
            else: row[f'{x}_vs_{y}']=diff(f'{H}/runs/{t}.{x}.sorted.gz',f'{H}/runs/{t}.{y}.sorted.gz')
        out.append(row)
    json.dump(out,open(f'{H}/compare.json','w'),indent=1)
    for r in out:
        print(r['tag'],'A',r['A'],r['lines'],r['sha'])
        for k in ('prod_vs_fix1','prod_vs_fix2','fix1_vs_fix2'):
            v=r[k]; print('  ',k, v if v=='IDENTICAL' else f"first_only={v['only_first']} (a>=64:{v['first_only_a_ge64']}) second_only={v['only_second']} (a>=64:{v['second_only_a_ge64']}, a<64:{v['second_only_a_lt64']}/{v['first_only_a_lt64']}) common={v['common']}")
