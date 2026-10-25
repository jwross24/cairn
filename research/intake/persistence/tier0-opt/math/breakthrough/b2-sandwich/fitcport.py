import re, math, numpy as np, sys
sys.path.insert(0, '/Users/jwross/Documents/cairn/research/intake/persistence/tier0')
rows = []
for l in open('/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/cport/SANDWICH-full.txt'):
    m = re.search(r'a=(\d+) .*k=(\d+) reps=(\d+) log10G=([\d.]+) depth=(\d+) subcosets=(\d+)', l)
    if m: rows.append(tuple(float(x) for x in m.groups()))
A = np.array(rows)
a, k, reps, G, D, N = A.T
y = np.log10(N / reps)
X = np.vstack([k, D, np.ones(len(k))]).T
c, *_ = np.linalg.lstsq(X, y, rcond=None)
res = y - X @ c
print('n', len(k), 'log10(N/reps) = %.3f k + %.3f D + %.3f' % tuple(c), 'rms', float(np.sqrt((res ** 2).mean())), 'max', float(np.abs(res).max()))
X2 = np.vstack([k, np.log10(D), np.ones(len(k))]).T
c2, *_ = np.linalg.lstsq(X2, y, rcond=None)
res2 = y - X2 @ c2
print('log10(N/reps) = %.3f k + %.3f log10 D + %.3f' % tuple(c2), 'rms', float(np.sqrt((res2 ** 2).mean())))
X3 = np.vstack([k, np.ones(len(k))]).T
c3, *_ = np.linalg.lstsq(X3, y, rcond=None)
print('k only: slope %.3f (base %.2f) intercept %.3f' % (c3[0], 10 ** c3[0], c3[1]), 'rms', float(np.sqrt(((y - X3 @ c3) ** 2).mean())))
for kk in (31, 44):
    for DD in (6, 8):
        print(kk, DD, 'model1 %.1f' % (c[0] * kk + c[1] * DD + c[2]), 'model2 %.1f' % (c2[0] * kk + c2[1] * math.log10(DD) + c2[2]))
from baker_chain import baker_upper_bound
for kk in (11, 31, 44):
    for a_ in (0, 1):
        print('logU', kk, a_, round(math.log10(baker_upper_bound(kk, a_)), 1))
