import sys, math
import numpy as np

def parse(path, tags=("U",)):
    out = []
    for line in open(path):
        parts = line.split(" | ")
        head = parts[0].split()
        if head[0] not in tags:
            continue
        rk, nu, q = int(head[1]), int(head[2]), int(head[3])
        digs = [tuple(int(v) for v in t.split(":")) for t in head[4:4 + q]]
        out.append((rk, nu, digs))
    return out

def cycle_vals(e, mod):
    v0 = pow(10, e, mod)
    step = pow(10, 12, mod)
    vals = [v0]
    v = (v0 * step) % mod
    while v != v0:
        vals.append(v)
        v = (v * step) % mod
    return vals

def reach_zero(M, nu, digs):
    n_opts = set(((v - 1) // 9) % M for v in cycle_vals(nu, 9 * M))
    cur = np.zeros(M, dtype=bool)
    for r in n_opts:
        cur[r] = True
    for d, e in digs:
        vs = set(v % M for v in cycle_vals(e, M))
        nxt = np.zeros(M, dtype=bool)
        for v in vs:
            nxt |= np.roll(cur, ((d - 1) * v) % M)
        cur = nxt
    return bool(cur[0]), int(cur.sum())

MAINSEL = [None]
def main():
    pats = parse(sys.argv[1])
    lim = int(sys.argv[2])
    mods = [("27", 27), ("81", 81), ("243", 243), ("729", 729), ("49", 49), ("343", 343), ("27*49", 27 * 49), ("81*343", 81 * 343)]
    sel = []
    for rk, nu, digs in pats:
        s3 = (nu + sum(d - 1 for d, e in digs)) % 3
        r7 = [0]
        for i in range(5):
            r7.append((r7[-1] * 10 + 1) % 7)
        y7 = (r7[nu % 6] + sum((d - 1) * pow(10, e % 6, 7) for d, e in digs)) % 7
        sel.append((s3 == 0, y7 == 0, nu, digs))
    for name, M in mods:
        need3 = M % 3 == 0
        need7 = M % 7 == 0
        tested = 0; zero_ok = 0; sizes = []
        for d3, d7, nu, digs in sel:
            if (need3 and not d3) or (need7 and not d7):
                continue
            ok, sz = reach_zero(M, nu, digs)
            tested += 1; zero_ok += ok; sizes.append(sz)
            if tested >= lim:
                break
        MAINSEL[0] = sel
        print("modulus", name, "patterns with the needed divisibility tested", tested, "zero reachable", zero_ok, "mean reachable-set fraction %.3f" % (np.mean(sizes) / M if sizes else 0))

def negative(pats_sel, M, lim):
    tested = 0; zero_ok = 0
    for d3, d7, nu, digs in pats_sel:
        if d3:
            continue
        ok, sz = reach_zero(M, nu, digs)
        tested += 1; zero_ok += ok
        if tested >= lim:
            break
    return tested, zero_ok

main()
print("negative control (3 does not divide x), modulus 27: tested %d, zero reachable %d" % negative(MAINSEL[0], 27, 400))
print("negative control (7 does not divide x), modulus 49: tested %d, zero reachable %d" % negative([(a, True, c, d) for (a, b, c, d) in MAINSEL[0] if not b], 49, 400)) if False else None
