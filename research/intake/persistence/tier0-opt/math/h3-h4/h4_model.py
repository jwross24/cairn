import sys
from math import comb
from itertools import product

DIG = {2: (1, 0, 0), 3: (0, 1, 0), 4: (2, 0, 0), 6: (1, 1, 0), 7: (0, 0, 1), 8: (3, 0, 0), 9: (0, 2, 0)}
P = 5291005291
RHO = 1 / 49.5
T12_OPT = 10e-9
T12_REF = 46e-9
T_DESC = 25e-6


def multisets(a, b, c):
    ds = sorted(DIG)
    out = []

    def rec(i, ra, rb, rc, cur):
        if i == len(ds):
            if (ra, rb, rc) == (0, 0, 0):
                out.append(dict(cur))
            return
        d = ds[i]
        ea, eb, ec = DIG[d]
        m = 0
        while ra - m * ea >= 0 and rb - m * eb >= 0 and rc - m * ec >= 0:
            if m:
                cur[d] = m
            rec(i + 1, ra - m * ea, rb - m * eb, rc - m * ec, cur)
            if m:
                del cur[d]
            m += 1
            if ea == eb == ec == 0:
                break

    rec(0, a, b, c, {})
    return out


def npat(ms):
    r = 12
    for m in ms.values():
        r *= comb(11 + m, m)
    return r


def lifts(ms):
    num = 1
    den = 1
    for m in ms.values():
        num *= comb(23 + m, m)
        den *= comb(11 + m, m)
    return 2 * num / den


def model(label, a, b, c):
    mss = multisets(a, b, c)
    n = sum(npat(m) for m in mss)
    surv = n * RHO
    lift_children = sum(npat(m) * RHO * lifts(m) for m in mss)
    kmax = max(sum(m.values()) for m in mss)
    print(label, "multisets", len(mss), "kmax", kmax, "patterns %.3e" % n, "survivors %.3e" % surv)
    print("  mean N_M %.3e  mean N_M/P %.1f" % (n / len(mss), n / len(mss) / P))
    print("  enumeration 10ns: %.1f core-days; 46ns: %.1f" % (n * T12_OPT / 86400, n * T12_REF / 86400))
    print("  perfect-listing floor (survivors x 10ns): %.2f core-days" % (surv * T12_OPT / 86400))
    print("  descent at 25us per level-12 survivor: %.3e core-days" % (surv * T_DESC / 86400))
    print("  level-24 children of survivors (2*prod(j+1) expectation): %.3e ; at 6.1us: %.3e core-days" % (lift_children, lift_children * 6.1e-6 / 86400))
    print("  Amdahl: share of enumeration in (enum + descent): %.4f" % (n * T12_OPT / (n * T12_OPT + surv * T_DESC)))
    print("  BCJ-style representation count for k_max digits: C(k,k/2) = %d" % comb(kmax, kmax // 2))


model("71663616 = 2^15 3^7", 15, 7, 0)
model("1783627776 = 2^20 3^5 7^1", 20, 5, 1)
