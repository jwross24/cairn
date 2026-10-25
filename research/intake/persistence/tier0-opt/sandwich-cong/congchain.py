import sys, os, json, math, time, collections
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cc_lib import *

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
RB = B + "tierc-r2bill/data/"


def rep_groups(pairs, dedup=True):
    g = collections.OrderedDict()
    for d, e in pairs:
        g.setdefault(e, [])
        if (not dedup) or d not in g[e]:
            g[e].append(d)
    return g


def wrap_of(y, nu, pairs):
    R96 = (10 ** 96 - 1) // 9
    V = (10 ** nu - 1) // 9 + sum((d - 1) * 10 ** e for d, e in pairs)
    w, r = divmod(V - y, R96)
    assert r == 0, (y, nu)
    return w


def enum_masks(groups, e2, e5, T, want=False):
    assert e2 <= 58
    M2 = 1 << e2
    M5 = 5 ** e5
    arr2 = np.zeros(1, dtype=np.int64)
    arr5 = np.zeros(1, dtype=np.int64)
    choices = []
    order = []
    free = 1
    for e, ds in groups.items():
        t2 = [((d - 1) * pow(10, e, M2)) % M2 for d in ds]
        t5 = [((d - 1) * pow(10, e, M5)) % M5 for d in ds]
        if not want and not any(t2) and not any(t5):
            free *= 1 + len(ds)
            continue
        n = len(arr2)
        arr2 = np.concatenate([arr2] + [(arr2 + t) % M2 for t in t2])
        arr5 = np.concatenate([arr5] + [(arr5 + t) % M5 for t in t5])
        if want:
            choices = [np.tile(c, 1 + len(ds)) for c in choices]
            choices.append(np.repeat(np.arange(1 + len(ds), dtype=np.int16), n))
        order.append((e, ds))
    ok = ((9 * arr2 - (T % M2)) % M2 == 0) & ((9 * arr5 - (T % M5)) % M5 == 0)
    cnt = int(ok.sum()) * free
    if not want:
        return cnt
    res = set()
    for i in np.nonzero(ok)[0]:
        fx = []
        for k, (e, ds) in enumerate(order):
            c = int(choices[k][i])
            if c:
                fx.append((ds[c - 1], e))
        res.add(frozenset(fx))
    return cnt, res


def predict(y, a, nu, pairs, c96=(9, 5), c480=(10, 5), want=False, dedup=True):
    w = wrap_of(y, nu, pairs)
    groups = rep_groups(pairs, dedup)
    S_all = sum((d - 1) * 10 ** e for d, e in pairs)
    T = 10 ** nu + 9 * S_all + w
    r96 = enum_masks(groups, a + c96[0], c96[1], T, want)
    r480 = enum_masks(groups, a + c480[0], c480[1], T, want) if w == 0 else (0 if not want else (0, set()))
    return w, r96, r480


def factor237(y):
    a = b = c = 0
    while y % 2 == 0: y //= 2; a += 1
    while y % 3 == 0: y //= 3; b += 1
    while y % 7 == 0: y //= 7; c += 1
    assert y == 1
    return a, b, c


def predict2(y, a, nu, pairs, pairs_enum, nu_T, c96=(9, 5), c480=(10, 5), dedup=True):
    w = wrap_of(y, nu, pairs)
    groups = rep_groups(pairs_enum, dedup)
    S_all = sum((d - 1) * 10 ** e for d, e in pairs)
    T = 10 ** nu_T + 9 * S_all + w
    r96 = enum_masks(groups, a + c96[0], c96[1], T)
    r480 = enum_masks(groups, a + c480[0], c480[1], T) if w == 0 else 0
    return w, r96, r480
