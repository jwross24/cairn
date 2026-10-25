import sys
sys.dont_write_bytecode = True
sys.path.insert(0, '/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/tierc-family')
from collections import Counter
from famlib import *
from famtest import *
from validate import load_cases, load_recorded
from refcheck import key_of

cond = {96: (9, 5), 192: (9, 5), 288: (9, 7), 384: (13, 5), 480: (10, 5), 768: (13, 5), 1152: (13, 7)}
cases = load_cases()
rec = load_recorded()
surv = [c for c in cases if rec[key_of(c)]['verdict'] == 'CLOSED-sandwich']
c = Counter()
for (s, M, a, y) in surv:
    tot = Counter()
    for nu, De in reps_wrap0(M, y):
        r, _, _ = family_counts(a, y, De, cond)
        for L in r:
            tot[L] += r[L]
    for L in (288, 768, 1152):
        c[(L, tot[L] > 0)] += 1
print('of', len(surv), 'patterns alive at 384:', dict(sorted(c.items())))
