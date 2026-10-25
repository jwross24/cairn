"""Independent big-integer check of the survivor cosets the C certificate reports.

For every reported survivor (a level-384 depth-1 coset) take its nearest point (b, c) to the origin and verify, with Python integers only,
that y = 2^a 3^b 7^c satisfies every congruence of its branch: the level-96 primes against the anchor, the 96-digit word tail, the seven
level-192 primes against the shadow value V, the 192-digit tail, the four level-384 primes against V2(T, sn), and the 384-digit tail.
usage: verify_points.py DUMP.jsonl SURV.jsonl LATTICE96 LEVELPRIMES [--max N] [--seed S]"""
import sys, json, random, re
from fractions import Fraction

def R(n): return (10 ** n - 1) // 9

def nearest(off, basis):
    (u1, u2) = basis
    det = u1[0] * u2[1] - u1[1] * u2[0]
    x = round(Fraction(-off[0] * u2[1] + off[1] * u2[0], det)); y = round(Fraction(off[0] * u1[1] - off[1] * u1[0], det))
    best = None
    for dx in range(-3, 4):
        for dy in range(-3, 4):
            b = off[0] + (x + dx) * u1[0] + (y + dy) * u2[0]; c = off[1] + (x + dx) * u1[1] + (y + dy) * u2[1]
            nn = b * b + c * c
            if best is None or nn < best[0]: best = (nn, b, c)
    return best[1], best[2]

def main():
    dump, surv, lat, lpf = sys.argv[1:5]
    mx = int(sys.argv[sys.argv.index('--max') + 1]) if '--max' in sys.argv else 10 ** 9
    rng = random.Random(int(sys.argv[sys.argv.index('--seed') + 1]) if '--seed' in sys.argv else 1)
    reps = {}
    for l in open(dump):
        d = json.loads(l); reps[d['id']] = d
    p96 = [int(l.split()[0]) for l in open(lat) if l.strip() and not l.startswith('#')]
    P192 = []; P384 = []
    for l in open(lpf):
        if l.startswith('#') or not l.strip(): continue
        t = l.split(); (P192 if t[0] == '192' else P384).append(int(t[1]))
    P384 = sorted(set(P384))
    if '--p384' in sys.argv: P384 = [int(x) for x in sys.argv[sys.argv.index('--p384') + 1].split(',')]
    recs = [json.loads(l) for l in open(surv)]
    recs = [r for r in recs if r['tag'].startswith('shadow:')]
    if len(recs) > mx: recs = rng.sample(recs, mx)
    ok = bad = 0
    for r in recs:
        d = reps[f"{r['key']}#{r['rep']}"]
        s, M, a_s, y_s, _, _ = r['key'].split(' ')
        y = int(y_s); a = int(d['a']); nu = int(d['nu'])
        dg = [(x['d'], x['e']) for x in d['digits']]; k = len(dg)
        w = [(dd - 1) * 10 ** e for dd, e in dg]
        word = d['words'][r['word']]; fixed = set(word['fixed']); U = [j for j in range(k) if j not in fixed]
        m = re.match(r'shadow:T=(\d+),sn=(\d+),A=(\d+)', r['tag']); Tm, sn, Am = int(m[1]), int(m[2]), int(m[3])
        Tl = [U[t] for t in range(len(U)) if Tm >> t & 1]
        Al = [Tl[x] for x in range(len(Tl)) if Am >> x & 1]
        b, c = nearest([int(z) for z in r['offset']], [[int(z) for z in v] for v in r['basis']])
        if '--perturb' in sys.argv: b += 1
        def val(mod): return pow(2, a, mod) * pow(3, b, mod) % mod * pow(7, c, mod) % mod
        V = R(nu) + sum(w)
        Fs = sum(w[j] for j in fixed)
        checks = {}
        checks['level96 primes vs anchor'] = all(val(p) == y % p for p in p96)
        checks['anchor = V mod level96 primes'] = all(y % p == V % p for p in p96)
        checks['tail 10^96'] = val(10 ** 96) == (R(96) + Fs) % 10 ** 96
        checks['192 primes vs V'] = all(val(p) == V % p for p in P192)
        checks['tail 10^192'] = val(10 ** 192) == (R(192) + Fs) % 10 ** 192
        V2 = V + (10 ** 192 - 1) * sum(w[j] for j in Tl) + sn * 10 ** nu * R(192)
        checks['384 primes vs V2'] = all(val(p) == V2 % p for p in P384)
        checks['tail 10^384'] = val(10 ** 384) == (R(384) + Fs + 10 ** 192 * sum(w[j] for j in Al)) % 10 ** 384
        if all(checks.values()): ok += 1
        else:
            bad += 1; print('FAIL', r['key'], r['rep'], r['word'], r['tag'], [k_ for k_, v in checks.items() if not v])
    print(f"{len(recs)} shadow-branch survivors checked: {ok} points satisfy every congruence of their branch, {bad} do not")
    sys.exit(1 if bad else 0)
main()
