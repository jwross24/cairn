import json, subprocess, time, datetime
a, b, c = 24, 6, 6
M = [2] * a + [3] * b + [7] * c
t = time.time()
try:
    r = subprocess.run(["./fonga_v2_c"] + [str(d) for d in M], capture_output=True, text=True, timeout=14400)
    res = r.stdout.strip() or ("exit %d" % r.returncode)
except subprocess.TimeoutExpired:
    res = "TIMEOUT"
with open("tierc_c.jsonl", "a") as out:
    out.write(json.dumps({"a": a, "b": b, "c": c, "k": len(M), "result": res, "secs": round(time.time() - t, 1), "when": datetime.datetime.now().isoformat(timespec="seconds")}) + "\n")
