import json, os, re, signal, subprocess, sys, threading
from concurrent.futures import ThreadPoolExecutor

BIN = "/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/tierc-r2shadow/cport_r2c"
SHADOW = "/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/tierc-r2shadow/data/"
HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
RSS_LIMIT_KB = int(float(os.environ.get("R2_RSS_GB", "4")) * 1024 * 1024)
CPU_LIMIT_S = float(os.environ.get("R2_CPU_S", "7200"))
RAISED = ["--mitm-space-cap", "1e30", "--mitm-right-cap", "1e14"]
wait_evt = threading.Event()
lock = threading.Lock()


def ps_field(pid, field):
    r = subprocess.run(["ps", "-o", field + "=", "-p", str(pid)], capture_output=True, text=True)
    return r.stdout.strip()


def cpu_seconds(s):
    if not s:
        return 0.0
    parts = s.split(":")
    t = 0.0
    for p in parts:
        t = t * 60 + float(p)
    return t


def run_one(rep, utable, out, raised):
    cmd = ["nice", "-n", "10", BIN, "shadow480", "--rep-file", rep, "--lattice", SHADOW + "lattice96.txt",
           "--levelprimes", SHADOW + "levelprimes480.txt", "--utable", utable] + (RAISED if raised else [])
    with open(out, "x") as fo:
        p = subprocess.Popen(cmd, stdout=fo, stderr=subprocess.STDOUT, start_new_session=True)
    reason = None
    peak = 0
    last_cpu = 0.0
    while True:
        r = os.wait4(p.pid, os.WNOHANG)
        if r[0] != 0:
            ru = r[2]
            return {"rc": os.waitstatus_to_exitcode(r[1]), "cpu": ru.ru_utime + ru.ru_stime, "maxrss_mb": ru.ru_maxrss / 1e6, "killed": reason, "cmd": " ".join(cmd)}
        inner = None
        kids = subprocess.run(["pgrep", "-P", str(p.pid)], capture_output=True, text=True).stdout.split()
        targets = [int(x) for x in kids] or [p.pid]
        rss = max(int(ps_field(t, "rss") or 0) for t in targets)
        cpu = max(cpu_seconds(ps_field(t, "time")) for t in targets)
        peak = max(peak, rss)
        last_cpu = max(last_cpu, cpu)
        if reason is None and (rss > RSS_LIMIT_KB or cpu > CPU_LIMIT_S):
            reason = "rss" if rss > RSS_LIMIT_KB else "cpu"
            for t in targets:
                os.kill(t, signal.SIGKILL)
            os.kill(p.pid, signal.SIGKILL)
        wait_evt.wait(0.5)


def parse(out):
    t = open(out).read()
    v = re.search(r"^VERDICT (.*)$", t, re.M)
    d = re.search(r"^BUDGET detail: (.*)$", t, re.M)
    sp = re.search(r"space=([\d.e+]+)", t)
    return (v.group(1) if v else None), (d.group(1) if d else None), (sp.group(1) if sp else None)


def label(v, killed):
    if killed:
        return "BUDGET"
    if v is None:
        return "ERROR"
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
    jid, utable, tag, mode = args
    rep = HERE + "data/rep_" + jid + ".rep"
    out1 = HERE + "runs/" + tag + "_" + jid + "_def.txt"
    res = {"id": jid, "tag": tag}
    if mode in ("def", "defonly"):
        r = run_one(rep, utable, out1, False)
        v, d, sp = parse(out1)
        lab = label(v, r["killed"])
        res.update({"stage": "default", "label": lab, "verdict": v, "budget_detail": d, "space": sp, "cpu_s": r["cpu"], "maxrss_mb": r["maxrss_mb"], "killed": r["killed"], "cmd": r["cmd"]})
        if mode == "def" and lab == "BUDGET" and not r["killed"]:
            out2 = HERE + "runs/" + tag + "_" + jid + "_raised.txt"
            r2 = run_one(rep, utable, out2, True)
            v2, d2, sp2 = parse(out2)
            lab2 = label(v2, r2["killed"])
            res.update({"stage": "raised", "label": lab2, "verdict": v2, "budget_detail": d2, "space": sp2, "cpu_s": r2["cpu"] + r["cpu"], "maxrss_mb": r2["maxrss_mb"], "killed": r2["killed"], "cmd": r2["cmd"]})
    else:
        r = run_one(rep, utable, out1, True)
        v, d, sp = parse(out1)
        res.update({"stage": "raised", "label": label(v, r["killed"]), "verdict": v, "budget_detail": d, "space": sp, "cpu_s": r["cpu"], "maxrss_mb": r["maxrss_mb"], "killed": r["killed"], "cmd": r["cmd"]})
    with lock:
        with open(HERE + "results_" + tag + ".jsonl", "a") as f:
            f.write(json.dumps(res) + "\n")
    return res


if __name__ == "__main__":
    jobsf, utable, tag, mode = sys.argv[1:5]
    ids = [l.split()[0] for l in open(jobsf) if l.strip()]
    nw = int(os.environ.get("R2_WORKERS", "2"))
    with ThreadPoolExecutor(nw) as ex:
        for r in ex.map(job, [(i, utable, tag, mode) for i in ids]):
            print(r["id"], r["label"], round(r["cpu_s"], 1), r["maxrss_mb"], flush=True)
