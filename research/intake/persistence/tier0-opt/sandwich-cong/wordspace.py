import json, math, os, re, sys, glob
from math import comb
B = "/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/"
RB = B + "tierc-r2bill/data/"
HERE = os.path.dirname(os.path.abspath(__file__)) + "/"

def load_rep(i):
    p = open(RB + "rep_%s.rep" % i).read().split()
    y, nu, n = p[0], int(p[1]), int(p[2])
    pairs = sorted((int(t.split(":")[0]), int(t.split(":")[1])) for t in p[3:3 + n])
    return y, nu, pairs

def units(pairs):
    order = []
    cnt = {}
    for pr in pairs:
        if pr not in cnt:
            cnt[pr] = 0; order.append(pr)
        cnt[pr] += 1
    return order, cnt

def split_work(ncs):
    tot = 1.0
    for c in ncs: tot *= c
    lcap = min(max(math.sqrt(tot) * 4, 1), 6e7)
    NL = 1.0; NR = 1.0
    for c in sorted(ncs, reverse=True):
        if NL * c <= lcap: NL *= c
        else: NR *= c
    return tot, NL, NR

def work(ncs):
    tot, NL, NR = split_work(ncs)
    return tot, NL + NR

def words_of(i):
    out = []
    f = HERE + "runs/words_%s.jsonl" % i
    if not os.path.exists(f): return None
    for l in open(f):
        l = l.strip()
        if l: out.append(json.loads(l)["fixed"])
    return out

def analyze(i):
    y, nu, pairs = load_rep(i)
    order, cnt = units(pairs)
    uidx = {pr: q for q, pr in enumerate(order)}
    ws = words_of(i)
    if ws is None: return None
    fus = set()
    for w in ws:
        fu = [0] * len(order)
        for j in w: fu[uidx[pairs[j]]] += 1
        fus.add(tuple(fu))
    fus = list(fus)
    def leq(a, b): return all(x <= z for x, z in zip(a, b))
    mins = [f for f in fus if not any(g != f and leq(g, f) for g in fus)]
    ms = [cnt[pr] for pr in order]
    base = [comb(m + 4, 4) for m in ms] + [5]
    tot, wfull = work(base)
    wsum = 0.0; spsum = 0.0
    for f in mins:
        ncs = [comb(m - x + 4, 4) for m, x in zip(ms, f)] + [5]
        sp, w = work(ncs)
        wsum += w; spsum += sp
    return dict(id=i, k=len(pairs), nwords=len(ws), nmin=len(mins), space=tot, work=wfull, rspace=spsum, rwork=wsum)

if __name__ == "__main__":
    ids = sorted(os.path.basename(f)[6:-6] for f in glob.glob(HERE + "runs/words_*.jsonl"))
    rows = []
    for i in ids:
        r = analyze(i)
        if r: rows.append(r)
    json.dump(rows, open(HERE + "wordspace.json", "w"))
    import statistics
    print(len(rows))
    gains = [r["work"] / r["rwork"] for r in rows if r["rwork"] > 0]
    print("median work gain", statistics.median(gains), "min", min(gains), "max", max(gains))
    big = [r for r in rows if r["space"] > 1e16]
    for r in sorted(big, key=lambda r: -r["space"])[:15]:
        print(r["id"], r["k"], r["nwords"], r["nmin"], "%.3g %.3g %.3g %.3g" % (r["space"], r["work"], r["rspace"], r["rwork"]))
    print("sum work", sum(r["work"] for r in rows), "sum rwork", sum(r["rwork"] for r in rows))
