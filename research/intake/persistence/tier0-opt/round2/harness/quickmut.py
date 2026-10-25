import subprocess, hashlib, json, sys
L=json.load(open('mut/list.json'))
cfgs=['e864','eA','e10800'] if len(sys.argv)<2 else sys.argv[1:]
def run(b,c):
    p=subprocess.run([b,f'cfg/{c}.txt','0','12'],capture_output=True,text=True)
    return hashlib.sha256('\n'.join(sorted(p.stdout.splitlines())).encode()).hexdigest()[:12], p.stderr.strip(), p.returncode
ref={c:run('bin/ref',c) for c in cfgs}
for m in L:
    res=[]
    for c in cfgs:
        h,e,rc=run('mut/'+m['name'],c)
        res.append(f"{c}:{'out-same' if h==ref[c][0] else 'OUT-DIFF'},{'ctr-same' if e==ref[c][1] else 'CTR-DIFF'}" + ('' if rc==0 else f',rc={rc}'))
    print(m['name'],' '.join(res),flush=True)
