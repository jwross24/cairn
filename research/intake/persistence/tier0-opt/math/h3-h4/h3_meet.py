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


def phi_meet(k, a, nu, j, zmode, ctx=mp):
    logb = ctx.log(ctx.mpf(10))
    pa = ctx.mpf(1)
    for al in H.alphas_for(a):
        pa = pa * ctx.log(ctx.mpf(al))
    t0 = len(H.alphas_for(a))
    bm = H.bmax(ctx, a, nu)
    tt = 1 + ctx.log(bm)
    k0 = H.matveev_c(t0, ctx) * pa * tt
    k1 = H.matveev_c(t0 + 1, ctx) * pa * tt
    lu = ctx.log(ctx.mpf(80))
    lv = ctx.log(ctx.mpf(9))
    if j == 0:
        x = ctx.mpf(0)
    else:
        s = (k0 + lu) / logb
        for _ in range(1, j):
            s = s + (lu + k1 * (s * logb + lv)) / logb
        x = s
    if zmode == "codex":
        lb = 1 + ctx.log(frac_b(ctx, nu))
        tlogs = 4
        yk = yu_const(4, ctx) * ctx.log(ctx.mpf(3)) * ctx.log(ctx.mpf(7)) * lb
        y = yk
        zk = yk
    else:
        lb = ctx.log(bm)
        tlogs = 4 if a >= 1 else 3
        y = yu_const(tlogs, ctx) * ctx.log(ctx.mpf(3)) * ctx.log(ctx.mpf(7)) * lb
        if zmode == "audit":
            zk = y
        else:
            zk = ctx.mpf(0) if a >= 1 else H.ecap_bl(ctx, nu)
    z = zk
    for _ in range(j, k):
        z = y * (z * logb + lu)
    return x + z


def frac_b(ctx, nu):
    return ctx.mpf("3.4") * nu + 2


def solve_meet(k, a, j, zmode):
    def f(nu, ctx=mp):
        return phi_meet(k, a, nu, j, zmode, ctx)

    x = max(mpf(k + 1) / log(mpf(10)) + 1, mpf(2))
    for _ in range(200):
        xn = log(f(mpf(10) ** x)) / log(mpf(10))
        if xn <= x:
            break
        x = xn
    step = mpf("0.001")
    for _ in range(200000):
        n = mpf(10) ** x
        if n >= exp(mpf(k + 1)) and f(n) * (1 + mpf("1e-6")) < n:
            n_int = H.exact_int_at_least(x)
            s = str(n_int)
            m = int(s.rstrip("0"))
            e = len(s) - len(s.rstrip("0"))
            niv = iv.mpf(m) * iv.mpf(10) ** e
            if niv.a > iv.exp(iv.mpf(k + 1)).b and f(niv, iv).b < niv.a:
                return n_int
        x += step
    raise RuntimeError("none")


def best(k, a, zmode):
    res = []
    for j in range(0, k + 1):
        res.append((H.log10_int(solve_meet(k, a, j, zmode)), j))
    return min(res)


if __name__ == "__main__":
    import baker_chain as bc
    print("k a | old G | last-form | codex-replica (j) | audit (j) | audit+improved Zk (j)")
    for a, k in ((1, 22), (1, 31), (1, 44), (0, 22), (0, 31), (0, 44), (1, 6), (1, 8), (0, 6), (0, 7), (0, 10)):
        old = H.log10_int(bc.baker_upper_bound(k, a))
        last = H.log10_int(H.solve(k, a, H.MODES["last"]))
        c = best(k, a, "codex")
        au = best(k, a, "audit")
        im = best(k, a, "improved")
        print(f"{k} {a} | {old:.1f} | {last:.1f} | {c[0]:.1f} (j={c[1]}) | {au[0]:.1f} (j={au[1]}) | {im[0]:.1f} (j={im[1]})", flush=True)
