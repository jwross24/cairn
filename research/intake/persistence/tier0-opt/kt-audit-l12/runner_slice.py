import sys, os, json, subprocess, hashlib, gzip, time, threading
from concurrent.futures import ThreadPoolExecutor
HERE=os.path.dirname(os.path.abspath(__file__))
BINS={'prod':'lvl12_prod_pinned','fix1':'lvl12_fix1','fix2':'lvl12_fix2'}
ENV=dict(os.environ, LC_ALL='C')
lock=threading.Lock()
def job(tag, which, lo, hi):
    outp=f"{HERE}/runs/{tag}.nu{lo}-{hi}.{which}.sorted.gz"
    if os.path.exists(outp+'.done'): return
    cfg=f"{HERE}/cfgs/cfg_{tag}.txt"
    t0=time.time()
    p=subprocess.Popen(['nice','-n','10',f"{HERE}/{BINS[which]}",cfg,str(lo),str(hi),'bs'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    s=subprocess.Popen(['nice','-n','10','sort','-S','256M','-T',f"{HERE}/runs"],stdin=p.stdout,stdout=subprocess.PIPE,env=ENV)
    p.stdout.close()
    h=hashlib.sha256(); n=0
    errb=[]
    th=threading.Thread(target=lambda: errb.append(p.stderr.read())); th.start()
    with gzip.open(outp,'wb',compresslevel=1) as g:
        for chunk in iter(lambda: s.stdout.read(1<<20), b''):
            h.update(chunk); n+=chunk.count(b'\n'); g.write(chunk)
    rc=p.wait(); s.wait(); th.join()
    rec=dict(tag=tag,which=which,lo=lo,hi=hi,rc=rc,lines=n,sha256=h.hexdigest(),stderr=errb[0].decode().strip(),secs=round(time.time()-t0,1))
    with lock:
        open(f"{HERE}/runs_slice.jsonl",'a').write(json.dumps(rec)+'\n')
    if rc==0: open(outp+'.done','w').write(rec['sha256'])
if __name__=='__main__':
    tags=json.load(open(sys.argv[1])); nw=int(sys.argv[2])
    jobs=[(t,w,lo,hi) for (lo,hi) in ((0,3),(3,6)) for t in tags for w in ('prod','fix2')]
    with ThreadPoolExecutor(nw) as ex:
        list(ex.map(lambda a: job(*a), jobs))
