import sys, threading, time, tracemalloc
sys.dont_write_bytecode = True
srcdir, s = sys.argv[1], int(sys.argv[2])
sys.path.insert(0, srcdir)
sys.argv = ["run_base_mp.py", "8", "70", "12,24,48,96", "/dev/null", "1"]
import run_base_mp as R
t = dict((v[1], v[0]) for v in R.verts)[s]
tracemalloc.start(1)
best = [0, None]
stop = False
def watch():
    while not stop:
        time.sleep(10)
        cur, _ = tracemalloc.get_traced_memory()
        if cur > best[0]:
            best[0] = cur; best[1] = tracemalloc.take_snapshot()
th = threading.Thread(target=watch, daemon=True); th.start()
rec = R.do_vertex((t, s))
stop = True
print("secs", rec['secs'], "peak traced MB", tracemalloc.get_traced_memory()[1] // 2**20, "snapshot MB", best[0] // 2**20)
for st in best[1].statistics('lineno')[:8]: print(st)
