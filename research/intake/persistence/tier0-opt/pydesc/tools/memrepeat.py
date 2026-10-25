import sys, os, time, resource
src, s, nc, reps = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
os.chdir(src); sys.path.insert(0, src)
import run_c, tier0v2
from math import comb
from collections import Counter
def npat(M):
    p = 12
    for d, k in Counter(M).items(): p *= comb(12 + k - 1, k)
    return p
eqs = sorted([tuple(sorted(M)) for M in tier0v2.multisets(s)], key=npat)[:12]
def rss():
    import subprocess
    return int(subprocess.run(['ps', '-o', 'rss=', '-p', str(os.getpid())], capture_output=True, text=True).stdout) / 1024
print(os.path.basename(src), 'start rss', round(rss()), 'MB')
for r in range(reps):
    for M in eqs: run_c.run(s, M, [], ncores=nc)
    print(f'after pass {r+1} ({len(eqs)} equations): rss {rss():.0f} MB, maxrss {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/2**20:.0f} MB')
