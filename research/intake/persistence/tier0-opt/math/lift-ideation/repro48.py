import os, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ldiff
d = os.path.join(ldiff.H, '9437184_22222222222222222266'); cfg = os.path.join(d, 'cfgL48.txt'); par = os.path.join(d, 'parents48.txt')
out = os.path.join(ldiff.SCR, 'li')
rc, c, s, w = ldiff.run(os.path.join(ldiff.T0, 'lvlN'), cfg, par, os.path.join(out, 'rep_ref.out'))
print('ref', rc, round(c, 1), s)
rc, c, s, w = ldiff.run(os.path.join(ldiff.HERE, 'lvlJ3'), cfg, par, os.path.join(out, 'rep_join.out'))
print('join', rc, round(c, 1), {k: s[k] for k in s if k in ('tail-dead','open','exact','probes','cands','children')})
ref = [l.strip() for l in open(os.path.join(out, 'rep_ref.out'))]; jn = [l.strip() for l in open(os.path.join(out, 'rep_join.out'))]
print(len(ref), len(jn), 'distinct join', len(set(jn)), 'ref subset of join', set(ref) <= set(jn))
cnt = collections.Counter(jn); print('max multiplicity', max(cnt.values()))
for l in jn[:5]: print(l[:200])
extra = [l for l in jn if l not in set(ref)]; print('extra', len(extra))
print(collections.Counter(l.split()[0] for l in extra))
