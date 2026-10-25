import sys, os, math, random, time, itertools
from collections import Counter
from functools import lru_cache

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from n1lib import *

TIERC_CLASSES = {0: [3], 1: [2], 2: [2, 7], 3: [2], 4: [2, 3], 5: [2] * 8, 6: [2] * 6, 7: [2] * 2,
                 8: [2] * 2 + [3] * 2, 9: [2] + [3] * 3}


def tierc_types(classes=None):
    classes = classes or TIERC_CLASSES
    t = Counter()
    for e, l in classes.items():
        for d in l:
            t[(d, e)] += 1
    return t


def block_choices(rem):
    """unlabeled choices for one block: per class none or one value with remaining count."""
    byc = {}
    for (d, e), c in rem.items():
        if c > 0:
            byc.setdefault(e, []).append(d)
    classes = sorted(byc)
    opts = [[None] + sorted(byc[e]) for e in classes]
    for combo in itertools.product(*opts):
        yield [(d, e) for d, e in zip(combo, classes) if d is not None]


def count_blocks(rem, nblocks):
    """number of unlabeled fillings of nblocks blocks given remaining counts (classes independent)."""
    byc = {}
    for (d, e), c in rem.items():
        byc.setdefault(e, {})[d] = c
    total = 1
    for e, dd in byc.items():
        vals = sorted(dd)
        caps = tuple(dd[v] for v in vals)

        @lru_cache(None)
        def f(t, r):
            if t == nblocks:
                return 1
            s = f(t + 1, r)
            for i, x in enumerate(r):
                if x > 0:
                    nr = list(r)
                    nr[i] -= 1
                    s += f(t + 1, tuple(nr))
            return s
        total *= f(0, caps)
    return total


def tinsert(types, placed):
    rem = Counter(types)
    for (d, e) in placed:
        rem[(d, e)] -= 1
    return rem


def assigned_to_Tbase_digits(types):
    pass


class UBase:
    """unlabeled base: placed[t] = list of (d, e) at block t (t < E); stands in for (assigned, De) of build_system."""
    pass


def to_labeled(types, placed_by_block):
    """convert an unlabeled placement into (De, assigned) in the labeled format of build_system."""
    De = []
    for (d, e), c in sorted(types.items()):
        De += [(d, e)] * c
    used = set()
    assigned = []
    for t, lst in placed_by_block.items():
        for (d, e) in lst:
            j = next(i for i, x in enumerate(De) if x == (d, e) and i not in used)
            used.add(j)
            assigned.append((j, t))
    return De, tuple(sorted(assigned))


def Lfor(placed_by_block, K):
    RK = (10 ** K - 1) // 9
    L = RK
    for t, lst in placed_by_block.items():
        for (d, e) in lst:
            L += (d - 1) * 10 ** (e + LMAX * t)
    return L


def depth1_survivors(co0, a, types):
    out = []
    for ch in block_choices(types):
        L = Lfor({0: ch}, LMAX)
        if v2(L) != a or L % 5 == 0:
            continue
        co2 = cut_coset(co0, a, L, LMAX)
        if co2 is not None:
            out.append((ch, co2))
    return out


def extend(co, a, types, placed, tnew, rng=None, tries=1000):
    """random admissible child at block tnew (any choice survives by saturation; verified by the cut)."""
    rem = tinsert(types, [x for lst in placed.values() for x in lst])
    choices = list(block_choices(rem))
    for _ in range(tries):
        ch = rng.choice(choices)
        newp = dict(placed)
        newp[tnew] = ch
        K = LMAX * (tnew + 1)
        L = Lfor(newp, K)
        if v2(L) != a or L % 5 == 0:
            continue
        co2 = cut_coset(co, a, L, K)
        if co2 is not None:
            return newp, co2
    return None
