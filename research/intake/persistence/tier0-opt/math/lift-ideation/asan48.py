import os, sys, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ldiff
d = os.path.join(ldiff.H, sys.argv[1]); cfg = os.path.join(d, 'cfgL48.txt'); par = os.path.join(d, 'parents48.txt')
pr = subprocess.run(['nice', '-n', '10', os.path.join(ldiff.HERE, sys.argv[2]), cfg, par], capture_output=True, text=True, timeout=1200)
print('rc', pr.returncode, 'stdout lines', len(pr.stdout.splitlines()))
print(pr.stderr[:3000])
