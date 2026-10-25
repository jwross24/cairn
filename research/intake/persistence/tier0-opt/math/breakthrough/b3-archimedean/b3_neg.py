import b3_chain as bc
from mpmath import mp, mpf, iv, log10
iv.prec = 256
k, a, m = 31, 0, 17
v = bc.bound(k, a, m)
for f in (mpf('0.99'), mpf('1.0000002'), mpf(1)):
    e = int(mp.floor(log10(v))) - 6
    mant = int(mp.ceil(f * v / mpf(10) ** e))
    Niv = iv.mpf(mant) * iv.mpf(10) ** e
    X, q, *_ = bc.chain(iv, Niv, k, a, m)
    print(f, 'accepts' if (X[m] + q[m]).b < Niv.a else 'refuses')
