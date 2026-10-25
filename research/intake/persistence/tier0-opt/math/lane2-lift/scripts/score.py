import json, sys, os
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def load(n):
    p = os.path.join(HERE, "logs", f"eval_{n}.jsonl")
    return {json.loads(l)["eq"]: json.loads(l) for l in open(p)} if os.path.exists(p) else {}
base = load("J24")
names = sys.argv[1:]
H = sorted(base, key=lambda e: -base[e]["children"])[:12]
print("baseline J24 total cpu %.2f over %d eq; heavy12 %.2f" % (sum(r["cpu"] for r in base.values()), len(base), sum(base[e]["cpu"] for e in H)))
for n in names:
    d = load(n)
    common = [e for e in base if e in d]
    tb = sum(base[e]["cpu"] for e in common); tn = sum(d[e]["cpu"] for e in common)
    hh = [e for e in H if e in d]
    hb = sum(base[e]["cpu"] for e in hh); hn = sum(d[e]["cpu"] for e in hh)
    bad = [e for e in common if not d[e]["identical"]]
    tdb = [e for e in common if not d[e]["tail_dead_equal"]]
    rat = sorted(base[e]["cpu"] / max(d[e]["cpu"], 1e-4) for e in common if base[e]["cpu"] > 0.5)
    med = rat[len(rat) // 2] if rat else float("nan")
    print("%-8s n=%d identical=%d/%d tail-dead-differs=%d  total x%.2f (%.2f->%.2f)  heavy12 x%.2f  median per-eq(>0.5s) x%.2f" % (n, len(common), len(common) - len(bad), len(common), len(tdb), tb / max(tn, 1e-9), tb, tn, hb / max(hn, 1e-9), med))
