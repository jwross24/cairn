import argparse, math, os, sys

sys.dont_write_bytecode = True
TIER0 = '/Users/jwross/Documents/cairn/research/intake/persistence/tier0'
sys.path.insert(0, TIER0)
from mpmath import mp, mpf, iv, log10

iv.prec = 256
mp.dps = 40


def vmax(ctx, x, y):
    if ctx is mp:
        return max(x, y)
    return iv.mpf([max(x.a, y.a), max(x.b, y.b)])


class Yu2:
    def __init__(self, ctx, with_e=True):
        self.ctx = ctx
        m = ctx.mpf
        L = ctx.log
        mx = lambda x, y: vmax(ctx, x, y)
        e = ctx.exp(m(1))
        self.l2, self.l3, self.l5, self.l6, self.l7 = (L(m(x)) for x in (2, 3, 5, 6, 7))
        self.l10, self.l9, self.l80, self.l71 = (L(m(x)) for x in (10, 9, 80, 71))

        def c1(n):
            return (m(1473) * (m(32) / 3) ** n * m(n) ** n * m(n + 1) ** (n + 1) / math.factorial(n)
                    * m(5) / 4 * (m(2) / self.l5) ** (n + 2) * L(mx(m(2), e))
                    * mx(mx(L(e ** 4 * (n + 1) * 2), m(1)), self.l5))

        thm1 = lambda n: (n + 1) * c1(n)
        a0 = 1 + L(m(8))
        c2 = (m(1576) / 3 * (m(8) * e if with_e else m(8)) ** 3 * m(4) ** 4 / math.factorial(2)
              * m(5) / 4 * m(2) ** 5 / self.l5 ** 3 * L(mx(m(2), e))
              * mx(mx(L(e ** 4 * 4 * 2), m(1)), self.l5))
        self.G2 = 4 * (a0 * 3 + m('2.4') + L(a0 * 3 + m('6.44')) + L(m(4)) + L(m(2)) + self.l5)
        self.omega = 1 / (2 * self.l6 ** 3)
        self.c2l = c2 * self.l3 * self.l7
        e1 = thm1(1)
        e2 = thm1(2)
        e3 = thm1(3) * self.l5 / 140
        self.dep = mx(mx(e2 * self.l3 * self.l7, e1 * self.l7), e3 * self.l3 * self.l7)
        self.c2 = c2
        self.C = lambda t: m('1.4') * m(30) ** (t + 3) * m(t) ** m('4.5')

    def F(self, H, B):
        ctx = self.ctx
        ind = self.c2l * H * vmax(ctx, self.G2, ctx.log(self.omega * (B / H + 1 / self.l3)))
        return vmax(ctx, ind, self.dep * ctx.log(2 * B))

    def chain(self, nu, k, a):
        ctx = self.ctx
        L = ctx.log
        B = ctx.mpf('2.1') * nu + 2
        TA = 1 + L(B)
        at = a * self.l2
        if a == 0:
            K0 = self.C(3) * self.l3 * self.l7 * self.l10 * TA
        else:
            K0 = self.C(4) * self.l2 * self.l3 * self.l7 * self.l10 * TA
        K1 = self.C(4) * self.l3 * self.l7 * self.l10 * TA
        s = (K0 + self.l80) / self.l10
        X = {1: s}
        for j in range(1, k):
            s = s + (self.l80 + K1 * (s * self.l10 + self.l9 + at)) / self.l10
            X[j + 1] = s
        q = {}
        if a >= 1:
            cur = self.F(at + self.l71, B)
            q[k] = ctx.mpf(0)
            q[k - 1] = cur
            for j in range(k - 2, 0, -1):
                cur = self.F(at + cur * self.l10 + self.l80, B)
                q[j] = cur
        else:
            cur = self.F(ctx.mpf(1), B)
            q[k] = cur
            for j in range(k - 1, 0, -1):
                cur = self.F(cur * self.l10 + self.l80, B)
                q[j] = cur
        return X, q

    def totals(self, nu, k, a):
        X, q = self.chain(nu, k, a)
        return {m: X[m] + q[m] for m in range(1, k + 1)}


