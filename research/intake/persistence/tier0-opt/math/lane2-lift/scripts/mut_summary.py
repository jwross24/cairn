import json, glob, os
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in sorted(glob.glob(os.path.join(HERE, "logs", "mut_*.jsonl"))):
    rows = [json.loads(l) for l in open(p)]
    nonvac = [r for r in rows if r["outputs"] > 0]
    caught = [r for r in nonvac if r["caught"]]
    unc = [r for r in nonvac if not r["caught"]]
    forced_ok = 0
    for r in unc:
        f = r.get("forced", {})
        if f and any(f.values()):
            forced_ok += 1
    print("%-18s equations %d, non-vacuous (>=1 output line) %d, caught %d, uncaught %d (of which caught under some forced key set: %d)" % (os.path.basename(p)[4:-6], len(rows), len(nonvac), len(caught), len(unc), forced_ok))
