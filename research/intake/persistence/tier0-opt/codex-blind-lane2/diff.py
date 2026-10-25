import hashlib, json, os, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__))
C = "/private/tmp/claude-501/-Users-jwross-Documents-cairn/ec9f8f52-ce29-4a5c-9caf-2ecbd434509f/scratchpad/h12"
REF = os.path.join(HERE, "..", "join24swap", "lvlN")
OUT = os.path.join(HERE, "runs"); os.makedirs(OUT, exist_ok=True)

def run(binary, cfg, par, tag, env=None):
    e = dict(os.environ); e.update(env or {})
    op, ep = f"{OUT}/{tag}.out", f"{OUT}/{tag}.err"
    t = time.time()
    with open(op, "w") as fo, open(ep, "w") as fe:
        rc = subprocess.run(["nice", "-n", "10", binary, cfg, par], stdout=fo, stderr=fe, env=e).returncode
    raw = open(op, "rb").read()
    lines = sorted(raw.splitlines(keepends=True))
    srt = b"".join(lines)
    st = open(ep).read().split(); stats = {}
    for k, v in zip(st[0::2], st[1::2]):
        if v.lstrip("-").isdigit(): stats[k] = int(v)
    return dict(rc=rc, len=len(srt), sha=hashlib.sha256(srt).hexdigest(), n=len(lines),
                nopen=sum(l.startswith(b"OPEN") for l in lines), nexact=sum(l.startswith(b"EXACT") for l in lines),
                ctr=[stats.get(k) for k in ("parents", "children", "open", "exact")], secs=round(time.time() - t, 1))

def main():
    binary, label = sys.argv[1], sys.argv[2]
    env = {}
    for kv in sys.argv[3:]:
        k, v = kv.split("=", 1); env[k] = v
    eqs = [d for d in sorted(os.listdir(C)) if os.path.exists(f"{C}/{d}/cfgL24.txt") and os.path.exists(f"{C}/{d}/parents24.txt") and os.path.getsize(f"{C}/{d}/parents24.txt") > 0]
    assert len(eqs) == 228
    stride = int(os.environ.get("STRIDE", "1")); eqs = eqs[::stride]
    refcache = f"{HERE}/ref_cache.json"
    rc_ = json.load(open(refcache)) if os.path.exists(refcache) else {}
    def job(d):
        cfg, par = f"{C}/{d}/cfgL24.txt", f"{C}/{d}/parents24.txt"
        if d not in rc_: rc_[d] = run(REF, cfg, par, f"{d}.ref")
        r = rc_[d]; b = run(binary, cfg, par, f"{d}.{label}", env)
        same = r["rc"] == b["rc"] == 0 and r["sha"] == b["sha"] and r["len"] == b["len"] and r["ctr"] == b["ctr"] and b["nopen"] == b["ctr"][2] and b["nexact"] == b["ctr"][3]
        return dict(eq=d, same=same, ref=r, new=b)
    with ThreadPoolExecutor(2) as ex: rows = list(ex.map(job, eqs))
    if stride == 1: json.dump(rc_, open(refcache, "w"))
    with open(f"{HERE}/diff_{label}.jsonl", "w") as f:
        for r in rows: f.write(json.dumps(r) + "\n")
    ok = sum(r["same"] for r in rows)
    nonempty = sum(r["ref"]["n"] > 0 for r in rows)
    diffs = [r for r in rows if not r["same"]]
    print(label, f"match {ok}/{len(rows)} nonempty_ref {nonempty} diffs {[(r['eq'], r['ref']['rc'], r['new']['rc'], r['ref']['sha'][:12], r['new']['sha'][:12]) for r in diffs][:40]}")
    print("secs total ref", sum(r['ref']['secs'] for r in rows), "new", sum(r['new']['secs'] for r in rows))
main()
