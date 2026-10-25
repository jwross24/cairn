import json, re, collections
new = {r["id"][len("s3000cong"):]: r for r in map(json.loads, open("results_s3000cong.jsonl"))}
old = {r["id"][len("s300old"):]: r for r in map(json.loads, open("results_s300old.jsonl"))}
norm = lambda v: re.sub(r"\[\d+s\]", "", v or "")
c = collections.Counter(); bad = []
for i, o in old.items():
    n = new[i]
    same = (o["label"] == n["label"], norm(o["verdict"]) == norm(n["verdict"]))
    c[same] += 1
    if not all(same): bad.append((i, o["verdict"], n["verdict"]))
print(len(old), dict(c))
for b in bad[:3]: print(b)
print("cpu old", sum(o["cpu_s"] for o in old.values()), "new", sum(new[i]["cpu_s"] for i in old))
