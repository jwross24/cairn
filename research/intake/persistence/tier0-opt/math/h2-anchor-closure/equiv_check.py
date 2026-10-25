import sys, os, random, json, time
sys.dont_write_bytecode = True
T0 = "/Users/jwross/Documents/cairn/research/intake/persistence/tier0"
os.chdir(T0)
sys.path.insert(0, T0)
import deepcut as DC
import classify_open as C
from lattice import Coset
from descent import cut_coset, v2

random.seed(int(sys.argv[1]) if len(sys.argv) > 1 else 1)
trials = int(sys.argv[2]) if len(sys.argv) > 2 else 300
Lam = DC.kernel_lattice()
res = {"contain": [], "pos": [0, 0], "neg": [0, 0], "mism": []}
for g in (Lam.u1, Lam.u2):
    x, z = g
    for mod in (5 ** 5, 2 ** 9):
        v = pow(3, x, mod) * pow(7, z, mod) % mod
        res["contain"].append((mod, v))
for _ in range(trials):
    a = random.randint(0, 44)
    b, c = random.randint(0, 40), random.randint(0, 40)
    y = 2 ** a * 3 ** b * 7 ** c
    co = Coset((b, c), Lam.u1, Lam.u2)
    N = 5 ** 5 * 2 ** (a + 9)
    kind = random.choice(["pos", "pos", "neg", "near"])
    if kind == "pos":
        L = (y % N) + N * random.randrange(10 ** 96 // N)
    elif kind == "neg":
        L = random.randrange(10 ** 95, 10 ** 96)
    else:
        L = (y % N) + N * random.randrange(10 ** 96 // N)
        L += random.choice([1, 2, 5 ** 5, 2 ** (a + 9)]) * random.choice([1, -1])
    L %= 10 ** 96
    pred = (L - y) % N == 0
    if v2(L) != a or L % 5 == 0:
        got = False
    else:
        got = cut_coset(co, a, L, 96) is not None
    key = "pos" if pred else "neg"
    res[key][0] += 1
    if got != pred:
        res["mism"].append((a, b, c, kind, L))
        res[key][1] += 1
print(json.dumps(res))
