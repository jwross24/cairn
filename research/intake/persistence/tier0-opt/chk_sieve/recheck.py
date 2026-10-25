import gzip
import math
from gmpy2 import mpz, powmod

D = "/Users/jwross/Documents/cairn/research/intake/persistence/tier0/"
M = mpz(10) ** 600
LOG2, LOG3, LOG7 = math.log10(2), math.log10(3), math.log10(7)

seen = set()
lines = torn = 0
for w in (0, 1):
    with gzip.open(D + f"zfsieve_out_{w}.txt.gz", "rt") as fh:
        for line in fh:
            if not line.endswith("\n"):
                torn += 1
                continue
            if line.startswith("DONE"):
                continue
            p = line.split()
            if len(p) != 3:
                torn += 1
                continue
            lines += 1
            seen.add((int(p[0]), int(p[1]), int(p[2])))

low_rejected = full_checked = 0
zf = {}
for a, b, c in sorted(seen):
    est = a * LOG2 + b * LOG3 + c * LOG7
    if est > 604:
        low = powmod(2, a, M) * powmod(3, b, M) * powmod(7, c, M) % M
        if "0" in str(low).zfill(600):
            low_rejected += 1
            continue
    full_checked += 1
    s = str(mpz(2) ** a * mpz(3) ** b * mpz(7) ** c)
    if "0" not in s:
        zf[(a, b, c)] = len(s)

print("survivor lines", lines, "unique triples", len(seen), "torn/other lines", torn)
print("rejected by low 600 digits", low_rejected, "full checks", full_checked)
print("zero-free in survivors", len(zf), "digit range", min(zf.values()), max(zf.values()))
found = set()
for line in open(D + "zfsieve_found.txt"):
    p = line.split()
    found.add((int(p[2]), int(p[3]), int(p[4])))
print("equals chat found.txt:", set(zf) == found, "extra:", sorted(set(zf) - found), "missing:", sorted(found - set(zf)))
