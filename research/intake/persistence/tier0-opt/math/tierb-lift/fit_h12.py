import json, glob, math, sys
from collections import defaultdict
S = defaultdict(lambda: dict(n12=0, s12=0, par=0, ch=0, s24=0, ch48=0, s48=0, t12=0.0, t24=0.0, t48=0.0, n=0))
for f in glob.glob('logs/h12_*.jsonl'):
    for l in open(f):
        r = json.loads(l)
        if r.get('npat', 0) < float(sys.argv[1] if len(sys.argv) > 1 else 1e7): continue
        d = S[r['k']]
        d['n'] += 1; d['n12'] += r['npat']; d['s12'] += r['l12_n']
        l24 = r.get('lift24'); l48 = r.get('lift48')
        if l24:
            d['par'] += l24['parents']; d['ch'] += l24['children']; d['s24'] += l24['survivors']; d['t24'] += l24['secs']
        if l48:
            d['ch48'] += l48['children']; d['s48'] += l48['survivors']; d['t48'] += l48['secs']
xs = []; ys = []; zs = []
for k in sorted(S):
    d = S[k]
    print(f"k={k:2d} eqs={d['n']:3d} N12={d['n12']:.2e} s12/N12={d['s12']/d['n12']:.2e} children/parent={d['ch']/max(d['par'],1):.1f} tests24/N12={d['ch']/d['n12']:.3e} tests48/N12={d['ch48']/d['n12']:.3e} s24/ch={d['s24']/max(d['ch'],1):.2e} ns/child24={1e9*d['t24']/max(d['ch'],1):.0f} ns/child48={1e9*d['t48']/max(d['ch48'],1):.0f}")
    if d['ch'] > 0:
        xs.append(k); ys.append(math.log(d['ch'] / d['n12']))
        if d['ch48'] > 0: zs.append((k, math.log(d['ch48'] / d['n12'])))
def fit(x, y):
    n = len(x); mx = sum(x) / n; my = sum(y) / n
    b = sum((a - mx) * (c - my) for a, c in zip(x, y)) / sum((a - mx) ** 2 for a in x)
    return my - b * mx, b
if len(xs) >= 2:
    a, b = fit(xs, ys); print('lift24 tests/N12 = exp(%.3f + %.4f k), x%.3f per digit' % (a, b, math.exp(b)))
if len(zs) >= 2:
    a2, b2 = fit([z[0] for z in zs], [z[1] for z in zs]); print('lift48 tests/N12 = exp(%.3f + %.4f k), x%.3f per digit' % (a2, b2, math.exp(b2)))
