from common import *

def clone(rem):
    return {e: Counter(c) for e, c in rem.items()}

class Pat:
    def __init__(self, De, y, a, co0):
        self.De = De; self.y = y; self.a = a; self.co0 = co0
        g = defaultdict(Counter)
        for d, e in De: g[e][d] += 1
        self.g = {e: Counter(c) for e, c in g.items()}
        self.w = a + 9

    def events(self, k0, k1):
        ev = []
        for e in self.g:
            t = 0
            while e + LMAX * t < k1:
                p = e + LMAX * t
                if p >= k0: ev.append((p, e))
                t += 1
        ev.sort()
        return ev

    def root(self):
        return (0, clone(self.g), 0, self.co0)

    def expand(self, L, rem, k0, k1):
        out = []
        y = self.y; w = self.w
        starts = [(L, rem, k0)]
        if k0 == 0:
            starts = []
            top = min(w, k1)
            def low(p, Lc, remc):
                if p == top:
                    starts.append((Lc, remc, top))
                    return
                opts = [None] + [d for d in sorted(remc.get(p, {})) if remc[p][d] > 0]
                for d in opts:
                    dig = 1 if d is None else d
                    L2 = Lc + dig * 10 ** p
                    if (L2 - y) % 2 ** (p + 1): continue
                    if p == 4 and (L2 - y) % 5 ** 5: continue
                    r2 = remc
                    if d is not None:
                        r2 = clone(remc); r2[p][d] -= 1
                        if not r2[p][d]: del r2[p][d]
                    low(p + 1, L2, r2)
            low(0, 0, clone(rem))
        for (Ls, rems, ks) in starts:
            ev = self.events(ks, k1)
            base = Ls + 10 ** ks * ((10 ** (k1 - ks) - 1) // 9)
            def rec(i, Lc, remc, placed):
                if i == len(ev):
                    out.append((Lc, remc))
                    return
                p, e = ev[i]
                rec(i + 1, Lc, remc, placed)
                for d in sorted(remc.get(e, {})):
                    if remc[e][d] <= 0: continue
                    r2 = clone(remc)
                    r2[e][d] -= 1
                    if not r2[e][d]: del r2[e][d]
                    rec(i + 1, Lc + (d - 1) * 10 ** p, r2, placed)
            rec(0, base, rems, [])
        return out

def leaves_at(pat, K):
    res = []
    for (L, rem) in pat.expand(0, clone(pat.g), 0, K):
        if v2(L) != pat.a or L % 5 == 0: continue
        res.append(L)
    return res

def solve_direct(pat, K):
    out = []
    for L in leaves_at(pat, K):
        co = cut_coset(pat.co0, pat.a, L, K)
        if co is not None: out.append((L, co))
    return out

def solve_pruned(pat, schedule, logU):
    frontier = [pat.root()]
    cuts = 0; stages = []; pruned = 0
    for K in schedule:
        nxt = []
        for (L, rem, kk, co) in frontier:
            for (L2, rem2) in pat.expand(L, rem, kk, K):
                if v2(L2) != pat.a or L2 % 5 == 0: continue
                cuts += 1
                co2 = cut_coset(co, pat.a, L2, K)
                if co2 is None: continue
                if DC.digits_bound(co2) > logU: pruned += 1; continue
                nxt.append((L2, rem2, K, co2))
        frontier = nxt
        stages.append(len(frontier))
        if not frontier: return True, cuts, stages, pruned, []
    return False, cuts, stages, pruned, frontier
