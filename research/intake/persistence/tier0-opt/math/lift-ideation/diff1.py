import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ldiff
name = sys.argv[1]; L = sys.argv[2]
d = os.path.join(ldiff.H, name); cfg = os.path.join(d, f'cfgL{L}.txt'); par = os.path.join(d, f'parents{L}.txt')
o1 = os.path.join(ldiff.OUT, 'd_ref.out'); o2 = os.path.join(ldiff.OUT, 'd_j.out')
ldiff.run(os.path.join(ldiff.T0, 'lvlN'), cfg, par, o1); ldiff.run(os.path.join(ldiff.HERE, sys.argv[3]), cfg, par, o2)
a = sorted(open(o1)); b = sorted(open(o2)); print(len(a), len(b), a == b)
sa, sb = set(a), set(b); print('only ref', len(sa - sb), 'only other', len(sb - sa))
for x in list(sa - sb)[:3]: print('R', x.strip()[:200])
for x in list(sb - sa)[:3]: print('J', x.strip()[:200])
