"""memrun.py <srcdir> <s> <ncores> : run_vertex_c with RSS sampling; prints RSS after each finished equation"""
import sys, os, subprocess, threading, time, json
src, s, nc = sys.argv[1], sys.argv[2], sys.argv[3]
known = open(f'/private/tmp/persist-pydesc/known{s}.txt').read().strip()
t0 = time.time()
p = subprocess.Popen([sys.executable, 'run_vertex_c.py', s, known, nc], cwd=src, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
samples = []; rows = []
def rss():
    try: return int(subprocess.run(['ps', '-o', 'rss=', '-p', str(p.pid)], capture_output=True, text=True).stdout.strip() or 0) / 1024
    except Exception: return 0
def reader():
    for ln in p.stdout:
        if ln.startswith('{') and '"M"' in ln: rows.append((time.time() - t0, rss(), json.loads(ln)['npat']))
th = threading.Thread(target=reader); th.start()
while p.poll() is None:
    samples.append(rss()); time.sleep(0.5)
th.join()
print(f'{os.path.basename(src)} wall {time.time()-t0:.1f}s peak RSS {max(samples):.0f} MB over {len(samples)} samples')
for i, (t, r, n) in enumerate(rows): print(f'  eq {i+1:2d} done at {t:6.1f}s  rss {r:6.0f} MB  npat {n:.2e}')
