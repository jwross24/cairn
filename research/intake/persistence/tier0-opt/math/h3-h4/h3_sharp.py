import sys
from fractions import Fraction

sys.dont_write_bytecode = True
TIER0 = "/Users/jwross/Documents/cairn/research/intake/persistence/tier0"
sys.path.insert(0, TIER0)

from mpmath import mp, mpf, log, exp, floor, ceil, iv

mp.dps = 60
iv.prec = 256

SIGMA = Fraction(21, 10)
LOGU = 80
LOGV = 9


def matveev_c(t, ctx):
    val = ctx.mpf("1.4") * ctx.mpf(30) ** (t + 3) * ctx.mpf(t) ** ctx.mpf("4.5")
    if ctx is mp:
        val = val * (1 + mpf("1e-30"))
    return val


def frac(ctx, fr):
    return ctx.mpf(fr.numerator) / ctx.mpf(fr.denominator)


def alphas_for(a):
    return [3, 7, 10] if a == 0 else [2, 3, 7, 10]


def bmax(ctx, a, nu):
    return frac(ctx, SIGMA) * nu + 2 + a


def cmax(ctx, x, c):
    if ctx is mp:
        return max(x, mpf(c))
    return iv.mpf([max(x.a, mpf(c)), max(x.b, mpf(c))])


def kit_k0(ctx, a, nu):
    a1, a2, a3 = [cmax(ctx, ctx.mpf("6.296") * ctx.log(ctx.mpf(x)), 4) for x in (3, 10, 7)]
    omega = cmax(ctx, a1 * a2 * a3, 100)
    bm = bmax(ctx, a, nu)
    bprime = (bm / a2 + bm / a1) + (bm / a2 + bm / a3)
    lb = cmax(ctx, ctx.log(bprime) + ctx.mpf("0.882"), 10)
    return ctx.mpf("790.95") * omega * lb ** 2


def ecap_bl(ctx, nu):
    bm = bmax(ctx, 0, nu)
    log5 = ctx.log(ctx.mpf(5))
    log7 = ctx.log(ctx.mpf(7))
    b = 2 * bm / log7 + 2 * bm / log5
    inner = ctx.log(b) + ctx.log(log5) + ctx.mpf("0.4")
    lb = cmax(ctx, inner, max(10 * log(mpf(5)), mpf(5)) * (1 + mpf("1e-30")))
    base = ctx.mpf(1) / ((5 - 1) * log5 ** 4)
    mult = 24 * ctx.mpf(5) ** 4 * base
    return mult * lb ** 2 * log5 * log7


def phi(k, a, nu, mode, ctx=mp):
    logb = ctx.log(ctx.mpf(10))
    pa = ctx.mpf(1)
    for al in alphas_for(a):
        pa = pa * ctx.log(ctx.mpf(al))
    t0 = len(alphas_for(a))
    bm = bmax(ctx, a, nu)
    tt = 1 + ctx.log(bm)
    k0 = matveev_c(t0, ctx) * pa * tt
    k1 = matveev_c(t0 + 1, ctx) * pa * tt
    if mode.get("kit") and a == 0:
        k0 = kit_k0(ctx, a, nu)
    if mode.get("k0zero"):
        k0 = k0 * 0
    lu = ctx.log(ctx.mpf(LOGU))
    lv = ctx.log(ctx.mpf(LOGV))
    if k == 0:
        return k0 / logb
    g0 = (k0 + lu) / logb
    s = g0
    for _ in range(1, k):
        gj = (lu + k1 * (s * logb + lv)) / logb
        s = s + gj
    if mode.get("last"):
        if a >= 1:
            return s
        return s + ecap_bl(ctx, nu)
    return k1 * (s * logb + lv) / logb


def exact_int_at_least(x):
    xf = int(floor(x))
    fr = x - xf
    if xf < 7:
        return int(ceil(mpf(10) ** x)) + 1
    m = int(ceil(mpf(10) ** fr * 10 ** 6)) + 1
    return m * 10 ** (xf - 6)


def certify(k, a, mode, n_int):
    s = str(n_int)
    stripped = s.rstrip("0")
    e = len(s) - len(stripped)
    m = int(stripped)
    assert m < 2 ** 52
    n_iv = iv.mpf(m) * iv.mpf(10) ** e
    ek = iv.exp(iv.mpf(k))
    if not (n_iv.a > ek.b):
        return False
    p = phi(k, a, n_iv, mode, ctx=iv)
    return bool(p.b < n_iv.a)


def solve(k, a, mode):
    x = max(mpf(k) / log(mpf(10)) + 1, mpf(2))
    for _ in range(80):
        xn = log(phi(k, a, mpf(10) ** x, mode)) / log(mpf(10))
        if xn <= x:
            break
        x = xn
    step = mpf("0.001")
    for _ in range(100000):
        n = mpf(10) ** x
        if n >= exp(mpf(k)) and phi(k, a, n, mode) * (1 + mpf("1e-6")) < n:
            n_int = exact_int_at_least(x)
            if certify(k, a, mode, n_int):
                return n_int
        x += step
    raise RuntimeError("no certified point")


def log10_int(n_int):
    return float(log(mpf(n_int)) / log(mpf(10)))


MODES = {
    "old": {},
    "last": {"last": True},
    "last+kit": {"last": True, "kit": True},
    "last+k0zero": {"last": True, "k0zero": True},
    "old+kit": {"kit": True},
    "old+k0zero": {"k0zero": True},
}


def cross_check_old():
    import baker_chain as bc
    bad = 0
    total = 0
    for a in (0, 1, 40):
        for k in range(0, 33):
            mine = solve(k, a, MODES["old"])
            theirs = bc.baker_upper_bound(k, a)
            total += 1
            if mine != theirs:
                bad += 1
                print("MISMATCH", k, a, mine, theirs)
    return total, bad


def table(ks, avals, modes):
    out = {}
    for a in avals:
        for k in ks:
            for name in modes:
                if name in ("last+kit", "old+kit") and a != 0:
                    continue
                out[(a, k, name)] = log10_int(solve(k, a, MODES[name]))
    return out


if __name__ == "__main__":
    total, bad = cross_check_old()
    print(f"old-bound cross-check against baker_chain.baker_upper_bound: {total} entries, {bad} mismatches")
    tb = table(range(0, 33), (0, 1), list(MODES))
    names = list(MODES)
    for a in (0, 1):
        print(f"a={a}")
        print(" k  " + "  ".join(f"{n:>12s}" for n in names))
        for k in range(0, 33):
            row = []
            for n in names:
                v = tb.get((a, k, n))
                row.append(f"{v:12.3f}" if v is not None else f"{'-':>12s}")
            print(f"{k:2d}  " + "  ".join(row))
