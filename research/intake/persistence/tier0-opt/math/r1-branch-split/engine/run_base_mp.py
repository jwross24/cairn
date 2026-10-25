#!/usr/bin/env python3
"""
run_base_mp.py — run_base.py with a process pool over vertices (one vertex per task, largest first),
resumable (skips vertices already in the output jsonl).  Same record format as run_base.py.

Usage: python3 run_base_mp.py <b> <D> <levels> <out.jsonl> <ncores>
  e.g. uv run --no-project --with sympy python run_base_mp.py 8 70 12,24,48,96 base8_L96.jsonl 8
"""
import os, sys, json, time
from collections import defaultdict, Counter
from math import comb
from multiprocessing import Pool
from engine_b import Base, solve_equation, brute

b = int(sys.argv[1]); D = int(sys.argv[2]); levels = tuple(int(x) for x in sys.argv[3].split(','))
outp = sys.argv[4]; ncores = int(sys.argv[5]) if len(sys.argv) > 5 else 2
base = Base(b)

def corpus():
    zf = []; lim = b ** D
    def rec(i, v):
        if i == base.k:
            if v >= b and 0 not in base.digits(v): zf.append(v)
            return
        p = base.dp[i]; w = v
        while w < lim:                       # every exponent; b | y is excluded by the zero-digit test
            rec(i + 1, w); w *= p
    rec(0, 1); return sorted(zf)

def orbit_end(y):
    while y >= b: y = base.dprod(y)
    return y

zf = corpus()
kids = defaultdict(list)
for y in zf: kids[base.dprod(y)].append(y)
verts = sorted({(orbit_end(y), y) for y in zf if orbit_end(y) != 0} | {(d, d) for d in range(1, b)})

def npat(s):
    tot = 0
    for M in base.multisets(s):
        p = levels[0]
        for d, k in Counter(M).items(): p *= comb(levels[0] + k - 1, k)
        tot += p
    return tot

def do_vertex(ts):
    t, s = ts
    t0 = time.time(); found = set(); nopen = 0; eqs = []; incomplete = False; bounds = []
    for M in base.multisets(s):
        kn = sorted(set(brute(base, M, 12)) | {y for y in kids[s] if Counter(d for d in base.digits(y) if d != 1) == Counter(M)})
        try:
            r = solve_equation(base, s, M, kn, levels)
        except AssertionError as e:
            eqs.append(dict(M=M, error=str(e))); incomplete = True; continue
        sols = {y for y in r['solutions'] if y >= b}
        exceptional = []
        for (bv, nu, eps, co) in r['open']:
            pt = co.nearest(); y = None; issol = False
            if all(c >= 0 for c in pt) and max(pt) < 200:
                y = 1
                for p, a in zip(base.bounded, bv): y *= p ** a
                for q, v in zip(base.free, pt): y *= q ** v
                dg = base.digits(y)
                if y >= b and 0 not in dg and Counter(d for d in dg if d != 1) == Counter(M) and len(dg) % levels[-1] == nu % levels[-1] and y % b: sols.add(y); issol = True
            exceptional.append([list(bv), nu, list(eps), y, issol])
        found |= sols; nopen += len(r['open'])
        if r['bound_digits']: bounds.append(r['bound_digits'])
        eqs.append(dict(M=M, open=len(r['open']), sols=sorted(sols), brute=kn, exceptional=exceptional, descent_sols=r['descent_sols'],
                        levels=[(L, n, sv, cls) for (L, ps, n, sv, cls, el) in r['levels']]))
        if set(kn) - sols: incomplete = True
    st = 'INCOMPLETE' if incomplete else ('CLOSED' if nopen == 0 else f"CLOSED BELOW 10^{min(bounds):.1e} DIGITS")
    return dict(base=b, target=t, s=s, known=sorted(kids[s]), found=sorted(found), open=nopen, status=st, secs=round(time.time() - t0), eqs=eqs)

if __name__ == "__main__":
    done = set()
    if os.path.exists(outp):
        for line in open(outp):
            try: done.add(json.loads(line)['s'])
            except Exception: pass
    todo = sorted([v for v in verts if v[1] not in done], key=lambda v: -npat(v[1]))     # largest first
    print(f"base {b}: {len(verts)} vertices, {len(done)} done, {len(todo)} to go, {ncores} cores, levels {levels}", file=sys.stderr, flush=True)
    summary = Counter()
    with Pool(ncores) as pool, open(outp, 'a') as out:
        for rec in pool.imap_unordered(do_vertex, todo):
            out.write(json.dumps(rec) + '\n'); out.flush()
            summary[rec['status'].split()[0]] += 1
            print(f"  target {rec['target']} s={rec['s']} ({'.'.join(map(str, base.digits(rec['s'])))}_b) {rec['status']}; children {rec['found']} known {rec['known']} {rec['secs']}s", file=sys.stderr, flush=True)
    print("SUMMARY", dict(summary), file=sys.stderr)
