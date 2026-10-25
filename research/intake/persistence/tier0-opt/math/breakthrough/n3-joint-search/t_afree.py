import sys, random, time
sys.dont_write_bytecode = True
from joint import *

random.seed(11)
print("a>=K branch: scan a in [K, K+80]; scale  P   K   a_true  recovered_only_true  ms_total")
for E in (6, 12, 24, 40):
    for trial in range(2):
        P = E + 6
        K = max(8, (2 * E + 8 - P) * 10 // 7 + 1)
        a = random.randrange(K, K + 40)
        b = random.randrange(10**E // 3, 10**E)
        c = random.randrange(10**E // 3, 10**E)
        n, D, fr = leading_digits(a, b, c, P)
        Bt = pow(2, a, 10**K) * pow(3, b, 10**K) * pow(7, c, 10**K) % 10**K
        assert Bt % (1 << K) == 0
        t0 = time.perf_counter()
        res = []
        for aa in range(K, K + 81):
            res += [r for r in query_fixed_a(D, P, Bt, K, aa, P + K, 2 * n) if verify_candidate(*r, D, P, Bt, K)]
        ms = (time.perf_counter() - t0) * 1000
        print(f"1e{E:<3} {P:<4} {K:<4} {a:<4} {res == [(a, b, c, n)]!s:<6} {ms:9.0f}", flush=True)
