import hashlib, json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
L2 = HERE + "/../math/lane2-lift/src/lane2"
REF = HERE + "/../join24swap/lvlN"
BLIND = HERE + "/lvl24_blind"
BEST_ENV = {"LANE2_E0": "3", "LANE2_A": "3", "LANE2_C": "1", "LANE2_WCAND": "40"}
impls = {"join24": (REF, {}), "blind": (BLIND, {}), "BEST": (L2, BEST_ENV)}
extra = dict(a.split("=", 1) for a in sys.argv[2:])
if "bestbin" in extra: impls["BEST"] = (extra["bestbin"], BEST_ENV)
if "blindbin" in extra: impls["blind"] = (extra["blindbin"], {})
names = sys.argv[1].split(",") if sys.argv[1] != "all" else [c["name"] for c in json.load(open(HERE + "/cases/cases.json"))]
res = {}
for n in names:
    row = {}
    for k, (b, env) in impls.items():
        e = dict(os.environ); e.update(env)
        p = subprocess.run(["nice", "-n", "10", b, f"{HERE}/cases/{n}.cfg", f"{HERE}/cases/{n}.par"], capture_output=True, env=e)
        lines = sorted(p.stdout.splitlines())
        row[k] = dict(rc=p.returncode, nl=len(lines), sha=hashlib.sha256(b"\n".join(lines)).hexdigest()[:12],
                      kinds={t: sum(l.startswith(t.encode()) for l in lines) for t in ("OPEN", "EXACT")},
                      err=p.stderr.decode().strip().split("\n")[-1][:160], lines=[l.decode() for l in lines][:6])
    agree = len({(r["rc"], r["sha"]) for r in row.values()}) == 1
    print(n, "ALL_AGREE" if agree else "DISAGREE", {k: (r["rc"], r["kinds"]) for k, r in row.items()}, flush=True)
    res[n] = row
json.dump(res, open(HERE + "/focused_" + (extra.get("tag", "main")) + ".json", "w"), indent=1)
