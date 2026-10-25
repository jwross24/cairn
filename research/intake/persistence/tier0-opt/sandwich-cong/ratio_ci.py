import json, random, collections, os
HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
B = "/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/tierc-r2bill/"
new = json.load(open(HERE + "newcpu_wm.json"))
old = collections.defaultdict(float)
for fn in ("results_def1.jsonl", "results_raised1.jsonl", "results_def3.jsonl", "results_raised3.jsonl", "results_o1.jsonl"):
    for l in open(B + fn):
        r = json.loads(l); old[r["id"]] += r["cpu_s"]
ids = sorted(new)
pairs = [(old[i], new[i]) for i in ids]
rng = random.Random(5)
rs = []
for _ in range(20000):
    s = [pairs[rng.randrange(len(pairs))] for _ in pairs]
    rs.append(sum(a for a, b in s) / sum(b for a, b in s))
rs.sort()
print("ratio of sums %.0f, bootstrap 95%% [%.0f, %.0f]" % (sum(a for a, b in pairs) / sum(b for a, b in pairs), rs[500], rs[19500]))
