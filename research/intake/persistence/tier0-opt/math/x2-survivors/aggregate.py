import collections
import json
import math
import os

from scipy.stats import beta, chi2

HERE = os.path.dirname(os.path.abspath(__file__))
summ = json.load(open(os.path.join(HERE, "summary_by_eq.json")))
model = {}
for l in open(os.path.join(HERE, "model_out.jsonl")):
    r = json.loads(l)
    model[r["eq"]] = r
SYS = 0.03


def pois(n, lvl=0.95):
    a = (1 - lvl) / 2
    lo = chi2.ppf(a, 2 * n) / 2 if n > 0 else 0.0
    hi = chi2.ppf(1 - a, 2 * n + 2) / 2
    return lo, hi


def cp(x, n, lvl=0.95):
    a = (1 - lvl) / 2
    lo = beta.ppf(a, x, n - x + 1) if x > 0 else 0.0
    hi = beta.ppf(1 - a, x + 1, n - x) if x < n else 1.0
    return lo, hi


def ratio(obs, E):
    if E <= 0:
        return None
    lo, hi = pois(obs)
    return obs / E, lo / E / (1 + SYS), hi / E / (1 - SYS)


def verdict(r):
    if r is None:
        return "n/a"
    if r[2] < 0.8:
        return "SUPPRESSED"
    if r[1] > 1.25:
        return "ENHANCED"
    return "CONSISTENT"


def fmt_ratio(r):
    return "n/a" if r is None else f"{r[0]:.3f} [{r[1]:.3f}, {r[2]:.3f}] {verdict(r)}"


def block(sel):
    d = collections.Counter()
    for r in sel:
        for k in ("children", "tail_dead", "R", "R_sh", "T", "T_sh", "D", "D_sh", "tailkill_sh", "tailkill_acc", "half", "a_mismatch"):
            d[k] += r[k]
        d["E_R"] += model[r["eq"]]["E_resid"]
        d["E_T"] += model[r["eq"]]["E_tail"]
    d["R_acc"] = d["R"] - d["R_sh"]
    d["T_acc"] = d["T"] - d["T_sh"]
    d["D_acc"] = d["D"] - d["D_sh"]
    return d


def shfrac(x, n):
    if n == 0:
        return "n/a"
    lo, hi = cp(x, n)
    return f"{x / n:.4f} [{lo:.4f}, {hi:.4f}]"


lines = []
lines.append("| k | eqs | children | R | R shadows | R accidents | E_R | rho_R [95%] | T | T shadows | T accidents | E_T | rho_T [95%] | D | D shadows | D accidents | D shadow frac [CP 95%] |")
lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
ok = [r for r in summ if r["A"] < 64]
bad = [r for r in summ if r["A"] >= 64]


def row(label, sel):
    d = block(sel)
    return (f"| {label} | {len(sel)} | {d['children']} | {d['R']} | {d['R_sh']} | {d['R_acc']} | {d['E_R']:.1f} | {fmt_ratio(ratio(d['R_acc'], d['E_R']))} | "
            f"{d['T']} | {d['T_sh']} | {d['T_acc']} | {d['E_T']:.2f} | {fmt_ratio(ratio(d['T_acc'], d['E_T']))} | {d['D']} | {d['D_sh']} | {d['D_acc']} | {shfrac(d['D_sh'], d['D'])} |")


for k in sorted({r["k"] for r in ok}):
    lines.append(row(str(k), [r for r in ok if r["k"] == k]))
lines.append(row("k<=12 (A<64)", [r for r in ok if r["k"] <= 12]))
lines.append(row("k>=13 (A<64)", [r for r in ok if r["k"] >= 13]))
lines.append(row("all (A<64)", ok))
lines.append(row("A>=64 (3 eqs, separate)", bad))
open(os.path.join(HERE, "table_by_k.md"), "w").write("\n".join(lines) + "\n")
print("\n".join(lines))

hi = block([r for r in ok if r["k"] >= 13])
print()
print("H-owner (D shadow frac, k>=13, A<64):", hi["D_sh"], "/", hi["D"], shfrac(hi["D_sh"], hi["D"]))
print("T shadow frac k>=13:", shfrac(hi["T_sh"], hi["T"]), " R shadow frac k>=13:", shfrac(hi["R_sh"], hi["R"]))
al = block(ok)
print("descent pass rate of accidents d = D_acc/T_acc (A<64):", al["D_acc"], al["T_acc"], shfrac(al["D_acc"], al["T_acc"]))
print("tail pass rate of accidents (T_acc/R_acc):", shfrac(al["T_acc"], al["R_acc"]))
print("tail pass of shadows:", shfrac(al["T_sh"], al["R_sh"]))
print("half-anchor diagnostic:", al["half"], " a mismatch:", al["a_mismatch"])
per = []
for r in summ:
    m = model[r["eq"]]
    per.append({"eq": r["eq"], "k": r["k"], "A": r["A"], "R_acc": r["R"] - r["R_sh"], "E_R": round(m["E_resid"], 3), "T_acc": r["T"] - r["T_sh"], "E_T": round(m["E_tail"], 4),
                "R": r["R"], "R_sh": r["R_sh"], "T": r["T"], "T_sh": r["T_sh"], "D": r["D"], "D_sh": r["D_sh"]})
json.dump(per, open(os.path.join(HERE, "per_equation.json"), "w"), indent=0)
