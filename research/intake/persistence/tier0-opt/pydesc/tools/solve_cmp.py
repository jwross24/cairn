import sys, os, json, hashlib
src = sys.argv[1]; os.chdir(src); sys.path.insert(0, src)
import tier0v2
from math import prod
def known(s, lim=10**60):
    out = []; a2 = 1
    while a2 < lim:
        b3 = a2
        while b3 < lim:
            y = b3
            while y < lim:
                t = str(y)
                if y >= 10 and '0' not in t and prod(int(c) for c in t if c != '1') == s: out.append(y)
                y *= 7
            b3 *= 3
        a2 *= 2
    return sorted(out)
h = hashlib.sha256(); n = 0
for s in (2, 4, 6, 8, 12, 16, 18, 24, 36, 48, 72, 96, 144, 224):
    kn = known(s)
    for M in tier0v2.multisets(s):
        kk = [y for y in kn if sorted(ch for ch in str(y) if ch != '1') == sorted(str(d) for d in M)]
        r = tier0v2.solve_equation(s, tuple(sorted(M)), kk, verbose=False)
        obs = (s, M, sorted(r['solutions']), r['closed'], [(l[0], l[2], l[3], l[4]) for l in r['levels']], [(a, nu, e, co.v0, co.u1, co.u2) for (a, nu, e, co) in r['open']])
        h.update(json.dumps(obs, default=str).encode()); n += 1
print(os.path.basename(src), n, 'equations', h.hexdigest()[:16])
