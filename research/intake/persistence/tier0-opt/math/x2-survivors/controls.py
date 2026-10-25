import json
import os
import random
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import anchor  # noqa: E402

rng = random.Random(20261021)
R24 = anchor.R24
res = {}


def build(V):
    for nu in range(0, 24):
        W = V - anchor.rep(nu)
        if W < 0 or W >= 10 ** 24:
            continue
        digits, eps = [], []
        for e in range(24):
            c = (W // 10 ** e) % 10
            if c == 0:
                continue
            if c == 9:
                digits += [9, 2]
                eps += [e, e]
            else:
                digits.append(c + 1)
                eps.append(e)
        order = sorted(range(len(digits)), key=lambda i: (digits[i], eps[i]))
        return nu, [eps[i] for i in order], [digits[i] for i in order]
    return None


def s_units(limit):
    out = []
    a = 1
    while a <= limit:
        b = a
        while b <= limit:
            c = b
            while c <= limit:
                out.append(c)
                c *= 7
            b *= 3
        a *= 2
    return out


units = [u for u in s_units(R24 - 1) if u > 1]
res["s_units_below_R24"] = len(units)

r = anchor.anchor(6, [0, 1], [2, 3])
res["c1_111132"] = {"y": r["y"], "abc": r["abc"], "kappa": r["kappa"], "pass": r["y"] == 111132 and r["abc"] == (2, 4, 3) and r["kappa"] == 0}

planted = {"n": 0, "built": 0, "pass": 0, "fail": []}
for kappa in (0, 1, 2, 3):
    for y in rng.sample(units, 300):
        planted["n"] += 1
        b = build(y + kappa * R24)
        if b is None:
            continue
        nu, eps, digits = b
        if anchor.pattern_value(nu, eps, digits) != y + kappa * R24:
            planted["fail"].append(("roundtrip", y, kappa))
            continue
        planted["built"] += 1
        a = anchor.anchor(nu, eps, digits)
        if a is not None and a["y"] == y and a["kappa"] == kappa:
            planted["pass"] += 1
        else:
            planted["fail"].append((y, kappa, None if a is None else (a["y"], a["kappa"])))
planted["fail"] = planted["fail"][:5]
res["c1_planted_anchored"] = planted

n_rand = 100000
shadow_rand = []
for _ in range(n_rand):
    q = rng.randint(5, 20)
    digits = sorted(rng.randint(2, 9) for _ in range(q))
    eps = [rng.randrange(24) for _ in range(q)]
    nu = rng.randrange(24)
    if anchor.anchor(nu, anchor.canon(digits, eps), digits) is not None:
        shadow_rand.append((nu, eps, digits))
res["c2_random_patterns"] = {"n": n_rand, "classified_shadow": len(shadow_rand), "examples": shadow_rand[:3]}

shadows = []
for line in open(os.path.join(HERE, "survivors.jsonl")):
    r = json.loads(line)
    if r["shadow"]:
        shadows.append(r)
pert = {"shadows_available": len(shadows), "tested": 0, "still_shadow": 0}
cap = 20000
for r in rng.sample(shadows, min(cap, len(shadows))):
    digits_d = None
    q = len(r["eps"])
    from_eq = r["eq"]
    digits_d = DIG.get(from_eq) if "DIG" in globals() else None
    if digits_d is None:
        cfg = open(os.path.join("/private/tmp/claude-501/-Users-jwross-Documents-cairn/ec9f8f52-ce29-4a5c-9caf-2ecbd434509f/scratchpad/h12", from_eq, "cfgL24.txt")).read().split("\n")
        digits_d = list(map(int, cfg[1].split()))
        globals().setdefault("DIG", {})[from_eq] = digits_d
    eps = list(r["eps"])
    j = rng.randrange(q)
    eps[j] = (eps[j] + 1) % 24
    pert["tested"] += 1
    if anchor.anchor(r["nu"], eps, digits_d) is not None:
        pert["still_shadow"] += 1
    nu2 = (r["nu"] + 1) % 24
    pert["tested"] += 1
    if anchor.anchor(nu2, r["eps"], digits_d) is not None:
        pert["still_shadow"] += 1
res["c3_perturbed_real_shadows"] = pert

neg = {}
neg["5_times_unit_is_refused"] = anchor.s_unit(5 * 2 ** 10 * 3 ** 5) is None
neg["prime_11_refused"] = anchor.s_unit(11) is None
neg["zero_refused"] = anchor.s_unit(0) is None
neg["V_multiple_of_R24_refused"] = anchor.anchor(0, [], [], modulus=R24) is None
v = anchor.pattern_value(6, [0, 1], [2, 3])
neg["V_5y_refused"] = anchor.s_unit((5 * v) % R24) is None
res["c4_false_anchor_refusals"] = neg
json.dump(res, open(os.path.join(HERE, "controls_out.json"), "w"), indent=1, default=str)
print(json.dumps(res, indent=1, default=str)[:3000])
