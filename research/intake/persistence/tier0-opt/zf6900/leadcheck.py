import sys
import gmpy2
from gmpy2 import mpz, mpfr
gmpy2.get_context().precision = 200
mpf = mpfr
worst = 0.0
n = 0
for line in sys.stdin:
    a, b, c, e, hi, lo = line.split()
    a, b, c, e = int(a), int(b), int(c), int(e)
    x = mpz(2) ** a * mpz(3) ** b * mpz(7) ** c
    s = str(x)
    assert len(s) == e + 1, (a, b, c, len(s), e)
    exact = mpf(int(s[:60])) / mpf(10) ** (len(s[:60]) - 1)
    got = mpf(float(hi)) + mpf(float(lo))
    rel = abs(got - exact) / exact
    worst = max(worst, float(rel))
    n += 1
print("samples", n, "worst relative error", worst)
