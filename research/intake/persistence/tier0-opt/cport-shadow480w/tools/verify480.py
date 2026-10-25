import sys, json

pts, lat, lpf, y_s = sys.argv[1:5]
perturb = '--perturb' in sys.argv
y = int(y_s)
p96 = [int(l.split()[0]) for l in open(lat) if l.strip() and not l.startswith('#')]
p480 = []
for l in open(lpf):
    t = l.split()
    if not t or t[0] == '#':
        continue
    if t[0] == 'B' and t[1] == '480':
        p480.append(int(t[2]))
    elif t[0] == '480':
        p480.append(int(t[1]))
ok = bad = 0
for l in open(pts):
    r = json.loads(l)
    a = r['a']
    b, c = int(r['pb']), int(r['pc'])
    if perturb:
        b += 1
    V, Lv, nn = int(r['V']), int(r['Lv']), int(r['nn'])

    def val(mod):
        return pow(2, a, mod) * pow(3, b, mod) % mod * pow(7, c, mod) % mod

    checks = {
        'norm': b * b + c * c == nn,
        'level96 primes vs anchor': all(val(p) == y % p for p in p96),
        'level480 primes vs V': all(val(p) == V % p for p in p480),
        'tail 10^480': val(10 ** 480) == Lv % 10 ** 480,
    }
    if all(checks.values()):
        ok += 1
    else:
        bad += 1
        print('FAIL', r['key'], r['rep'], r['word'], r['tag'], [k for k, v in checks.items() if not v])
print(f"{ok + bad} survivor points checked with Python integers: {ok} satisfy every congruence, {bad} do not; level-96 primes {len(p96)}, level-480 primes {len(p480)}")
sys.exit(1 if bad else 0)
