import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import runbin

HERE = runbin.HERE
GATE = os.path.join(HERE, "..", "..", "join24swap", "gate.jsonl")
TARGET = float(os.environ.get("MEAS_TARGET", "3e6"))
OUTF = os.path.join(HERE, "logs", "measure.jsonl")
rows = {}
for l in open(GATE):
    r = json.loads(l)
    if r["phase"] == "diff" and r["level"] == "24":
        rows[r["eq"]] = r
done = set()
if os.path.exists(OUTF):
    done = {json.loads(l)["eq"] for l in open(OUTF)}
eqs = sorted(rows, key=lambda e: rows[e]["children"][0])
for eq in eqs:
    if eq in done:
        continue
    ch = rows[eq]["children"][0]
    rho = min(1.0, TARGET / max(ch, 1))
    res = runbin.run(os.path.join(HERE, "src", "measure"), eq, "meas", env={"MEAS_RHO": repr(rho), "MEAS_SEED": str(__import__("zlib").crc32(eq.encode()) % 1000003)})
    meas = None
    for line in open(os.path.join(runbin.OUT, f"{eq}_L24.meas.err")):
        if line.startswith("MEAS "):
            meas = json.loads(line[5:])
    ref_sha = rows[eq]["sha_ref"]
    rec = dict(eq=eq, A=rows[eq]["A"], children_gate=ch, rho=rho, cpu=res["cpu"], rc=res["rc"], sha_prefix_match=res["sha"][:16] == ref_sha, meas=meas)
    with open(OUTF, "a") as f:
        f.write(json.dumps(rec) + "\n")
print("done", len(eqs))
