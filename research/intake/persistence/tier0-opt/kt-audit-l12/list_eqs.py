import json, sys
from collections import Counter
from math import comb
sys.dont_write_bytecode=True
P='/Users/jwross/Documents/cairn/research/intake/persistence/'
E=json.load(open(P+'tier0-opt/kt-audit/eqs_lift.json'))
R=json.load(open(P+'tier0/remaining_A64.json'))
def npat(M):
    p=12
    for d,k in Counter(M).items(): p*=comb(12+k-1,k)
    return p
out={}
for s,M,A,lv,fs in E:
    if A>=64: out[tuple(M)]=dict(s=s,M=list(M),A=A,src='known19',npat=npat(M))
for e in R['eqs']:
    t=tuple(e['M'])
    if t in out: out[t]['src']+='+remaining'; out[t]['done']=e['done']
    else: out[t]=dict(s=e['s'],M=e['M'],A=e['A'],src='pending',npat=e['npat'],done=e['done'])
L=sorted(out.values(),key=lambda d:d['npat'])
json.dump(L,open('eqs_all.json','w'),indent=0)
for d in L: print(d['s'],''.join(map(str,d['M'])),d['A'],d['src'],'%.2e'%d['npat'],d.get('done'))
print(len(L), sum(1 for d in L if d['src'].startswith('known')), sum(1 for d in L if d['src']=='pending'))
