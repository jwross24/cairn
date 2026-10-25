import sys, os, json, math, random, time
from collections import Counter

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from n1lib import *
from n1solve import *
from n1cert import *
import n1diff as ND


def genuine_test(a, b, c, E, D, lam, node_cap=2):
    y = 2 ** a * 3 ** b * 7 ** c
    ds = [int(ch) for ch in str(y)[::-1]]
    K = LMAX * D
    s = LMAX * E
    assert len(ds) > K + 2
    co0 = Coset((b, c), lam.u1, lam.u2)
    co = cut_coset(co0, a, y % 10 ** s, s)
    assert co is not None and co.contains(b, c)
    De = []
    pos_of = []
    for i in range(K):
        if ds[i] != 1:
            De.append((ds[i], i % LMAX))
            pos_of.append(i)
    order = sorted(range(len(De)), key=lambda j: (De[j], pos_of[j]))
    De = [De[j] for j in order]
    pos_of = [pos_of[j] for j in order]
    assigned = tuple((j, pos_of[j] // LMAX) for j in range(len(De)) if pos_of[j] < s)
    sysd = build_system(co, assigned, a, De, E, D)
    u1, u2 = co.u1, co.u2
    det = u1[0] * u2[1] - u2[0] * u1[1]
    db, dc = b - co.v0[0], c - co.v0[1]
    z1n = db * u2[1] - dc * u2[0]
    z2n = -db * u1[1] + dc * u1[0]
    assert z1n % det == 0 and z2n % det == 0
    z1, z2 = z1n // det, z2n // det
    x = [1 if (e + LMAX * t < K and ds[e + LMAX * t] == d and d != 1) else 0 for (d, e, t) in sysd['vars']]
    M = sysd['M']
    lhs = (sysd['alpha'][0] * z1 + sysd['alpha'][1] * z2 + sum(o * xi for o, xi in zip(sysd['omega'], x))) % M
    lin_ok = lhs == sysd['beta'] % M
    ex_ok = lattice_point_value(b, c, a, K) == target_value(sysd['Tbase'], sysd['vars'], x, K)
    adm = valid_x(x, sysd['vars'], sysd['types'])
    rho2 = b * b + c * c
    res, st = certify_branching(sysd, rho2, node_cap=node_cap)
    return dict(a=a, b=b, c=c, E=E, D=D, m=len(sysd['vars']), linear_ok=lin_ok, exact_ok=ex_ok, admissible=adm,
                exact_system=sysd['exact'], certified_at_planted=(res is True), nodes=st['nodes'])


if __name__ == '__main__':
    lam = ND.load_lam()
    rng = random.Random(int(sys.argv[1]) if len(sys.argv) > 1 else 7)
    ntr = int(sys.argv[2]) if len(sys.argv) > 2 else 6
    bad = 0
    tot = 0
    for ED in ((1, 2), (2, 3), (2, 4)):
        for _ in range(ntr):
            a = rng.choice([0, 0, 1, 2, 3, 5, 9, 17])
            b = rng.randrange(900, 1400)
            c = rng.randrange(500, 900)
            r = genuine_test(a, b, c, ED[0], ED[1], lam)
            tot += 1
            ok = r['linear_ok'] and r['exact_ok'] and r['admissible'] and not r['certified_at_planted']
            bad += (not ok)
            print(r, 'OK' if ok else 'FAIL', flush=True)
    print('genuine S-unit plants', tot, 'failures', bad)
