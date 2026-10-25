from mpmath import mp, mpf, log10
mp.dps = 40
S0 = mpf(10) ** 14.3
C = mpf(10) ** 16.3
for k in (31, 44):
    for th in (0, 0.25, 0.5, 0.75, 0.9, 1):
        s = S0
        for j in range(k):
            s = s + C * s ** mpf(th) if th else s + C
        print('k=%d theta=%.2f  log10 S_k = %.1f' % (k, th, float(log10(s))))
