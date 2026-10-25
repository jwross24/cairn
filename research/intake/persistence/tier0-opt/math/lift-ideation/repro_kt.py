import os, sys, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ldiff
d = os.path.join(ldiff.H, '9437184_22222222222222222266')
cfg = os.path.join(d, 'cfgL48.txt'); par = os.path.join(d, 'parents48.txt')
tmp = os.path.join(ldiff.OUT, 'parents_head1.txt')
open(tmp, 'w').write(open(par).readline())
a = int(open(cfg).readline().split()[2]); print('A =', a, 'KT capacity in tier0/lvlN.c = 64 (needs A+1 =', a + 1, ')')
for name in ('lvlN_asan', 'lvlNf_asan'):
    pr = subprocess.run([os.path.join(ldiff.HERE, name), cfg, tmp], capture_output=True, text=True, timeout=300)
    print(name, 'rc', pr.returncode, 'global-buffer-overflow' in pr.stderr, ('KT' in pr.stderr and 'located 0 bytes after global variable' in pr.stderr))
