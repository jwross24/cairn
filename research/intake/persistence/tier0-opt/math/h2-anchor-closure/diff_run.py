import sys, os, json, time
from collections import Counter, defaultdict
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
T0 = "/Users/jwross/Documents/cairn/research/intake/persistence/tier0"
os.chdir(T0)
sys.path.insert(0, T0)
sys.path.insert(0, HERE)
import deepcut as DC
import classify_open as C
from anchor_closure import Anchor, decide, window_of

baseline_path = sys.argv[1]
files = sys.argv[2:]

base = {}
for bp in baseline_path.split(","):
    for line in open(bp):
        r = json.loads(line)
        k = (r["s"], tuple(r["M"]), r["a"], r["y"], r["nu"], None if r["eps"] is None else tuple(r["eps"]))
        base[k] = r

patterns = []
seen = set()
for f in files:
    for (s, M, a, nu, eps, y, sol) in C.entries(f):
        key = (s, M, a, y, nu, None if eps is None else tuple(eps))
        if key in seen:
            continue
        seen.add(key)
        if key not in base:
            continue
        reps = DC.all_representations(M, y)
        if nu is not None:
            reps = [r for r in reps if r[0] == nu and Counter(e for _, e in r[1]) == Counter(e % DC.LMAX for e in eps)]
        patterns.append({"key": key, "file": os.path.basename(f), "s": s, "M": M, "a": a, "y": y, "reps": reps})

by_anchor = defaultdict(list)
for p in patterns:
    by_anchor[(p["y"], p["a"])].append(p)

best = None
for trial in range(2):
    t0 = time.perf_counter()
    anchor_time = {}
    verdicts = {}
    for (y, a), plist in by_anchor.items():
        t1 = time.perf_counter()
        A = Anchor(y, a)
        for p in plist:
            res = []
            for nu, de in p["reps"]:
                surv, window = decide(A, de)
                res.append(surv)
            verdicts[p["key"]] = res
        anchor_time[(y, a)] = time.perf_counter() - t1
    total = time.perf_counter() - t0
    if best is None or total < best[0]:
        best = (total, anchor_time, verdicts)
total, anchor_time, verdicts = best

n_pat = n_cmp = n_rep = 0
verdict_dis = []
surv_dis = []
budget = []
missing = []
base_time_pat = 0.0
base_time_anchor = defaultdict(float)
n_closed_mine = n_closed_base = 0
for p in patterns:
    b = base.get(p["key"])
    if b is None:
        missing.append(p["key"])
        continue
    n_pat += 1
    mine = verdicts[p["key"]]
    mine_closed = all(x == 0 for x in mine)
    brep = b["reps"]
    assert len(brep) == len(mine), (p["key"], len(brep), len(mine))
    base_closed = True
    has_budget = False
    for m, r in zip(mine, brep):
        n_rep += 1
        if r["closed"] is None:
            has_budget = True
            base_closed = False
            continue
        n_cmp += 1
        if (m == 0) != bool(r["closed"]):
            verdict_dis.append((p["key"], m, r["closed"], r["surv"]))
        elif r["surv"] != m:
            surv_dis.append((p["key"], m, r["surv"]))
        if not r["closed"]:
            base_closed = False
    if has_budget:
        budget.append((p["key"], mine))
    n_closed_mine += mine_closed
    n_closed_base += base_closed and not has_budget
    base_time_pat += b["t"]
    base_time_anchor[(p["y"], p["a"])] += b["t"]

out = {
    "patterns": n_pat, "reps": n_rep, "reps_compared": n_cmp, "anchors": len(by_anchor),
    "verdict_disagreements": verdict_dis, "survivor_count_disagreements": surv_dis,
    "budget_patterns": [(k, m) for k, m in budget], "missing_in_baseline": missing,
    "closed_mine": n_closed_mine, "closed_base": n_closed_base,
    "time_anchor_total_s": total, "time_deepcut_total_s": base_time_pat,
    "per_anchor": [{"y": y, "a": a, "patterns": len(by_anchor[(y, a)]), "t_mine": anchor_time[(y, a)],
                    "t_base": base_time_anchor[(y, a)]} for (y, a) in by_anchor],
}
json.dump(out, open(os.path.join(HERE, "diff_result.json"), "w"), default=str)
print({k: (v if not isinstance(v, list) else len(v)) for k, v in out.items()})
