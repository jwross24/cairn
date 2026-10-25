import subprocess, os, shutil, glob
S = '/private/tmp/persist-patterns'
P = '/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/patterns'
env = dict(os.environ, PYTHONHASHSEED='0', PYTHONDONTWRITEBYTECODE='1')
for f in glob.glob(f'{S}/cand/*'):
    if os.path.isfile(f): shutil.copy2(f, f'{S}/mut/')
p = f'{S}/mut/run_c.py'
s = open(p).read()
old = "eps=[int(e) for e in eps],v0"
new = "eps=[int(e) for e in r['open'][(i+1)%len(r['open'])][2]] if len(r['open'])>1 else [(int(eps[0])+1)%12]+[int(e) for e in eps[1:]],v0"
assert s.count(old) == 1
s = s.replace(old, new).replace("for (a,nu,eps,co) in r['open']])", "for i,(a,nu,eps,co) in enumerate(r['open'])])")
open(p, 'w').write(s)
for v in (14336, 131712):
    kn = open(f'/private/tmp/persist-pydesc/known{v}.txt').read().strip()
    subprocess.run([f'{S}/py', f'{P}/tools/vertex_rows.py', f'{S}/mut', str(v), kn, '3', f'{S}/out/mut_{v}.jsonl'], cwd=f'{S}/mut', env=env, check=True)
r = subprocess.run([f'{S}/py', f'{P}/tools/roundtrip.py', f'{S}/out/mut_14336.jsonl', f'{S}/out/mut_131712.jsonl'], capture_output=True, text=True, env=env)
print(r.stdout[-1500:], 'rc', r.returncode)
kn = open('/private/tmp/persist-pydesc/known14336.txt').read().strip()
with open(f'{S}/out/real_14336.txt', 'w') as fo:
    subprocess.run([f'{S}/py', 'run_vertex_c.py', '14336', kn, '3'], cwd=f'{S}/prod', env=env, stdout=fo, stderr=subprocess.DEVNULL)
r = subprocess.run([f'{S}/py', f'{P}/tools/strip_cmp.py', f'{S}/out/real_14336.txt', f'{S}/out/prod_14336.jsonl'], capture_output=True, text=True)
print(r.stdout, r.stderr[-300:])
