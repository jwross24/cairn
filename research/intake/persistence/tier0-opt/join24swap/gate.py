import hashlib
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, "lvlN_prod_ref")
NEW = os.path.join(HERE, "lvlN")
MUT = os.path.join(HERE, "lvlN_mut")
ASAN = os.path.join(HERE, "lvlN_asan")
CORPUS = "/private/tmp/claude-501/-Users-jwross-Documents-cairn/ec9f8f52-ce29-4a5c-9caf-2ecbd434509f/scratchpad/h12"
OUT = os.path.join(HERE, "runs")
TIMEOUT = float(os.environ.get("GATE_TIMEOUT", "1200"))
KEYS = ("tail-dead", "open", "exact")
os.makedirs(OUT, exist_ok=True)


def run(binary, cfg, par, tag, env=None):
    e = dict(os.environ)
    e.update(env or {})
    outp, errp = os.path.join(OUT, tag + ".out"), os.path.join(OUT, tag + ".err")
    with open(outp, "w") as fo, open(errp, "w") as fe:
        proc = subprocess.Popen(["nice", "-n", "10", binary, cfg, par], stdout=fo, stderr=fe, env=e)
        _, status, ru = os.wait4(proc.pid, 0)
    rc = os.waitstatus_to_exitcode(status)
    cpu = ru.ru_utime + ru.ru_stime
    lines = sorted(line for line in open(outp) if line.strip())
    stderr = open(errp).read()
    parts = stderr.split()
    stats = {}
    for k, v in zip(parts[0::2], parts[1::2]):
        try:
            stats[k] = int(v)
        except ValueError:
            pass
    sha = lambda ls: hashlib.sha256("".join(ls).encode()).hexdigest()
    return {
        "rc": rc, "cpu": cpu, "n": len(lines), "sha": sha(lines),
        "open_sha": sha([l for l in lines if l.startswith("OPEN")]),
        "exact_sha": sha([l for l in lines if l.startswith("EXACT")]),
        "sig": [stats.get(k) for k in KEYS], "children": stats.get("children"), "parents": stats.get("parents"),
    }


def same(a, b):
    return a["rc"] == b["rc"] and a["sha"] == b["sha"] and a["open_sha"] == b["open_sha"] and a["exact_sha"] == b["exact_sha"] and a["sig"] == b["sig"]


def paths(name, level):
    d = os.path.join(CORPUS, name)
    return os.path.join(d, f"cfgL{level}.txt"), os.path.join(d, f"parents{level}.txt")


def eq_a(name):
    return int(open(paths(name, 24)[0]).readline().split()[2])


def items(levels):
    out = []
    for name in sorted(os.listdir(CORPUS)):
        for level in levels:
            cfg, par = paths(name, level)
            if os.path.exists(cfg) and os.path.exists(par) and os.path.getsize(par) > 0:
                out.append((name, level))
    return out


def job_diff(item):
    name, level = item
    cfg, par = paths(name, level)
    base = f"{name}_L{level}"
    ref = run(REF, cfg, par, base + ".ref")
    new = run(NEW, cfg, par, base + ".new")
    row = {"phase": "diff", "eq": name, "level": level, "A": eq_a(name), "rc": [ref["rc"], new["rc"]], "identical": same(ref, new),
           "lines": [ref["n"], new["n"]], "sig_ref": ref["sig"], "sig_new": new["sig"], "children": [ref["children"], new["children"]],
           "sha_ref": ref["sha"][:16], "sha_new": new["sha"][:16], "cpu_ref": round(ref["cpu"], 3), "cpu_new": round(new["cpu"], 3),
           "count": sum(x or 0 for x in ref["sig"][1:])}
    if level == "24":
        m1 = run(MUT, cfg, par, base + ".m1", {"JOIN_MUTANT": "3"})
        m2 = run(MUT, cfg, par, base + ".m2", {"JOIN_MUTANT": "2"})
        row["m1_caught"] = not same(ref, m1)
        row["m2_caught"] = not same(ref, m2)
        if not row["m2_caught"] and row["count"] > 0:
            row["m2_forced"] = {}
            for fs in range(0, 8):
                m = run(MUT, cfg, par, base + f".m2f{fs}", {"JOIN_MUTANT": "2", "JOIN_FORCE_SET": str(fs)})
                row["m2_forced"][fs] = not same(ref, m)
    return row


