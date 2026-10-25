import random
from fractions import Fraction
from math import floor, log


def simplest_between(lo, hi):
    if lo > hi:
        lo, hi = hi, lo
    fl = floor(lo)
    if fl + 1 <= hi or lo == fl:
        if lo == fl:
            return Fraction(fl)
        return Fraction(fl + 1)
    rest = simplest_between(1 / (hi - fl), 1 / (lo - fl))
    return fl + 1 / rest


def sparse_x(s, c, upto):
    x = Fraction(1)
    for i in range(upto):
        x += Fraction(c[i], 10 ** s[i])
    return x


def lemma_h_trial(rng, relax=1):
    j = rng.randint(1, 4)
    s = [rng.randint(3, 12)]
    for _ in range(j):
        s.append(s[-1] + rng.randint(4, 60))
    c = [rng.choice([9, 18, 27, 36, 54, 63, 72]) for _ in range(j + 1)]
    x = sparse_x(s, c, j + 1)
    sj, g = s[j - 1], s[j] - s[j - 1]
    delta = Fraction(80, 10 ** s[j]) * relax
    q = simplest_between(x - delta, x + delta).denominator
    bound = min(Fraction(10 ** sj, 8), Fraction(10 ** g, 160))
    return q, bound, sj, g


def lemma_h():
    rng = random.Random(7)
    viol = 0
    tight = 0
    n = 4000
    for _ in range(n):
        q, bound, sj, g = lemma_h_trial(rng)
        if q < bound:
            viol += 1
        if q <= 50 * bound:
            tight += 1
    print('Lemma H: min denominator within 80*10^-s_{j+1} of x is >= min(10^s_j/8, 10^g_j/160): violations %d of %d trials; within factor 50 of the bound in %d' % (viol, n, tight))
    rng = random.Random(7)
    neg = 0
    for _ in range(n):
        q, bound, sj, g = lemma_h_trial(rng, relax=10 ** 12)
        if q < bound:
            neg += 1
    print('planted negative (tolerance widened by 10^12, hypothesis broken): bound violated in %d of %d trials' % (neg, n))
    return viol, neg


def liouville():
    print('Liouville sharpness: beta = U (1 + 10^-m), U in the group <2,3,7,10> with fixed small exponents; Lambda = U/beta - 1')
    U_exp = (5, 4, 3, 2)
    U = Fraction(2 ** U_exp[0] * 3 ** U_exp[1] * 7 ** U_exp[2], 10 ** U_exp[3])
    rows = []
    for m in (10, 40, 160, 640, 2560):
        beta = U * (1 + Fraction(1, 10 ** m))
        lam = U / beta - 1
        hb = log(max(abs(beta.numerator), beta.denominator))
        loglam = log(abs(lam.numerator)) - log(lam.denominator)
        rows.append((m, hb, -loglam, -loglam / hb))
        print('  m=%5d  h(beta)=%10.2f  -log|Lambda|=%10.2f  ratio=%.5f' % rows[-1])
    return rows[-1][3]


if __name__ == '__main__':
    v, n = lemma_h()
    r = liouville()
    print('FAILURES:', v, int(n == 0), int(abs(r - 1) > 0.02))