def search(Y, k, a):
    floor = mp.log10(mp.exp(k + 1)) + mpf('1e-9')

    def margin(x):
        nu = mpf(10) ** x
        t = Y.totals(nu, k, a)
        return min(t.values()) / nu

    lo, hi = floor, mpf(10)
    while margin(hi) >= 1:
        hi *= 2
        if hi > 20000:
            raise RuntimeError(('no crossing', k, a))
    if margin(lo) < 1:
        return lo
    for _ in range(80):
        mid = (lo + hi) / 2
        if margin(mid) >= 1:
            lo = mid
        else:
            hi = mid
    return hi


def certified(Yi, k, a, m, v):
    e = max(0, int(mp.floor(log10(v))) - 6)
    mant = int(mp.ceil(v / mpf(10) ** e)) + 2
    for _ in range(200):
        n = mant * 10 ** e
        niv = iv.mpf(mant) * iv.mpf(10) ** e
        tot = Yi.totals(niv, k, a)[m]
        if tot.b < niv.a and niv.a > iv.exp(iv.mpf(k + 1)).b:
            return n
        mant += max(1, mant // 10 ** 6)
    raise RuntimeError(('not certified', k, a, m))


def best_u2(k, a, Y=None, Yi=None, with_e=True):
    Y = Y or Yu2(mp, with_e)
    Yi = Yi or Yu2(iv, with_e)
    x = search(Y, k, a)
    nu = mpf(10) ** x
    t = Y.totals(nu, k, a)
    for m in sorted(t, key=lambda i: t[i])[:4]:
        try:
            return certified(Yi, k, a, m, nu), m
        except RuntimeError:
            continue
    raise RuntimeError(('no certified m', k, a))


def planted_negative(k, a):
    Y = Yu2(mp)
    Yi = Yu2(iv)
    n, m = best_u2(k, a, Y, Yi)
    low = int(n * 99 // 100)
    niv = iv.mpf(low)
    tot = Yi.totals(niv, k, a)[m]
    return not (tot.b < niv.a), n, low


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--kmax', type=int, default=24)
    ap.add_argument('--amax', type=int, default=24)
    ap.add_argument('--out')
    ap.add_argument('--log')
    ap.add_argument('--prime', default=None)
    ap.add_argument('--probe', nargs='*', default=None)
    ap.add_argument('--no-e', action='store_true')
    ap.add_argument('--selftest', action='store_true')
    args = ap.parse_args()
    if args.selftest:
        bad = 0
        for (k, a) in ((6, 0), (11, 1), (31, 0), (31, 40)):
            refused, n, low = planted_negative(k, a)
            print(f"k={k} a={a}: certified log10 {float(log10(mpf(n))):.4f}; 0.99 of it refused: {refused}")
            bad += not refused
        sys.exit(1 if bad else 0)
    if args.probe is not None:
        Y = Yu2(mp, not args.no_e)
        Yi = Yu2(iv, not args.no_e)
        for p in args.probe:
            k, a = map(int, p.split(','))
            n, m = best_u2(k, a, Y, Yi)
            print(f"k={k} a={a} m={m} log10 U'' = {float(log10(mpf(n))):.4f}", flush=True)
        sys.exit(0)
    prime = {}
    if args.prime:
        for l in open(args.prime):
            k, a, u = l.split()
            prime[(int(k), int(a))] = int(u)
    from baker_chain import baker_upper_bound
    Y = Yu2(mp)
    Yi = Yu2(iv)
    fo = open(args.out, 'x')
    fl = open(args.log, 'x')
    for k in range(1, args.kmax + 1):
        for a in range(0, args.amax + 1):
            n, m = best_u2(k, a, Y, Yi)
            u = baker_upper_bound(k, a)
            keep = n > u
            use = u if keep else n
            up = prime.get((k, a))
            tag = 'KEEP-U (U2 > U)' if keep else "U'' used"
            if up is not None and use > up:
                tag += " ; U'' > U' (NOT <=)"
            fo.write(f"{k} {a} {use}\n")
            fl.write(f"k={k} a={a} m={m} log10U''={float(log10(mpf(n))):.4f} log10U={float(log10(mpf(u))):.4f} "
                     f"log10U'={'-' if up is None else format(float(log10(mpf(up))), '.4f')} {tag}\n")
            fo.flush()
            fl.flush()
    fo.close()
    fl.close()
