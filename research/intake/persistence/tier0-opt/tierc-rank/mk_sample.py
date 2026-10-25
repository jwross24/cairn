import sys, json, random

rank = int(sys.argv[1])
n = int(sys.argv[2])
seed = int(sys.argv[3])
out = sys.argv[4]
rows = []
for ln in open("pairs_filtered.jsonl"):
    y, a, b, c, k = json.loads(ln)
    if (b > 0) + (c > 0) == rank:
        rows.append((y, k))
random.seed(seed)
if n < len(rows):
    rows = random.sample(rows, n)
with open(out, "w") as f:
    for y, k in rows:
        f.write(f"{y} {k}\n")
print(len(rows))
