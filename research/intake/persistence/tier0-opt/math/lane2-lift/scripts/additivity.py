import os, sys, json, random
from fractions import Fraction
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import runbin
from cfgparse import parse

S = runbin.S
HERE = runbin.HERE
EQS = sys.argv[1:] or ["124416_222222222399", "9437184_2234688888", "393216_22222222222222226", "3211264_222222222222222277"]
res = []
for eq in EQS:
    dump = os.path.join(HERE, "runs", f"{eq}_dump.txt")
    rho = os.environ.get("ADD_RHO", "1e-3")
    r = runbin.run(os.path.join(HERE, "src", "measure"), eq, "dump", env={"MEAS_RHO": rho, "MEAS_SEED": "7", "MEAS_DUMPFILE": dump, "MEAS_DUMPN": "4000", "MEAS_DUMPEVERY": "1", "MEAS_PSTRIDE": os.environ.get("ADD_PSTRIDE", "1")})
    cfg = parse(f"{S}/{eq}/cfgL24.txt")
    Lold, Lnew = cfg["Lold"], cfg["Lnew"]
    ps = [p["p"] for p in cfg["primes"]]
    digits = cfg["digits"]
    parents = [l.split() for l in open(f"{S}/{eq}/parents24.txt")]
    q = cfg["q"]

    def Rn(n):
        return (10 ** n - 1) // 9

    def val(nu, eps):
        return Rn(nu) + sum((d - 1) * 10 ** e for d, e in zip(digits, eps))

    KORD = []
    for p in ps:
        from sympy import n_order
        from math import lcm
        KORD.append(lcm(n_order(pow(3, cfg["Uold"][1][0], p), p) if pow(3, cfg["Uold"][1][0], p) != 1 else 1, n_order(pow(7, cfg["Uold"][0][1], p), p) if pow(7, cfg["Uold"][0][1], p) != 1 else 1))
    stat = {"n": 0, "pass0": 0, "pass1": 0, "pass2": 0, "allcond": 0, "mask0": 0, "mask0_not_cond": 0}
    dsets = [dict() for _ in ps]
    n = bad_y = bad_id = 0
    for l in open(dump):
        t = l.split()
        pidx, nu_c = int(t[1]), int(t[2])
        eps = list(map(int, t[3:3 + q]))
        ys = list(map(int, t[3 + q:3 + q + len(ps)]))
        mask = int(t[3 + q + len(ps)])
        par = parents[pidx]
        nu_p = int(par[1])
        eps_p = list(map(int, par[2:2 + q]))
        Vc = val(nu_c, eps)
        Vp = val(nu_p, eps_p)
        n += 1
        if [Vc % p for p in ps] != ys:
            bad_y += 1
        sn = (nu_c - nu_p) // Lold
        S_ = [j for j in range(q) if eps[j] != eps_p[j]]
        lifted_ok = all(eps[j] - eps_p[j] == Lold for j in S_) and sn in (0, 1)
        Delta = sum(Fraction((digits[j] - 1) * 10 ** eps_p[j]) for j in S_) + Fraction(sn * 10 ** nu_p, 9)
        if not lifted_ok or Vc - Vp != (10 ** Lold - 1) * Delta:
            bad_id += 1
        a_p = int(par[0]); b_p = int(par[2 + q]); c_p = int(par[3 + q])
        conds = []
        dres = []
        for i, p in enumerate(ps):
            T = pow(2, a_p, p) * pow(3, b_p % (p - 1), p) % p * pow(7, c_p % (p - 1), p) % p
            u = ys[i] * pow(T, -1, p) % p
            conds.append(pow(u, KORD[i], p) == 1)
            den = Delta.denominator
            dres.append((Delta.numerator * pow(den, -1, p)) % p)
        stat["n"] += 1
        for i in range(len(ps)):
            stat["pass%d" % i] += conds[i]
        allc = all(conds)
        stat["allcond"] += allc
        stat["mask0"] += (mask == 0)
        stat["mask0_not_cond"] += (mask == 0 and not allc)
        for i in range(len(ps)):
            if conds[i]:
                dsets[i].setdefault(pidx, set()).add(dres[i])
    maxd = [max((len(v) for v in d.values()), default=0) for d in dsets]
    res.append(dict(eq=eq, dumped=n, y_mismatch=bad_y, identity_mismatch=bad_id, cpu=r["cpu"], kord=KORD, stat=stat, max_distinct_delta_residues_among_passers_per_parent=maxd))
    print(json.dumps(res[-1]))
