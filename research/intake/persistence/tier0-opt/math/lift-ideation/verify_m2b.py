import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ldiff
name = '124416_33344489'; d = os.path.join(ldiff.H, name); cfg = os.path.join(d, 'cfgL48.txt'); par = os.path.join(d, 'parents48.txt')
o = os.path.join(ldiff.OUT, 'm2b.out'); r = os.path.join(ldiff.OUT, 'm2b_ref.out')
rc, c, s, w = ldiff.run(os.path.join(ldiff.T0, 'lvlN'), cfg, par, r); ref = ldiff.sig(s), ldiff.canon(r)
print('ref', ref)
for force in (0, 1, 2):
    for mut in ('', '2'):
        env = {'JOIN_FORCE_SET': str(force)}
        if mut: env['JOIN_MUTANT'] = mut
        rc, c, s, w = ldiff.run(os.path.join(ldiff.HERE, 'lvlJ3'), cfg, par, o, env)
        print('force set', force, 'mutant', mut or '-', 'sig', ldiff.sig(s), 'equal-to-ref', (ldiff.sig(s), ldiff.canon(o)) == ref, [k for k in s if k.startswith('set')][:3])
