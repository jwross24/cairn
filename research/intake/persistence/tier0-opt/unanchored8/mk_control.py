import sys, json
sys.dont_write_bytecode = True
sys.path.insert(0, '/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/unanchored8')
from uncut import *

CONTROLS = [(1161216, '22222222222799', 14, 11519532122112), (11239424, '222222222247778', 8, 952342272), (1161216, '22222222223679', 1, 44471322)]
items = load_items({1161216, 11239424})
anchored, itemlines, pyv = [], [], []
for (s, Ms, a, y) in CONTROLS:
    M = tuple(int(ch) for ch in Ms)
    fa, fb, fc = factor237(y)
    cand = [r for r in items if r['s'] == s and r['M'] == M and r['a'] == a and r['adm'] and (r['b0'], r['c0']) == (fb, fc)]
    co = cand[0]['co']
    anchored.append(f'{s} {Ms} {a} {y}@{co.v0[0]},{co.v0[1]} - -')
    for c in cand:
        line = f"{s} {Ms} {a} {c['co'].v0[0]},{c['co'].v0[1]} {c['nu']} {','.join(map(str, c['eps']))}"
        itemlines.append(line)
        cl, bound, cases, stats = deep_cut(c['co'], a, rep_from_record(M, c['nu'], c['eps']), 1, 5000000)
        pyv.append((line, 'CLOSED' if cl else 'SURVIVOR'))
        print('py item', s, Ms, a, y, 'item', c['i'], 'nu', c['nu'], 'CLOSED' if cl else 'SURVIVOR', flush=True)
with open('control_anchored.txt', 'x') as f:
    f.write('\n'.join(anchored) + '\n')
with open('control_items.txt', 'x') as f:
    f.write('\n'.join(itemlines) + '\n')
json.dump(pyv, open('control_items_py.json', 'x'))
