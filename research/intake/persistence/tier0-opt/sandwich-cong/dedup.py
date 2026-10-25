import json, os, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wordspace import load_rep, units
from congchain import wrap_of, factor237
HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
rec = json.load(open(HERE + "recorded550.json"))
rows = []
for i in sorted(rec):
    y, nu, pairs = load_rep(i); y = int(y)
    a, b, c = factor237(y)
    w = wrap_of(y, nu, pairs)
    rows.append((i, y, a, nu, tuple(pairs), w))


def tab(rows, label):
    n = len(rows)
    ky = {
        "anchor y": lambda r: r[1],
        "(y, nu)": lambda r: (r[1], r[3]),
        "(a, nu)": lambda r: (r[2], r[3]),
        "a": lambda r: r[2],
        "pattern (y, digit multiset)": lambda r: (r[1], tuple(sorted(d for d, e in r[4]))),
        "MITM unit key (units with multiplicity, nu, wrap)": lambda r: (tuple(sorted(collections.Counter(r[4]).items())), r[3], r[5]),
        "full rep (y, nu, units)": lambda r: (r[1], r[3], tuple(sorted(r[4]))),
        "(y, nu, units) positions only": lambda r: (r[1], r[3], tuple(sorted(e for d, e in r[4]))),
    }
    print(label, "survivors", n)
    for name, f in ky.items():
        d = len(set(f(r) for r in rows))
        print("  %-52s distinct %6d  dedup ratio %.2f" % (name, d, n / d))
    cnt = collections.Counter(r[1] for r in rows)
    print("  survivors per anchor: max %d, top5 %s" % (max(cnt.values()), cnt.most_common(5)))


tab(rows, "R2BILL 550")
rows2 = []
for line in open(HERE + "runs/base1335.reps"):
    f = line.rstrip("\n").split("\t")
    if int(f[8]) == 0:
        continue
    y = int(f[2]); a = int(f[3]); nu = int(f[4])
    pairs = tuple(tuple(int(x) for x in t.split(":")) for t in f[6].split())
    rows2.append((f[0] + "." + f[1], y, a, nu, pairs, int(f[7])))
tab(rows2, "1335 set, representations with >= 1 depth-1 word")
