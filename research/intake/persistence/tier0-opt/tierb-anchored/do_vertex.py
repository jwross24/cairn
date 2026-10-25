import json, os, random, subprocess, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
vi = int(sys.argv[1]); NTRI = int(sys.argv[2]); NSURV = int(sys.argv[3]); seed = int(sys.argv[4])
v = [json.loads(l) for l in open("/Users/jwross/Documents/cairn/research/intake/persistence/tier0/census-tierB/tierB13.txt")][vi]
A, B, C = v["a"], v["b"], v["c"]
subprocess.run(["uv", "run", "--no-project", "python", "-I", "mk_triples.py", str(vi)], check=True)
rows = [l.split() for l in open(f"work/expect_v{vi}.txt")]
tot = [int(r[3]) for r in rows]
random.seed(seed)
draws = random.choices(range(len(rows)), weights=tot, k=NTRI)
mult = collections.Counter(draws)
tf = f"work/smp_v{vi}_triples.txt"
with open(tf, "w") as f:
    for i in sorted(mult):
        f.write(" ".join(rows[i][:3]) + "\n")
cnt = f"work/smp_v{vi}_count.out"
with open(tf) as fi, open(cnt, "w") as fo:
    subprocess.run(["nice", "-n", "10", "./enum_surv2", str(A), str(B), str(C), "count"], stdin=fi, stdout=fo, check=True)
st = {}
for l in open(cnt):
    t = l.split()
    if t[0] == "T":
        st[(t[1], int(t[2]), int(t[3]))] = (int(t[5]), int(t[6]))
ssum = sum(s for (_, s) in st.values())
p = min(1.0, NSURV / max(1, ssum))
em = f"work/smp_v{vi}_emit.out"
with open(tf) as fi, open(em, "w") as fo:
    subprocess.run(["nice", "-n", "10", "./enum_surv2", str(A), str(B), str(C), "emit", str(seed), repr(p)], stdin=fi, stdout=fo, check=True)
json.dump({"vi": vi, "s": v["s"], "A": A, "B": B, "C": C, "ntri": NTRI, "uniq": len(mult), "p": p, "surv_unique_total": ssum,
           "mult": {f"{rows[i][0]} {rows[i][1]} {rows[i][2]}": m for i, m in mult.items()},
           "tot": {f"{k[0]} {k[1]} {k[2]}": list(x) for k, x in st.items()}, "N": sum(tot)}, open(f"work/smp_v{vi}_meta.json", "w"))
print(vi, v["s"], "uniq", len(mult), "surv in sampled triples", ssum, "p", p)