def job_mut(item):
    name, level = item
    cfg, par = paths(name, level)
    base = f"{name}_L{level}"
    new = run(NEW, cfg, par, base + ".new")
    row = {"phase": "mut", "eq": name, "level": level, "A": eq_a(name), "count": sum(x or 0 for x in new["sig"][1:]), "against": "new"}
    m1 = run(MUT, cfg, par, base + ".m1", {"JOIN_MUTANT": "3"})
    m2 = run(MUT, cfg, par, base + ".m2", {"JOIN_MUTANT": "2"})
    row["m1_caught"] = not same(new, m1)
    row["m2_caught"] = not same(new, m2)
    row["m2_forced"] = {}
    if not row["m2_caught"] and row["count"] > 0:
        for fs in range(0, 8):
            m = run(MUT, cfg, par, base + f".m2f{fs}", {"JOIN_MUTANT": "2", "JOIN_FORCE_SET": str(fs)})
            row["m2_forced"][fs] = not same(new, m)
    return row


def job_force(item):
    name, level = item
    cfg, par = paths(name, level)
    base = f"{name}_L{level}"
    ref = run(REF, cfg, par, base + ".ref")
    res = {}
    for fs in range(0, 8):
        m = run(MUT, cfg, par, base + f".f{fs}", {"JOIN_FORCE_SET": str(fs)})
        res[fs] = same(ref, m)
    return {"phase": "force", "eq": name, "level": level, "A": eq_a(name), "identical_by_forced_set": res, "count": sum(x or 0 for x in ref["sig"][1:])}


def job_asan(item):
    name, level = item
    cfg, par = paths(name, level)
    a = eq_a(name)
    if a >= 64 and level == "24":
        src = par
    else:
        src = os.path.join(OUT, f"{name}_L{level}.head")
        with open(par) as s, open(src, "w") as t:
            for i, line in enumerate(s):
                if i >= 300:
                    break
                t.write(line)
    proc = subprocess.run(["nice", "-n", "10", ASAN, cfg, src], capture_output=True, text=True, timeout=TIMEOUT * 4)
    key_full = src == par
    san = "AddressSanitizer" in proc.stderr or "runtime error" in proc.stderr
    return {"phase": "asanfull" if key_full else "asan", "eq": name, "level": level, "A": a, "full": src == par, "rc": proc.returncode, "sanitizer_report": san}


def main():
    phase = sys.argv[1]
    workers = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    log_path = os.path.join(HERE, "gate.jsonl")
    done = set()
    if os.path.exists(log_path):
        for r in map(json.loads, open(log_path)):
            done.add((r["phase"], r["eq"], r["level"]))
    if phase == "diff24":
        todo, fn = items(("24",)), job_diff
        key = "diff"
    elif phase == "diff4896":
        todo, fn = items(("48", "96")), job_diff
        key = "diff"
    elif phase == "mut24":
        todo, fn, key = items(("24",)), job_mut, "mut"
    elif phase == "asanfull":
        todo, fn, key = [t for t in items(("24",)) if eq_a(t[0]) >= 64], job_asan, "asanfull"
    elif phase == "force":
        todo = items(("24",))[:: max(1, len(items(("24",))) // 30)]
        fn, key = job_force, "force"
    elif phase == "asan":
        todo, fn, key = items(("24", "48", "96")), job_asan, "asan"
    else:
        raise SystemExit("phase")
    todo = [t for t in todo if (key, t[0], t[1]) not in done]
    with open(log_path, "a") as log, ThreadPoolExecutor(workers) as pool:
        for row in pool.map(fn, todo):
            log.write(json.dumps(row) + "\n")
            log.flush()


main()
