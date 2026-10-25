import sys

def rank2(nu, digits, eps):
    s3 = (nu + sum(d - 1 for d in digits)) % 3
    r7 = [0]
    for i in range(5):
        r7.append((r7[-1] * 10 + 1) % 7)
    y7 = (r7[nu % 6] + sum((d - 1) * pow(10, e % 6, 7) for d, e in zip(digits, eps))) % 7
    return s3 == 0 and y7 == 0

def load(path, digits, filt):
    out = []
    q = len(digits)
    for line in open(path):
        f = line.split()
        if f[0] not in ("OPEN", "EXACT"):
            continue
        nu = int(f[2]); eps = [int(x) for x in f[3:3 + q]]
        if filt and not rank2(nu, digits, eps):
            continue
        out.append(tuple(f))
    return out

digits = [int(x) for x in sys.argv[1].split(",")]
base = load(sys.argv[2], digits, True)
r2 = load(sys.argv[3], digits, False)
r2_bad = [l for l in r2 if not rank2(int(l[2]), digits, [int(x) for x in l[3:3 + len(digits)]])]
print("baseline rank-2 lines", len(base), "stream lines", len(r2), "stream lines outside rank 2", len(r2_bad))
print("identical as sorted lists:", sorted(base) == sorted(r2))
