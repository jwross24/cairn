import json, sys, time
from fonga_v2 import exact_max_v2, Budget
from oldbound import old_capped, StateCap
cap = int(sys.argv[1])
rows = [json.loads(l) for l in open("diff_recorded.jsonl")]
out = open("diff_recorded_retry.jsonl", "w")
for r in rows:
    if "M" in r and r["new"] is None:
        M = tuple(r["M"])
        t = time.time()
        try:
            n = exact_max_v2(M, node_limit=cap)
        except Budget:
            n = None
        o = r["old"]
        out.write(json.dumps({"M": M, "k": len(M), "old": o, "new": n, "secs": round(time.time() - t, 2)}) + "\n")
        out.flush()
