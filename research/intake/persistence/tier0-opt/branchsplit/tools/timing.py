import sys, os, subprocess, time, json
W = '/private/tmp/persist-branchsplit'
vs = [int(x) for x in sys.argv[1].split(',')]
reps = int(sys.argv[2])
res = {}
for s in vs:
    known = subprocess.run(['uv', 'run', '--no-project', 'python', f'{W}/known.py', str(s)], capture_output=True, text=True).stdout.strip()
    t = {'prod': [], 'cand': []}
    loads = []
    for i in range(reps):
        for d in ('prod', 'cand'):
            loads.append(os.getloadavg()[0])
            t0 = time.time()
            p = subprocess.run(['nice', '-n', '10', 'uv', 'run', '--no-project', '--with', 'gmpy2', '--with', 'sympy', 'python', 'run_vertex_c.py', str(s), known, '2'],
                               cwd=f'{W}/{d}', capture_output=True, text=True)
            assert p.returncode == 0, p.stderr[-300:]
            t[d].append(round(time.time() - t0, 2))
    res[s] = dict(prod=t['prod'], cand=t['cand'], best_prod=min(t['prod']), best_cand=min(t['cand']), speedup=round(min(t['prod']) / min(t['cand']), 3), load_1min_samples=[round(x, 1) for x in loads])
    print(json.dumps({s: res[s]}), flush=True)
