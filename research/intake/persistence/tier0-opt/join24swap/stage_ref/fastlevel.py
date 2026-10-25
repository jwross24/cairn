"""Level solver with pattern-independent lattice algebra.

At a level with primes p_1..p_k the solution set of
    a*l2_p + b*l3_p + c*l7_p ≡ w_p  (mod p-1)   for all p
is either empty or  v + Λ0, where Λ0 (the common kernel) does not depend on the pattern.
Z^3/Λ0 ≅ H = <v2,v3,v7> ⊂ ∏ Z/(p-1) decomposes into ℓ-primary parts H_ℓ.  For each ℓ we
tabulate H_ℓ with, for every element, one preimage x_ℓ ∈ Z^3 (found during the BFS that
enumerates H_ℓ).  Given w, membership is per-ℓ lookup, and a representative is
    v = Σ_ℓ c_ℓ · x_ℓ(w_ℓ),   c_ℓ ≡ 1 (mod N_ℓ), c_ℓ ≡ 0 (mod N_ℓ') for ℓ' ≠ ℓ,
with N the exponent of H and N_ℓ its ℓ-part.  No lattice arithmetic per pattern.
Splitting by a: the a-coordinates of v + Λ0 form v_a + g Z; for each admissible a0 the (b,c)
representative is  v_bc + ((a0 - v_a)/g)·u_bc  with u ∈ Λ0 of a-component g, and the 2-D
lattice is Λ0 ∩ {a = 0}, fixed.
"""
from collections import defaultdict
from math import gcd
import sympy
from lattice3 import CosetK, _egcd
from lattice import Coset, _reduce


class FastLevel:
    def __init__(self, pdatas, cap=3_000_000):
        self.pdatas = pdatas
        comps = defaultdict(list)
        for i, pd in enumerate(pdatas):
            for l, k in sympy.factorint(pd.p - 1).items():
                comps[l].append((i, l ** k))
        self.comps = []
        for l, lst in sorted(comps.items()):
            size = 1
            for _, m in lst: size *= m
            assert size <= cap, f"component {l} too large ({size}); add a fallback"
            mods = tuple(m for _, m in lst)
            gens = [tuple(getattr(pdatas[i], f) % m for i, m in lst) for f in ("l2", "l3", "l7")]
            H = {tuple(0 for _ in lst): (0, 0, 0)}
            frontier = [tuple(0 for _ in lst)]
            while frontier:
                nxt = []
                for h in frontier:
                    x = H[h]
                    for gi, g in enumerate(gens):
                        t = tuple((u + v) % m for u, v, m in zip(h, g, mods))
                        if t not in H:
                            e = list(x); e[gi] += 1
                            H[t] = tuple(e); nxt.append(t)
                frontier = nxt
            # exponent N_ℓ of H_ℓ: lcm of element orders divides size; use the group order
            # of the ℓ-part of ∏Z/(p-1): the component modulus max is an upper bound; take lcm of mods
            Nl = 1
            for m in mods: Nl = Nl * m // gcd(Nl, m)
            self.comps.append((lst, mods, H, Nl))
        # CRT coefficients
        N = 1
        for _, _, _, Nl in self.comps: N = N * Nl // gcd(N, Nl)
        self.N = N
        self.crt = []
        for lst, mods, H, Nl in self.comps:
            q = N // Nl
            c = q * pow(q % Nl, -1, Nl) if Nl > 1 else 0
            self.crt.append(c % N)
        # common kernel Λ0 and its a-structure
        c3 = CosetK.full(3)
        for pd in pdatas:
            c3 = c3.intersect_congruence([pd.l2, pd.l3, pd.l7], 0, pd.p - 1)
        from lattice3 import _lll
        c3 = CosetK((0, 0, 0), _lll(c3.U))
        self.L0 = c3
        # vector u in Λ0 with minimal positive a-component g, and Λ0 ∩ {a=0}
        g, coeffs = self._gcd_combination([u[0] for u in c3.U])
        self.g = g
        self.u = tuple(sum(cf * c3.U[j][i] for j, cf in enumerate(coeffs)) for i in range(3))
        assert self.u[0] == g
        plane = c3.intersect_equation([1, 0, 0], 0, reduce=True)
        assert all(v[0] == 0 for v in plane.U) and len(plane.U) == 2
        self.U2 = _reduce((plane.U[0][1], plane.U[0][2]), (plane.U[1][1], plane.U[1][2]))

    @staticmethod
    def _gcd_combination(vals):
        g, coeffs = vals[0], [1] + [0] * (len(vals) - 1)
        for j in range(1, len(vals)):
            if vals[j] == 0: continue
            g2, x, y = _egcd(g, vals[j])
            coeffs = [x * cf for cf in coeffs]; coeffs[j] = y; g = g2
        if g < 0:
            g = -g; coeffs = [-cf for cf in coeffs]
        return g, coeffs

    def solve(self, logs):
        """logs[i] = log_{g_i}(y mod p_i).  Returns representative (a,b,c) of the coset, or None."""
        v = [0, 0, 0]
        for (lst, mods, H, Nl), c in zip(self.comps, self.crt):
            t = tuple(logs[i] % m for (i, m) in lst)
            x = H.get(t)
            if x is None:
                return None
            v[0] += c * x[0]; v[1] += c * x[1]; v[2] += c * x[2]
        return tuple(v)

    def verify(self, v, logs):
        for pd, lg in zip(self.pdatas, logs):
            if (v[0] * pd.l2 + v[1] * pd.l3 + v[2] * pd.l7 - lg) % (pd.p - 1):
                return False
        return True

    def split_by_a(self, v, A):
        """yield (a0, Coset2D) for a0 in [0, A] with (a0, b, c) in v + Λ0."""
        g = self.g
        out = []
        r = v[0] % g
        for a0 in range(r, A + 1, g):
            k = (a0 - v[0]) // g
            b = v[1] + k * self.u[1]; c = v[2] + k * self.u[2]
            out.append((a0, Coset((b, c), self.U2[0], self.U2[1])))
        return out


