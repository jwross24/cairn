import json, os, sys, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import runbin

HERE = runbin.HERE
REF = {}
refp = os.path.join(HERE, "logs", "ref228.jsonl")
if os.path.exists(refp):
    for l in open(refp):
        r = json.loads(l)
        REF[r["eq"]] = r
GATE = {}
for l in open(os.path.join(HERE, "..", "..", "join24swap", "gate.jsonl")):
    r = json.loads(l)
    if r["phase"] == "diff" and r["level"] == "24":
        GATE[r["eq"]] = r


def one(binary, tag, eq, env):
    res = runbin.run(binary, eq, tag, env=env)
    errp = os.path.join(runbin.OUT, f"{eq}_L24.{tag}.err")
    err = open(errp).read().splitlines()
    summ = [l for l in err if l.startswith("parents ")]
    summ = summ[-1] if summ else ""
    ref = REF.get(eq)
    ok = None
    if ref:
        ok = (ref["sha"] == res["sha"]) and res["rc"] == ref["rc"]
        sig = {}
        t = summ.split()
        for i in range(0, len(t), 2):
            if t[i + 1].lstrip("-").isdigit():
                sig[t[i]] = int(t[i + 1])
        keys = ("children", "open", "exact") + (() if os.environ.get("IGNORE_TD") else ("tail-dead",))
        ok = ok and all(ref["sig"].get(k) == sig.get(k) for k in keys)
    else:
        ok = GATE[eq]["sha_ref"] == res["sha"][:16]
    return dict(eq=eq, tag=tag, ok=ok, cpu=res["cpu"], n=res["n"], rc=res["rc"], sha=res["sha"], summ=summ)


if __name__ == "__main__":
    binary = sys.argv[1]
    tag = sys.argv[2]
    envs = dict(kv.split("=", 1) for kv in sys.argv[3].split(",") if "=" in kv)
    for eq in sys.argv[4:]:
        r = one(binary, tag, eq, envs)
        print(json.dumps(dict(eq=eq, ok=r["ok"], cpu=round(r["cpu"], 3), n=r["n"], rc=r["rc"])))
