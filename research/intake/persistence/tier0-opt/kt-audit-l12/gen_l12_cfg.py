import sys, os, json, time
sys.dont_write_bytecode=True
T0='/Users/jwross/Documents/cairn/research/intake/persistence/tier0'
sys.path.insert(0,T0)
HERE=os.path.dirname(os.path.abspath(sys.argv[0]))
os.chdir(T0)
from export_cfg import export
out=HERE+'/cfgs'
for d in json.load(open(os.path.join(out,'..','eqs_all.json'))) if len(sys.argv)<2 else [json.loads(a) for a in sys.argv[1:]]:
    M=tuple(sorted(d['M'])); tag=f"{d['s']}_{''.join(map(str,M))}"
    p=f"{out}/cfg_{tag}.txt"
    if os.path.exists(p): continue
    t=time.time(); cfg=export(M,p)
    print(tag,'A',cfg['A'],'L',cfg['L'],'secs',round(time.time()-t,1),flush=True)
