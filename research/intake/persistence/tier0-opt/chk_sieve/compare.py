import sys
from gmpy2 import mpz

D = "/Users/jwross/Documents/cairn/research/intake/persistence/"
OUT = D + "tier0-opt/chk_sieve/"


def exact(a, b, c):
    s = str(mpz(2) ** a * mpz(3) ** b * mpz(7) ** c)
    return len(s), "0" not in s


def load_cairn(path):
    out = {}
    for line in open(path):
        p = line.split()
        assert p[0] == "ZF"
        t = (int(p[2]), int(p[3]), int(p[4]))
        assert t not in out
        out[t] = int(p[1])
    return out


def load_chat_found(path):
    out = {}
    for line in open(path):
        p = line.split()
        assert p[0] == "ZF-NEW"
        t = (int(p[2]), int(p[3]), int(p[4]))
        assert t not in out
        out[t] = int(p[1])
    return out


def load_ctrl(path):
    tri = set()
    for line in open(path):
        p = line.split()
        if len(p) == 3 and p[0] != "DONE":
            tri.add((int(p[0]), int(p[1]), int(p[2])))
    zf = {}
    for t in tri:
        n, ok = exact(*t)
        if ok:
            zf[t] = n
    return len(tri), zf


def diff(x, y):
    return sorted(set(x) - set(y)), sorted(set(y) - set(x))


cairn = load_cairn(D + "tier0-opt/zf6900/zf_below_1e6900.txt")
cairn_tier0 = load_cairn(D + "tier0/zf_below_1e6900.txt")
found = load_chat_found(D + "tier0/zfsieve_found.txt")
nctrl, ctrl = load_ctrl(D + "tier0/zfsieve_ctrl80.txt")

print("cairn entries", len(cairn), "tier0 copy equal:", cairn == cairn_tier0)
bad = [t for t, n in cairn.items() if exact(*t) != (n, True)]
print("cairn entries failing exact recheck (digits, zero-free):", len(bad))
bad = [t for t, n in found.items() if exact(*t) != (n, True)]
print("chat found entries failing exact recheck:", len(bad))
print("cairn max digits", max(cairn.values()), "count with >140 digits", sum(1 for n in cairn.values() if n > 140))

cairn_hi = {t: n for t, n in cairn.items() if n >= 80}
print("cairn entries with >=80 digits:", len(cairn_hi), " chat found:", len(found))
only_cairn, only_chat = diff(cairn_hi, found)
print("common range >=80 digits: only in cairn", only_cairn, "only in chat", only_chat)
print("digit counts agree on common entries:", all(cairn_hi[t] == found[t] for t in set(cairn_hi) & set(found)))
print("found digit range", min(found.values()), max(found.values()))

cairn_lo = {t: n for t, n in cairn.items() if n <= 80}
print("ctrl80 stage survivors", nctrl, "exact zero-free", len(ctrl), "cairn with <=80 digits", len(cairn_lo))
print("ctrl80 digit max", max(ctrl.values()))
oc, ot = diff(cairn_lo, ctrl)
print("range <10^80: only in cairn", oc, "only in ctrl", ot)

all_chat = dict(ctrl)
all_chat.update(found)
oc, ot = diff(cairn, all_chat)
print("union (ctrl80 + found) vs cairn full list: only cairn", len(oc), "only chat", len(ot), "equal:", cairn == all_chat)


def comparator_flags(a, b):
    x, y = diff(a, b)
    return bool(x or y), x, y


drop = sorted(found)[17]
found_dropped = {t: n for t, n in found.items() if t != drop}
open(OUT + "planted_found_drop1.txt", "w").write("".join(f"ZF-NEW {n} {t[0]} {t[1]} {t[2]}\n" for t, n in found_dropped.items()))
reloaded = load_chat_found(OUT + "planted_found_drop1.txt")
print("planted drop", drop, "-> comparator flags:", comparator_flags(cairn_hi, reloaded))

drop2 = sorted(cairn)[5000]
cairn_dropped = {t: n for t, n in cairn.items() if t != drop2}
print("planted drop from cairn", drop2, "-> comparator flags:", comparator_flags(cairn_dropped, all_chat))

extra = dict(found)
extra[(3, 4, 5)] = 9
print("planted extra entry -> comparator flags:", comparator_flags(cairn_hi, extra))
print("unplanted control flags:", comparator_flags(cairn_hi, found))
