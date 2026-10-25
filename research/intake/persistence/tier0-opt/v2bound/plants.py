import json, os
from collections import Counter
from gmpy2 import mpz

TIER0 = "/Users/jwross/Documents/cairn/research/intake/persistence/tier0"


def digits_of(y):
    s = str(y)
    return tuple(sorted(int(c) for c in s if c != "1")), "0" in s


def zf_units():
    out = []
    for line in open(os.path.join(TIER0, "zf_below_1e4000.txt")):
        if line.startswith("ZF"):
            _, nd, a, b, c, pers = line.split()
            out.append((int(a), int(b), int(c)))
    return out


def recorded():
    ms = {}
    kids = set()
    for fn in ("runall_final.jsonl", "trees_c.jsonl", "trees_mac.jsonl"):
        for line in open(os.path.join(TIER0, fn)):
            r = json.loads(line)
            for y in r.get("known", []) + r.get("found", []):
                kids.add(int(y))
            for e in r["eqs"]:
                if isinstance(e, dict):
                    ms.setdefault(tuple(sorted(e["M"])), set()).add(fn)
                    for y in e.get("sols", []):
                        if isinstance(y, int):
                            kids.add(y)
                else:
                    ms.setdefault(tuple(sorted(e[0])), set()).add(fn)
                    for y in e[2]:
                        kids.add(int(y))
    return ms, kids
