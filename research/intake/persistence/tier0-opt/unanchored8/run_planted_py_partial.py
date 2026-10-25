import sys, json, itertools
sys.dont_write_bytecode = True
sys.path.insert(0, '/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/unanchored8')
from uncut import *

rows = [r for r in load_items({1161216, 11239424}) if not r['adm']]
lines = []
print('real verdict -> planted verdict (python)')
for r in rows:
    M, a, nu, eps = r['M'], r['a'], r['nu'], r['eps']
    rep = rep_from_record(M, nu, eps)
    De = rep[1]
    planted = None
    for choice in itertools.product((0, 1), repeat=len(De)):
        taken = Counter(De[j][1] for j, c in enumerate(choice) if c)
        if any(v > 1 for v in taken.values()):
            continue
        L = (10 ** 96 - 1) // 9 + sum((De[j][0] - 1) * 10 ** De[j][1] for j, c in enumerate(choice) if c)
        if v2(L) != a or L % 5 == 0:
            continue
        z = cut_coset(Coset((0, 0), (1, 0), (0, 1)), a, L, 96)
        if z is None:
            continue
        planted = (choice, Coset(z.v0, r['co'].u1, r['co'].u2))
        break
    assert planted
    real, _, _, _ = deep_cut(r['co'], a, rep, 1, 5000000)
    pl, bound, cases, stats = deep_cut(planted[1], a, rep, 1, 5000000)
    print(r['s'], ''.join(map(str, M)), 'a', a, 'planted subset', ''.join(map(str, planted[0])), 'real', 'CLOSED-cut' if real else 'SURVIVOR', '-> planted', 'CLOSED-cut' if pl else 'SURVIVOR (survivors %s)' % stats, flush=True)
    lines.append(f"{r['s']} {''.join(map(str, M))} {a} {planted[1].v0[0]},{planted[1].v0[1]} {nu} {','.join(map(str, eps))}")
open('cases8_planted.txt', 'x').write('\n'.join(lines) + '\n')
