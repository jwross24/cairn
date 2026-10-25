import math, re

def wilson(k, n, z=1.96):
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h

def report(name, total, kept):
    lo, hi = wilson(kept, total)
    print("%-52s %d -> %d   cut %.2fx  [%.2f, %.2f]" % (name, total, kept, total / kept, 1 / hi, 1 / lo))

rows = {}
caps = {}
for line in open("rs_main.out"):
    f = line.split()
    if f[0] == "rank":
        rk = int(f[1]); rows[rk] = {f[i]: int(f[i + 1]) for i in range(2, len(f), 2)}
    if f[0] == "cap":
        caps[(int(f[1]), int(f[3]))] = {f[i]: int(f[i + 1]) for i in range(4, len(f), 2)}
n = sum(r["pat"] for r in rows.values())
print("samples", n)
for rk in (0, 1, 2):
    lo, hi = wilson(rows[rk]["pat"], n)
    print("rank %d share of patterns %.4f%% [%.4f, %.4f]" % (rk, 100 * rows[rk]["pat"] / n, 100 * lo, 100 * hi))
lo, hi = wilson(rows[2]["pat"], n)
print("hot-loop upper bound (rank-2 stream only): %.2fx [%.2f, %.2f]" % (n / rows[2]["pat"], 1 / hi, 1 / lo))
surv = sum(r["surv"] for r in rows.values())
report("residue survivors, rank filter", surv, sum(r["surv_keep"] for r in rows.values()))
print("residue survival rate 1/%.2f" % (n / surv))
op = sum(r["openpat"] for r in rows.values())
report("tail-open patterns (any a<=118), rank filter", op, sum(r["openpat_keep"] for r in rows.values()))
for cap in (60, 118, 160):
    lines = sum(caps[(cap, rk)]["lines"] for rk in (0, 1, 2))
    lk = sum(caps[(cap, rk)]["lines_keep"] for rk in (0, 1, 2))
    report("(a,pattern) lines cap %d, rank filter" % cap, lines, lk)
    o = sum(caps[(cap, rk)]["open"] for rk in (0, 1, 2))
    ok = sum(caps[(cap, rk)]["open_keep"] for rk in (0, 1, 2))
    report("tail-open lines cap %d, rank filter" % cap, o, ok)
ok_pat = sum(r["openpat_keep"] for r in rows.values())
lo, hi = wilson(rows[1]["openpat_keep"] + rows[0]["openpat_keep"], ok_pat)
print("share of final open&keep patterns outside rank 2: %d of %d = %.2f%% [%.2f, %.2f]" % (rows[1]["openpat_keep"] + rows[0]["openpat_keep"], ok_pat, 100 * (rows[1]["openpat_keep"] + rows[0]["openpat_keep"]) / ok_pat, 100 * lo, 100 * hi))
ks = sum(r["surv_keep"] for r in rows.values())
print("share of kept residue survivors outside rank 2: %d of %d = %.2f%%" % (ks - rows[2]["surv_keep"], ks, 100 * (ks - rows[2]["surv_keep"]) / ks))
for rk in (0, 1, 2):
    r = rows[rk]
    lo, hi = wilson(r["surv_keep"], r["surv"])
    print("rank %d: survivors kept by the rank filter %d / %d = %.5f [%.5f, %.5f]" % (rk, r["surv_keep"], r["surv"], r["surv_keep"] / r["surv"], lo, hi))
N = 17240008221052531200
rate = ok_pat / n
lo, hi = wilson(ok_pat, n)
print("Tier C vertex: open&keep parent patterns %.3e [%.3e, %.3e]" % (N * rate, N * lo, N * hi))
ch = 4561 / 9529
clo, chi = wilson(4561, 9529)
print("chain pass %.4f [%.4f, %.4f] -> cut %.3fx [%.3f, %.3f]" % (ch, clo, chi, 1 / ch, 1 / chi, 1 / clo))
print("parents after chain %.3e" % (N * rate * ch))
sec_hot = N * 8e-9
print("hot loop at 8 ns: %.0f core-years; rank-2 stream (1/21): %.0f" % (sec_hot / 3.156e7, sec_hot / 3.156e7 / 21))
for ms in (1.0,):
    print("lift floor at %.0f ms per parent: before chain %.0f core-years, after chain %.0f" % (ms, N * rate * ms * 1e-3 / 3.156e7, N * rate * ch * ms * 1e-3 / 3.156e7))
