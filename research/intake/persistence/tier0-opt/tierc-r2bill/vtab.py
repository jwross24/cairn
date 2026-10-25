import json, collections
meta = {}
for fn in ("data/survivors_meta.tsv", "data/survivors_meta_b3.tsv"):
    for ln in open(fn):
        t = ln.split("\t")
        meta[t[0]] = int(t[1])
lab = {}
cpu = collections.defaultdict(float)
dflt = {}
for fn in ("results_def1.jsonl", "results_raised1.jsonl", "results_def3.jsonl", "results_raised3.jsonl"):
    for ln in open(fn):
        r = json.loads(ln)
        cpu[r["id"]] += r["cpu_s"]
        lab[r["id"]] = "BUDGET" if r["label"] == "ERROR" else r["label"]
        if fn.startswith("results_def"):
            dflt[r["id"]] = r["label"]
t = collections.defaultdict(collections.Counter)
for i, l in lab.items():
    k = meta[i]
    t[k][l] += 1
    t[k]["default_caps_budget" if dflt[i] == "BUDGET" else "default_caps_final"] += 1
print("k | n | cut | sandwich | open | NOTAPPL | BUDGET | needed raised caps")
for k in sorted(t):
    c = t[k]
    n = sum(c[x] for x in ("closed by the cut", "closed by the sandwich (U'')", "BUDGET", "open", "NOTAPPL"))
    print(k, n, c["closed by the cut"], c["closed by the sandwich (U'')"], c["open"], c["NOTAPPL"], c["BUDGET"], c["default_caps_budget"])
tot = collections.Counter(lab.values())
print(dict(tot))
