import json, sys
def load(p):
    return {(json.loads(l)['s'], tuple(json.loads(l)['M'])): json.loads(l) for l in open(p)}
pairs=[('prod_recorded_14336','v14336_off'),('prod_recorded_8192','v8192_off'),('prod_recorded_28672','v28672_off')]
for b,n in pairs:
    B=load(f'../logs/{b}.jsonl'); N=load(f'../logs/{n}.jsonl')
    same=diff=0
    for k,v in N.items():
        p=B[k]
        if p['levels']==v['levels'] and p['sols']==v['sols'] and p['open']==v['open'] and p['c_stats']==v['c_stats']: same+=1
        else: diff+=1; print('DIFF',k,p['levels'],v['levels'])
    print(b,'vs',n,'identical',same,'different',diff,'of',len(N),'recorded',len(B))
