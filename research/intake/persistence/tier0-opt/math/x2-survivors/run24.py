import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
CORPUS = "/private/tmp/claude-501/-Users-jwross-Documents-cairn/ec9f8f52-ce29-4a5c-9caf-2ecbd434509f/scratchpad/h12"
BINS = {
    "new": os.path.join(P, "tier0-opt", "join24swap", "lvlN"),
    "x2": os.path.join(HERE, "inst", "lvlN_x2"),
    "ref": os.path.join(P, "tier0", "lvlN"),
}
WANT = {"new": "b43dad7d891e8a9e19ac7aec10fd042c", "ref": "20e091fc7eecabb906406dfd37bed87d"}
for k, v in WANT.items():
    got = hashlib.md5(open(BINS[k], "rb").read()).hexdigest()
    assert got == v, (k, got)
which = sys.argv[1].split(",")
eqs = [json.loads(l)["eq"] for l in open(os.path.join(P, "tier0-opt", "join24swap", "gate.jsonl")) if '"phase": "diff"' in l and '"level": "24"' in l]
log = open(os.path.join(HERE, "run24.log"), "a")
for eq in sorted(eqs):
    d = os.path.join(CORPUS, eq)
    for w in which:
        outp = os.path.join(HERE, "out", f"{eq}.{w}.out")
        errp = os.path.join(HERE, "out", f"{eq}.{w}.err")
        if os.path.exists(errp) and os.path.getsize(errp) > 0:
            continue
        with open(outp, "w") as fo, open(errp, "w") as fe:
            proc = subprocess.Popen(["nice", "-n", "10", BINS[w], os.path.join(d, "cfgL24.txt"), os.path.join(d, "parents24.txt")], stdout=fo, stderr=fe)
            _, status, ru = os.wait4(proc.pid, 0)
        log.write(json.dumps({"eq": eq, "bin": w, "rc": os.waitstatus_to_exitcode(status), "cpu": round(ru.ru_utime + ru.ru_stime, 2)}) + "\n")
        log.flush()
