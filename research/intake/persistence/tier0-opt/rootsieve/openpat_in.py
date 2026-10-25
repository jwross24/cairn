import json, sys
T = "/Users/jwross/Documents/cairn/research/intake/persistence/tier0/"
fin = open("openpat_in.txt", "w"); fmeta = open("openpat_meta.txt", "w")
n = 0; rows = set()
for fn in ("trees_mac.jsonl", "trees_c.jsonl", "runall_final.jsonl"):
    for line in open(T + fn):
        if '"open_patterns"' not in line:
            continue
        r = json.loads(line)
        for e in r.get("eqs", []):
            op = e.get("open_patterns")
            if not op or not isinstance(op, dict) or not op.get("items"):
                continue
            M = op["M"]
            for it in op["items"]:
                nu = it["nu"] % 12
                pat = ["%d:%d" % (d, ep % 12) for d, ep in zip(M, it["eps"]) if d != 1]
                fin.write("%d %d %s\n" % (nu, len(pat), " ".join(pat)))
                fmeta.write("%d %d %s\n" % (it["a"], r["s"], op["level"]))
                n += 1; rows.add(r["s"])
print("open items", n, "vertices", len(rows), sorted(rows))
