import sys, itertools
sys.dont_write_bytecode = True
sys.path.insert(0, '/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/unanchored8')
from uncut import *

rows = [r for r in load_items({1161216, 11239424}) if not r['adm']]
lines = []
for r in rows:
    M, a, nu, eps = r['M'], r['a'], r['nu'], r['eps']
    De = rep_from_record(M, nu, eps)[1]
    planted = None
    for aa in [a] + [x for x in range(0, 30) if x != a]:
        for choice in itertools.product((0, 1), repeat=len(De)):
            taken = Counter(De[j][1] for j, c in enumerate(choice) if c)
            if any(v > 1 for v in taken.values()):
                continue
            L = (10 ** 96 - 1) // 9 + sum((De[j][0] - 1) * 10 ** De[j][1] for j, c in enumerate(choice) if c)
            if v2(L) != aa or L % 5 == 0:
                continue
            z = cut_coset(Coset((0, 0), (1, 0), (0, 1)), aa, L, 96)
            if z is None:
                continue
            planted = (aa, choice, z.v0)
            break
        if planted:
            break
    assert planted
    lines.append(f"{r['s']} {''.join(map(str, M))} {planted[0]} {planted[2][0]},{planted[2][1]} {nu} {','.join(map(str, eps))}")
    print(r['s'], ''.join(map(str, M)), 'recorded a', a, 'planted a', planted[0], 'planted subset', ''.join(map(str, planted[1])), flush=True)
open('cases8_planted.txt', 'x').write('\n'.join(lines) + '\n')
