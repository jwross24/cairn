import sys

sys.dont_write_bytecode = True
sys.path.insert(0, "/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/math/yu-audit")

from mpmath import mp, mpf, log, log10

import yu_consts as Y

mp.dps = 50

L = log
l10, l2, l3, l7, l80, l9, l71 = [L(mpf(x)) for x in (10, 2, 3, 7, 80, 9, 71)]


def matveev(t):
    return mpf("1.4") * mpf(30) ** (t + 3) * mpf(t) ** mpf("4.5")


def make_F(variant):
    # F(H, B): bound on E_j given the height H of the folded rational and the exponent bound B.
    if variant == "bk":
        c = Y.bk(3)
        return lambda H, B: c * l3 * l7 * L(B) * H
    if variant == "yu190":
        c = Y.yu190(3, 10)
        return lambda H, B: c * l3 * l7 * L(B) * H
    if variant == "thm3":
        c = Y.thm3(3)
        return lambda H, B: c * l3 * l7 * L(B) * H
    if variant == "t1_07":
        c = Y.thm1(3)
        return lambda H, B: c * l3 * l7 * L(B) * H
    if variant == "t1_13":
        c = Y.thm1_2013(3)
        return lambda H, B: c * l3 * l7 * max(L(B), Y.LOG5) * H
    if variant == "t2_13":
        c = 4 * Y.c2_2013(3)
        return lambda H, B: c * l3 * l7 * max(L(B), Y.LOG5) * H
    if variant == "main13":
        c = Y.c2_2013(3)
        G = max(Y.g2_2013(3), 4 * Y.LOG5)
        w = Y.omega1()
        d2 = Y.thm1_2013(2)
        d3 = Y.thm1_2013(3) * mpf(3) / 96

        def F(H, B):
            ind = c * l3 * l7 * H * max(G, L(w * (B / H + 1 / l3)))
            bp = 2 * B
            dep = max(d2 * l3 * l7 * L(bp), d3 * l3 * l7 * L(bp))
            return max(ind, dep)

        return F
    if variant == "main_rig":
        c = Y.c2_theorem3(3)
        G = Y.g2(3)
        w = Y.omega(2)
        e2 = Y.thm1(2)
        e1 = Y.thm1(1)
        e3 = Y.thm1(3) * (Y.LOG5 / (10 * 7 * 2))

        def F(H, B):
            ind = c * l3 * l7 * H * max(G, L(w * (B / H + 1 / l3)))
            bp = 2 * B
            dep = max(e2 * l3 * l7 * L(bp), e1 * l7 * L(bp), e3 * l3 * l7 * L(bp))
            return max(ind, dep)

        return F
    if variant == "main":
        c = Y.c2_theorem3(3)
        G = Y.g2(3)
        w = Y.omega(2)
        c2s = Y.thm3(2)
        c1s = Y.thm3(1)
        cm1 = Y.thm3(3) / (Y.KAPPA2 * 2)

        def F(H, B):
            ind = c * l3 * l7 * H * max(G, L(w * (B / H + 1 / l3)))
            bp = 2 * B
            dep = max(c2s * l3 * l7 * L(bp), c1s * l7 * L(bp), cm1 * l3 * l7 * L(bp))
            return max(ind, dep)

        return F
    raise ValueError(variant)


def chain(nu, k, a, F, bottom=1):
    B = mpf("2.1") * nu + 2
    TA = 1 + L(B)
    if a == 0:
        K0 = matveev(3) * l3 * l7 * l10 * TA
    else:
        K0 = matveev(4) * l2 * l3 * l7 * l10 * TA
    K1 = matveev(4) * l3 * l7 * l10 * TA
    at = a * l2
    s = (K0 + l80) / l10
    X = {1: s}
    for j in range(1, k):
        s = s + (l80 + K1 * (s * l10 + l9 + at)) / l10
        X[j + 1] = s
    q = {}
    if a >= 1:
        cur = F(at + l71, B)
        q[k] = mpf(0)
        q[k - 1] = cur
        for j in range(k - 2, 0, -1):
            cur = F(at + cur * l10 + l80, B)
            q[j] = cur
    else:
        cur = F(mpf(bottom), B)
        q[k] = cur
        for j in range(k - 1, 0, -1):
            cur = F(cur * l10 + l80, B)
            q[j] = cur
    return X, q


def bound(k, a, m, F):
    nu = mpf(10) ** 30
    for _ in range(4000):
        X, q = chain(nu, k, a, F)
        new = X[m] + q[m]
        if abs(new - nu) < nu * mpf(10) ** -12:
            return new
        nu = new
    raise RuntimeError("no convergence")


def best(k, a, F):
    out = []
    for m in range(1, k + 1):
        out.append((float(log10(bound(k, a, m, F))), m))
    return min(out)


if __name__ == "__main__":
    ks = [(31, 0), (44, 0), (31, 1), (44, 1)]
    for variant in ("bk", "yu190", "t1_07", "t1_13", "thm3", "main", "t2_13", "main13", "main_rig"):
        F = make_F(variant)
        for k, a in ks:
            v, m = best(k, a, F)
            print(f"{variant} k={k} a={a}: log10 G' = {v:.2f} (m={m})", flush=True)
