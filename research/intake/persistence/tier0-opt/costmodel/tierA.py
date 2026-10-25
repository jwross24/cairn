import sys,json,re,math
sys.path.insert(0,'/Users/jwross/Documents/cairn/research/intake/persistence/tier0')
from load import *
from collections import Counter
from math import comb
from tier0v2 import multisets
def npat(M):
    p=12
    for d,k in Counter(M).items(): p*=comb(12+k-1,k)
    return p
def tierA():
    rows=[]
    for l in open(T+'FRONTIER.md'):
        m=re.match(r'\| A \| A_(\d) \| (\d+) \| 2\^(\d+)·3\^(\d+)·7\^(\d+) \| ([\d.e+]+) \| (\d+) \| (\d+) \|',l)
        if m: rows.append(dict(tree=int(m[1]),s=int(m[2]),pat=float(m[6]),kmax=int(m[7]),nms=int(m[8])))
    return rows
def done():
    d=set()
    for f in ('trees_mac.jsonl','runall_final.jsonl','trees_c.jsonl'):
        for l in open(T+f):
            try: d.add(json.loads(l)['s'])
            except Exception: pass
    return d
if __name__=='__main__':
    A=tierA(); D=done()
    print(len(A), sum(r['s'] in D for r in A))
    rem=[r for r in A if r['s'] not in D]
    print(len(rem), sum(r['pat'] for r in rem))
    for r in A:
        r['exact']=sum(npat(tuple(sorted(M))) for M in multisets(r['s']))
    print(max(abs(r['exact']/r['pat']-1) for r in A))
    json.dump(A,open('tierA_rows.json','w'))
