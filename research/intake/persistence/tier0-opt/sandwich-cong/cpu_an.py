import json, os, collections, statistics, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parse550 import parse_file
HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
B = "/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/tierc-r2bill/"
new = json.load(open(HERE + "newcpu_wm.json"))
old = collections.defaultdict(float)
for fn in ("results_def1.jsonl", "results_raised1.jsonl", "results_def3.jsonl", "results_raised3.jsonl", "results_o1.jsonl"):
    for l in open(B + fn):
        r = json.loads(l); old[r["id"]] += r["cpu_s"]
meta = {}
for fn in ("survivors_meta.tsv", "survivors_meta_b3.tsv", "survivors_meta_o1.tsv"):
    for l in open(B + "data/" + fn):
        t = l.rstrip("\n").split("\t"); meta[t[0]] = int(t[1])
print("n", len(new), "old total", sum(old[i] for i in new), "new total", sum(new.values()), "ratio", sum(old[i] for i in new) / sum(new.values()))
byk = collections.defaultdict(lambda: [0, 0.0, 0.0, 0.0, 0.0])
for i in new:
    k = meta.get(i, -1)
    kk = "<=24" if k <= 24 else str(k)
    v = byk[kk]; v[0] += 1; v[1] += old[i]; v[2] += new[i]; v[3] = max(v[3], old[i]); v[4] = max(v[4], new[i])
for kk in ["<=24", "25", "26", "27", "28", "29", "30", "31"]:
    v = byk[kk]
    if v[0]: print(kk, v[0], "old mean %.2f max %.1f | new mean %.3f max %.2f | ratio of sums %.0f" % (v[1] / v[0], v[3], v[2] / v[0], v[4], v[1] / v[2]))
top = sorted(new.items(), key=lambda x: -x[1])[:8]
print("top new", [(i, meta.get(i), round(c, 2), round(old[i], 1)) for i, c in top])
vals = sorted(new.values())
print("new median %.3f p90 %.3f p99 %.3f max %.3f" % (vals[len(vals)//2], vals[int(.9*len(vals))], vals[int(.99*len(vals))], vals[-1]))
