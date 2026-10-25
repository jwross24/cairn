import json
import os
import re
import sys
import time
from collections import Counter

sys.dont_write_bytecode = True
TIER0 = "/Users/jwross/Documents/cairn/research/intake/persistence/tier0"
os.chdir(TIER0)
sys.path.insert(0, TIER0)

import classify_open as C
import deepcut as DC
from lattice import Coset

RUN = TIER0 + "/SANDWICH-run.txt"
FILES = [TIER0 + "/trees_mac.jsonl"]
LINE = re.compile(r"s=(\d+)\s+M=(\d+)\s+a=(\d+) y=(\d+)\s+k=(\d+) log10 U=([\d.]+) reps=(\d+) -> (\w+) (\[.*\]) \[")
MAXCASES = 2_000_000


def recorded():
    out = []
    for line in open(RUN):
        m = LINE.match(line)
        if not m:
            continue
        s, mm, a, y, k, u, reps, verdict, rest = m.groups()
        out.append({"key": (s, mm, a, y), "k": int(k), "a": int(a), "logU": float(u), "verdicts": eval(rest)})
    return out


def main(out_path, only_depth_lt=None, control_every=0):
    rec = recorded()
    by_key = {}
    for r in rec:
        by_key.setdefault(r["key"], []).append(r)
    lam = DC.kernel_lattice()
    seen = set()
    done = set()
    if os.path.exists(out_path):
        for line in open(out_path):
            done.add(json.loads(line)["idx"])
    matched = 0
    t0 = time.time()
    order = []
    for f in FILES:
        for (s, M, a, nu, eps, y, sol) in C.entries(f):
            key = (str(s), "".join(map(str, M)), str(a), str(y))
            fullkey = key + (nu, None if eps is None else tuple(eps))
            if key not in by_key or fullkey in seen:
                continue
            seen.add(fullkey)
            order.append((key, s, M, a, nu, eps, y))
    used = Counter()
    jobs = []
    for (key, s, M, a, nu, eps, y) in order:
        i = used[key]
        used[key] += 1
        if i >= len(by_key[key]):
            continue
        jobs.append((by_key[key][i], s, M, a, nu, eps, y))
    print(f"matched {len(jobs)} of {len(rec)} recorded patterns", flush=True)
    jobs.sort(key=lambda j: (max([v[1] for v in j[0]["verdicts"] if v[0] == "CLOSED-sandwich"] or [1]), j[0]["k"]))
    for idx, (r, s, M, a, nu, eps, y) in enumerate(jobs):
        if idx in done:
            continue
        fct = C.factor237(y)
        co0 = Coset((fct[1], fct[2]), lam.u1, lam.u2)
        reps = DC.all_representations(M, y)
        if nu is not None:
            reps = [x for x in reps if x[0] == nu and Counter(e for _, e in x[1]) == Counter(e % 96 for e in eps)]
        assert len(reps) == len(r["verdicts"]), (r["key"], len(reps), len(r["verdicts"]))
        per_rep = []
        for rep, ver in zip(reps, r["verdicts"]):
            entry = {"recorded": [ver[0], ver[1]] + ([ver[3]] if len(ver) > 3 else [])}
            bounds = {}
            if ver[0] == "CLOSED-sandwich":
                dstar = ver[1]
                for d in range(1, dstar):
                    closed, bound, cases, stats = DC.deep_cut(co0, a, rep, d, MAXCASES)
                    bounds[d] = "cut" if closed else (None if closed is None else bound)
                    if closed or closed is None:
                        break
                if control_every and (dstar <= control_every):
                    closed, bound, cases, stats = DC.deep_cut(co0, a, rep, dstar, MAXCASES)
                    entry["control"] = {"D": dstar, "bound": bound, "recorded": ver[3]}
            entry["bounds"] = bounds
            per_rep.append(entry)
        row = {"idx": idx, "key": list(r["key"]), "k": r["k"], "a": r["a"], "logU_recorded": r["logU"], "reps": per_rep,
               "t": round(time.time() - t0, 1)}
        with open(out_path, "a") as fh:
            fh.write(json.dumps(row) + "\n")
        print(idx, r["key"], r["k"], r["a"], f"{time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main(sys.argv[1], control_every=int(sys.argv[2]) if len(sys.argv) > 2 else 0)
