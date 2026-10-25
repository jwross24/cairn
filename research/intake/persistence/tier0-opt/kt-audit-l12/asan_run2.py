import subprocess, os
H=os.path.dirname(os.path.abspath(__file__))
tag='69441624_23333333336677'
r=subprocess.run(['nice','-n','10',f'{H}/lvl12_asan_fix2',f'{H}/cfgs/cfg_{tag}.txt','0','1','bs'],capture_output=True,text=True,timeout=3000)
open(f'{H}/asan_fix2_A70.err','w').write(r.stderr); open(f'{H}/asan_fix2_A70.out','w').write(r.stdout)
print('rc',r.returncode,'stdout lines',r.stdout.count('\n'),'ASan lines',sum('AddressSanitizer' in l for l in r.stderr.splitlines()))
print(r.stderr.splitlines()[-1][:200])
