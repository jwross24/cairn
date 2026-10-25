import sys, json, math, time
sys.dont_write_bytecode = True
sys.path.insert(0, '/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/unanchored8')
from uncut import *

rows = [r for r in load_items({1161216, 11239424}) if not r['adm']]
print('unanchored items', len(rows))
for r in rows:
    co = r['co']
    u1, u2 = co.u1, co.u2
    dot = u1[0] * u2[0] + u1[1] * u2[1]
    lag = abs(2 * dot) <= u1[0] ** 2 + u1[1] ** 2 <= u2[0] ** 2 + u2[1] ** 2
    nn, b0, c0 = nearest(co)
    wide = min((v0b ** 2 + v0c ** 2) for v0b, v0c in [(co.v0[0] + x * u1[0] + y * u2[0], co.v0[1] + x * u1[1] + y * u2[1]) for x in range(-40, 41) for y in range(-40, 41)])
    assert wide >= nn
    rep = rep_from_record(r['M'], r['nu'], r['eps'])
    V = pattern_value(r['M'], r['nu'], r['eps'])
    t0 = time.time()
    closed, bound, cases, stats = deep_cut(co, r['a'], rep, 1, 5000000)
    print(r['s'], ''.join(map(str, r['M'])), 'item', r['i'], 'a', r['a'], 'nu', r['nu'], 'q', len(r['M']),
          'reduced', lag, 'b0<0' if b0 < 0 else 'b0>=0', 'c0<0' if c0 < 0 else 'c0>=0',
          'log10 digits floor %.3f' % digits_bound_log10(co), 'V<R96', V < (10 ** 96 - 1) // 9, 'cases', cases, 'survivors', stats,
          'CLOSED-cut' if closed else ('BUDGET' if closed is None else 'SURVIVOR bound %.3f' % bound), '%.1fs' % (time.time() - t0), flush=True)
