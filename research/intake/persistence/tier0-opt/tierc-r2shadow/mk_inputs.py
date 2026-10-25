import json, sys

CLS = [[3], [2], [2, 7], [2], [2, 3], [2] * 8, [2] * 6, [2, 2], [2, 2, 3, 3], [2, 3, 3, 3]]


def rep_line(y, nu, words):
    ws = sorted((int(d), int(e)) for d, e in words)
    return "%d %d %d %s" % (y, nu, len(ws), " ".join("%d:%d" % (d, e) for d, e in ws))


def case_line(y, a, words):
    ds = sorted(int(d) for d, e in words)
    s = 1
    for d in ds:
        s *= d
    return "%d %s %d %d - -" % (s, "".join(str(d) for d in ds), a, y)


def v2(n):
    c = 0
    while n % 2 == 0:
        n //= 2
        c += 1
    return c


def main():
    out = sys.argv[1]
    srcs = sys.argv[2:]
    rows = []
    for p in srcs:
        for ln in open(p):
            r = json.loads(ln)
            rows.append(r)
    with open(out + ".rep", "w") as f, open(out + ".cases", "w") as g, open(out + ".meta", "w") as m:
        for r in rows:
            f.write(rep_line(r["y"], r["nu"], r["words"]) + "\n")
            g.write(case_line(r["y"], v2(r["y"]), r["words"]) + "\n")
            m.write("%d\t%d\t%d\t%d\t%d\n" % (r["y"], len(r["words"]), v2(r["y"]), r["nu"], r.get("wrap", r.get("k", 0))))


def k31():
    words = [(d, c) for c in range(10) for d in CLS[c]]
    y = 3 ** 3 * 7 ** 10
    print(rep_line(y, 2, words))


if __name__ == "__main__":
    if sys.argv[1] == "k31":
        k31()
    else:
        main()
