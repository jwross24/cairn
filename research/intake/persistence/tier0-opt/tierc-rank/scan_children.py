import json, sys

base = "/Users/jwross/Documents/cairn/research/intake/persistence/tier0/"
seen = {}
for fn in ("runall_final.jsonl", "trees_c.jsonl", "trees_mac.jsonl"):
    for ln in open(base + fn):
        try:
            r = json.loads(ln)
        except Exception:
            continue
        s = r.get("s")
        for key in ("known", "found"):
            for v in r.get(key, []) or []:
                seen.setdefault(v, set()).add(s)
        for e in r.get("eqs", []) or []:
            if isinstance(e, dict):
                for v in e.get("sols", []) or []:
                    seen.setdefault(v, set()).add(s)
def rank(y):
    return (y % 3 == 0) + (y % 7 == 0)
pw2 = sorted(v for v in seen if isinstance(v, int) and v > 0 and v & (v - 1) == 0)
print("distinct recorded children", len(seen))
print("rank counts", {r: sum(1 for v in seen if isinstance(v, int) and rank(v) == r) for r in (0, 1, 2)})
print("powers of two among them", pw2)
json.dump({"children": sorted(v for v in seen if isinstance(v, int))}, open("recorded_children.json", "w"))
