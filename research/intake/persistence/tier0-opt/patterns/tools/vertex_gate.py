import subprocess, os, time
S = '/private/tmp/persist-patterns'
P = '/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/patterns'
env = dict(os.environ, PYTHONHASHSEED='0', PYTHONDONTWRITEBYTECODE='1')
for v in (72, 224, 14336, 10800, 131712):
    kn = open(f'/private/tmp/persist-pydesc/known{v}.txt').read().strip()
    for w in ('prod', 'cand'):
        t0 = time.time()
        with open(f'{S}/out/{w}_{v}.log', 'w') as lg:
            rc = subprocess.run([f'{S}/py', f'{P}/tools/vertex_rows.py', f'{S}/{w}', str(v), kn, '3', f'{S}/out/{w}_{v}.jsonl'],
                                cwd=f'{S}/{w}', env=env, stdout=lg, stderr=subprocess.STDOUT).returncode
            lg.write(f'rc={rc} secs={time.time() - t0:.1f}\n')
open(f'{S}/out/ALLDONE', 'w').write('done\n')
