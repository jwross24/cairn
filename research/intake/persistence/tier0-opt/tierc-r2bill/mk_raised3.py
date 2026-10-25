import json
rows = []
for ln in open("results_def3.jsonl"):
    r = json.loads(ln)
    if r["label"] == "BUDGET":
        rows.append((float(r["space"]), r["id"]))
rows.sort()
with open("data/ids_raised3.txt", "x") as f:
    for s, i in rows:
        f.write(i + "\n")
print(len(rows), "max space %.3g" % rows[-1][0], [("%.2g" % s) for s, i in rows[-6:]])
