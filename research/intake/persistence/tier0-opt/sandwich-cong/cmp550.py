import json, os, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parse550 import parse_file
HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
tag = sys.argv[1]
rec = json.load(open(HERE + "recorded550.json"))
res = {}
for l in open(HERE + "res_%s.jsonl" % tag):
    r = json.loads(l); res[r["id"]] = r
cnt = collections.Counter()
diffs = []
newcpu = {}
for i, rc in sorted(rec.items()):
    me = parse_file(HERE + "runs/%s/%s.txt" % (tag, i))
    newcpu[i] = res[i]["cpu"]
    keys = ["wrap", "words", "notappl", "T", "units", "shadow", "compat", "nscompat", "passchain", "windows", "alive", "wordsalive", "nsalive", "nn", "nndig"]
    same = all(rc.get(k) == me.get(k) for k in keys)
    vr = rc.get("verdict")
    vm = me.get("verdict")
    cnt["same_counters" if same else "diff_counters"] += 1
    if vr == vm:
        cnt["same_verdict"] += 1
    else:
        cnt["diff_verdict"] += 1
        diffs.append((i, rc.get("verdict"), me.get("verdict")))
    if not same and rc.get("verdict") is not None:
        diffs.append((i, "COUNTERS", {k: (rc.get(k), me.get(k)) for k in keys if rc.get(k) != me.get(k)}))
print(dict(cnt))
for d in diffs[:20]: print(d)
json.dump(newcpu, open(HERE + "newcpu_%s.json" % tag, "w"))
print("total cpu new", sum(newcpu.values()))
