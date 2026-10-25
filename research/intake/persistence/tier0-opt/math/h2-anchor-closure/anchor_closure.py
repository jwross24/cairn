import itertools
from collections import Counter, defaultdict

MOD5 = 5 ** 5


class Anchor:
    def __init__(self, y, a):
        self.y = y
        self.a = a
        self.w = a + 9
        assert 9 <= self.w <= 96
        self.m2 = 1 << self.w
        self.pow10 = [10 ** e for e in range(self.w)]
        self.p2 = [t % self.m2 for t in self.pow10]
        self.p5 = [t % MOD5 for t in self.pow10]
        self.start = (y % self.m2, y % MOD5)
        self.trans = {}
        self.sigcache = {}
        self.witnesses = None

    def step(self, e, st):
        key = (e, st)
        hit = self.trans.get(key)
        if hit is not None:
            return hit
        q2, q5 = st
        par = (q2 >> e) & 1
        out = []
        for l in range(par, 10, 2):
            n2 = (q2 - l * self.p2[e]) % self.m2
            n5 = (q5 - l * self.p5[e]) % MOD5 if e < 5 else 0
            out.append((l, (n2, n5)))
        self.trans[key] = out
        return out

    def count_window(self, window):
        hit = self.sigcache.get(window)
        if hit is not None:
            return hit
        masks = {e: dict(c) for e, c in window}
        layer = {self.start: 1}
        for e in range(self.w):
            if e == 5:
                layer = {st: wt for st, wt in layer.items() if st[1] == 0}
            if not layer:
                break
            cls = masks.get(e)
            nxt = defaultdict(int)
            for st, wt in layer.items():
                for l, ns in self.step(e, st):
                    if l == 1:
                        nxt[ns] += wt
                    elif cls is not None and l in cls:
                        nxt[ns] += wt * cls[l]
            layer = nxt
        total = sum(layer.values())
        self.sigcache[window] = total
        return total

    def build_witnesses(self, cap=2_000_000):
        out = []
        count = 0

        def rec(e, st, acc):
            nonlocal count
            if e == 5 and st[1] != 0:
                return
            if e == self.w:
                out.append(tuple(acc))
                count += 1
                if count > cap:
                    raise OverflowError
                return
            for l, ns in self.step(e, st):
                if l != 1:
                    acc.append((e, l))
                rec(e + 1, ns, acc)
                if l != 1:
                    acc.pop()

        rec(0, self.start, [])
        self.witnesses = out
        return out

    def count_by_witnesses(self, window):
        cls = {e: dict(c) for e, c in window}
        total = 0
        for wit in self.witnesses:
            wt = 1
            for e, l in wit:
                c = cls.get(e)
                if c is None or l not in c:
                    wt = 0
                    break
                wt *= c[l]
            total += wt
        return total


def window_of(anchor, de):
    by = defaultdict(Counter)
    for d, e in de:
        by[e][d] += 1
    window = tuple(sorted((e, tuple(sorted(c.items()))) for e, c in by.items() if e < anchor.w))
    high = [sum(c.values()) for e, c in by.items() if e >= anchor.w]
    mult = 1
    for n in high:
        mult *= 1 + n
    return window, mult


def decide(anchor, de):
    window, mult = window_of(anchor, de)
    return anchor.count_window(window) * mult, window
