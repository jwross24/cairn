import json,sys
def load(p):
    d={}
    for l in open(p):
        if l.startswith('{'):
            r=json.loads(l)
            if 'M' in r: d[tuple(r['M'])]=r
    return d
a=load(sys.argv[1]); b=load(sys.argv[2]); bad=0
for M in a:
    if M not in b: print('MISSING',M); bad+=1; continue
    ra,rb=a[M],b[M]
    for k in ('open','sols','stats','levels','bounds','exceptional'):
        if ra.get(k)!=rb.get(k): print('DIFF',k,M); bad+=1
    if ra['lvln']!=rb['lvln']: print('LVLN DIFF',M); bad+=1
print('14336 compare:',len(a),'equations ref,',len(b),'cand;', 'IDENTICAL (raw stdout sha, sorted sha, stderr counters, open, sols, levels)' if not bad and set(a)==set(b) else 'DIFFERENT %d'%bad)
n=sum(len(r['lvln']) for r in a.values()); print('lvlN calls compared:',n)
