import subprocess, os, shutil, glob, json
S = '/private/tmp/persist-patterns'
P = '/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/patterns'
T = '/Users/jwross/Documents/cairn/research/intake/persistence/tier0'
env = dict(os.environ, PYTHONHASHSEED='0', PYTHONDONTWRITEBYTECODE='1')
O = f'{S}/out'
for f in glob.glob(f'{O}/t_*'): os.remove(f)

def trees(w, outp, skipf=None):
    cmd = [f'{S}/py', 'run_trees_c_v2.py', '/private/tmp/persist-pydesc/mini14336.zf', outp, '3', '1e30']
    r = subprocess.run(cmd, cwd=f'{S}/{w}', env=env, capture_output=True, text=True)
    print(w, 'rc', r.returncode, r.stderr[-200:])

trees('prod', f'{O}/t_prod.jsonl')
trees('cand', f'{O}/t_cand.jsonl')
lines = open(f'{O}/t_prod.jsonl.eqs.jsonl').read().splitlines()
open(f'{O}/t_mixed.jsonl.eqs.jsonl', 'w').write('\n'.join(lines[:8]) + '\n')
trees('cand', f'{O}/t_mixed.jsonl')
for n in ('t_cand', 't_mixed'):
    for suf in ('.jsonl', '.jsonl.eqs.jsonl'):
        r = subprocess.run([f'{S}/py', f'{P}/tools/strip_cmp.py', f'{O}/t_prod{suf}', f'{O}/{n}{suf}'], capture_output=True, text=True)
        print(n, suf, r.stdout.strip(), r.stderr[-200:])
r = subprocess.run([f'{S}/py', f'{P}/tools/roundtrip.py', f'{O}/t_cand.jsonl', f'{O}/t_cand.jsonl.eqs.jsonl', f'{O}/t_mixed.jsonl'], capture_output=True, text=True)
print(r.stdout[-400:], r.returncode)
cons = f'{S}/cons'
os.makedirs(cons, exist_ok=True)
for f in glob.glob(f'{T}/*.py') + [f'{T}/zf_below_1e4000.txt', f'{T}/runall_final.jsonl']:
    shutil.copy2(f, cons)
outs = {}
for n in ('t_prod', 't_cand', 't_mixed'):
    res = []
    for scr, extra in (('classify_open.py', []), ('deepcut.py', ['--depth', '1'])):
        r = subprocess.run([f'{S}/py', scr, f'{O}/{n}.jsonl'] + extra, cwd=cons, env=env, capture_output=True, text=True)
        res.append((r.returncode, r.stdout, r.stderr[-150:]))
    outs[n] = res
for n in ('t_cand', 't_mixed'):
    print(n, 'consumers identical to prod:', outs[n] == outs['t_prod'], [x[0] for x in outs[n]], [len(x[1]) for x in outs[n]])
