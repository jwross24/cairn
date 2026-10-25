import json, collections
meta = {}
for ln in open("data/survivors_meta.tsv"):
    t = ln.split("\t")
    meta[t[0]] = (int(t[1]), int(t[2]))
c = collections.defaultdict(collections.Counter)
cpu = collections.defaultdict(list)
sp = collections.defaultdict(list)
for ln in open("results_def1.jsonl"):
    r = json.loads(ln)
    k = meta[r["id"]][0]
    c[k][r["label"]] += 1
    cpu[k].append(r["cpu_s"])
    if r["space"]:
        sp[k].append(float(r["space"]))
for k in sorted(c):
    print(k, dict(c[k]), "maxcpu %.1f" % max(cpu[k]), "space range", (min(sp[k]), max(sp[k])) if sp[k] else None)
