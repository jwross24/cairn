"""ab.py <s> <ncores> <reps> <dir>... : interleaved A/B of run_vertex_c over the candidate dirs"""
import sys, subprocess, json, statistics
s, nc, reps, dirs = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4:]
res = {d: [] for d in dirs}
for r in range(reps):
    for d in (dirs if r % 2 == 0 else dirs[::-1]):
        p = subprocess.run(['/private/tmp/persist-pydesc/py', '/private/tmp/persist-pydesc/tools/rvm.py', d, s, nc], capture_output=True, text=True)
        try: res[d].append(json.loads(p.stdout.strip().splitlines()[-1]))
        except Exception: print('FAILED', d, p.stdout[-200:], p.stderr[-300:]); continue
        print(json.dumps(res[d][-1]), flush=True)
print()
base = None
for d in dirs:
    rs = res[d]
    if not rs: continue
    w = statistics.median(x['wall'] for x in rs); sc = statistics.median(x['self_cpu'] for x in rs); cc = statistics.median(x['child_cpu'] for x in rs)
    lo = statistics.median(x['load0'] for x in rs)
    base = base or (w, sc, cc)
    print(f"{d.split('/')[-1]:8s} wall {w:7.2f}s ({base[0]/w:5.2f}x)  python-cpu {sc:7.2f}s ({base[1]/max(sc,1e-9):5.1f}x)  child-cpu {cc:7.2f}s  load {lo:.1f}  n={len(rs)}")
