import json, subprocess, sys
rows = [json.loads(l) for l in open("diff_recorded.jsonl")] + [json.loads(l) for l in open("diff_recorded_retry.jsonl")]
py = {}
for r in rows:
    if "M" in r and r["new"] is not None:
        py[tuple(r["M"])] = r["new"]
bad = 0
for M, v in py.items():
    out = subprocess.run(["./fonga_v2_c"] + [str(d) for d in M], capture_output=True, text=True).stdout.split()[0]
    if int(out) != v:
        bad += 1
        print("MISMATCH", M, v, out)
print(len(py), "compared", bad, "mismatches")
for sl in ("-1", "1"):
    cnt = 0
    for M, v in list(py.items())[:300]:
        out = subprocess.run(["./fonga_v2_c", "-s", sl] + [str(d) for d in M], capture_output=True, text=True).stdout.split()[0]
        cnt += int(out) != v
    print("slack", sl, "differs from baseline on", cnt, "of 300")
