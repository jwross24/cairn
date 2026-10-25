"""eqrun.py <srcdir> <s> <M> <ncores> : one equation through run_c.run; prints a digest of every observable plus wall"""
import sys, os, time, json, hashlib
src, s, M, nc = sys.argv[1], int(sys.argv[2]), tuple(int(x) for x in sys.argv[3].split(',')), int(sys.argv[4])
os.chdir(src); sys.path.insert(0, src)
import run_c
t = time.perf_counter(); c0 = time.process_time()
r = run_c.run(s, M, [], ncores=nc)
wall = time.perf_counter() - t
obs = dict(open=[(a, nu, eps, co.v0, co.u1, co.u2) for (a, nu, eps, co) in r['open']], sols=sorted(r['solutions']), closed=r['closed'], complete_below=r['complete_below'],
           bounds=r['bounds'], exceptional=r['exceptional'], c_stats=r['c_stats'], levels=[(l[0], l[2], l[3], l[4]) for l in r['levels']],
           new=sorted(r.get('new_children', [])), missing=sorted(r.get('missing_children', [])))
d = hashlib.sha256(json.dumps(obs, default=str, sort_keys=False).encode()).hexdigest()
print(json.dumps(dict(src=os.path.basename(src), digest=d[:16], n_open=len(r['open']), levels=obs['levels'], wall=round(wall, 2), self_cpu=round(time.process_time() - c0, 2))))
