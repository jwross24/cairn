import b3_chain as bc
from mpmath import mp, mpf, iv, log10
iv.prec = 256
for a in (0, 1, 40):
    for k in (31, 44):
        best = None
        for m in range(1, k + 1):
            v = bc.bound(k, a, m)
            if best is None or v < best[1]: best = (m, v)
        m, v = best
        e = int(mp.floor(log10(v))) - 6
        mant = int(mp.ceil(v / mpf(10) ** e)) + 2
        Niv = iv.mpf(mant) * iv.mpf(10) ** e
        X, q, K0, K1, Y1 = bc.chain(iv, Niv, k, a, m)
        tot = X[m] + q[m]
        ok = (tot.b < Niv.a) and (Niv.a > iv.exp(iv.mpf(k + 1)).b)
        print('a=%d k=%d m=%d certified=%s log10 N=%.4f ratio=%s' % (a, k, m, ok, float(log10(mpf(mant) * mpf(10) ** e)), iv.nstr(tot / Niv, 8)))
