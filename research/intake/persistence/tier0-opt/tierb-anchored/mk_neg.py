import json
lines = [l for l in open("work/surv_v0_s3000.txt")]
res = [json.loads(l) for l in open("results_s3000cong.jsonl")]
res.sort(key=lambda r: r["id"])
sand = [i for i, r in enumerate(res) if r["label"].startswith("closed by the sandwich")][:8]
cut = [i for i, r in enumerate(res) if r["label"] == "closed by the cut"][:4]
open("work/neg_in.txt", "w").writelines(lines[i] for i in sand + cut)
print(len(sand), len(cut))
