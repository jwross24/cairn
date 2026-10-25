import sys, json, zlib
sys.path.insert(0, "/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/tierc-rank")
from depth1d import analyze_rank
from depth1c import v2
from uppp import depth_for, exact_e

src, dst, tally, frac_low = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4])
kmin_full = 30
n_by_k, t_by_k, s_by_k = {}, {}, {}
with open(dst, "a") as g:
    for i, ln in enumerate(open(src)):
        r = json.loads(ln)
        w = [tuple(x) for x in r["words"]]
        k = len(w)
        n_by_k[k] = n_by_k.get(k, 0) + 1
        if k < kmin_full and (zlib.crc32(ln.encode()) % 1000000) / 1e6 >= frac_low:
            continue
        t_by_k[k] = t_by_k.get(k, 0) + 1
        y = r["y"]
        s1, nodes, nc = analyze_rank(y, w, 1, 2)
        if s1:
            s_by_k[k] = s_by_k.get(k, 0) + 1
            D, x = depth_for(k, v2(y))
            E = exact_e(D, v2(y))
            s1e, nodesE, _ = analyze_rank(y, w, E, 2)
            g.write(json.dumps({"y": y, "k": k, "a": v2(y), "s1": s1, "ncases1": nc, "E": E, "nodes": nodesE, "words": r["words"], "nu": r["nu"], "wrap": r["k"], "src": src}) + "\n")
            g.flush()
with open(tally, "x") as f:
    json.dump({"src": src, "frac_low": frac_low, "n_by_k": n_by_k, "tested_by_k": t_by_k, "surv_by_k": s_by_k}, f)
