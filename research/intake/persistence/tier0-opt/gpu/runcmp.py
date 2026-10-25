import sys, os, subprocess, hashlib, json, time, glob, resource
from concurrent.futures import ThreadPoolExecutor
binp, vertex, outjson, jobs = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
env = dict(os.environ)
cfgs = sorted(glob.glob(f"/private/tmp/persist-gpu/cfg/{vertex}_*.txt"))
def run(cfg):
    t=time.time()
    p=subprocess.run(["nice","-n","10",binp,cfg],capture_output=True,text=True,env=env)
    dt=time.time()-t
    lines=sorted(p.stdout.splitlines())
    h=hashlib.sha256(('\n'.join(lines)+'\n' if lines else '').encode()).hexdigest()
    err=[l for l in p.stderr.splitlines() if l.startswith('patterns')]
    return dict(eq=os.path.basename(cfg)[:-4],rc=p.returncode,nlines=len(lines),sha=h,counters=err[0] if err else p.stderr.strip()[:300],secs=round(dt,3),
                timing=[l for l in p.stderr.splitlines() if l.startswith('gpu-timing')])
with ThreadPoolExecutor(jobs) as ex: res=list(ex.map(run,cfgs))
json.dump(res,open(outjson,'w'),indent=1)
allh=hashlib.sha256('\n'.join(r['eq']+' '+r['sha']+' '+r['counters'] for r in res).encode()).hexdigest()
print(vertex,len(res),"equations; combined",allh,"total secs",round(sum(r['secs'] for r in res),2))
