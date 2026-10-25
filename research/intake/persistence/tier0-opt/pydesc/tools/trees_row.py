"""trees_row.py <srcdir> <out.jsonl> : run_trees_c_v2 on the 14336 mini zf list; writes normalized rows (secs dropped) to <out>.norm"""
import sys, os, subprocess, json, time
src, out = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
assert not os.path.exists(out), out
t = time.time()
p = subprocess.run([sys.executable, 'run_trees_c_v2.py', '/private/tmp/persist-pydesc/mini14336.zf', out, '3', '1e30'], cwd=src, capture_output=True, text=True, env=dict(os.environ, PYTHONHASHSEED='0'))
w = time.time() - t
norm = []
for l in open(out):
    d = json.loads(l); d.pop('secs', None); norm.append(json.dumps(d))
open(out + '.norm', 'w').write('\n'.join(norm) + '\n')
print(f'rc={p.returncode} rows={len(norm)} wall={w:.2f}s', p.stderr[-200:] if p.returncode else '')
