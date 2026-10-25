import sys, os, math, itertools, time
from collections import Counter, defaultdict
from fractions import Fraction

sys.dont_write_bytecode = True
TIER0 = '/Users/jwross/Documents/cairn/research/intake/persistence/tier0'
HERE = os.path.dirname(os.path.abspath(__file__))
_cwd = os.getcwd()
os.chdir(TIER0)
sys.path.insert(0, TIER0)
import deepcut as DC
from descent import cut_coset, v2
from lattice import Coset
os.chdir(_cwd)

LMAX = 96
ELL_LO = 4771212547


def egcd(a, b):
    x0, y0, x1, y1 = 1, 0, 0, 1
    while b:
        q, a, b = a // b, b, a % b
        x0, x1 = x1, x0 - q * x1
        y0, y1 = y1, y0 - q * y1
    return a, x0, y0


def closes(nn, U):
    return nn * ELL_LO ** 2 > 2 * U * U * 10 ** 20


def log10_big(n):
    return math.log10(n) if n < 10 ** 300 else (len(str(n)) - 1) + math.log10(int(str(n)[:15]) / 1e14)


def bound_digits_log(nn):
    return 0.5 * log10_big(nn) - 0.5 * math.log10(2) + math.log10(math.log10(3))


def exact_E(D, a):
    for E in range(1, D + 1):
        if 2 * LMAX * E - a >= LMAX * D:
            return E
    return D


def class_structure(De):
    types = Counter(De)
    return types


def survivors_to(co0, a, rep, E):
    """labeled survivors of deepcut.deep_cut after depth E: list of (coset, assigned) where assigned = tuple of (digit index, copy)"""
    nu, De = rep
    survivors = [(co0, ())]
    for D in range(1, E + 1):
        K = LMAX * D
        RK = (10 ** K - 1) // 9
        new = []
        for co, assigned in survivors:
            fixed = dict(assigned)
            free = [j for j in range(len(De)) if j not in fixed]
            for choice in itertools.product((0, 1), repeat=len(free)):
                taken = Counter(De[j][1] for j, c in zip(free, choice) if c)
                if any(cnt > 1 for cnt in taken.values()):
                    continue
                L = RK
                for j, t in fixed.items():
                    L += (De[j][0] - 1) * 10 ** (De[j][1] + LMAX * t)
                for j, c in zip(free, choice):
                    if c:
                        L += (De[j][0] - 1) * 10 ** (De[j][1] + LMAX * (D - 1))
                if v2(L) != a or L % 5 == 0:
                    continue
                co2 = cut_coset(co, a, L, K)
                if co2 is None:
                    continue
                new.append((co2, assigned + tuple((j, D - 1) for j, c in zip(free, choice) if c)))
        survivors = new
    return survivors


def pow_mod(b, e, m):
    return pow(b, e, m)


_GC = {}


def _gcached(b, c, mod):
    k = (b, c, mod)
    r = _GC.get(k)
    if r is None:
        r = pow(3, b, mod) * pow(7, c, mod) % mod
        if len(_GC) > 4096:
            _GC.clear()
        _GC[k] = r
    return r


