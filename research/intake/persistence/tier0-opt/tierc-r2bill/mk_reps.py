import json, glob, sys
sys.dont_write_bytecode = True
sys.path.insert(0, "/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/tierc-r2shadow")
from mk_inputs import rep_line

rows = []
seen = {}
for f in sorted(glob.glob("surv_*.jsonl")):
    for ln in open(f):
        r = json.loads(ln)
        key = rep_line(r["y"], r["nu"], r["words"])
        seen.setdefault(key, []).append(f)
        if len(seen[key]) == 1:
            rows.append((key, r))
rows.sort(key=lambda kr: (kr[1]["k"], kr[1]["y"], kr[1]["nu"]))
with open("data/survivors_meta.tsv", "x") as m, open("data/ids_all.txt", "x") as ids:
    for i, (key, r) in enumerate(rows):
        sid = "s%03d" % i
        with open("data/rep_%s.rep" % sid, "x") as f:
            f.write(key + "\n")
        m.write("%s\t%d\t%d\t%d\t%d\t%d\t%d\t%s\n" % (sid, r["k"], r["a"], r["y"], r["nu"], r["E"], r["nodes"], r["src"]))
        ids.write(sid + "\n")
print("distinct", len(rows), "draws", sum(len(v) for v in seen.values()), "dups", sum(1 for v in seen.values() if len(v) > 1))
