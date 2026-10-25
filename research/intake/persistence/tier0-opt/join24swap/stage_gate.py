import hashlib
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "stage_gate.jsonl")
UV = ["uv", "run", "--no-project", "--with", "gmpy2", "--with", "sympy", "python"]


def rec(row):
    with open(LOG, "a") as f:
        f.write(json.dumps(row) + "\n")
    print(json.dumps(row)[:300], flush=True)


def sh(args, cwd, outp, errp):
    t0 = time.time()
    with open(outp, "w") as fo, open(errp, "w") as fe:
        p = subprocess.run(["nice", "-n", "10"] + args, cwd=cwd, stdout=fo, stderr=fe)
    return p.returncode, round(time.time() - t0, 1)


def difftests():
    d = os.path.join(HERE, "stage_new")
    for spec in (("72", "98,189,294,1161216"), ("10800", "11519532122112"), ("6", "16,32,111132"), ("224", "784,2744,41472,71442,122472"), ("162", "93312")):
        out = os.path.join(HERE, "runs", f"difftest_{spec[0]}.out")
        rc, secs = sh(UV + ["difftest.py", spec[0], spec[1]], d, out, os.path.join(HERE, "runs", f"difftest_{spec[0]}.err"))
        rec({"stage": "difftest", "vertex": spec[0], "rc": rc, "secs": secs, "out": open(out).read().strip()[:400]})


def vertex_pair(vertex, known, names=("ref", "new")):
    res = {}
    for name in names:
        d = os.path.join(HERE, "stage_" + name)
        log = os.path.join(d, "lvlN_calls.log")
        if os.path.exists(log):
            os.rename(log, log + f".{int(time.time())}")
        out = os.path.join(HERE, "runs", f"v{vertex}_{name}.jsonl")
        rc, secs = sh(UV + ["run_vertex_c.py", vertex, known, "3"], d, out, os.path.join(HERE, "runs", f"v{vertex}_{name}.err"))
        rows = []
        for line in open(out):
            if line.startswith("{"):
                r = json.loads(line)
                r.pop("secs", None)
                rows.append(json.dumps(r, sort_keys=True))
        calls = sorted(open(log).read().split("\n")) if os.path.exists(log) else []
        res[name] = (rc, secs, rows, calls)
    same_rows = res[names[0]][2] == res[names[1]][2]
    same_calls = res[names[0]][3] == res[names[1]][3]
    ncalls = len([c for c in res[names[1]][3] if c])
    rec({"stage": "vertex_" + names[1], "vertex": vertex, "rc": [res[names[0]][0], res[names[1]][0]], "secs": [res[names[0]][1], res[names[1]][1]], "rows": len(res[names[1]][2]),
         "rows_identical": same_rows, "lvlN_calls": ncalls, "lvlN_call_outputs_identical": same_calls and ncalls > 0,
         "rows_sha": hashlib.sha256("".join(res[names[1]][2]).encode()).hexdigest()[:16]})


def eq6():
    outs = {}
    for name in ("ref", "new"):
        d = os.path.join(HERE, "stage_" + name)
        out = os.path.join(HERE, "runs", f"eq6_{name}.jsonl")
        rc, secs = sh(UV + ["eq_golden.py", out, "3"], d, os.path.join(HERE, "runs", f"eq6_{name}.stdout"), os.path.join(HERE, "runs", f"eq6_{name}.err"))
        outs[name] = (rc, secs, sorted(json.dumps({k: v for k, v in json.loads(l).items() if k != "secs"}, sort_keys=True) for l in open(out)))
    rec({"stage": "eq6", "rc": [outs["ref"][0], outs["new"][0]], "secs": [outs["ref"][1], outs["new"][1]], "identical": outs["ref"][2] == outs["new"][2], "rows": len(outs["new"][2])})


if __name__ == "__main__":
    what = sys.argv[1]
    if what == "difftest":
        difftests()
    elif what == "v14336":
        vertex_pair("14336", "")
    elif what == "neg":
        os.environ["JOIN_MUTANT"] = "3"
        vertex_pair("14336", "", ("ref", "neg"))
    elif what == "golden":
        for v, k in (("4", "14"), ("14", "27,72"), ("27", ""), ("98", ""), ("189", ""), ("294", ""), ("72", "98,189,294,1161216")):
            vertex_pair(v, k)
        eq6()
