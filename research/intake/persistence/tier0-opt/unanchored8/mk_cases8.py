import sys
sys.dont_write_bytecode = True
sys.path.insert(0, '/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/unanchored8')
from uncut import *

lines = []
for r in load_items({1161216, 11239424}):
    if r['adm']:
        continue
    Ms = ''.join(map(str, r['M']))
    lines.append(f"{r['s']} {Ms} {r['a']} {r['co'].v0[0]},{r['co'].v0[1]} {r['nu']} {','.join(map(str, r['eps']))}")
with open('cases8.txt', 'x') as f:
    f.write('\n'.join(lines) + '\n')
print(len(lines))
