#!/usr/bin/env python3
"""
classify_open.py — what are the open patterns?  For every open pattern recorded in the base-10 sweep
outputs (its exceptional coset point y = 2^a 3^b 7^c, Babai-nearest to the origin), decide whether the
pattern is anchored on a genuine zero-free S-unit:

  SELF      y is a known child of the vertex with exactly the pattern's digits (a = t silences Lemma B)
  CARRY     y is zero-free, in the 10^4000 corpus, but its digit multiset differs from M: the pattern
            impersonates y through a carry coincidence (two digits in one residue class, (d-1) sums to 10)
  ZF-OTHER  y is zero-free but not in the corpus (would be a corpus gap -> finding)
  UNANCHORED y has a zero digit (no small genuine element explains the pattern)

Usage: python3 classify_open.py <jsonl files...>   (runall_final.jsonl, trees_c.jsonl, trees_mac.jsonl)
"""
import sys, json
from collections import Counter, defaultdict

corpus = set()
for l in open('zf_below_1e4000.txt'):
    t = l.split()
    if len(t) >= 5 and t[0] == 'ZF': corpus.add(2 ** int(t[2]) * 3 ** int(t[3]) * 7 ** int(t[4]))

def factor237(y):
    e = []
    for p in (2, 3, 7):
        c = 0
        while y % p == 0: y //= p; c += 1
        e.append(c)
    return tuple(e) if y == 1 else None

def digits_nz(y): return Counter(int(ch) for ch in str(y) if ch != '1')

def entries(path):
    for line in open(path):
        r = json.loads(line)
        if 'eqs' not in r: continue
        for eq in r['eqs']:
            if isinstance(eq, dict):
                M, ex = eq['M'], eq.get('exceptional', [])
                for e in ex:
                    if len(e) == 3: a, y, sol = e; yield r['s'], tuple(M), a, None, None, y, sol
                    else: yield r['s'], tuple(M), e[1], e[2], e[3], e[4][0], e[4][1]
        for e in r.get('exceptional', []):
            M, a, nu, eps, (y, sol) = e
            yield r['s'], tuple(M), a, nu, eps, y, sol

def classify(s, M, y, sol):
    f = factor237(y)
    if f is None: return 'NOT-S-UNIT'
    if '0' in str(y): return 'UNANCHORED'
    if y not in corpus: return 'ZF-OTHER'
    if sol or digits_nz(y) == Counter(M): return 'SELF'
    return 'CARRY'

def carry_explanation(M, y, L=96):
    """per-residue-class (d-1) sums: pattern side is unknown here, so report y's folded class sums and
    which pairs of M-digits sum (d-1)+(d'-1) = 10 are available."""
    pairs = sorted({(d, 11 - d) for d in M if (11 - d) in M and d <= 11 - d})
    return pairs

if __name__ == "__main__":
    files = sys.argv[1:]
    seen = set(); rows = []
    for f in files:
        for (s, M, a, nu, eps, y, sol) in entries(f):
            key = (s, M, a, nu, None if eps is None else tuple(eps), y)
            if key in seen: continue
            seen.add(key); rows.append((f, s, M, a, y, sol, classify(s, M, y, sol)))
    cnt = Counter(c for *_, c in rows)
    print(f"{len(rows)} open patterns from {len(files)} files: {dict(cnt)}")
    anchors = Counter((y, c) for (_, s, M, a, y, sol, c) in rows)
    print("\nanchors (exceptional point y, class, #patterns anchored on it):")
    for (y, c), n in sorted(anchors.items(), key=lambda t: (-t[1], t[0][0])):
        f = factor237(y)
        print(f"  {y:>22}  2^{f[0]} 3^{f[1]} 7^{f[2]:<3} {c:<10} x{n}   digits {''.join(sorted(str(y)))}")
    print("\nper vertex:")
    byv = defaultdict(Counter)
    for (_, s, M, a, y, sol, c) in rows: byv[s][c] += 1
    for s in sorted(byv): print(f"  s={s:<16} {dict(byv[s])}")
    bad = [r for r in rows if r[-1] in ('UNANCHORED', 'ZF-OTHER', 'NOT-S-UNIT')]
    print(f"\nunanchored / other: {len(bad)}")
    for r in bad: print("  ", r)
    print("\ncarry pairs available per anchored CARRY pattern (digits d, d' in M with (d-1)+(d'-1)=10):")
    cp = Counter()
    for (_, s, M, a, y, sol, c) in rows:
        if c == 'CARRY': cp[tuple(carry_explanation(M, y))] += 1
    for k, n in cp.most_common(): print(f"  {k}: {n}")

# --------------------------------------------------------------------------- exact identity search
def exact_identity(M, y, L=96, b=10):
    """Find nu in [0,L) and positions e_j in [0,L) (any multiplicity) with
       y == R_nu + sum (d_j - 1) b^{e_j}  exactly over the integers.  Returns (nu, eps) or None.
       Digit DP from the lowest position up: the digits placed at position e must match rem mod b^{e+1}."""
    from functools import lru_cache
    from itertools import combinations
    M = tuple(sorted(M)); q = len(M)
    RL = (b ** L - 1) // (b - 1)
    for k in (0, 1):                       # pattern value = y + k*R_L: k = 1 when the digits above the top wrap a full period
      for nu in range(0, L):
        target = y + k * RL - (b ** nu - 1) // (b - 1)
        if target < 0: continue
        emax = len(str(target)) if b == 10 else len(_digits(target, b))
        @lru_cache(maxsize=None)
        def rec(e, rem_ms, rem):
            if not rem_ms: return () if rem == 0 else None
            if e > emax or rem < 0: return None
            need = (rem // b ** e) % b
            ms = list(rem_ms); idx = range(len(ms))
            tried = set()
            for k in range(0, len(ms) + 1):
                for sub in combinations(idx, k):
                    ds = tuple(ms[i] for i in sub)
                    if ds in tried: continue
                    tried.add(ds)
                    tot = sum(d - 1 for d in ds)
                    if tot % b != need: continue
                    rest = tuple(ms[i] for i in idx if i not in sub)
                    r = rec(e + 1, rest, rem - tot * b ** e)
                    if r is not None: return tuple((d, e) for d in ds) + r
            return None
        r = rec(0, M, target)
        if r is not None:
            # return positions in the order of sorted-descending M, as before
            byd = {}
            for d, e in r: byd.setdefault(d, []).append(e)
            Md = sorted(M, reverse=True); eps = []
            for d in Md: eps.append(byd[d].pop(0))
            if max(eps) >= L: continue
            return nu, tuple(eps)
    return None

def _digits(n, b):
    out = []
    while n: out.append(n % b); n //= b
    return out[::-1]

def run_exact(files):
    seen = set(); n_ok = n_fail = 0; fails = []
    for f in files:
        for (s, M, a, nu, eps, y, sol) in entries(f):
            key = (s, M, y)
            if key in seen: continue
            seen.add(key)
            r = exact_identity(M, y)
            if r is None: n_fail += 1; fails.append((s, M, a, y))
            else: n_ok += 1
    print(f"\nexact-identity check (pattern == anchor over Z with positions in [0,96)): {n_ok} ok, {n_fail} fail")
    for x in fails: print("   NO EXACT IDENTITY:", x)
