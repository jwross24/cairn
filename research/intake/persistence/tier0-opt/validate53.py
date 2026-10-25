import sys, json
from collections import defaultdict
from math import comb
from tier0v2 import multisets
from run_c import run
from eq_golden import kids
K = kids()
bad = 0
for n, line in enumerate(open('runall_final.jsonl')):
    rec = json.loads(line); s = rec['s']
    found = set(); nopen = 0; bounds = []; exc = []
    for M in sorted(tuple(sorted(M)) for M in multisets(s)):
        r = run(s, M, K[s] if s in K else rec['known'], ncores=4)
        found |= {y for y in r['solutions'] if y >= 10}; nopen += len(r['open']); bounds += r['bounds']; exc += [list(e) for e in r['exceptional']]
    new = dict(found=sorted(found), open=nopen, closed=(nopen == 0 and found == set(rec['known'])), complete_below=(found == set(rec['known'])),
               digit_bound=(min(bounds) if bounds else None))
    old = {k: rec[k] for k in new}
    ok = new == old
    bad += (not ok)
    print(n, s, 'OK' if ok else 'MISMATCH', '' if ok else (new, old), flush=True)
print('MISMATCHES', bad)
