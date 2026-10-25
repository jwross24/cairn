import sys

ref = {}
for l in open(sys.argv[1]):
    c = l.rstrip("\n").split("\t")
    ref[c[0]] = (c[1], c[2])
got = {}
for l in open(sys.argv[2]):
    c = l.rstrip("\n").split("\t")
    got[" ".join(c[0].split()[:4])] = (c[7], c[8])
match = sum(1 for k in ref if got.get(k) == ref[k])
missing = [k for k in ref if k not in got]
diff = [(k, ref[k], got[k]) for k in ref if k in got and got[k] != ref[k]]
print("ref", len(ref), "run", len(got), "match", match, "missing", len(missing), "differ", len(diff))
for d in diff[:10]:
    print(d)
