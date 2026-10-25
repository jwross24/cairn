import sys, subprocess, hashlib, os, json
T0='/Users/jwross/Documents/cairn/research/intake/persistence/tier0/lvlN'
FIX='/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/math/lift-ideation/lvlNf'
def run(b,cfg,par,out):
    with open(out,'w') as fo:
        pr=subprocess.run(['nice','-n','10',b,cfg,par],stdout=fo,stderr=subprocess.PIPE,text=True)
    return pr.returncode,pr.stderr.strip()
def load(out,q):
    keys=set(); lines=set()
    for l in open(out):
        f=l.split()
        if f[0] not in('OPEN','EXACT'): continue
        keys.add((f[0],)+tuple(f[1:4+q])); lines.add(l)
    return keys,lines
def sha(lines): return hashlib.sha256(''.join(sorted(lines)).encode()).hexdigest()[:12]
if __name__=='__main__':
    cfg,par,tag=sys.argv[1:4]
    q=int(open(cfg).readline().split()[3]); A=int(open(cfg).readline().split()[2])
    rp,sp=run(T0,cfg,par,f'kc_{tag}_prod.out'); rf,sf=run(FIX,cfg,par,f'kc_{tag}_fix.out')
    kp,lp=load(f'kc_{tag}_prod.out',q); kf,lf=load(f'kc_{tag}_fix.out',q)
    print(tag,'A',A,'rc',rp,rf,'| prod:',sp,'| fix:',sf)
    print(' prod keys',len(kp),'fix keys',len(kf),'fixed-not-in-prod',len(kf-kp),'prod-not-in-fixed',len(kp-kf),'lines sha prod',sha(lp),'fix',sha(lf),'lines equal',lp==lf)
    json.dump({'fix_not_prod':sorted(kf-kp)[:20]},open(f'kc_{tag}.json','w'))
    print(' sample fixed-not-in-prod',sorted(kf-kp)[:3])
