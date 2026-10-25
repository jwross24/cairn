import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import runbin, eval as ev
HERE = runbin.HERE
names = sys.argv[1].split(",")
reps = int(sys.argv[2])
topn = int(sys.argv[3])
eqs = sorted(ev.GATE, key=lambda e: -ev.GATE[e]["children"][0])[:topn]
if len(sys.argv) > 4:
    eqs = sys.argv[4].split(",")
out = os.path.join(HERE, "logs", "timing.jsonl")
for r in range(reps):
    for eq in eqs:
        for n in names:
            b, env = ev.CONFIGS[n]
            b = b if os.path.isabs(b) else os.path.join(HERE, b)
            res = runbin.run(b, eq, "tm_" + n, env=env)
            sh = ev.sets(eq, "tm_" + n)
            ok = eq in ev.REF and sh[0] == ev.REF[eq]["sha"]
            with open(out, "a") as f:
                f.write(json.dumps(dict(rep=r, eq=eq, cfg=n, cpu=res["cpu"], ok=ok, children=ev.GATE[eq]["children"][0])) + "\n")
print("done")
