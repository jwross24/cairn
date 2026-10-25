import sys, random
src, n, seed, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
lines = [l for l in open(src) if not l.startswith("T")]
random.seed(seed)
pick = random.sample(lines, n)
open(out, "w").writelines(pick)
print(len(lines), len(pick))
