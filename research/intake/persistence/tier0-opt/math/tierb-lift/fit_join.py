import json, sys, math
rows = [json.loads(l) for l in open(sys.argv[1] if len(sys.argv) > 1 else 'logs/join24_diff.jsonl')]
rows = [r for r in rows if r.get('built') is not None and r['cpu_ref'] > 0.05]
T0 = float(sys.argv[2]) if len(sys.argv) > 2 else 0.03

def lstsq(X, y):
    n = len(X[0])
    A = [[sum(X[k][i] * X[k][j] for k in range(len(X))) for j in range(n)] for i in range(n)]
    b = [sum(X[k][i] * y[k] for k in range(len(X))) for i in range(n)]
    for i in range(n):
        p = max(range(i, n), key=lambda r: abs(A[r][i])); A[i], A[p] = A[p], A[i]; b[i], b[p] = b[p], b[i]
        for r in range(i + 1, n):
            f = A[r][i] / A[i][i]
            for c in range(i, n): A[r][c] -= f * A[i][c]
            b[r] -= f * b[i]
    x = [0.0] * n
    for i in reversed(range(n)):
        x[i] = (b[i] - sum(A[i][j] * x[j] for j in range(i + 1, n))) / A[i][i]
    return x

X = [[r['probes'], r['cands'], r['built']] for r in rows]
y = [max(r['cpu_join'] - T0, 1e-4) for r in rows]
w = lstsq(X, y)
print('n=%d  ns per probe %.1f  per cand %.1f  per built %.1f' % (len(rows), w[0] * 1e9, w[1] * 1e9, w[2] * 1e9))
yr = [r['cpu_ref'] for r in rows]; tc = sum(yr) / sum(r['children'] for r in rows)
print('ref ns per child %.1f' % (tc * 1e9))
res = [abs(sum(w[i] * X[k][i] for i in range(3)) - y[k]) / y[k] for k in range(len(rows))]
print('median relative residual %.2f' % sorted(res)[len(res) // 2])
print('speedup net of startup, by C/parent:')
for r in sorted(rows, key=lambda r: r['children'] / r['parents']):
    print('  C=%7.0f  x%.1f' % (r['children'] / r['parents'], r['cpu_ref'] / max(r['cpu_join'] - T0, 1e-3)))
