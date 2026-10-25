import sys, itertools, collections, time
sys.dont_write_bytecode = True
T0 = "/Users/jwross/Documents/cairn/research/intake/persistence/tier0"
sys.path.insert(0, T0)
from lattice import Coset
from descent import cut_coset, v2
import deepcut as DC

Lam96 = DC.kernel_lattice()
R96 = (10**96 - 1) // 9
CHOICE_CAP = 60000

def fct(y):
    e = []
    for p in (2, 3, 7):
        c = 0
        while y % p == 0:
            y //= p; c += 1
        e.append(c)
    assert y == 1
    return e

def exact_verdict(y, De):
    a, b, c = fct(y)
    co0 = Coset((b, c), Lam96.u1, Lam96.u2)
    bycls = collections.defaultdict(set)
    for d, e in De:
        bycls[e].add(d - 1)
    classes = sorted(bycls)
    lists = [sorted(bycls[e]) for e in classes]

    def rec(i, L):
        e = classes[i] if i < len(classes) else 96
        if e <= a:
            if L % (1 << e) != 0:
                return False
        elif v2(L) != a:
            return False
        if e >= 1 and L % 5 == 0:
            return False
        if i == len(classes):
            return cut_coset(co0, a, L, 96) is not None
        if rec(i + 1, L):
            return True
        for m in lists[i]:
            if rec(i + 1, L + m * 10**e):
                return True
        return False

    return rec(0, R96), False

def identity_ok(y, k, nu, De, s):
    T = sum((d - 1) * 10**e for d, e in De)
    p = 1
    for d, e in De:
        p *= d
    R = lambda n: (10**n - 1) // 9
    return T == y + k * R96 - R(nu) and p == s and all(0 <= e < 96 for d, e in De)

if __name__ == "__main__":
    path, s = sys.argv[1], int(sys.argv[2])
    stat = collections.Counter(); bad = []
    t0 = time.time()
    for l in open(path):
        t = l.split()
        if t[0] != "P": continue
        y, k, nu, a, verd, n = int(t[1]), int(t[2]), int(t[3]), int(t[4]), int(t[5]), int(t[6])
        De = [tuple(map(int, x.split(":"))) for x in t[7:7 + n]]
        assert len(De) == n
        if not identity_ok(y, k, nu, De, s):
            stat["identity_fail"] += 1; bad.append(("IDENTITY", l.strip())); continue
        ex, red = exact_verdict(y, De)
        cls = "wrap0" if k == 0 else ("wrapneg" if k < 0 else "wrap>=1")
        stat[(cls, "C=%d" % verd, "exact=%d" % ex)] += 1
        stat["reduced"] += red
        if bool(verd) != ex:
            bad.append(("MISMATCH", l.strip()))
    for k, v in sorted(stat.items(), key=str): print(k, v)
    print("total", sum(v for k, v in stat.items() if isinstance(k, tuple)), "mismatches", len([b for b in bad if b[0] == "MISMATCH"]), "identity_fail", stat["identity_fail"], "sec", round(time.time() - t0))
    for b in bad[:10]: print(b)
