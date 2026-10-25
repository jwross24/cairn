import sys, os, json, math, random, time
from decimal import Decimal, getcontext
from collections import Counter

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
getcontext().prec = 60
from n1lib import *
from n1tier import *
from n1cert import *
import n1diff as ND

FROZEN = ND.FROZEN


def U_from_log10(x):
    return int(Decimal(10) ** Decimal(str(x)))


def tierc_setup():
    lam = ND.load_lam()
    from descent import factor237
    y = 7626831723
    f = factor237(y)
    assert f == (0, 3, 10)
    co0 = Coset((f[1], f[2]), lam.u1, lam.u2)
    types = tierc_types()
    return co0, 0, types


def sample_base(co0, a, types, E, rng, surv1):
    ch, co = rng.choice(surv1)
    placed = {0: ch}
    for t in range(1, E):
        r = extend(co, a, types, placed, t, rng)
        placed, co = r
    return placed, co


def system_for(co, placed, a, types, E, D, extra_types=None):
    tt = Counter(types)
    if extra_types:
        tt = Counter(tt)
        for k, v in extra_types.items():
            tt[k] += v
    De, assigned = to_labeled(tt, placed)
    return build_system(co, assigned, a, De, E, D)


if __name__ == '__main__':
    what = sys.argv[1] if len(sys.argv) > 1 else 'depth1'
    co0, a, types = tierc_setup()
    t0 = time.time()
    if what == 'depth1':
        surv1 = depth1_survivors(co0, a, types)
        print('depth-1 survivors', len(surv1), 'of', count_blocks(types, 1), f'{time.time()-t0:.0f}s')
        json.dump([[ch, c.v0, c.u1, c.u2] for ch, c in surv1], open(os.path.join(FROZEN, 'tierc_surv1.json'), 'w'))
        for ch, c in surv1:
            rem = tinsert(types, ch)
            print(sorted(ch), 'next-block fillings', count_blocks(rem, 1), 'E=2..5 base counts',
                  [count_blocks(rem, E - 1) for E in (2, 3, 4, 5)])
