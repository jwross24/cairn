import sys, os, random, json, itertools
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
T0 = "/Users/jwross/Documents/cairn/research/intake/persistence/tier0"
os.chdir(T0)
sys.path.insert(0, T0)
sys.path.insert(0, HERE)
import deepcut as DC
import classify_open as C
from lattice import Coset
from descent import cut_coset, v2
from anchor_closure import Anchor, decide

random.seed(7)
files = sys.argv[1:]
Lam = DC.kernel_lattice()
MOD = 10 ** 96
anchors = {}
for f in files:
    for (s, M, a, nu, eps, y, sol) in C.entries(f):
        anchors[(y, a)] = (C.factor237(y)[1], C.factor237(y)[2])

res = {"anchors": len(anchors), "planted_points": 0, "false_kills": [], "cut_checked": 0, "cut_disagree": [],
       "perturbed": 0, "perturbed_killed": 0, "perturbed_disagree": [], "shared_anchor_multi": 0}


def digits_pattern(L):
    s = str(L).zfill(96)[::-1]
    return [(int(ch), e) for e, ch in enumerate(s) if ch != "1"]


combos = [(i, j) for i in range(-2, 3) for j in range(-2, 3) if (i, j) != (0, 0)]
for (y, a), (b, c) in anchors.items():
    A = Anchor(y, a)
    co = Coset((b, c), Lam.u1, Lam.u2)
    open_here = 0
    for (i, j) in random.sample(combos, 6):
        x = i * Lam.u1[0] + j * Lam.u2[0]
        z = i * Lam.u1[1] + j * Lam.u2[1]
        L = y % MOD * pow(3, x, MOD) % MOD * pow(7, z, MOD) % MOD
        surv, _ = decide(A, digits_pattern(L))
        res["planted_points"] += 1
        if surv == 0:
            res["false_kills"].append((y, a, i, j))
        else:
            open_here += 1
        if random.random() < 0.15:
            res["cut_checked"] += 1
            if cut_coset(co, a, L, 96) is None:
                res["cut_disagree"].append((y, a, i, j))
        e = random.randrange(0, A.w)
        dl = random.choice([1, 2, 3, 4, -1, -2, -3])
        L2 = (L + dl * 10 ** e) % MOD
        res["perturbed"] += 1
        pred = (L2 - y) % (5 ** 5 * 2 ** (a + 9)) == 0
        ref = v2(L2) == a and L2 % 5 != 0 and cut_coset(co, a, L2, 96) is not None
        res["perturbed_killed"] += not ref
        if ref != pred:
            res["perturbed_disagree"].append((y, a, e, dl))
    if open_here >= 2:
        res["shared_anchor_multi"] += 1

self_n = self_open = 0
self_bad = []
for yv in sorted(C.corpus):
    f = C.factor237(yv)
    n = len(str(yv))
    if f is None or n >= 96 or n < f[0] + 9:
        continue
    A = Anchor(yv, f[0])
    surv, _ = decide(A, [(int(ch), e) for e, ch in enumerate(str(yv)[::-1]) if ch != "1"])
    self_n += 1
    self_open += surv > 0
    if surv == 0:
        self_bad.append(yv)
res.update(self_corpus_units=self_n, self_corpus_open=self_open, self_corpus_killed=self_bad)
print(json.dumps(res))
