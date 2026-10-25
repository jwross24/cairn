import subprocess, os, sys
H=os.path.dirname(os.path.abspath(__file__))
for tag in sys.argv[1:]:
    r=subprocess.run([f'{H}/lvl12_fix2_dbg',f'{H}/cfgs/cfg_{tag}.txt','0','0','bs'],capture_output=True,text=True)
    L={l.split(':')[0]:l.split(':')[1].split() for l in r.stderr.splitlines() if l.startswith('DBG KT') or l.startswith('DBG P2A')}
    KT=list(map(int,L['DBG KT'])); P2A=list(map(int,L['DBG P2A'])); A=len(KT)-1
    kt_ok=all(k==3 for k in KT); p_ok=all(P2A[a]==pow(2,a,10**KT[a]) for a in range(A+1))
    print(tag,'A',A,'KT all 3:',kt_ok,'P2A[a]==2^a mod 10^K for all a<=A:',p_ok, 'P2A[64:]',P2A[64:])
