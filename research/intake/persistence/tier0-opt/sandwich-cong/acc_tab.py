import collections
rows = [l.rstrip("\n").split("\t") for l in open("runs/base1335.reps")]
per = collections.defaultdict(lambda: [0, 0, 0])
for f in rows:
    ci = int(f[0]); alive = int(f[10]); nsalive = int(f[11])
    per[ci][0] += alive; per[ci][1] += nsalive; per[ci][2] += 1
flip = [ci for ci, (a, n, r) in per.items() if a > 0 and a == n]
print("cases", len(per), "cases with any alive", sum(1 for v in per.values() if v[0] > 0), "cases whose only alive points are non-shadow:", len(flip))
for f in rows:
    if int(f[11]) > 0:
        print("rep with non-shadow alive: case", f[0], "ri", f[1], "y", f[2], "a", f[3], "nu", f[4], "n", f[5], "wrap", f[7], "words", f[8], "alive", f[10], "nsalive", f[11], "compat", f[12], "nscompat", f[13], "nG", f[16])
w0 = sum(1 for f in rows if int(f[8]) > 0 and f[7] == "0")
wn = sum(1 for f in rows if int(f[8]) > 0 and f[7] != "0")
print("reps with words: wrap0", w0, "wrap>0", wn)
print("nscompat total", sum(int(f[13]) for f in rows), "reps nscompat>0", sum(1 for f in rows if int(f[13]) > 0))
