import json, subprocess, sys, time, datetime
rows = [(6, 27, 1), (23, 7, 1), (29, 5, 1), (24, 6, 6), (34, 8, 0), (39, 3, 2)]
tmo = int(sys.argv[1])
out = open("tierc_c.jsonl", "a")
for a, b, c in rows:
    M = [2] * a + [3] * b + [7] * c
    t = time.time()
    try:
        r = subprocess.run(["./fonga_v2_c"] + [str(d) for d in M], capture_output=True, text=True, timeout=tmo)
        res = r.stdout.strip()
    except subprocess.TimeoutExpired:
        res = "TIMEOUT"
    out.write(json.dumps({"a": a, "b": b, "c": c, "k": len(M), "result": res, "secs": round(time.time() - t, 1), "when": datetime.datetime.now().isoformat(timespec="seconds")}) + "\n")
    out.flush()
