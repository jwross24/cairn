import sys, json, math
from collections import Counter

PER_CASE = 640000


def v2(n):
    return (n & -n).bit_length() - 1


def analyze(rec):
    a = v2(rec["y"])
    c = Counter((d, e) for d, e in rec["words"])
    ncases = 1
    qlow = 0
    for (d, e), m in c.items():
        if e < a + 9:
            ncases *= m + 1
            qlow += m
    p = -math.expm1(-ncases / PER_CASE)
    return a, len(rec["words"]), qlow, ncases, p


if __name__ == "__main__":
    rows = [json.loads(l) for l in open(sys.argv[1])]
    ps = []
    for r in rows:
        a, k, ql, nc, p = analyze(r)
        ps.append(p)
    print(len(rows), sum(ps) / len(rows))