def build_system(co, assigned, a, De, E, D, nu=None):
    """linear system over the high Boolean variables of one depth-E base.
    returns dict with: vars (list of (d, e, t)), alpha (alpha1, alpha2), omega (list), beta, modulus parts"""
    K = LMAX * D
    s = LMAX * E
    fixed = dict(assigned)
    free = [j for j in range(len(De)) if j not in fixed]
    RK = (10 ** K - 1) // 9
    Tbase = RK
    for j, t in fixed.items():
        Tbase += (De[j][0] - 1) * 10 ** (De[j][1] + LMAX * t)
    types = Counter(De[j] for j in free)
    vars_ = []
    for (d, e), cnt in sorted(types.items()):
        for t in range(E, D):
            vars_.append((d, e, t))
    W2 = 2 ** (K - a)
    W5 = 5 ** K
    v0 = co.v0
    u1, u2 = co.u1, co.u2

    def G(b, c, mod):
        return pow(3, b, mod) * pow(7, c, mod) % mod

    G02, G05 = G(v0[0], v0[1], W2), G(v0[0], v0[1], W5)
    gu2, gu5 = _gcached(u1[0], u1[1], W2), _gcached(u1[0], u1[1], W5)
    gv2, gv5 = _gcached(u2[0], u2[1], W2), _gcached(u2[0], u2[1], W5)
    s2 = s - a
    s5 = s
    assert (gu2 - 1) % 2 ** s2 == 0 and (gv2 - 1) % 2 ** s2 == 0, "lattice vectors not 1 mod 2^(s-a)"
    assert (gu5 - 1) % 5 ** s5 == 0 and (gv5 - 1) % 5 ** s5 == 0, "lattice vectors not 1 mod 5^s"
    assert Tbase % 2 ** a == 0 and (Tbase >> a) % 2 == 1
    tau2 = (Tbase >> a) % W2
    tau5 = Tbase * pow(2 ** a, -1, W5) % W5
    rho2 = (G02 - tau2) % W2
    rho5 = (G05 - tau5) % W5
    assert rho2 % 2 ** s2 == 0 and rho5 % 5 ** s5 == 0, "base is not on the depth-E fiber"
    m2 = min(K - a, 2 * s2)
    m5 = min(K, 2 * s5)
    h2 = m2 - s2
    h5 = m5 - s5
    mod2, mod5 = 2 ** h2, 5 ** h5
    al2 = [G02 * (gu2 - 1) // 2 ** s2 % mod2, G02 * (gv2 - 1) // 2 ** s2 % mod2]
    al5 = [G05 * (gu5 - 1) // 5 ** s5 % mod5, G05 * (gv5 - 1) // 5 ** s5 % mod5]
    om2, om5 = [], []
    inv2a5 = pow(2 ** a, -1, mod5) if h5 > 0 else 0
    for (d, e, t) in vars_:
        pos = e + LMAX * t
        w = (d - 1) * 10 ** pos
        om2.append(-((w >> a) // 2 ** s2) % mod2)
        om5.append(-(w // 5 ** s5 * inv2a5) % mod5)
    be2 = -(rho2 // 2 ** s2) % mod2
    be5 = -(rho5 // 5 ** s5) % mod5
    M = mod2 * mod5
    c2 = mod5 * pow(mod5, -1, mod2) if mod2 > 1 else 0
    c5 = mod2 * pow(mod2, -1, mod5) if mod5 > 1 else 0

    def crt(x2, x5):
        return (x2 * c2 + x5 * c5) % M

    alpha = [crt(al2[i], al5[i]) for i in range(2)]
    omega = [crt(om2[i], om5[i]) for i in range(len(vars_))]
    beta = crt(be2, be5)
    return dict(K=K, s=s, h2=h2, h5=h5, M=M, alpha=alpha, omega=omega, beta=beta, vars=vars_,
                types=types, Tbase=Tbase, exact=(h2 == K - s and h5 == K - s), co=co)


def kernel_basis_and_particular(a_vec, beta, M):
    n = len(a_vec)
    piv = None
    for i, x in enumerate(a_vec):
        if math.gcd(x, M) == 1:
            piv = i
            break
    if piv is None:
        raise ValueError("no unit coefficient; saturation failed")
    inv = pow(a_vec[piv], -1, M)
    rows = []
    for j in range(n):
        if j == piv:
            continue
        r = [0] * n
        r[j] = 1
        r[piv] = (-a_vec[j] * inv) % M
        rows.append(r)
    r = [0] * n
    r[piv] = M
    rows.append(r)
    part = [0] * n
    part[piv] = beta * inv % M
    return rows, part


def exact_check(co, a, De, assigned, E, D, xsel, vars_):
    """exact verification that point (b, c) in co satisfies 2^a 3^b 7^c = L (mod 10^K) is done by the caller via check_point"""
    raise NotImplementedError


def lattice_point_value(b, c, a, K):
    return 2 ** a * pow(3, b, 10 ** K) * pow(7, c, 10 ** K) % 10 ** K


def target_value(Tbase, vars_, x, K):
    L = Tbase
    for (d, e, t), xi in zip(vars_, x):
        if xi:
            L += (d - 1) * 10 ** (e + LMAX * t)
    return L % 10 ** K
