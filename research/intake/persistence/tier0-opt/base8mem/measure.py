import sys, os, json, subprocess, time, resource, signal
LIMIT_KB = 8 * 1024 * 1024
if len(sys.argv) > 1 and sys.argv[1] == "child":
    srcdir, s, outp = sys.argv[2], int(sys.argv[3]), sys.argv[4]
    sys.dont_write_bytecode = True
    sys.path.insert(0, srcdir)
    sys.argv = ["run_base_mp.py", "8", "70", "12,24,48,96", "/dev/null", "1"]
    import run_base_mp as R
    t = dict((v[1], v[0]) for v in R.verts)[s]
    rec = R.do_vertex((t, s))
    json.dump(rec, open(outp, "w"))
    sys.exit(0)
srcdir, s, outp = sys.argv[1], sys.argv[2], sys.argv[3]
env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
p = subprocess.Popen([sys.executable, __file__, "child", srcdir, s, outp], env=env)
peak = 0; killed = False; t0 = time.time()
while p.poll() is None:
    time.sleep(0.5)
    try:
        r = int(subprocess.run(["ps", "-o", "rss=", "-p", str(p.pid)], capture_output=True, text=True).stdout.strip() or 0)
    except Exception:
        r = 0
    peak = max(peak, r)
    if r > LIMIT_KB:
        p.kill(); killed = True; break
p.wait()
print(json.dumps(dict(s=int(s), src=srcdir, peak_rss_mb=round(peak / 1024), killed=killed, wall=round(time.time() - t0), rc=p.returncode)), flush=True)
