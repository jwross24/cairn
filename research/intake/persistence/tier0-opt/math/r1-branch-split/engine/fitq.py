import json, math
rows = []
for s in (10800, 14336, 8192, 28672):
    for l in open(f'v{s}_off.jsonl'):
        r = json.loads(l)
        if len(r['levels']) < 2:
            continue
        q = len(r['M']); N = r['npat']
        op = r['c_stats']['open']; ch = r['levels'][1][1]
        if op > 0 and ch > 0:
            rows.append((q, N, op, ch, r['levels'][0][2], r['secs']))
rows.sort()
for q, N, op, ch, s12, secs in rows:
    print(q, '%.2e' % N, 'open/N %.2e' % (op / N), 'children/open %.1f' % (ch / op), 'secs %.2f' % secs)
import statistics
xs = [r[0] for r in rows]; y1 = [math.log(r[3] / r[2]) for r in rows]; y2 = [math.log(r[2] / r[1]) for r in rows]
def lin(xs, ys):
    mx = sum(xs) / len(xs); my = sum(ys) / len(ys)
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
    return my - b * mx, b
a1, b1 = lin(xs, y1); a2, b2 = lin(xs, y2)
print('log(children/open) = %.3f + %.3f q ; at q=25: %.0f, q=29: %.0f' % (a1, b1, math.exp(a1 + b1 * 25), math.exp(a1 + b1 * 29)))
print('log(open/N) = %.3f + %.3f q ; at q=25: %.2e' % (a2, b2, math.exp(a2 + b2 * 25)))
