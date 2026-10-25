import sys, os, json, math, random, time
from decimal import Decimal, getcontext
from collections import Counter

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
getcontext().prec = 60
from n1lib import *
from n1tier import *
from n1cert import *
from lattice import Coset as _Coset, _reduce
import n1diff as ND
from n1scale import tierc_setup, U_from_log10

FROZEN = ND.FROZEN


def child_coset(co, a, Tc, s, K):
    """depth-(s/96) coset co refined by 2^a 3^b 7^c = Tc (mod 10^K) with K <= 2 s - a, by Theorem 1 (no discrete logarithms)."""
    assert K <= 2 * s - a and K > s
    h = K - s
    W2, W5 = 2 ** (K - a), 5 ** K
    v0, u1, u2 = co.v0, co.u1, co.u2

    def G(b, c, mod):
        return pow(3, b, mod) * pow(7, c, mod) % mod
    G02, G05 = G(v0[0], v0[1], W2), G(v0[0], v0[1], W5)
    gu2, gu5 = G(u1[0], u1[1], W2), G(u1[0], u1[1], W5)
    gv2, gv5 = G(u2[0], u2[1], W2), G(u2[0], u2[1], W5)
    s2 = s - a
    tau2 = (Tc >> a) % W2
    tau5 = Tc * pow(2 ** a, -1, W5) % W5
    rho2, rho5 = (G02 - tau2) % W2, (G05 - tau5) % W5
    if rho2 % 2 ** s2 or rho5 % 5 ** s:
        return None
    m2, m5 = 2 ** h, 5 ** h
    al2 = [G02 * (gu2 - 1) // 2 ** s2 % m2, G02 * (gv2 - 1) // 2 ** s2 % m2]
    al5 = [G05 * (gu5 - 1) // 5 ** s % m5, G05 * (gv5 - 1) // 5 ** s % m5]
    be2 = -(rho2 // 2 ** s2) % m2
    be5 = -(rho5 // 5 ** s) % m5
    M = m2 * m5
    c2 = m5 * pow(m5, -1, m2)
    c5 = m2 * pow(m2, -1, m5)
    al = [(al2[i] * c2 + al5[i] * c5) % M for i in range(2)]
    be = (be2 * c2 + be5 * c5) % M
    zc = _Coset((0, 0), (1, 0), (0, 1)).intersect(al[0], al[1], be, M)
    if zc is None:
        return None
    z0, k1, k2 = zc.v0, zc.u1, zc.u2
    nv0 = (v0[0] + z0[0] * u1[0] + z0[1] * u2[0], v0[1] + z0[0] * u1[1] + z0[1] * u2[1])
    n1 = (k1[0] * u1[0] + k1[1] * u2[0], k1[0] * u1[1] + k1[1] * u2[1])
    n2 = (k2[0] * u1[0] + k2[1] * u2[0], k2[0] * u1[1] + k2[1] * u2[1])
    n1, n2 = _reduce(n1, n2)
    return Coset(nv0, n1, n2)


def same_coset(c1, c2):
    if c1.index() != c2.index():
        return False
    return c1.contains(*c2.v0) and c1.contains(c2.v0[0] + c2.u1[0], c2.v0[1] + c2.u1[1]) and c1.contains(c2.v0[0] + c2.u2[0], c2.v0[1] + c2.u2[1])


def Tfor(placed, K):
    return Lfor(placed, K)


def children(co, a, types, placed, e, lift=True):
    """all unlabeled block-e fillings of the remaining digits, with the refined coset."""
    rem = tinsert(types, [x for lst in placed.values() for x in lst])
    for ch in block_choices(rem):
        newp = dict(placed)
        newp[e] = ch
        K = LMAX * (e + 1)
        L = Lfor(newp, K)
        if v2(L) != a or L % 5 == 0:
            continue
        if lift:
            c2 = child_coset(co, a, L, LMAX * e, K)
        else:
            c2 = cut_coset(co, a, L, K)
        if c2 is not None:
            yield newp, c2


if __name__ == '__main__':
    mode = sys.argv[1]
    co0, a, types = tierc_setup()
    s1 = json.load(open(os.path.join(FROZEN, 'tierc_surv1.json')))
    surv1 = [(tuple(map(tuple, ch)), Coset(tuple(v0), tuple(u1), tuple(u2))) for ch, v0, u1, u2 in s1]
    if mode == 'liftcheck':
        rng = random.Random(5)
        ok = bad = 0
        for ch, co1 in surv1:
            placed = {0: ch}
            kids = list(children(co1, a, types, placed, 1, lift=True))
            ref = {tuple(sorted(p[1])): c for p, c in children(co1, a, types, placed, 1, lift=False)} if False else None
            pick = rng.sample(kids, 12)
            for newp, c in pick:
                L = Lfor(newp, 192)
                c_ref = cut_coset(co1, a, L, 192)
                good = same_coset(c, c_ref)
                ok += good
                bad += (not good)
            gkids = []
            for newp, c in rng.sample(kids, 3):
                for newp2, c2 in rng.sample(list(children(c, a, types, newp, 2, lift=True)), 4):
                    L = Lfor(newp2, 288)
                    c_ref = cut_coset(c, a, L, 288)
                    good = same_coset(c2, c_ref)
                    ok += good
                    bad += (not good)
        print('lift vs discrete-log cut: equal', ok, 'different', bad)
    elif mode == 'family':
        fam = int(sys.argv[2])
        E = 3
        D = 6
        logU = float(sys.argv[3]) if len(sys.argv) > 3 else 281.51
        rho2 = disc_radius2(U_from_log10(logU))
        limit = int(sys.argv[4]) if len(sys.argv) > 4 else 0
        ch, co1 = surv1[fam]
        placed0 = {0: ch}
        nb = ncert = nfail = 0
        t0 = time.time()
        tl = tc = 0.0
        minslack = None
        fails = []
        for p1, c1 in children(co1, a, types, placed0, 1):
            for p2, c2 in children(c1, a, types, p1, 2):
                ta = time.time()
                De, assigned = to_labeled(types, p2)
                sysd = build_system(c2, assigned, a, De, E, D)
                tb = time.time()
                res, st = certify_branching(sysd, rho2, node_cap=400)
                tcc = time.time()
                tl += tb - ta
                tc += tcc - tb
                nb += 1
                if res is True:
                    ncert += 1
                else:
                    nfail += 1
                    fails.append((sorted(p2[0]), sorted(p1[1]), sorted(p2[2]), res, st['nodes']))
                if nb % 2000 == 0:
                    print(json.dumps(dict(family=fam, bases=nb, certified=ncert, failed=nfail, elapsed=round(time.time() - t0), t_build=round(tl, 1), t_cert=round(tc, 1))), flush=True)
                if limit and nb >= limit:
                    break
            if limit and nb >= limit:
                break
        print(json.dumps(dict(family=fam, DONE=True, bases=nb, certified=ncert, failed=nfail, elapsed=round(time.time() - t0), t_build=round(tl, 1), t_cert=round(tc, 1), fails=fails[:20])), flush=True)