def _selftest():
    import random
    from tier0v2 import PrimeData, primes_for_level
    ps = primes_for_level(12, set()); pd = [PrimeData(p, 12) for p in ps]
    fl = FastLevel(pd)
    rng = random.Random(3)
    for _ in range(300):
        a, b, c = rng.randrange(0, 20), rng.randrange(0, 2000), rng.randrange(0, 2000)
        logs = [(a * p.l2 + b * p.l3 + c * p.l7) % (p.p - 1) for p in pd]
        v = fl.solve(logs); assert v is not None and fl.verify(v, logs)
        # (a,b,c) must lie in the coset: check via split
        found = False
        for a0, co in fl.split_by_a(v, 25):
            if a0 == a and co.contains(b, c): found = True
        assert found, (a, b, c, v)
        # random non-member logs should mostly be rejected or, if accepted, verify
        logs2 = [rng.randrange(0, p.p - 1) for p in pd]
        v2 = fl.solve(logs2)
        if v2 is not None: assert fl.verify(v2, logs2)
    print("fastlevel selftest ok; g =", fl.g, " |H_l| =", [len(H) for _, _, H, _ in fl.comps], " N =", fl.N)


if __name__ == "__main__":
    _selftest()


class FastLevelGen:
    """Pattern-independent algebra for a LIFT level, in 2-D with a fixed.

    Parent coset: (b,c) ∈ v + Λ_old, Λ_old with basis U_old (2×2, rows). New primes p with logs
    (l3_p, l7_p). Writing (b,c) = v + t·U_old, t ∈ Z², the new congruences read
        Σ_i t_i·(U_old[i]·(l3_p,l7_p)) ≡ w_p − a·l2_p − v·(l3_p,l7_p)   (mod p−1).
    So the generators are G_i = (U_old[i]·ℓ_p)_p ∈ ∏ Z/(p−1), i = 1,2, and everything from
    FastLevel applies with these two generators over Z²: ℓ-component tables with coefficient
    representatives, CRT, the common kernel Λ_t ⊂ Z² (fixed), and Λ_new = Λ_t·U_old.
    """
    def __init__(self, pdatas, U_old, cap=3_000_000):
        self.pdatas = pdatas; self.U_old = [tuple(u) for u in U_old]
        self.gens = []   # per prime: (G1, G2)
        for pd in pdatas:
            m = pd.p - 1
            self.gens.append(tuple((u[0] * pd.l3 + u[1] * pd.l7) % m for u in self.U_old))
        comps = defaultdict(list)
        for i, pd in enumerate(pdatas):
            for l, k in sympy.factorint(pd.p - 1).items():
                comps[l].append((i, l ** k))
        self.comps = []
        self.linear = []   # single-prime large components solved by a linear congruence
        for l, lst in sorted(comps.items()):
            mods = tuple(m for _, m in lst)
            gl = [tuple(self.gens[i][j] % m for i, m in lst) for j in range(2)]
            Nl = 1
            for m in mods: Nl = Nl * m // gcd(Nl, m)
            if len(lst) == 1 and mods[0] > 1_000_000:
                self.linear.append((lst[0][0], mods[0], gl[0][0], gl[1][0], Nl))
                continue
            H = {tuple(0 for _ in lst): (0, 0)}
            frontier = [tuple(0 for _ in lst)]
            while frontier:
                nxt = []
                for h in frontier:
                    x = H[h]
                    for gi, g in enumerate(gl):
                        t = tuple((u + v) % m for u, v, m in zip(h, g, mods))
                        if t not in H:
                            e = list(x); e[gi] += 1
                            H[t] = tuple(e); nxt.append(t)
                frontier = nxt
                assert len(H) <= cap, f"component {l}: image larger than cap"
            self.comps.append((lst, mods, H, Nl))
        N = 1
        for _, _, _, Nl in self.comps: N = N * Nl // gcd(N, Nl)
        for _, _, _, _, Nl in self.linear: N = N * Nl // gcd(N, Nl)
        self.N = N
        self.crt = []
        for lst, mods, H, Nl in self.comps:
            q = N // Nl
            self.crt.append((q * pow(q % Nl, -1, Nl) if Nl > 1 else 0) % N)
        self.crt_lin = []
        for _, _, _, _, Nl in self.linear:
            q = N // Nl
            self.crt_lin.append((q * pow(q % Nl, -1, Nl) if Nl > 1 else 0) % N)
        # kernel in t-coordinates: all congruences with rhs 0
        from lattice3 import CosetK, _lll
        ck = CosetK.full(2)
        for pd, g in zip(pdatas, self.gens):
            ck = ck.intersect_congruence(list(g), 0, pd.p - 1)
        kt = _lll(ck.U)
        # Λ_new basis = t·U_old
        U_new = [tuple(sum(t[i] * self.U_old[i][k] for i in range(2)) for k in range(2)) for t in kt]
        self.U_new = _reduce(U_new[0], U_new[1])

    def solve(self, a, v, logs):
        """logs[i] = log(y mod p_i) for the NEW primes. Returns the child coset (Coset) or None."""
        t = [0, 0]
        for (lst, mods, H, Nl), c, in zip(self.comps, self.crt):
            key = tuple((logs[i] - a * self.pdatas[i].l2 - v[0] * self.pdatas[i].l3 - v[1] * self.pdatas[i].l7) % m
                        for (i, m) in lst)
            x = H.get(key)
            if x is None: return None
            t[0] += c * x[0]; t[1] += c * x[1]
        for (i, m, g1, g2, Nl), c in zip(self.linear, self.crt_lin):
            key = (logs[i] - a * self.pdatas[i].l2 - v[0] * self.pdatas[i].l3 - v[1] * self.pdatas[i].l7) % m
            # solve t1*g1 + t2*g2 ≡ key (mod m)
            from lattice import _egcd
            g, x1, x2 = _egcd(g1, g2)            # x1 g1 + x2 g2 = g
            d = gcd(g, m)
            if key % d: return None
            f = key // d; mm = m // d
            inv = pow((g // d) % mm, -1, mm) if mm > 1 else 0
            s_ = f * inv % mm if mm > 1 else 0
            t[0] += c * x1 * s_; t[1] += c * x2 * s_
        b = v[0] + t[0] * self.U_old[0][0] + t[1] * self.U_old[1][0]
        cc = v[1] + t[0] * self.U_old[0][1] + t[1] * self.U_old[1][1]
        # verify
        for pd, lg in zip(self.pdatas, logs):
            assert (a * pd.l2 + b * pd.l3 + cc * pd.l7 - lg) % (pd.p - 1) == 0
        return Coset((b, cc), self.U_new[0], self.U_new[1])
