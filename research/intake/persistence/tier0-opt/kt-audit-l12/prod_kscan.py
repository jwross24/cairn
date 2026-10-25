import json,subprocess,os
H=os.path.dirname(os.path.abspath(__file__))
tags=json.load(open(f'{H}/queue_tags.json')); rows=[]
for t in tags:
    r=subprocess.run(['nice','-n','10',f'{H}/lvl12_dbg',f'{H}/cfgs/cfg_{t}.txt','0','0','bs'],capture_output=True,text=True)
    d={}
    for l in r.stderr.splitlines():
        if l.startswith('DBG KT:'): d['KT']=list(map(int,l.split(':')[1].split()))
        if l.startswith('DBG P2A'): d['P2A']=l.split(':')[1].split()
        if l.startswith('DBG A='): d['hdr']=l
    A=int(open(f'{H}/cfgs/cfg_{t}.txt').readline().split()[1])
    if A<64: continue
    kt=d['KT'][64:A+1]
    true=[pow(2,a,1000) for a in range(64,A+1)]
    p2=[int(x) for x in d['P2A'][4:4+(A-63)]]
    rows.append((t,A,kt,[p==w for p,w in zip(p2,true)]))
    print(t,'A',A,'prod K(a>=64)=',kt,'P2A correct:',[p==w for p,w in zip(p2,true)])
