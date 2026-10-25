import os, sys, subprocess, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ldiff
rep = int(sys.argv[2]) if len(sys.argv) > 2 else 8
name = sys.argv[1]; L = sys.argv[3] if len(sys.argv) > 3 else '48'
d = os.path.join(ldiff.H, name); cfg = os.path.join(d, f'cfgL{L}.txt'); par = os.path.join(d, f'parents{L}.txt')
big = os.path.join(ldiff.OUT, f'sat_{name}_{L}.txt'); lines = open(par).read().splitlines()
open(big, 'w').write('\n'.join(lines * rep) + '\n')
rc, c, s, w = ldiff.run(os.path.join(ldiff.HERE, os.environ.get('SATBIN', 'lvlG')), cfg, big, os.path.join(ldiff.OUT, 'sat.out'), env=({'GPU_SMALLFIRST': '1'} if os.environ.get('SMALLFIRST') else None), timeout=1800)
print(name, 'level', L, 'x%d' % rep, 'rc', rc, 'cpu %.2f wall %.2f' % (c, w), {k: s.get(k) for k in ('children', 'gpu_us', 'cpu_cand_us', 'prep_us', 'total_us', 'gcand', 'retry', 'p0', 'p1')})
print('kernel children/s %.3e ; end-to-end children/s %.3e ; cpu ns per candidate %.0f ; candidate fraction %.2e' % (s['children'] / (s['gpu_us'] * 1e-6), s['children'] / (s['total_us'] * 1e-6), s['cpu_cand_us'] * 1e3 / max(s['gcand'], 1), s['gcand'] / s['children']))
