import sys, json
sys.path.insert(0, "/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/tierc-rank")
from depth1c import analyze
from depth1d import analyze_rank

CL = {0: [3], 1: [2], 2: [2, 7], 3: [2], 4: [2, 3], 5: [2] * 8, 6: [2] * 6, 7: [2] * 2, 8: [2] * 2 + [3] * 2, 9: [2] + [3] * 3}
words = [(d, e) for e, l in CL.items() for d in l]
y = 3 ** 3 * 7 ** 10
print(analyze(y, words, 3), analyze_rank(y, words, 3, 2))
rows = [json.loads(l) for l in open("r2_pat.jsonl")][:300]
diff = sum(1 for r in rows if analyze(r["y"], [tuple(w) for w in r["words"]], 2)[0] != analyze_rank(r["y"], [tuple(w) for w in r["words"]], 2, 2)[0])
print("rank-2 old vs generalized mismatches on 300:", diff)
