import sys,json
sys.path.insert(0,'/private/tmp/persist-costmodel')
from tierA import *
A=tierA(); D=done()
doneq=set()
for e in eqs(): doneq.add((e['s'],tuple(e['M'])))
out=[]
for r in A:
    s=r['s']; es=[]
    for M in multisets(s):
        M=tuple(sorted(M)); es.append(dict(M=M,npat=npat(M),done=(s in D) or ((s,M) in doneq)))
    out.append(dict(s=s,tree=r['tree'],kmax=r['kmax'],vertex_done=s in D,eqs=es))
json.dump(out,open('tierA_eqs.json','w'))
print(len(out),sum(len(v['eqs']) for v in out), sum(e['npat'] for v in out for e in v['eqs'] if not e['done']))
import collections
c=collections.Counter()
for v in out:
    for e in v['eqs']:
        if not e['done']: c[len(e['M'])]+=e['npat']
print(sorted(c.items()))
