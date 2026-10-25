import sys, os, json
src, s, known, nc, outp = sys.argv[1], int(sys.argv[2]), sys.argv[3], int(sys.argv[4]), sys.argv[5]
os.chdir(src); sys.path.insert(0, src)
from collections import Counter
from math import comb
from tier0v2 import multisets
from run_c import run
def npat(M):
    p = 12
    for d, k in Counter(M).items(): p *= comb(12 + k - 1, k)
    return p
kn = [int(x) for x in known.split(',')] if known else []
out = open(outp, 'w')
for M in sorted([tuple(sorted(M)) for M in multisets(s)], key=npat):
    r = run(s, M, kn, ncores=nc)
    sols = sorted(y for y in r['solutions'] if y >= 10)
    row = dict(s=s, M=M, npat=npat(M), open=len(r['open']), sols=sols, bounds=r['bounds'], exceptional=r['exceptional'], c_stats=r['c_stats'],
               levels=[(L, n, sv, cls) for (L, ps, n, sv, cls, el) in r['levels']])
    if 'open_patterns' in r: row['open_patterns'] = r['open_patterns']
    out.write(json.dumps(row) + '\n'); out.flush()
