import json, math
rows = [json.loads(l) for l in open("r2_cost_rows.jsonl")]
ex = []
for r in rows:
    m = 3125 * 2 ** (r["a"] + 9)
    ex.append((r["ncases1"] / m, r["ncases1"], r["a"], r["k"]))
ex.sort(reverse=True)
print("expected survivors in sample (proper per-case prob 1/(3125*2^(a+9)))", sum(e[0] for e in ex))
print("top", [(round(e[0], 3), e[1], e[2], e[3]) for e in ex[:8]])
print("patterns with expected>=0.01:", sum(1 for e in ex if e[0] >= 0.01))
