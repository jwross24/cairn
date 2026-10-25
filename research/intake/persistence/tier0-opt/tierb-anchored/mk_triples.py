import sys, collections
vi = sys.argv[1]
agg = collections.OrderedDict()
for l in open(f"in/hits_v{vi}_sample100000000_7.txt"):
    y, k, nu, W, n = l.split()
    key = (y, k, nu)
    agg[key] = agg.get(key, 0) + int(n)
with open(f"work/triples_v{vi}.txt", "w") as f, open(f"work/expect_v{vi}.txt", "w") as g:
    for (y, k, nu), n in agg.items():
        f.write(f"{y} {k} {nu}\n")
        g.write(f"{y} {k} {nu} {n}\n")
print(vi, len(agg), sum(agg.values()))
