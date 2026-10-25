import sys
sys.dont_write_bytecode = True
sys.path.insert(0, '/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/tierc-family')
import random, json
from collections import Counter
from famlib import *
from famtest import *
from validate import load_cases, load_recorded
from refcheck import key_of

cases = load_cases()
rec = load_recorded()
surv = [c for c in cases if rec[key_of(c)]['verdict'] == 'CLOSED-sandwich']
stat = Counter()
shown = 0
for (s, M, a, y) in surv:
    reps = reps_wrap0(M, y)
    q = a + 13
    for nu, De in reps:
        g = groups_of(De)
        mm = modulus(a, 384)
        base = R(96) - y
        positions = sorted(g)
        opts = [[None] + list(range(len(g[e]))) for e in positions]
        import itertools
        for choice in itertools.product(*opts):
            sm = 0
            fixed = []
            for e, ch in zip(positions, choice):
                if ch is not None:
                    sm += g[e][ch]
                    fixed.append(e)
            if (base + sm) % mm == 0:
                unplaced = []
                chosen = {e: ch for e, ch in zip(positions, choice)}
                for d, e in De:
                    pass
                su = (y - R(nu)) - sm
                stat[('nu>=len(y)', nu >= len(str(y)))] += 1
                stat[('S_U==0', su == 0)] += 1
                stat[('len(y)', len(str(y)))] += 1
                if shown < 6:
                    print('key', (s, ''.join(map(str, M)), a, y), 'nu', nu, 'De', sorted(De, key=lambda t: t[1]), 'S_F', sm, 'S_U', su)
                    shown += 1
print(dict(stat))
