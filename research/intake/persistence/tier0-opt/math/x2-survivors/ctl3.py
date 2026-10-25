import json, os, random, sys, collections
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import anchor
rng = random.Random(20261021)
C = "/private/tmp/claude-501/-Users-jwross-Documents-cairn/ec9f8f52-ce29-4a5c-9caf-2ecbd434509f/scratchpad/h12"
dig = {}
sh = [json.loads(l) for l in open(os.path.join(HERE, "survivors.jsonl"))]
sh = [r for r in sh if r["shadow"]]
byk = collections.Counter(); tot = collections.Counter(); ex = []
for r in sh:
    if r["eq"] not in dig:
        dig[r["eq"]] = list(map(int, open(os.path.join(C, r["eq"], "cfgL24.txt")).read().split("\n")[1].split()))
for kind in ("eps", "nu"):
    for r in rng.sample(sh, 20000):
        d = dig[r["eq"]]; eps = list(r["eps"]); nu = r["nu"]
        if kind == "eps":
            j = rng.randrange(len(eps)); eps[j] = (eps[j] + 1) % 24
        else:
            nu = (nu + 1) % 24
        tot[(kind, r["k"])] += 1
        a = anchor.anchor(nu, eps, d)
        if a:
            byk[(kind, r["k"])] += 1
            if len(ex) < 6: ex.append((kind, r["eq"], r["nu"], r["eps"], d, a["y"], a["abc"], a["kappa"], r["y"]))
for k in sorted(tot): print(k, byk[k], tot[k])
for e in ex: print(e)
