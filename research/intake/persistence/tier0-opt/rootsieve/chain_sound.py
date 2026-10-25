import sys, random
from collections import Counter

CAP_NODES = 30000

def chain_feasible(a, digs):
    q = len(digs)
    exact = a < q
    w = a if exact else q
    pool = {}
    for d, e in digs:
        pool.setdefault(e, Counter())[d] += 1
    nodes = [0]

    def rec(p, u):
        nodes[0] += 1
        if nodes[0] > CAP_NODES:
            return True
        cls = pool.get(p % 12)
        cands = [1]
        if cls:
            cands += [d for d, c in cls.items() if c > 0]
        if p == w:
            if not exact:
                return True
            for c in cands:
                if (c - u) % 2 == 1:
                    return True
            return False
        pw = pow(5, p)
        for c in cands:
            if (c - u) % 2 != 0:
                continue
            if c != 1:
                cls[c] -= 1
            ok = rec(p + 1, (u + c * pw) // 2)
            if c != 1:
                cls[c] += 1
            if ok:
                return True
        return False

    return rec(0, 0)

def load(inp, meta, aidx):
    out = []
    for l1, l2 in zip(open(inp), open(meta)):
        f = l1.split(); nu, q = int(f[0]), int(f[1])
        digs = [tuple(int(v) for v in t.split(":")) for t in f[2:2 + q]]
        out.append((int(l2.split()[aidx]), digs))
    return out

rng = random.Random(7)
for name, inp, meta in (("plants", "plants_in.txt", "plants_meta.txt"), ("open@96 items", "openpat_in.txt", "openpat_meta.txt")):
    items = load(inp, meta, 0)
    ok = sum(chain_feasible(a, digs) for a, digs in items)
    neg_fail = 0; neg_n = 0
    for a, digs in items:
        if a < 3 or not digs:
            continue
        j = rng.randrange(len(digs))
        d, e = digs[j]
        pert = list(digs); pert[j] = (d, (e + rng.randrange(1, 12)) % 12)
        neg_n += 1
        neg_fail += (not chain_feasible(a, pert))
    print(name, "items", len(items), "chain feasible at the recorded a:", ok, "| planted negative (one digit moved to another class, a >= 3): rejected", neg_fail, "of", neg_n)
