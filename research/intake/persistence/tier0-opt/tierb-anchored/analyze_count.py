import sys, collections, math
vi = sys.argv[1]
exp = {}
for l in open(f"work/expect_v{vi}.txt"):
    y, k, nu, n = l.split()
    exp[(y, int(k), int(nu))] = int(n)
got = {}
nov = 0
ovf = 0
bywrap = collections.Counter(); bywrap_t = collections.Counter(); bya = collections.Counter(); bya_t = collections.Counter()
for l in open(f"work/count_v{vi}.out"):
    t = l.split()
    if t[0] == "NOV": nov += 1; continue
    if "OVERFLOW" in l: ovf += 1
    y, k, nu, a, tot, s, ns = t[1], int(t[2]), int(t[3]), int(t[4]), int(t[5]), int(t[6]), int(t[7])
    assert s + ns == tot
    got[(y, k, nu)] = tot
    cl = "w0" if k == 0 else ("w<0" if k < 0 else "w>=1")
    bywrap[cl] += s; bywrap_t[cl] += tot; bya[a] += s; bya_t[a] += tot
mism = [(key, exp[key], got.get(key)) for key in exp if got.get(key) != exp[key]]
print("triples expected", len(exp), "got", len(got), "NOV", nov, "overflow lines", ovf, "count mismatches", len(mism))
print(mism[:5])
T = sum(bywrap_t.values()); S = sum(bywrap.values())
print("patterns", T, "survivors", S, "rate", S / T)
for c in bywrap: print(c, bywrap_t[c], bywrap[c], bywrap[c] / max(1, bywrap_t[c]))
print("by a:", sorted((a, bya_t[a], bya[a]) for a in bya))
