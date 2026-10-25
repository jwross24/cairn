import sys, json
src, out, mode = sys.argv[1], sys.argv[2], sys.argv[3]
n = 0
with open(out, "w") as f:
    for ln in open(src):
        r = json.loads(ln)
        if (r["k"] == 0) == (mode == "w0"):
            f.write(ln)
            n += 1
print(mode, n)
