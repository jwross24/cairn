"""rv.py <srcdir> <s> <ncores> <outfile> : run_vertex_c under srcdir, normalized stdout (secs removed) -> outfile; prints wall"""
import sys, os, subprocess, json, time
src, s, nc, out = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
known = open(f'/private/tmp/persist-pydesc/known{s}.txt').read().strip()
t = time.time()
p = subprocess.run([sys.executable, 'run_vertex_c.py', s, known, nc], cwd=src, capture_output=True, text=True, env=dict(os.environ, PYTHONHASHSEED='0'))
w = time.time() - t
rows = []
for ln in p.stdout.splitlines():
    if ln.startswith('{'):
        d = json.loads(ln); d.pop('secs', None); rows.append(json.dumps(d, sort_keys=False))
open(out, 'w').write('\n'.join(rows) + '\n')
print(f'rc={p.returncode} rows={len(rows)} wall={w:.2f}s', p.stderr[-200:] if p.returncode else '')
