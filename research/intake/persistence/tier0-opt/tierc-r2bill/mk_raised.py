import json
meta = {}
for ln in open("data/survivors_meta.tsv"):
    t = ln.split("\t")
    meta[t[0]] = (int(t[1]), int(t[2]))
rows = []
for ln in open("results_def1.jsonl"):
    r = json.loads(ln)
    if r["label"] == "BUDGET":
        rows.append((float(r["space"]), r["id"], meta[r["id"]][0]))
rows.sort()
with open("data/ids_raised.txt", "x") as f:
    for s, i, k in rows:
        f.write(i + "\n")
for s, i, k in rows:
    print(i, k, "%.3g" % s)
