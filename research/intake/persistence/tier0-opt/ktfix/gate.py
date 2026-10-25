import hashlib
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
PROD = os.path.normpath(os.path.join(HERE, "..", "..", "tier0", "lvlN"))
NEW = os.path.join(HERE, "lvlN")
ASAN = os.path.join(HERE, "lvlN_asan")
CORPUS = "/private/tmp/claude-501/-Users-jwross-Documents-cairn/ec9f8f52-ce29-4a5c-9caf-2ecbd434509f/scratchpad/h12"
OUT = os.path.join(HERE, "runs")
TIMEOUT = float(os.environ.get("GATE_TIMEOUT", "900"))
os.makedirs(OUT, exist_ok=True)


def run(binary, cfg, par, tag):
    path = os.path.join(OUT, tag)
    with open(path, "w") as out:
        try:
            proc = subprocess.run(["nice", "-n", "10", binary, cfg, par], stdout=out, stderr=subprocess.PIPE, text=True, timeout=TIMEOUT)
        except subprocess.TimeoutExpired:
            return None, None, None, ""
    lines = sorted(line for line in open(path) if line.strip())
    opens = {line for line in lines if line.startswith("OPEN")}
    return proc.returncode, hashlib.sha256("".join(lines).encode()).hexdigest(), opens, proc.stderr


def job(item):
    name, level = item
    d = os.path.join(CORPUS, name)
    cfg, par = os.path.join(d, f"cfgL{level}.txt"), os.path.join(d, f"parents{level}.txt")
    a = int(open(cfg).readline().split()[2])
    base = f"{name}_L{level}"
    p = run(PROD, cfg, par, base + ".prod")
    n = run(NEW, cfg, par, base + ".new")
    row = {"eq": name, "level": level, "A": a, "rc": [p[0], n[0]]}
    if p[0] is None or n[0] is None:
        row["verdict"] = "TIMEOUT"
        return row
    row["identical"] = p[1] == n[1]
    row["open"] = [len(p[2]), len(n[2])]
    row["new_open_not_in_prod"] = len(n[2] - p[2])
    if a >= 64:
        head = os.path.join(OUT, base + ".parents_head1")
        with open(par) as source, open(head, "w") as target:
            target.write(source.readline())
        try:
            asan = subprocess.run([ASAN, cfg, head], capture_output=True, text=True, timeout=TIMEOUT)
            row["asan_new"] = [asan.returncode, "AddressSanitizer" in asan.stderr]
            asan_ok = asan.returncode == 0
        except subprocess.TimeoutExpired:
            row["asan_new"] = ["timeout", None]
            asan_ok = False
        row["verdict"] = "OK-A64" if row["new_open_not_in_prod"] == 0 and n[0] == 0 and asan_ok else "FAIL"
    else:
        row["verdict"] = "OK" if row["identical"] and p[0] == n[0] == 0 else "FAIL"
    return row


items = []
for name in sorted(os.listdir(CORPUS)):
    for level in ("24", "48", "96"):
        d = os.path.join(CORPUS, name)
        cfg, par = os.path.join(d, f"cfgL{level}.txt"), os.path.join(d, f"parents{level}.txt")
        if os.path.exists(cfg) and os.path.exists(par) and os.path.getsize(par) > 0:
            items.append((name, level))
workers = int(sys.argv[1]) if len(sys.argv) > 1 else 2
log_path = os.path.join(HERE, "gate.jsonl")
done = set()
if os.path.exists(log_path):
    done = {(row["eq"], row["level"]) for row in map(json.loads, open(log_path))}
items = [item for item in items if item not in done]
with open(log_path, "a") as log, ThreadPoolExecutor(workers) as pool:
    for row in pool.map(job, items):
        log.write(json.dumps(row) + "\n")
        log.flush()
rows = [json.loads(line) for line in open(os.path.join(HERE, "gate.jsonl"))]
summary = {}
for row in rows:
    summary[row["verdict"]] = summary.get(row["verdict"], 0) + 1
print(json.dumps({"equations": len(rows), "verdicts": summary, "a64": [r for r in rows if r["A"] >= 64]}))
sys.exit(0 if summary.get("FAIL", 0) == 0 and summary.get("TIMEOUT", 0) == 0 else 1)
