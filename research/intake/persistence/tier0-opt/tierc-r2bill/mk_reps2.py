import json, sys
sys.dont_write_bytecode = True
sys.path.insert(0, "/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/tierc-r2shadow")
from mk_inputs import rep_line

src, prefix, meta_out, ids_out = sys.argv[1:5]
rows = []
seen = set()
for ln in open(src):
    r = json.loads(ln)
    key = rep_line(r["y"], r["nu"], r["words"])
    if key in seen:
        continue
    seen.add(key)
    rows.append((key, r))
rows.sort(key=lambda kr: (kr[1]["k"], kr[1]["y"], kr[1]["nu"]))
with open(meta_out, "x") as m, open(ids_out, "x") as ids:
    for i, (key, r) in enumerate(rows):
        sid = "%s%03d" % (prefix, i)
        with open("data/rep_%s.rep" % sid, "x") as f:
            f.write(key + "\n")
        m.write("%s\t%d\t%d\t%d\t%d\t%d\t%d\t%d\n" % (sid, r["k"], r["a"], r["y"], r["nu"], r["E"], r["nodes"], r["wrap"]))
        ids.write(sid + "\n")
print(src, "distinct", len(rows))
