import sys, json, signal
sys.path.insert(0, "/Users/jwross/Documents/cairn/research/intake/persistence/tier0")
import tier0 as T
from lattice import Coset
from descent import descend
L = 96
pdata = [T.PrimeData(p, L) for p in T.primes_for_level(L, set())]
rec = json.load(open("/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/math/h1-anchoring/counterexamples.json"))[0]
a, nu, D, eps = rec["a"], rec["nu"], tuple(rec["M"]), tuple(rec["eps"])
co = Coset()
for pd in pdata:
    y = pd.R[nu % L]
    for d, e in zip(D, eps):
        y = (y + (d - 1) * pd.pow10[e % L]) % pd.p
    co = co.intersect(pd.l3, pd.l7, (pd.log(y) - a * pd.l2) % (pd.p - 1), pd.p - 1)
K = T.ten_adic_K(co, 400, a)
def h(*_): raise TimeoutError
signal.signal(signal.SIGALRM, h); signal.alarm(240)
try:
    print("descend ->", descend(a, D, eps, nu, co, L, D, K, 400))
except TimeoutError:
    print("descend timed out at 240s")
