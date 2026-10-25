import sys, json
from collections import Counter, defaultdict


def v2(n):
    return (n & -n).bit_length() - 1


def s1_count(y, words, base_r96=True):
    a = v2(y)
    m2 = 1 << (a + 9)
    mod = m2 * 5 ** 5
    g = Counter((d, e) for d, e in words)
    by_class = defaultdict(list)
    for (d, e), c in g.items():
        if e < a + 9:
            by_class[e].append((d - 1, c))
    base = ((10 ** 96 - 1) // 9) % mod
    states = {base: 1}
    for e in range(a + 9):
        grp = by_class.get(e)
        if grp:
            opts = [(0, 1)]
            for w, c in grp:
                new = {}
                for s, mult in opts:
                    for m in range(c + 1):
                        new[s + m * w] = new.get(s + m * w, 0) + mult
                opts = list(new.items())
            p10 = pow(10, e, mod)
            nxt = {}
            for t, mult in states.items():
                for s, om in opts:
                    tt = (t + s * p10) % mod
                    nxt[tt] = nxt.get(tt, 0) + mult * om
            states = nxt
        mask = (1 << (e + 1)) - 1
        states = {t: m for t, m in states.items() if (t - y) & mask == 0}
        if not states:
            return 0
    tot = 0
    for t, m in states.items():
        if (t - y) % (5 ** 5) == 0:
            tot += m
    return tot


if __name__ == "__main__":
    rows = [json.loads(l) for l in open(sys.argv[1])]
    surv = 0
    tot = Counter()
    for r in rows:
        s = s1_count(r["y"], [tuple(w) for w in r["words"]])
        r["s1"] = s
        surv += 1 if s else 0
    print(len(rows), surv)
