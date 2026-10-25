import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ldiff
name = '124416_33344489'; d = os.path.join(ldiff.H, name); cfg = os.path.join(d, 'cfgL48.txt'); par = os.path.join(d, 'parents48.txt')
lines = open(par).read().splitlines()
a0 = [l for l in lines if l.split()[0] == '0']; an = [l for l in lines if l.split()[0] != '0']
print('parents', len(lines), 'a==0:', len(a0), 'a!=0:', len(an))
for tag, sub in (('a==0', a0), ('a!=0', an)):
    p = os.path.join(ldiff.OUT, 'm2_%s.txt' % tag.replace('=', '').replace('!', 'n')); open(p, 'w').write('\n'.join(sub) + '\n')
    rc, c, s, w = ldiff.run(os.path.join(ldiff.T0, 'lvlN'), cfg, p, os.path.join(ldiff.OUT, 'm2.out'))
    print(tag, 'rc', rc, 'children', s.get('children'), 'tail-dead/open/exact', ldiff.sig(s))
