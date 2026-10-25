import sys, importlib.util, math, hashlib
sys.dont_write_bytecode = True
from mpmath import mp, mpf, log10
P = '/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/'
spec = importlib.util.spec_from_file_location('cross', P + 'cport/tools/cross_utable_u2.py')
X = importlib.util.module_from_spec(spec); spec.loader.exec_module(X)
new = {}
for l in open(P + 'cport-shadow/data/utable_u2_k29.txt'):
    k, a, u = l.split(); new[(int(k), int(a))] = int(u)
old = {}
for l in open(P + 'cport/data/utable_u2.txt'):
    k, a, u = l.split(); old[(int(k), int(a))] = int(u)
prime = {}
for l in open(P + 'cport/data/utable_prime.txt'):
    k, a, u = l.split(); prime[(int(k), int(a))] = int(u)
print('rows', len(new), 'k range', min(k for k, _ in new), max(k for k, _ in new))
same = all(new[key] == v for key, v in old.items())
print('rows k<=24 byte-identical integers to cport/data/utable_u2.txt:', same, len(old))
print('U2 <= U-prime at all k<=24 entries:', all(new[key] <= prime[key] for key in prime))
mono_k = all(new[(k + 1, a)] >= new[(k, a)] for (k, a) in new if (k + 1, a) in new)
print('nondecreasing in k at every a:', mono_k)
pts = [(k, a) for k in range(25, 30) for a in range(0, 25)]
if len(sys.argv) > 1 and sys.argv[1] == 'quick': pts = [(k, a) for k in (25, 29) for a in (0, 1, 24)]
worst = 0; bad = 0
for (k, a) in pts:
    v, m = X.best(k, a)
    tl = float(log10(mpf(new[(k, a)]))); cl = float(log10(v)); d = tl - cl
    worst = max(worst, abs(d))
    ok = abs(d) < 1e-5 and tl >= cl - 1e-9
    bad += not ok
    print(f"k={k} a={a} table-log10 {tl:.4f} cross-log10 {cl:.4f} diff {d:+.2e} m={m} {'ok' if ok else 'MISMATCH'}", flush=True)
print(f"second typing: {len(pts)} points, {bad} mismatches, max |diff| {worst:.2e}")
