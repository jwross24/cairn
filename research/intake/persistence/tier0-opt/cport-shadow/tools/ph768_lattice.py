import sys, math
from math import isqrt
def nrm(u): return isqrt(u[0] * u[0] + u[1] * u[1])

sys.dont_write_bytecode = True
sys.path.insert(0, '/Users/jwross/Documents/cairn/research/intake/persistence/tier0')
from sympy import primitive_root
from lattice import Coset
from descent import cut_coset
import deepcut as DC, deepcut_lift as DL
from dlog import discrete_log

def lat_with(co, ps):
    for p in ps:
        g = primitive_root(p)
        co = co.intersect(discrete_log(p, 3 % p, g), discrete_log(p, 7 % p, g), 0, p - 1)
        assert co is not None
    return co

def report(tag, co):
    n1 = nrm(co.u1); n2 = nrm(co.u2)
    print(f"{tag}: index 10^{math.log10(co.index()):.2f}, shortest basis vector 10^{math.log10(min(n1, n2)):.2f}", flush=True)

L96 = DC.kernel_lattice()
report('Lambda_96', L96)
ps192 = DL.new_primes(192, 96); L192 = lat_with(L96, ps192); report('Lambda_192', L192)
ps384 = DL.new_primes(384, 192); L384 = lat_with(L192, ps384); report('Lambda_384', L384)
ps768 = [257, 15361, 453377, 434689, 859393]
L768 = lat_with(L384, ps768); report('Lambda_768 (384 primes + the five PH-feasible new primes)', L768)
for a in (0, 1):
    for (lvl, K, co) in (('384', 384, L384), ('768', 768, L768)):
        z = Coset((0, 0), co.u1, co.u2)
        w = cut_coset(z, a, pow(2, a), K)
        n1 = nrm(w.u1); n2 = nrm(w.u2)
        lam1 = min(n1, n2)
        dig = math.log10(lam1) - 0.5 * math.log10(2) + math.log10(math.log10(3))
        print(f"a={a} level {lvl}: homogeneous window kernel at K={K}: index 10^{math.log10(w.index()):.2f}, shortest vector 10^{math.log10(lam1):.2f} => digits bound for a typical coset ~ 10^{dig:.1f} (worst case over cosets can be smaller by the covering radius, not larger than ~ this order)", flush=True)
