import json, os, itertools
C = "/private/tmp/claude-501/-Users-jwross-Documents-cairn/ec9f8f52-ce29-4a5c-9caf-2ecbd434509f/scratchpad/h12/124416_222222222399/cfgL24.txt"
HERE = os.path.dirname(os.path.abspath(__file__)) + "/cases"
lines = open(C).read().split("\n")
assert lines[0].split() == ["12", "24", "46", "12"]
A = 46
assert len(lines[-1].split()) == A + 1 or len(lines[-2].split()) == A + 1
kt_idx = len(lines) - 1 if len(lines[-1].split()) == A + 1 else len(lines) - 2
body = lines[2:kt_idx]

def write_cfg(name, digits, kt):
    kts = [kt(a) if callable(kt) else kt for a in range(A + 1)]
    t = [f"12 24 {A} {len(digits)}", " ".join(map(str, digits))] + body + [" ".join(map(str, kts))]
    open(f"{HERE}/{name}.cfg", "w").write("\n".join(t) + "\n")

def parent(a, b, c, Y):
    s = str(Y); L = len(s)
    nonone = sorted((int(ch), i) for i, ch in enumerate(reversed(s)) if ch != "1")
    digs = [d for d, _ in nonone]
    eps = [i % 12 for _, i in nonone]
    nu = L % 12
    return digs, f"{a} {nu} {' '.join(map(str, eps))} {b} {c}"

def case(name, abc, kt):
    a, b, c = abc
    Y = 2**a * 3**b * 7**c
    assert "0" not in str(Y), (abc, Y)
    digs, line = parent(a, b, c, Y)
    write_cfg(name, digs, kt)
    open(f"{HERE}/{name}.par", "w").write(line + "\n")
    return dict(name=name, abc=abc, Y=Y, digits=digs, parent=line, kt=kt if not callable(kt) else "fn")

cases = []
cases.append(case("short_exact", (2, 1, 0), 4))
cases.append(case("short_exact_kt3", (2, 1, 0), 3))
cases.append(case("short_exact_kt2", (2, 1, 0), 2))
cases.append(case("k_lt1", (2, 1, 0), 0))
cases.append(case("a0_21", (0, 1, 1), 5))
cases.append(case("a0_21_k0", (0, 1, 1), 0))
cases.append(case("a0_27", (0, 3, 0), 6))
cases.append(case("a0_63", (0, 2, 1), 6))
cases.append(case("a0_189", (0, 3, 1), 7))
cases.append(case("short_exact_a1_18", (1, 2, 0), 4))
# searches
found = {}
for a in range(0, 36):
    for b in range(0, 28):
        for c in range(0, 14):
            Y = 2**a * 3**b * 7**c; s = str(Y); L = len(s)
            if "0" in s or L < 13 or L > 23 or L == 24: continue
            digs, line = parent(a, b, c, Y)
            slots = {}
            for ch_i, ch in enumerate(reversed(s)):
                if ch != "1": slots[(int(ch), ch_i % 12)] = slots.get((int(ch), ch_i % 12), 0) + 1
            rep = any(v >= 2 for v in slots.values())
            multi = len({r for (d, r) in slots}) > 1 and any(sum(1 for (dd, r) in slots if dd == d) >= 2 for d in {d for d, _ in slots})
            if rep and "rep" not in found: found["rep"] = (a, b, c)
            if multi and not rep and "multi" not in found: found["multi"] = (a, b, c)
            if rep and multi and "both" not in found: found["both"] = (a, b, c)
print(found)
for k, abc in found.items():
    for kt in (0, 4, 12):
        cases.append(case(f"long_{k}_k{kt}", abc, kt))
json.dump(cases, open(f"{HERE}/cases.json", "w"), indent=1, default=str)
for c in cases: print(c["name"], c["abc"], c["Y"], c["digits"], c["parent"])
