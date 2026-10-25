import sys, json, random
from mpmath import mp, mpf, log10, ceil

mp.dps = 160
words_path, out_path, n_per_word, seed = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
a = 0
M = 10 ** 480
rng = random.Random(seed)
words = [json.loads(l) for l in open(words_path)]
scales = [10 ** 3, 10 ** 9, 10 ** 20, 10 ** 40]
rows = []
for w in words:
    wi = int(w['id'][1:])
    v0 = [int(x) for x in w['offset']]
    u1, u2 = [[int(x) for x in v] for v in w['basis']]
    for t in range(n_per_word):
        R = scales[(wi + t) % len(scales)]
        while True:
            z1, z2 = rng.randint(-R, R), rng.randint(-R, R)
            b = v0[0] + z1 * u1[0] + z2 * u2[0]
            c = v0[1] + z1 * u1[1] + z2 * u2[1]
            if b > 0 and c > 0:
                break
            R *= 4
        Lv = pow(2, a, M) * pow(3, b, M) % M * pow(7, c, M) % M
        digits = a * log10(mpf(2)) + b * log10(mpf(3)) + c * log10(mpf(7))
        U = int(ceil(digits))
        rows.append((wi, b, c, U, Lv))
with open(out_path, 'x') as f:
    for wi, b, c, U, Lv in rows:
        f.write(f"{wi} {b} {c} {U} {Lv}\n")
print(len(rows), 'planted points over', len(words), 'words; coordinate sizes (digits):', sorted(len(str(r[1])) for r in rows))
