import json, os, sys, math, collections

T = "/Users/jwross/Documents/cairn/research/intake/persistence/tier0/"
E_ = []
for l in open(T + "trees_mac.jsonl.eqs.jsonl"):
    try:
        E_.append(json.loads(l))
    except Exception:
        pass
for l in open(T + "trees_c.jsonl"):
    try:
        r = json.loads(l)
    except Exception:
        continue
    for e in r.get("eqs", []):
        if isinstance(e, dict) and "levels" in e:
            E_.append(e)
seen = set()
g = collections.defaultdict(lambda: collections.defaultdict(float))
cnt = 0
for e in E_:
    if e.get("npat", 0) <= 2e6 or "levels" not in e:
        continue
    key = (e.get("s"), tuple(e["M"]), e["npat"])
    if key in seen:
        continue
    seen.add(key)
    q = len(e["M"])
    L = {l[0]: l for l in e["levels"]}
    d = g[q]
    d["npat"] += e["npat"]
    d["sv12"] += L[12][2]
    f12 = L[12][3] if len(L[12]) > 3 else {}
    d["open12"] += f12.get("OPEN", 0)
    d["res12"] += sum(v for k_, v in f12.items() if k_ != "OPEN")
    if 24 in L:
        d["n24"] += L[24][1]
        d["sv24"] += L[24][2]
        d["eq24"] += 1
        d["open12_with24"] += f12.get("OPEN", 0)
    d["neq"] += 1


def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"),) * 2
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0.0, c - h), min(1.0, c + h)


print("q neq npat sv12 open12 | sv12/npat [CI] | open12/npat [CI] | open/sv12 | n24/open12 (children per OPEN parent) | n24/sv12")
out = {}
for q in sorted(g):
    d = g[q]
    if d["npat"] == 0:
        continue
    lo, hi = wilson(d["sv12"], d["npat"])
    lo2, hi2 = wilson(d["open12"], d["npat"])
    ch = d["n24"] / d["open12_with24"] if d["open12_with24"] else float("nan")
    print(q, int(d["neq"]), "%.3g" % d["npat"], int(d["sv12"]), int(d["open12"]), "| %.3e [%.3e,%.3e]" % (d["sv12"] / d["npat"], lo, hi), "| %.3e [%.3e,%.3e]" % (d["open12"] / d["npat"], lo2, hi2), "| %.3f" % (d["open12"] / d["sv12"] if d["sv12"] else float("nan")), "| %.1f" % ch, "| %.1f" % (d["n24"] / d["sv12"] if d["sv12"] else float("nan")))
    out[q] = dict(d)
json.dump({str(k): v for k, v in out.items()}, open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs", "rates_by_k.json"), "w"))
