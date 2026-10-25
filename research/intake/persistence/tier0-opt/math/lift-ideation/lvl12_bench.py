import os, sys, subprocess, glob, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ldiff
GP = os.path.join(ldiff.HERE, '..', '..', 'gpu')
cfgs = sorted(glob.glob('/private/tmp/persist-gpu/cfg/14336_*.txt'))
rows = []
for cfg in cfgs:
    out = os.path.join(ldiff.OUT, 'l12.out')
    t = time.time()
    with open(out, 'w') as fo:
        pr = subprocess.run(['nice', '-n', '10', os.path.join(GP, 'lvl12_gpu'), cfg], stdout=fo, stderr=subprocess.PIPE, text=True, timeout=900)
    dt = time.time() - t
    err = pr.stderr.strip().splitlines()
    pats = [l for l in err if l.startswith('patterns')]
    tim = [l for l in err if l.startswith('gpu-timing')]
    n = None
    if pats:
        parts = pats[0].split(); n = int(parts[parts.index('patterns') + 1]) if 'patterns' in parts else None
    rows.append((n, dt)) if n else None
    pass #, pr.returncode, 'wall %.2f' % dt, 'patterns', n, (n / dt if n else None), pats[:1], tim[:2])

rows.sort()
import statistics
big = rows[-6:]
print('largest six: ', big)
(n1, t1), (n2, t2) = big[0], big[-1]
print('marginal rate between smallest and largest of top six: %.3e patterns/s' % ((n2 - n1) / (t2 - t1)))
print('best end-to-end %.3e' % max(n / t for n, t in rows))
