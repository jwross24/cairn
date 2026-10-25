import os, sys, json, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import model_cuda as mc
from collections import Counter
rows = mc.load_rows(1e8); L = mc.laws_from(rows)
scale = 16.7e12 / mc.M['imad_per_s_m5']; eff = 0.6
def multiset_cost(n, k):
    par = n * mc.ev(L['par'], k); par48 = n * mc.ev(L['par48'], k)
    h12 = n / (mc.M['lvl12_patterns_per_s_m5'] * scale * eff)
    h24 = par * mc.ev(L['C24'], k) / (mc.M['pf24_children_per_s_m5'] * scale * eff)
    h48 = par48 * mc.ev(L['C48'], k) / (mc.M['pf48_children_per_s_m5'] * scale * eff)
    return (h12 + h24 + h48) / 3600
tot = 0; per = {}
best = []
for s in mc.TIER_B:
    ms = mc.vertex_multisets(s)
    costs = sorted(((multiset_cost(n, k), n, k) for n, k in ms), reverse=True)
    v = sum(c[0] for c in costs); per[s] = v; tot += v
    top5 = sum(c[0] for c in costs[:5])
    print('%15d multisets %3d vertex %.1f GPU-h | top multiset %.1f GPU-h (k=%d, npat=%.2g) = %.1f%% | top5 = %.1f%% | kmax %d' % (s, len(ms), v, costs[0][0], costs[0][2], costs[0][1], 100 * costs[0][0] / v, 100 * top5 / v, max(k for _, k in ms)))
    best.append((costs[0][0], s, costs[0]))
print('total %.0f GPU-h at eff %.1f' % (tot, eff))
b = max(best); print('single most expensive multiset: vertex %d  %.1f GPU-h  (k=%d, npat=%.3g)' % (b[1], b[0], b[2][2], b[2][1]))
budget = 8 * 168
print('budget assumed 8 x 168 h = %d GPU-h; modeled total / budget = %.2f' % (budget, tot / budget))
srt = sorted(per.items(), key=lambda x: -x[1]); acc = 0
for s, v in srt:
    acc += v
    print('  cumulative largest-first through %d: %.0f' % (s, acc))
# adverse scenarios for the largest vertex
big = srt[0][0]
bs = [mc.laws_from([__import__('random').choice(rows) for _ in rows]) for _ in range(60)]
import random; random.seed(3)
vals = []
for Lb in bs:
    t = 0
    for n, k in mc.vertex_multisets(big):
        par = n * mc.ev(Lb['par'], k); par48 = n * mc.ev(Lb['par48'], k)
        t += (n / (mc.M['lvl12_patterns_per_s_m5'] * scale * eff) + par * mc.ev(Lb['C24'], k) / (mc.M['pf24_children_per_s_m5'] * scale * eff) + par48 * mc.ev(Lb['C48'], k) / (mc.M['pf48_children_per_s_m5'] * scale * eff)) / 3600
    vals.append(t)
vals.sort(); print('largest vertex %d bootstrap p5/p50/p95 GPU-h at eff 0.6: %.0f %.0f %.0f ; at eff 0.4 p95: %.0f' % (big, vals[3], vals[30], vals[56], vals[56] * 1.5))
