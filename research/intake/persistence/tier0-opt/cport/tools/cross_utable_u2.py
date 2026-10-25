import sys

sys.dont_write_bytecode = True
from mpmath import mp, mpf, log, exp, factorial, log10, power

mp.dps = 60

P, KAPPA, FP, EP, QU, DEG = 5, 0, 1, 1, 4, 2
EU = exp(1)
LP = log(P)


def big_c1(n):
    c, a1 = 1473, mpf(8) * (P - 1) / (P - 2)
    return (c * a1 ** n * mpf(n) ** n * mpf(n + 1) ** (n + 1) / factorial(n) * mpf(P) ** FP / QU
            * (mpf(DEG) / (FP * LP)) ** (n + 2) * log(max(DEG, EU)) * max(log(EU ** 4 * (n + 1) * DEG), EP, FP * LP))


def big_c2(n):
    c, a2 = mpf(394) * (P - 1) / (P - 2), 8
    return (c / mpf(P) ** KAPPA * (a2 * EU * mpf(P) ** KAPPA) ** n * mpf(n + 1) ** (n + 1) / factorial(n - 1)
            * mpf(P) ** FP / QU * mpf(DEG) ** (n + 2) / (FP * LP) ** 3 * log(max(DEG, EU))
            * max(log(EU ** 4 * (n + 1) * DEG), EP, FP * LP))


def small_g2(n):
    a0, a1, a2 = 1 + log(8), mpf('2.4'), mpf('6.44')
    return (n + 1) * (a0 * n + a1 + log(a0 * n + a2) + log(n + 1) + log(DEG) + FP * LP)


def omega():
    return 1 / (DEG * log(3 * DEG) ** 3)


LN = {x: log(x) for x in (2, 3, 7, 9, 10, 71, 80)}
G2 = small_g2(3)
OM = omega()
IND = big_c2(3) * LN[3] * LN[7]
T1 = lambda n: (n + 1) * big_c1(n)
DEPK = max(T1(2) * LN[3] * LN[7], T1(1) * LN[7], T1(3) * LP / (10 * 7 * DEG) * LN[3] * LN[7])


def yu_bound(H, B):
    indep = IND * H * max(G2, log(OM * (B / H + 1 / LN[3])))
    dependent = DEPK * log(2 * B)
    return max(indep, dependent)


def mat(t):
    return mpf('1.4') * power(30, t + 3) * power(t, mpf(9) / 2)


def fixed_point(k, a, m):
    nu = mpf(10) ** 1500
    for _ in range(100000):
        B = mpf('2.1') * nu + 2
        TA = 1 + log(B)
        first = (mat(3) if a == 0 else mat(4) * LN[2]) * LN[3] * LN[7] * LN[10] * TA
        other = mat(4) * LN[3] * LN[7] * LN[10] * TA
        S = (first + LN[80]) / LN[10]
        for _j in range(1, m):
            S += (LN[80] + other * (S * LN[10] + LN[9] + a * LN[2])) / LN[10]
        if a >= 1:
            if m == k:
                E = mpf(0)
            else:
                E = yu_bound(a * LN[2] + LN[71], B)
                for _j in range(k - 2, m - 1, -1):
                    E = yu_bound(a * LN[2] + E * LN[10] + LN[80], B)
        else:
            E = yu_bound(mpf(1), B)
            for _j in range(k - 1, m - 1, -1):
                E = yu_bound(E * LN[10] + LN[80], B)
        new = S + E
        if abs(new - nu) <= nu * mpf(10) ** -25:
            return new
        nu = new
    raise RuntimeError('no convergence')


def best(k, a):
    return min((fixed_point(k, a, m), m) for m in range(1, k + 1))


if __name__ == '__main__':
    pts = [tuple(map(int, s.split(','))) for s in sys.argv[1:]]
    for (k, a) in pts:
        v, m = best(k, a)
        print(f"k={k} a={a}: log10 U'' = {float(log10(v)):.4f} (m={m})", flush=True)
