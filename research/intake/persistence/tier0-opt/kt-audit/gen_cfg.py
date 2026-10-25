import sys, os, json, time
sys.dont_write_bytecode=True
sys.path.insert(0,'/Users/jwross/Documents/cairn/research/intake/persistence/tier0')
from export_level import export
E=json.load(open('eqs_lift.json'))
big=sorted([e for e in E if e[2]>=64],key=lambda e:(e[0],e[1]))
for s,M,A,lv,fs in big:
    tag=f"{s}_{''.join(map(str,M))}"
    for L in (24,48,96):
        p=f'cfgs/{tag}_L{L}.txt'
        if os.path.exists(p): continue
        t=time.time(); info=export(tuple(M),L,p)
        print(tag,L,'A',info['A'],'K64+',info['K'][64:],'secs',round(time.time()-t,1),flush=True)
