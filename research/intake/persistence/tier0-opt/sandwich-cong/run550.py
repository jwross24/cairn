import json, os, resource, signal, subprocess, sys, threading, time
B = "/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/"
HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
SH = B + "tierc-r2shadow/data/"
RB = B + "tierc-r2bill/data/"
tag = sys.argv[1]
extra = sys.argv[2:]
RSS_KB = 2 * 1024 * 1024
CPU_LIMIT = 3600.0
ev = threading.Event()
ids = []
for f in ("ids_all.txt", "ids_b3.txt", "ids_o1.txt"):
    ids += [l.strip() for l in open(RB + f) if l.strip()]
ids = sorted(set(ids))
os.makedirs(HERE + "runs/" + tag, exist_ok=True)
rf = HERE + "res_%s.jsonl" % tag
done = set()
if os.path.exists(rf):
    for l in open(rf):
        try: done.add(json.loads(l)["id"])
        except Exception: pass
out = open(rf, "a")

def rss_cpu(pid):
    r = subprocess.run(["ps", "-o", "rss=,time=", "-p", str(pid)], capture_output=True, text=True).stdout.split()
    if len(r) < 2: return 0, 0.0
    t = 0.0
    for x in r[1].split(":"): t = t * 60 + float(x)
    return int(r[0]), t

for i in ids:
    if i in done: continue
    of = HERE + "runs/%s/%s.txt" % (tag, i)
    cmd = ["nice", "-n", "10", HERE + "cport_cong", "shadow480", "--rep-file", RB + "rep_%s.rep" % i,
           "--lattice", SH + "lattice96.txt", "--levelprimes", SH + "levelprimes480.txt", "--utable", RB + "utable_u2_k34.txt"] + extra
    t0 = time.time()
    with open(of, "w") as fo:
        p = subprocess.Popen(cmd, stdout=fo, stderr=subprocess.STDOUT, start_new_session=True)
        pid, _, ru = None, None, None
        killed = None; peak = 0
        while True:
            r = os.wait4(p.pid, os.WNOHANG)
            if r[0] != 0:
                ru = r[2]; rc = os.waitstatus_to_exitcode(r[1]); break
            kids = subprocess.run(["pgrep", "-P", str(p.pid)], capture_output=True, text=True).stdout.split()
            tg = [int(x) for x in kids] or [p.pid]
            for t in tg:
                rss, cpu = rss_cpu(t)
                peak = max(peak, rss)
                if killed is None and (rss > RSS_KB or cpu > CPU_LIMIT):
                    killed = "rss" if rss > RSS_KB else "cpu"
                    os.kill(t, signal.SIGKILL)
            ev.wait(0.3)
    out.write(json.dumps({"id": i, "rc": rc, "cpu": ru.ru_utime + ru.ru_stime, "maxrss_mb": ru.ru_maxrss / 1e6, "killed": killed, "wall": time.time() - t0}) + "\n"); out.flush()
print("done")
