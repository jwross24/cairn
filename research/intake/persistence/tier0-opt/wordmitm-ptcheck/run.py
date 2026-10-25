import json, os, resource, subprocess, sys
B = "/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/"
SH = B + "tierc-r2shadow/data/"
RB = B + "tierc-r2bill/data/"
HERE = "/private/tmp/claude-501/-Users-jwross-Documents-cairn/ec9f8f52-ce29-4a5c-9caf-2ecbd434509f/scratchpad/ptprobe/"
binary = HERE + sys.argv[1]
ids = []
for f in ("ids_all.txt", "ids_b3.txt", "ids_o1.txt"):
    ids += [l.strip() for l in open(RB + f) if l.strip()]
ids = sorted(set(ids))
bound = (1 << 64) // 32


def limits():
    resource.setrlimit(resource.RLIMIT_CPU, (600, 600))


rows = []
for i in ids:
    cmd = ["nice", "-n", "10", binary, "shadow480", "--word-mitm", "--mitm-space-cap", "1e30", "--mitm-right-cap", "1e14",
           "--rep-file", RB + "rep_%s.rep" % i, "--lattice", SH + "lattice96.txt",
           "--levelprimes", SH + "levelprimes480.txt", "--utable", RB + "utable_u2_k34.txt"]
    p = subprocess.run(cmd, capture_output=True, text=True, preexec_fn=limits)
    pts = [int(l.split()[1]) for l in p.stderr.splitlines() if l.startswith("PTLOG")]
    verdict = [l for l in p.stdout.splitlines() if "VERDICT" in l]
    rows.append({"id": i, "rc": p.returncode, "pts": pts, "verdict": verdict[-1] if verdict else None})
with open(HERE + "pt_%s.jsonl" % sys.argv[1], "w") as fo:
    for r in rows:
        fo.write(json.dumps(r) + "\n")
allpt = [x for r in rows for x in r["pts"]]
print("cases", len(rows), "rc!=0", sum(r["rc"] != 0 for r in rows), "reps with PT", len(allpt))
print("max PT %.4g" % max(allpt), "bound 32P<2^64 needs P<%.4g" % bound, "over", sum(x >= bound for x in allpt))
print("distinct PT", sorted(set(allpt))[-8:])
