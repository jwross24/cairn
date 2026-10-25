import sys, os, json, math, random, time
from decimal import Decimal, getcontext
from collections import Counter

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
getcontext().prec = 60
from n1lib import *
from n1tier import *
from n1cert import *
from n1tierc import info_budget
import n1diff as ND
from n1scale import tierc_setup, sample_base, U_from_log10

FROZEN = ND.FROZEN


def system_custom(co, placed, a, free_types, E, D):
    De = []
    assigned = []
    for t, lst in sorted(placed.items()):
        for (d, e) in lst:
            assigned.append((len(De), t))
            De.append((d, e))
    for (d, e), c in sorted(free_types.items()):
        De += [(d, e)] * c
    return build_system(co, tuple(assigned), a, De, E, D)


def free_set(nclasses, nvals, mult=1):
    t = Counter()
    for e in range(nclasses):
        for v in range(nvals):
            t[(2 + v if v < 2 else 7, e)] += mult
    return t


if __name__ == '__main__':
    E = int(sys.argv[1])
    Dlist = [int(x) for x in sys.argv[2].split(',')]
    logU = float(sys.argv[3])
    bkzlist = [int(x) for x in sys.argv[4].split(',')] if len(sys.argv) > 4 else [0]
    seed = int(sys.argv[5]) if len(sys.argv) > 5 else 1
    rng = random.Random(seed)
    co0, a, types = tierc_setup()
    s1 = json.load(open(os.path.join(FROZEN, 'tierc_surv1.json')))
    surv1 = [(tuple(map(tuple, ch)), Coset(tuple(v0), tuple(u1), tuple(u2))) for ch, v0, u1, u2 in s1]
    placed, co = sample_base(co0, a, types, E, rng, surv1)
    U = U_from_log10(logU)
    rho2 = disc_radius2(U)
    for D in Dlist:
        for ncl in (3, 5, 8, 10, 14, 20, 30):
            for nv in (1, 2):
                ft = free_set(ncl, nv)
                sysd = system_custom(co, placed, a, ft, E, D)
                b = info_budget(sysd, rho2)
                for bkz in bkzlist:
                    t0 = time.time()
                    st = {'nodes': 0, 'certs': 0, 'max_depth': 0}
                    res, st = certify_branching(sysd, rho2, node_cap=1, bkz=bkz, stats=st)
                    dt = time.time() - t0
                    print(json.dumps(dict(E=E, D=D, classes=ncl, vals=nv, vars=b['vars'], groups=b['groups'], logM=round(b['logM'], 1),
                                          logZ=round(b['logZ1'], 1), slack=round(b['predicted_slack'], 1), bkz=bkz, certified=(res is True), t=round(dt, 2))), flush=True)
