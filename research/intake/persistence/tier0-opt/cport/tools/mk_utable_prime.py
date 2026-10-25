import argparse, math, os, sys

sys.dont_write_bytecode = True
MATH = '/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/math'
TIER0 = '/Users/jwross/Documents/cairn/research/intake/persistence/tier0'
sys.path.insert(0, os.path.join(MATH, 'breakthrough', 'b3-archimedean'))
sys.path.insert(0, os.path.join(MATH, 'h3-h4'))
sys.path.insert(0, TIER0)
import b3_chain as bc
from mpmath import mp, mpf, iv, log10
from baker_chain import baker_upper_bound

iv.prec = 256


def certified(k, a, m, v):
    e = max(0, int(mp.floor(log10(v))) - 6)
    mant = int(mp.ceil(v / mpf(10) ** e)) + 2
    for _ in range(200):
        n = mant * 10 ** e
        niv = iv.mpf(mant) * iv.mpf(10) ** e
        X, q, *_ = bc.chain(iv, niv, k, a, m)
        tot = X[m] + q[m]
        if tot.b < niv.a and niv.a > iv.exp(iv.mpf(k + 1)).b:
            return n
        mant += max(1, mant // 10 ** 6)
    raise RuntimeError(('not certified', k, a, m))


def best_b3(k, a):
    mp.dps = 50
    cands = []
    for m in range(1, k + 1):
        try:
            v = bc.bound(k, a, m)
        except Exception:
            continue
        if v > 0 and mp.isfinite(v):
            cands.append((v, m))
    cands.sort()
    for v, m in cands[:3]:
        try:
            return certified(k, a, m, v), m
        except RuntimeError:
            continue
    raise RuntimeError(('no certified m', k, a))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--kmax', type=int, default=24)
    ap.add_argument('--amax', type=int, default=24)
    ap.add_argument('--out', required=True)
    ap.add_argument('--log', required=True)
    ap.add_argument('--old', default=None)
    args = ap.parse_args()
    old = {}
    if args.old:
        for l in open(args.old):
            k, a, u = l.split()
            old[(int(k), int(a))] = int(u)
    fo = open(args.out, 'w')
    fl = open(args.log, 'w')
    for k in range(1, args.kmax + 1):
        for a in range(0, args.amax + 1):
            n, m = best_b3(k, a)
            u = old.get((k, a))
            if u is None:
                u = baker_upper_bound(k, a)
            keep = n > u
            use = u if keep else n
            fo.write(f"{k} {a} {use}\n")
            fl.write(f"k={k} a={a} m={m} log10U'={float(log10(mpf(n))):.4f} log10U={float(log10(mpf(u))):.4f} "
                     f"{'KEEP-OLD (U\' > U)' if keep else 'U\' used'}\n")
            fo.flush()
            fl.flush()
    fo.close()
    fl.close()
