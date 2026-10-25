import sys, os, json
from math import gcd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cfgparse import parse
S = "/private/tmp/claude-501/-Users-jwross-Documents-cairn/ec9f8f52-ce29-4a5c-9caf-2ecbd434509f/scratchpad/h12"
out = []
for name in sorted(os.listdir(S)):
    f = f"{S}/{name}/cfgL24.txt"
    if not os.path.exists(f): continue
    c = parse(f)
    row = dict(eq=name, A=c['A'], k=c['q'], primes=[p['p'] for p in c['primes']], N=c['N'], Uold=c['Uold'], K=c['KT'][-1])
    row['comps'] = [dict(idx=x['cidx'], mod=x['cmod'], hs=x['hs'], size=eval('*'.join(map(str, x['cmod'])))) for x in c['comps']]
    row['lins'] = [dict(idx=x['lidx'], mod=x['lmod'], g=gcd(gcd(x['lg1'], x['lg2']), x['lmod'])) for x in c['lins']]
    out.append(row)
json.dump(out, open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs', 'content.json'), 'w'))
print(len(out))
