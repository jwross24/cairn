import sys
sys.path.insert(0, "/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/tierc-rank")
import gmpy2
from gmpy2 import mpfr
from chainrank import matveev_c, prodlog
import mvchain

for xe in (300, 400, 500):
    tt = 1 + gmpy2.log(mpfr("2.1") * mpfr(10) ** xe + 2 + 6)
    k1_r2 = matveev_c(5) * prodlog([2, 3, 7, 10]) * tt
    k1_r1 = matveev_c(4) * prodlog([2, 3, 10]) * tt
    k1_r1_fold = matveev_c(3) * prodlog([3, 10]) * tt
    kk = mvchain.k1_mv(xe, "b")[0]
    kc = mvchain.k1_mv(xe, "c")[0]
    print(xe, "log10 K1: baker rank2", round(float(gmpy2.log10(k1_r2)), 2), "matveev rank1", round(float(gmpy2.log10(k1_r1)), 2), "matveev rank1 folded", round(float(gmpy2.log10(k1_r1_fold)), 2), "kit b", round(float(gmpy2.log10(kk)), 2), "kit c", round(float(gmpy2.log10(kc)), 2))
