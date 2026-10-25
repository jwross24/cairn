import gzip
import sys
import numpy as np
import gmpy2

T0 = "/Users/jwross/Documents/cairn/research/intake/persistence/tier0/"
gmpy2.get_context().precision = 200
S = 1 << 48


def scaled_log(x):
    return int(gmpy2.rint(gmpy2.log(gmpy2.mpfr(x)) * S))


L2, L3, L7, L10 = (scaled_log(x) for x in (2, 3, 7, 10))
DELTA = int(1e-9 * S)


def per_c(c, X, shift):
    top = X * L10 + shift - c * L7
    if top <= 0:
        return 0
    nb = (top - 1) // L3 + 1
    b = np.arange(nb, dtype=np.int64)
    r = top - b * L3
    return int(((r - 1) // L2 + 1).sum())


def total(X, shift):
    cmax = (X * L10 + shift) // L7 + 1
    return sum(per_c(c, X, shift) for c in range(cmax + 1))


bounds = [79, 80, 6883, 6885, 6900]
tot = {}
for X in bounds:
    vals = {s: total(X, s) for s in (-DELTA, 0, DELTA)}
    tot[X] = vals[0]
    print("F", X, vals[-DELTA], vals[0], vals[DELTA], "robust" if len(set(vals.values())) == 1 else "NOT ROBUST")

print("chat range [10^79,10^6885):", tot[6885] - tot[79])
print("chat range [10^80,10^6883):", tot[6883] - tot[80])
print("cairn range [1,10^6900):", tot[6900])

done = {}
dups = 0
conflicts = 0
for w in (0, 1):
    with gzip.open(T0 + f"zfsieve_out_{w}.txt.gz", "rt") as fh:
        for line in fh:
            if line.startswith("DONE") and line.endswith("\n"):
                p = line.split()
                c, cnt = int(p[1]), int(p[2])
                if c in done:
                    dups += 1
                    if done[c] != cnt:
                        conflicts += 1
                done[c] = cnt
print("DONE c values:", len(done), "min", min(done), "max", max(done), "duplicates", dups, "conflicting", conflicts)
print("missing c:", [c for c in range(max(done) + 1) if c not in done][:10])
print("DONE sum:", sum(done.values()))
mism = [c for c in sorted(done) if done[c] != per_c(c, 6885, 0) - per_c(c, 79, 0)]
print("per-c count mismatches vs exact:", len(mism), mism[:10])
print("worker parity ok:", all(c <= 8146 for c in done))
