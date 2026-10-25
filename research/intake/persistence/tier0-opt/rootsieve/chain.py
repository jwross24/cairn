import sys, math
from collections import Counter

CAP_NODES = 30000

def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))

def parse(path):
    pats = []
    for line in open(path):
        parts = line.rstrip("\n").split(" | ")
        head = parts[0].split()
        tag, rk, nu, q = head[0], int(head[1]), int(head[2]), int(head[3])
        digs = [tuple(int(v) for v in t.split(":")) for t in head[4:4 + q]]
        lines = []
        for seg in parts[1:]:
            f = seg.split()
            lines.append((int(f[0]), int(f[1]), int(f[2])))
        pats.append((tag, rk, nu, digs, lines))
    return pats

def chain_feasible(a, digs):
    q = len(digs)
    exact = a < q
    w = a if exact else q
    pool = {}
    for d, e in digs:
        pool.setdefault(e, Counter())[d] += 1
    nodes = [0]
    capped = [False]

    def rec(p, u):
        nodes[0] += 1
        if nodes[0] > CAP_NODES:
            capped[0] = True
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

    r = rec(0, 0)
    return r, capped[0]

def main():
    pats = parse(sys.argv[1])
    amax = 118
    ok_set = []
    for tag, rk, nu, digs, lines in pats:
        sel = [l for l in lines if l[0] <= amax and l[1] == 1 and l[2] == 1]
        if sel:
            ok_set.append((tag, rk, nu, digs, sel))
    print("patterns in dump", len(pats), "open&keep patterns", len(ok_set))
    pass_n = 0; capped_n = 0; lines_total = 0; lines_pass = 0
    by_a0 = Counter(); by_a0_pass = Counter()
    for tag, rk, nu, digs, sel in ok_set:
        any_pass = False; any_cap = False
        for a, keep, op in sorted(sel):
            lines_total += 1
            r, cp = chain_feasible(a, digs)
            by_a0[a % 12] += 1
            if cp:
                any_cap = True
            if r:
                lines_pass += 1; by_a0_pass[a % 12] += 1; any_pass = True
                break
        pass_n += any_pass
        capped_n += any_cap
    n = len(ok_set)
    lo, hi = wilson(pass_n, n)
    print("pattern pass", pass_n, "/", n, "rate %.4f [%.4f, %.4f]" % (pass_n / max(n, 1), lo, hi), "capped patterns", capped_n)
    print("line pass", lines_pass, "/", lines_total)
    print("by a mod 12 (line pass/total):", " ".join("%d:%d/%d" % (k, by_a0_pass[k], by_a0[k]) for k in range(12)))
    u = [p for p in pats if p[0] == "U"]
    print("uniform survivor subsample", len(u))
    for rk in (2,):
        sub = [p for p in u if p[1] == rk]
        n_all = len(sub)
        n_ch = 0; n_tail = 0; n_both = 0; capc = 0
        for tag, r_, nu, digs, lines in sub:
            ls = [l for l in lines if l[0] <= amax]
            ch = False; tl = False; both = False
            for a, keep, op in sorted(ls):
                f, cp = chain_feasible(a, digs)
                capc += cp
                ch |= f; tl |= bool(op); both |= (f and bool(op))
            n_ch += ch; n_tail += tl; n_both += both
        print("rank", rk, "survivors", n_all, "chain-any", n_ch, "tail-any", n_tail, "both", n_both, "capped lines", capc)

main()
