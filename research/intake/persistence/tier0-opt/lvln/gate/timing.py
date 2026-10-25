import subprocess,sys,time,os,statistics,json
R='/private/tmp/persist-lvln'
cases={
 'L24 222222222227 (1500 parents)':(f'{R}/bench/222222222227/cfgL24.txt',f'{R}/prof/p1500.txt'),
 'L24 14336/2222222447 (all 12958 parents)':(f'{R}/bench2/14336/2222222447/cfgL24.txt',f'{R}/bench2/14336/2222222447/parents24.txt'),
 'L48 14336/22224478 (23 parents)':(f'{R}/bench2/14336/22224478/cfgL48.txt',f'{R}/bench2/14336/22224478/parents48.txt'),
 'L96 14336/22224478':(f'{R}/bench2/14336/22224478/cfgL96.txt',f'{R}/bench2/14336/22224478/parents96.txt'),
}
vars_=['base','v1','v2','v3','v4','v5','v6','v7','v8','v8pgo']
rounds=int(sys.argv[1]) if len(sys.argv)>1 else 5
only=sys.argv[2:] 
out={}
for name,(cfg,par) in cases.items():
    if not os.path.exists(par): continue
    res={v:[] for v in vars_}; loads=[]
    for r in range(rounds):
        for v in vars_:
            if v=='base' and 'L24 14336' in name and r>=1: pass
            t=f'{R}/logs/t.time'
            subprocess.run(['/usr/bin/time','-p','-o',t,'nice','-n','10',f'{R}/{v}/lvlN',cfg,par],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            u=[l for l in open(t) if l.startswith('user')][0].split()[1]; res[v].append(float(u))
        loads.append(os.getloadavg()[0])
    out[name]=dict(res=res,load1=loads)
    b=statistics.median(res['base'])
    print(name,'load1 per round',[round(x,1) for x in loads])
    for v in vars_:
        x=res[v]; print(f'  {v:6s} user s min {min(x):.3f} med {statistics.median(x):.3f} max {max(x):.3f}  ratio(base med/med) {b/statistics.median(x):.1f}',flush=True)
json.dump(out,open(f'{R}/logs/timing.json','w'))
