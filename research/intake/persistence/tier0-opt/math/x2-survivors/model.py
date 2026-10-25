import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
GATE = os.path.join(HERE, "..", "..", "join24swap", "gate.jsonl")
CORPUS = "/private/tmp/claude-501/-Users-jwross-Documents-cairn/ec9f8f52-ce29-4a5c-9caf-2ecbd434509f/scratchpad/h12"
RHO24 = 6.361e-9
RHO12 = 1.684e-3
R24_RATIO = RHO24 / RHO12
SAMPLES = int(os.environ.get("X2_SAMPLES", "20000"))
SEED = 20261021


def equations():
    out = []
    for line in open(GATE):
        r = json.loads(line)
        if r["phase"] == "diff" and r["level"] == "24":
            out.append((r["eq"], r["A"], r["children"][0], r["sig_ref"]))
    return sorted(out)


def read_cfg(path):
    lines = open(path).read().split("\n")
    lines = [l for l in lines if l.strip()]
    lold, lnew, A, q = map(int, lines[0].split())
    digits = list(map(int, lines[1].split()))
    uo = list(map(int, lines[-3].split()))
    un = list(map(int, lines[-2].split()))
    kt = list(map(int, lines[-1].split()))
    return lold, lnew, A, q, digits, uo, un, kt


def ten_adic_K(u1, u2, a, kcap=60):
    K = 0
    for k in range(1, kcap + 1):
        m5 = 5 ** k
        m2 = 2 ** max(k - a, 0)
        ok = True
        for be, ga in (u1, u2):
            if pow(3, be, m5) * pow(7, ga, m5) % m5 != 1:
                ok = False
                break
            if m2 > 1 and pow(3, be, m2) * pow(7, ga, m2) % m2 != 1:
                ok = False
                break
        if not ok:
            break
        K = k
    return K


def subgroup(g1, g2, mod):
    seen = {1}
    frontier = [1]
    while frontier:
        nxt = []
        for x in frontier:
            for g in (g1, g2):
                y = x * g % mod
                if y not in seen:
                    seen.add(y)
                    nxt.append(y)
        frontier = nxt
    return np.array(sorted(seen), dtype=np.int64)


def children_count(eps, digits):
    groups = {}
    for d, e in zip(digits, eps):
        groups.setdefault(d, {}).setdefault(e, 0)
        groups[d][e] += 1
    n = 2
    for d in groups:
        for m in groups[d].values():
            n *= m + 1
    return n, groups


def eq_model(name, A, children_gate, rng):
    d = os.path.join(CORPUS, name)
    lold, lnew, A_cfg, q, digits, uo, un, kt = read_cfg(os.path.join(d, "cfgL24.txt"))
    assert A_cfg == A and lold == 12 and lnew == 24
    u1, u2 = (uo[0], uo[1]), (uo[2], uo[3])
    parents = []
    for line in open(os.path.join(d, "parents24.txt")):
        f = line.split()
        if not f:
            continue
        a, nu = int(f[0]), int(f[1])
        eps = [int(x) for x in f[2:2 + q]]
        b, c = int(f[2 + q]), int(f[3 + q])
        parents.append((a, nu, eps, b, c))
    sub_cache = {}
    k12_cache = {}
    info = []
    total_children = 0
    for (a, nu, eps, b, c) in parents:
        n, groups = children_count(eps, digits)
        total_children += n
        if a not in k12_cache:
            k12_cache[a] = ten_adic_K(u1, u2, a)
        k12 = k12_cache[a]
        keep = 1.0
        need = []
        if k12 >= 1:
            w = pow(2, a, 10 ** k12) * pow(3, b, 10 ** k12) * pow(7, c, 10 ** k12) % 10 ** k12
            for i in range(k12):
                dg = (w // 10 ** i) % 10
                if dg in (0, 1):
                    continue
                m = groups.get(dg, {}).get(i, 0)
                if m == 0:
                    keep = 0.0
                    break
                keep *= m / (m + 1)
                need.append((dg, i))
        info.append((n, keep, need))
    assert total_children == children_gate, (name, total_children, children_gate)
    weights = np.array([n * k for n, k, _ in info], dtype=float)
    W = weights.sum()
    res = {"eq": name, "A": A, "q": q, "parents": len(parents), "children": total_children,
           "E_resid": total_children * R24_RATIO, "W_keep": W}
    if W == 0:
        res.update({"E_tail": 0.0, "E_tail_se": 0.0, "tbar": 0.0, "tbar_se": 0.0})
        return res
    pidx = rng.choice(len(parents), size=SAMPLES, p=weights / W)
    vals = np.zeros(SAMPLES)
    for s, pi in enumerate(pidx):
        a, nu, eps, b, c = parents[pi]
        n, keep, need = info[pi]
        K = min(kt[a], 18)
        mod = 10 ** K
        key = (a, K)
        if key not in sub_cache:
            g1 = pow(3, u1[0], mod) * pow(7, u1[1], mod) % mod
            g2 = pow(3, u2[0], mod) * pow(7, u2[1], mod) % mod
            sub_cache[key] = subgroup(g1, g2, mod)
        S = sub_cache[key]
        Y0 = pow(2, a, mod) * pow(3, b, mod) * pow(7, c, mod) % mod
        Ys = (S * Y0) % mod
        groups = children_count(eps, digits)[1]
        needset = set(need)
        has = np.zeros((10, max(K, 1)), dtype=bool)
        for dg, gr in groups.items():
            for r, m in gr.items():
                forced_keep = (dg, r) in needset
                lo = 0
                hi = m - 1 if forced_keep else m
                k = rng.integers(lo, hi + 1)
                if m - k > 0 and r < K:
                    has[dg, r] = True
                if k > 0 and r + 12 < K:
                    has[dg, r + 12] = True
        ok = np.ones(len(Ys), dtype=bool)
        for i in range(K):
            dig = (Ys // 10 ** i) % 10
            ok &= (dig == 1) | ((dig != 0) & has[dig, i])
        vals[s] = ok.mean()
    tbar = vals.mean()
    se = vals.std(ddof=1) / math.sqrt(SAMPLES)
    res.update({"tbar": tbar, "tbar_se": se, "E_tail": total_children * R24_RATIO * (W / total_children) * tbar,
                "E_tail_se": total_children * R24_RATIO * (W / total_children) * se})
    return res


def main():
    rng = np.random.default_rng(SEED)
    out = []
    sel = sys.argv[1:]
    for name, A, ch, sig in equations():
        if sel and name not in sel:
            continue
        r = eq_model(name, A, ch, rng)
        out.append(r)
        print(json.dumps(r), flush=True)
    path = os.path.join(HERE, "model_out.jsonl") if not sel else os.path.join(HERE, "model_probe.jsonl")
    with open(path, "w") as f:
        for r in out:
            f.write(json.dumps(r) + "\n")


main()
