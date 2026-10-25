import subprocess, os
H=os.path.dirname(os.path.abspath(__file__))
for v in ('orig','fix1','fix2'):
    r=subprocess.run(['cc','-O3','-march=native','-g','-fsanitize=address','-fno-omit-frame-pointer','-o',f'{H}/lvl12_asan_{v}',f'{H}/lvl12_{v}.c'],capture_output=True,text=True); print(v,'build rc',r.returncode,r.stderr[-200:])
    r=subprocess.run(['nice','-n','10',f'{H}/lvl12_asan_{v}',f'{H}/cfgs/cfg_393216_22222222222222234.txt','0','1','bs'],capture_output=True,text=True,timeout=1500)
    open(f'{H}/asan_{v}.err','w').write(r.stderr); open(f'{H}/asan_{v}.out','w').write(r.stdout)
    print(v,'rc',r.returncode,'stdout lines',r.stdout.count('\n'))
    for l in r.stderr.splitlines():
        if 'ERROR' in l or 'SUMMARY' in l or ' is located' in l or l.startswith('patterns'): print('  ',l[:230])
    fr=[l for l in r.stderr.splitlines() if l.strip().startswith('#')][:4]
    for l in fr: print('  ',l[:200])
