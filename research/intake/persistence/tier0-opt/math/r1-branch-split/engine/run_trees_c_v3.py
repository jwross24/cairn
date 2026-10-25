#!/usr/bin/env python3
"""All vertices of A_2/A_4/A_6/A_8 (from the verified <10^4000 enumeration), smallest pattern
count first, through the C level-12 pass.  python3 run_trees_c.py <zf_list> <out.jsonl> [ncores] [per_vertex_cap] [skip.jsonl ...]"""
import sys, json, time, os
from collections import Counter, defaultdict
from math import comb
from gmpy2 import mpz
from tier0v2 import multisets
from run_c import run
zf, outp = sys.argv[1], sys.argv[2]
ncores = int(sys.argv[3]) if len(sys.argv) > 3 else os.cpu_count()
cap = float(sys.argv[4]) if len(sys.argv) > 4 else 1e30
mcap = float(os.environ.get('MULTISET_CAP', '1e30'))   # per-multiset cap: skip equations above it (recorded as skipped)
skip = set()
for f in sys.argv[5:]:
    for l in open(f):
        try: skip.add(json.loads(l)['s'])
        except Exception: pass
def dp(x):
    p = 1
    for ch in str(x): p *= int(ch)
    return p
rows = [l.split() for l in open(zf) if l.startswith('ZF')]
S = [int(mpz(2)**int(a)*mpz(3)**int(b)*mpz(7)**int(c)) for _, d, a, b, c, p in rows]
kids = defaultdict(list)
for y in S:
    if y >= 10: kids[dp(y)].append(y)
def orbit_end(x):
    while x >= 10: x = dp(x)
    return x
def npat(M):
    p = 12
    for d, k in Counter(M).items(): p *= comb(12 + k - 1, k)
    return p
verts = []
for y in S + [2, 4, 6, 8]:
    e = orbit_end(y) if y >= 10 else y
    if e not in (2, 4, 6, 8) or y in skip: continue
    tot = sum(npat(tuple(sorted(M))) for M in multisets(y))
    if tot <= cap or any(npat(tuple(sorted(M))) <= mcap for M in multisets(y)) and mcap < 1e30: verts.append((tot, e, y))
verts = sorted(set(verts))
print(f"{len(verts)} vertices, {sum(t for t, _, _ in verts):.2e} patterns", file=sys.stderr, flush=True)
# resumability: per-equation progress file; finished vertices are skipped via the output itself
eqp = outp + '.eqs.jsonl'
done_eqs = {}
if os.path.exists(eqp):
    for l in open(eqp):
        try:
            d = json.loads(l); done_eqs[(d['s'], tuple(d['M']))] = d
        except Exception: pass
if os.path.exists(outp):
    for l in open(outp):
        try: skip.add(json.loads(l)['s'])
        except Exception: pass
verts = [v for v in verts if v[2] not in skip]
print(f"resuming: {len(done_eqs)} equations already done, {len(verts)} vertices to go", file=sys.stderr, flush=True)
out = open(outp, 'a'); eqout = open(eqp, 'a')
for tot, e, s in verts:
    t0 = time.time(); found = set(); nopen = 0; eqs = []; bounds = []
    skipped = []
    for M in sorted((tuple(sorted(M)) for M in multisets(s)), key=npat):
        key = (s, M)
        if npat(M) > mcap:
            skipped.append(M); continue
        if key in done_eqs:
            d = done_eqs[key]
        else:
            r = run(s, M, kids[s], ncores=ncores)
            sols = sorted(y for y in r['solutions'] if y >= 10)
            d = dict(s=s, M=M, npat=npat(M), open=len(r['open']), sols=sols, bounds=r['bounds'], exceptional=r['exceptional'],
                     c_stats=r['c_stats'], levels=[(L, n, sv, cls) for (L, ps, n, sv, cls, el) in r['levels']])
            eqout.write(json.dumps(d) + '\n'); eqout.flush()
        found |= set(d['sols']); nopen += d['open']; bounds += d['bounds']; eqs.append(d)
    rec = dict(target=e, s=s, patterns=tot, known=sorted(kids[s]), found=sorted(found), open=nopen, skipped_multisets=skipped,
               closed=(nopen == 0 and found == set(kids[s]) and not skipped), complete_below=(found == set(kids[s]) and not skipped),
               digit_bound=(min(bounds) if bounds else None), secs=round(time.time() - t0), eqs=eqs)
    out.write(json.dumps(rec) + '\n'); out.flush()
    st = 'CLOSED' if rec['closed'] else (f"CLOSED BELOW 10^{rec['digit_bound']:.1e} DIGITS" if rec['complete_below'] else ('PARTIAL (%d multisets skipped by cap)' % len(skipped) if skipped and found == set(kids[s]) else 'INCOMPLETE'))
    print(f"A_{e} s={s} patterns={tot:.2e} {st}; open {nopen}; children {sorted(found)} known {sorted(kids[s])} {rec['secs']}s", file=sys.stderr, flush=True)
