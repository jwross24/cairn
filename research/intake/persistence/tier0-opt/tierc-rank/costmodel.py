import sys, json, math, random
from collections import Counter
from math import comb

PER_CASE = 640000
T_CERT = 0.02319973129992738
T_VERIFY = 0.02166669526143791
K31_NODES = 440640
K31_CLASSES = {0: [3], 1: [2], 2: [2, 7], 3: [2], 4: [2, 3], 5: [2] * 8, 6: [2] * 6, 7: [2] * 2, 8: [2] * 2 + [3] * 2, 9: [2] + [3] * 3}


def v2(n):
    return (n & -n).bit_length() - 1


def groups(words):
    return Counter((d, e) for d, e in words)


def model_nodes(g, a, E):
    low = 1
    for (d, e), c in g.items():
        if e < a + 9:
            low *= comb(c + E, E)
    return low / PER_CASE


def calib():
    g = Counter()
    for e, l in K31_CLASSES.items():
        for d in l:
            g[(d, e)] += 1
    return K31_NODES / model_nodes(g, 0, 3)


def per_pattern(rec, kappa, E=3):
    a = v2(rec["y"])
    g = groups(rec["words"])
    n1 = 1
    base = 1
    for (d, e), c in g.items():
        if e < a + 9:
            n1 *= c + 1
            base *= comb(c + E, E) / (c + 1)
    p = -math.expm1(-n1 / PER_CASE)
    nodes = max(kappa * model_nodes(g, a, E), base)
    return a, len(rec["words"]), n1, p, nodes


def main():
    path = sys.argv[1]
    pop_lo, pop_mid, pop_hi = float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4])
    kappa = calib()
    rows = [json.loads(l) for l in open(path)]
    pp = [per_pattern(r, kappa) for r in rows]
    n = len(pp)
    psurv = [x[3] for x in pp]
    cost = [x[3] * x[4] * (T_CERT + T_VERIFY) for x in pp]
    cost_a = [x[3] * x[4] * T_CERT for x in pp]
    rng = random.Random(3)

    def boot(v, reps=4000):
        out = []
        for _ in range(reps):
            s = 0.0
            for _ in range(n):
                s += v[rng.randrange(n)]
            out.append(s / n)
        out.sort()
        return out[100], out[3899], sum(v) / n

    ps = boot(psurv)
    cs = boot(cost)
    ca = boot(cost_a)
    res = {
        "n_patterns": n,
        "kappa": kappa,
        "mean_p_depth1_survive": ps,
        "mean_core_seconds_per_anchored_pattern_certify_plus_verify": cs,
        "mean_core_seconds_per_anchored_pattern_certify_only": ca,
        "median_k": sorted(x[1] for x in pp)[n // 2],
        "median_a": sorted(x[0] for x in pp)[n // 2],
        "frac_ncases1_ge_640000": sum(1 for x in pp if x[2] >= PER_CASE) / n,
        "survivors_total": [ps[0] * pop_lo, ps[2] * pop_mid, ps[1] * pop_hi],
        "core_days_total_cert_plus_verify": [cs[0] * pop_lo / 86400, cs[2] * pop_mid / 86400, cs[1] * pop_hi / 86400],
        "core_days_total_cert_only": [ca[0] * pop_lo / 86400, ca[2] * pop_mid / 86400, ca[1] * pop_hi / 86400],
        "core_days_if_32s_per_survivor": [ps[0] * pop_lo * 32 / 86400, ps[2] * pop_mid * 32 / 86400, ps[1] * pop_hi * 32 / 86400],
    }
    print(json.dumps(res, indent=1))


main()
