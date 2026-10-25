import sys, random, time
sys.dont_write_bytecode = True
from joint import *

random.seed(20261021)
print("scale   P    K     n_digits   ms_planted  recovered  tail_perturbed  head_perturbed  enum_pts")
for E in (6, 12, 24, 40, 70, 100, 150, 220, 281):
    for trial in range(3):
        a = random.randrange(1, 120)
        P = E + 6
        K = E + 6 + a // 2 + 1
        b = random.randrange(10**E // 3, 10**E)
        c = random.randrange(10**E // 3, 10**E)
        n, D, fr = leading_digits(a, b, c, P)
        Bt = pow(2, a, 10**K) * pow(3, b, 10**K) * pow(7, c, 10**K) % 10**K
        nmax = 2 * n
        if a >= K - 5:
            print(f'1e{E:<4} {P:<4} {K:<4} a={a} >= K-5: UNRESOLVED branch (a-free), skipped', flush=True)
            continue
        st = {}
        t0 = time.perf_counter()
        r = query(D, P, Bt, K, P + K, nmax, st)
        ms = (time.perf_counter() - t0) * 1000
        ok = r == [(a, b, c, n)]
        Bt2 = (Bt + (1 << (a + 1))) % 10**K
        rn = query(D, P, Bt2, K, P + K, nmax) if (Bt2 >> a) % 2 == 1 and Bt2 % 5 else "skip"
        rh = query(D + 7, P, Bt, K, P + K, nmax)
        rw = query_fixed_a(D, P, Bt, K, a + 1, P + K, nmax) if False else None
        print(f"1e{E:<4} {P:<4} {K:<4} {n:<10.2e} {ms:9.1f}  {ok!s:<9}  {rn!s:<14}  {rh!s:<14}  {st.get('enum_points')}", flush=True)
