import sys

sys.dont_write_bytecode = True
sys.path.insert(0, "/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/math/h3-h4")

from mpmath import mp, mpf, log, exp, iv
import h3_sharp as H

mp.dps = 60
iv.prec = 256


def yu_const(t, ctx):
    e = ctx.exp(ctx.mpf(1))
    lp = ctx.log(ctx.mpf(5))
    return (16 * e) ** (2 * (t + 1)) * ctx.mpf(t) ** ctx.mpf("2.5") * ctx.log(ctx.mpf(2 * t)) ** 2 * 5 / lp ** 2


def pieces(ctx, nu, k, a, m, ymult=1, bl=False):
    l10, l2, l3, l7, l80, l9, l71 = [ctx.log(ctx.mpf(x)) for x in (10, 2, 3, 7, 80, 9, 71)]
    bm = ctx.mpf("2.1") * nu + 2 + (0 if a == 0 else 0)
    bmax_all = bm
    tt = 1 + ctx.log(bmax_all)
    if a == 0:
        k0 = H.matveev_c(3, ctx) * l3 * l7 * l10 * tt
    else:
        k0 = H.matveev_c(4, ctx) * l2 * l3 * l7 * l10 * tt
    k1 = H.matveev_c(4, ctx) * l3 * l7 * l10 * tt
    y1 = yu_const(3, ctx) * l3 * l7 * ctx.log(bmax_all) * ymult
    at = a * l2
    s = (k0 + l80) / l10
    x = {1: s}
    for j in range(1, k):
        s = s + (l80 + k1 * (s * l10 + l9 + at)) / l10
        x[j + 1] = s
    q = {}
    if a >= 1:
        q[k] = ctx.mpf(0)
        cur = y1 * (at + l71)
        q[k - 1] = cur
        for j in range(k - 2, 0, -1):
            cur = y1 * (at + cur * l10 + l80)
            q[j] = cur
    else:
        cur = H.ecap_bl(ctx, nu) if bl else y1 * 1
        q[k] = cur
        for j in range(k - 1, 0, -1):
            cur = y1 * (cur * l10 + l80)
            q[j] = cur
    return x[m] + q[m]


def solve(k, a, m, ymult=1, bl=False):
    x = mpf(30)
    for _ in range(400):
        xn = log(pieces(mp, mpf(10) ** x, k, a, m, ymult, bl)) / log(mpf(10))
        if abs(xn - x) < mpf("1e-12"):
            break
        x = xn
    step = mpf("0.0005")
    for _ in range(400000):
        n = mpf(10) ** x
        if n >= exp(mpf(k + 1)) and pieces(mp, n, k, a, m, ymult, bl) * (1 + mpf("1e-6")) < n:
            n_int = H.exact_int_at_least(x)
            s = str(n_int)
            mm = int(s.rstrip("0"))
            e = len(s) - len(s.rstrip("0"))
            niv = iv.mpf(mm) * iv.mpf(10) ** e
            if niv.a > iv.exp(iv.mpf(k + 1)).b and pieces(iv, niv, k, a, m, ymult, bl).b < niv.a:
                return n_int
        x += step
    raise RuntimeError("none")


def best(k, a, ymult=1, bl=False):
    out = []
    for m in range(1, k + 1):
        out.append((H.log10_int(solve(k, a, m, ymult, bl)), m))
    return min(out)


if __name__ == "__main__":
    for k in (31, 44):
        for a in (0, 1, 40):
            v = best(k, a)
            w = best(k, a, 1, True) if a == 0 else v
            print(f"k={k} a={a}: B3-style {v[0]:.2f} (m={v[1]}); with BL two-log E_k cap {w[0]:.2f} (m={w[1]})", flush=True)
