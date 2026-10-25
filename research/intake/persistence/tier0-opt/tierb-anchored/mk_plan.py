import sys, random
vi, n0, n1, seed, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
rows = [l.split() for l in open(f"work/expect_v{vi}.txt")]
rows = [(r[0], int(r[1]), r[2], int(r[3])) for r in rows]
random.seed(seed)
w0 = [r for r in rows if r[1] == 0]
w1 = [r for r in rows if r[1] != 0]
pick = random.choices(w0, weights=[r[3] for r in w0], k=n0) + random.choices(w1, weights=[r[3] for r in w1], k=n1)
random.shuffle(pick)
with open(out, "w") as f:
    for y, k, nu, n in pick:
        f.write(f"{y} {k} {nu} 1\n")
print(len(w0), len(w1), sum(r[3] for r in w0), sum(r[3] for r in w1))
