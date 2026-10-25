import json, os, re, signal, subprocess, sys, threading, time
from concurrent.futures import ThreadPoolExecutor

P = "/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/"
BIN = os.environ.get("TB_BIN", P + "tierc-r2shadow/cport_r2c")
EXTRA = os.environ.get("TB_FLAGS", "").split()
SH = P + "tierc-r2shadow/data/"
HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
RSS_LIMIT_KB = int(float(os.environ.get("TB_RSS_GB", "3")) * 1024 * 1024)
CPU_LIMIT_S = float(os.environ.get("TB_CPU_S", "7200"))
RAISED = ["--mitm-space-cap", "1e30", "--mitm-right-cap", "1e14"]
wait_evt = threading.Event()
lock = threading.Lock()


def ps_field(pid, field):
    return subprocess.run(["ps", "-o", field + "=", "-p", str(pid)], capture_output=True, text=True).stdout.strip()


def cpu_seconds(s):
    t = 0.0
    for p in (s.split(":") if s else []):
        t = t * 60 + float(p)
    return t


def run_one(rep, utable, out, raised):
    cmd = ["nice", "-n", "10", BIN, "shadow480", "--rep-file", rep, "--lattice", SH + "lattice96.txt",
           "--levelprimes", SH + "levelprimes480.txt", "--utable", utable] + EXTRA + (RAISED if raised else [])
    with open(out, "w") as fo:
        p = subprocess.Popen(cmd, stdout=fo, stderr=subprocess.STDOUT, start_new_session=True)
    reason = None
    last_ps = time.monotonic()
    while True:
        r = os.wait4(p.pid, os.WNOHANG)
        if r[0] != 0:
            ru = r[2]
            return {"rc": os.waitstatus_to_exitcode(r[1]), "cpu": ru.ru_utime + ru.ru_stime, "maxrss_mb": ru.ru_maxrss / 1e6, "killed": reason}
        if time.monotonic() - last_ps < 0.25:
            wait_evt.wait(0.003)
            continue
        last_ps = time.monotonic()
        kids = subprocess.run(["pgrep", "-P", str(p.pid)], capture_output=True, text=True).stdout.split()
        targets = [int(x) for x in kids] or [p.pid]
        rss = max(int(ps_field(t, "rss") or 0) for t in targets)
        cpu = max(cpu_seconds(ps_field(t, "time")) for t in targets)
        if reason is None and (rss > RSS_LIMIT_KB or cpu > CPU_LIMIT_S):
            reason = "rss" if rss > RSS_LIMIT_KB else "cpu"
            for t in targets:
                os.kill(t, signal.SIGKILL)
            os.kill(p.pid, signal.SIGKILL)


def parse(out):
    t = open(out).read()
    v = re.search(r"^VERDICT (.*)$", t, re.M)
    d = re.search(r"^BUDGET detail: (.*)$", t, re.M)
    sp = re.search(r"space=([\d.e+]+)", t)
    return (v.group(1) if v else None), (d.group(1) if d else None), (sp.group(1) if sp else None), t


def label(v, killed, text):
    if killed:
        return "BUDGET"
    if v is None:
        return "BUDGET" if "FATAL" in text else "ERROR"
    if v.startswith("CLOSED-cut"):
        return "closed by the cut"
    if v.startswith("CLOSED-sandwich"):
        return "closed by the sandwich (U'')"
    if v.startswith("BUDGET"):
        return "BUDGET"
    if v.startswith("NOTAPPL"):
        return "NOTAPPL"
    return "open"


def job(args):
    jid, line, utable, tag, mode, outdir = args
    t = line.split()
    y, k, nu, a, n = t[0], t[1], t[2], t[3], t[4]
    rep = outdir + "/rep_" + jid + ".rep"
    with open(rep, "w") as f:
        f.write(" ".join([y, nu, n] + t[5:]) + "\n")
    out1 = outdir + "/" + jid + "_def.txt"
    res = {"id": jid, "tag": tag, "y": y, "k_wrap": int(k), "nu": int(nu), "a": int(a), "n": int(n)}
    r = run_one(rep, utable, out1, mode == "raised")
    v, d, sp, text = parse(out1)
    lab = label(v, r["killed"], text)
    res.update({"stage": "default", "label": lab, "verdict": v, "budget_detail": d, "space": sp, "cpu_s": r["cpu"], "maxrss_mb": r["maxrss_mb"], "killed": r["killed"]})
    if mode == "def" and lab == "BUDGET" and not r["killed"]:
        out2 = outdir + "/" + jid + "_raised.txt"
        r2 = run_one(rep, utable, out2, True)
        v2, d2, sp2, text2 = parse(out2)
        res.update({"stage": "raised", "label": label(v2, r2["killed"], text2), "verdict": v2, "budget_detail": d2, "space": sp2, "cpu_s": r2["cpu"] + r["cpu"], "maxrss_mb": max(r2["maxrss_mb"], r["maxrss_mb"]), "killed": r2["killed"]})
    with lock:
        with open(HERE + "results_" + tag + ".jsonl", "a") as f:
            f.write(json.dumps(res) + "\n")
    return res


if __name__ == "__main__":
    infile, utable, tag, mode = sys.argv[1:5]
    outdir = HERE + "runs/" + tag
    os.makedirs(outdir, exist_ok=True)
    lines = [l for l in open(infile) if l.strip() and not l.startswith("T")]
    nw = int(os.environ.get("TB_WORKERS", "2"))
    jobs = [("%s%05d" % (tag, i), l, utable, tag, mode, outdir) for i, l in enumerate(lines)]
    with ThreadPoolExecutor(nw) as ex:
        for r in ex.map(job, jobs):
            print(r["id"], r["label"], round(r["cpu_s"], 2), round(r["maxrss_mb"]), flush=True)
