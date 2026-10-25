import hashlib
import json
import math
import os
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(P, "tier0"))
import anchor  # noqa: E402
import pydesc  # noqa: E402
from lattice import Coset  # noqa: E402

CORPUS = "/private/tmp/claude-501/-Users-jwross/Documents-cairn/ec9f8f52-ce29-4a5c-9caf-2ecbd434509f/scratchpad/h12"
CORPUS = "/private/tmp/claude-501/-Users-jwross-Documents-cairn/ec9f8f52-ce29-4a5c-9caf-2ecbd434509f/scratchpad/h12"
OUT = os.path.join(HERE, "out")
KCAP = 400


def read_cfg(path):
    lines = [l for l in open(path).read().split("\n") if l.strip()]
    lold, lnew, A, q = map(int, lines[0].split())
    digits = list(map(int, lines[1].split()))
    uo = list(map(int, lines[-3].split()))
    un = list(map(int, lines[-2].split()))
    return A, q, digits, ((uo[0], uo[1]), (uo[2], uo[3])), ((un[0], un[1]), (un[2], un[3]))


def parse_stats(errp):
    parts = open(errp).read().split()
    st = {}
    for k, v in zip(parts[0::2], parts[1::2]):
        try:
            st[k] = int(v)
        except ValueError:
            pass
    return st


def lines_of(path):
    return [l for l in open(path).read().split("\n") if l.strip()]


def sha(lines):
    return hashlib.sha256("".join(l + "\n" for l in sorted(lines)).encode()).hexdigest()


def fallback_kind(co, a, D, nu, eps, M):
    import tier0v2
    kind, val = tier0v2.classify(co, a, D, nu, eps, 24, M, KCAP)
    if kind in ("OPEN", "SOLUTION+OPEN"):
        K = tier0v2.ten_adic_K(co, KCAP, a)
        if K >= 1:
            st, _ = tier0v2.descend(a, D, eps, nu, co, 24, M, K, KCAP)
            return "OPEN" if st == "OPEN" else "RESOLVED(descent)"
        return "OPEN"
    return kind


def main():
    eqs = sorted(json.loads(l)["eq"] for l in open(os.path.join(P, "tier0-opt", "join24swap", "gate.jsonl")) if '"phase": "diff"' in l and '"level": "24"' in l)
    only = sys.argv[1:]
    rows_out = open(os.path.join(HERE, "survivors.jsonl"), "w")
    summ = []
    gate = []
    for eq in eqs:
        if only and eq not in only:
            continue
        d = os.path.join(CORPUS, eq)
        A, q, digits, uo, un = read_cfg(os.path.join(d, "cfgL24.txt"))
        parents = []
        for line in open(os.path.join(d, "parents24.txt")):
            f = line.split()
            if f:
                parents.append((int(f[0]), int(f[1]), [int(x) for x in f[2:2 + q]], int(f[2 + q]), int(f[3 + q])))
        new = lines_of(os.path.join(OUT, f"{eq}.new.out"))
        x2 = lines_of(os.path.join(OUT, f"{eq}.x2.out"))
        ref_p = os.path.join(OUT, f"{eq}.ref.out")
        ref = lines_of(ref_p) if os.path.exists(ref_p) and os.path.exists(os.path.join(OUT, f"{eq}.ref.err")) and os.path.getsize(os.path.join(OUT, f"{eq}.ref.err")) > 0 else None
        st_new = parse_stats(os.path.join(OUT, f"{eq}.new.err"))
        st_x2 = parse_stats(os.path.join(OUT, f"{eq}.x2.err"))
        x2_oe = [l for l in x2 if not l.startswith("DEAD")]
        x2_dead = [l for l in x2 if l.startswith("DEAD")]
        g = {"eq": eq, "new_vs_x2_open_exact_identical": sha(new) == sha(x2_oe), "dead_lines_eq_counter": len(x2_dead) == st_x2["tail-dead"],
             "tail_dead_new_eq_x2": st_new["tail-dead"] == st_x2["tail-dead"], "children_eq": st_new["children"] == st_x2["children"],
             "ref_checked": ref is not None, "new_vs_ref_identical": (sha(new) == sha(ref)) if ref is not None else None}
        gate.append(g)
        surv = {}
        for l in x2:
            f = l.split()
            kind = f[0]
            pidx, a, nu = int(f[1]), int(f[2]), int(f[3])
            eps = [int(x) for x in f[4:4 + q]]
            t1, t2 = int(f[4 + q]), int(f[5 + q])
            key = (a, nu, anchor.canon(digits, eps))
            ent = surv.setdefault(key, {"kinds": set(), "pidx": pidx, "t": (t1, t2), "eps": eps})
            ent["kinds"].add(kind)
        batch = []
        order = []
        for key, ent in surv.items():
            a, nu, ceps = key
            pa = parents[ent["pidx"]]
            t1, t2 = ent["t"]
            b = pa[3] + t1 * uo[0][0] + t2 * uo[1][0]
            c = pa[4] + t1 * uo[0][1] + t2 * uo[1][1]
            if "DEAD" not in ent["kinds"] or len(ent["kinds"]) > 1:
                batch.append((a, nu, ceps, Coset((b, c), un[0], un[1])))
                order.append(key)
        res = pydesc.classify_batch(batch, tuple(digits), 24, KCAP, True) if batch else []
        dcode = {}
        for key, item, r in zip(order, batch, res):
            code = r[0]
            if code == pydesc.CODE_FALLBACK:
                kind = fallback_kind(item[3], item[0], tuple(digits), item[1], item[2], tuple(digits))
            else:
                kind = pydesc.KIND[code]
            dcode[key] = kind
        cnt = {"R": 0, "R_sh": 0, "T": 0, "T_sh": 0, "D": 0, "D_sh": 0, "tailkill_sh": 0, "tailkill_acc": 0, "half": 0, "a_mismatch": 0}
        resolved = {}
        for key, ent in surv.items():
            a, nu, ceps = key
            anc = anchor.anchor(nu, ceps, digits)
            inT = bool(ent["kinds"] & {"OPEN", "EXACT"})
            kind = dcode.get(key) if inT else None
            inD = kind == "OPEN"
            sh = anc is not None
            half = None
            if not sh:
                half = anchor.half_anchor(nu, ceps, digits)
                if half:
                    cnt["half"] += 1
            if sh and anc["abc"][0] != a:
                cnt["a_mismatch"] += 1
            cnt["R"] += 1
            cnt["R_sh"] += sh
            if inT:
                cnt["T"] += 1
                cnt["T_sh"] += sh
                resolved[kind] = resolved.get(kind, 0) + 1
            else:
                cnt["tailkill_sh" if sh else "tailkill_acc"] += 1
            if inD:
                cnt["D"] += 1
                cnt["D_sh"] += sh
            rows_out.write(json.dumps({"eq": eq, "k": q, "A": A, "a": a, "nu": nu, "eps": list(ceps), "kinds": sorted(ent["kinds"]), "descent": kind,
                                       "shadow": sh, "y": str(anc["y"]) if anc else None, "abc": anc["abc"] if anc else None,
                                       "kappa": anc["kappa"] if anc else None, "half_J": half}) + "\n")
        row = {"eq": eq, "k": q, "A": A, "children": st_new["children"], "tail_dead": st_x2["tail-dead"], **cnt, "descent_kinds": resolved}
        summ.append(row)
        print(json.dumps(row), flush=True)
    rows_out.close()
    if not only:
        json.dump(summ, open(os.path.join(HERE, "summary_by_eq.json"), "w"))
        json.dump(gate, open(os.path.join(HERE, "gate_instrument.json"), "w"))


main()
