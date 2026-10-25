import sys, json
sys.path.insert(0, "/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/tierc-rank")
from m0lib import *

L = L2()
print("ord2", L)
kids = json.load(open("recorded_children.json"))["children"]
pw = [v for v in kids if v > 0 and v & (v - 1) == 0]
extra = [2 ** a for a in range(1, 400) if set(str(2 ** a)) <= set("1234 6789".replace(" ", ""))]
cases = sorted(set(pw) | set(extra))
bad = 0
for y in cases:
    s = str(y)
    n = len(s)
    words = [(int(ch), (n - 1 - i) % 96) for i, ch in enumerate(s) if ch != "1"]
    if not words:
        continue
    d = decide(n % 96, words, 10 ** 18, L)
    ok = d["verdict"] == "open"
    bad += 0 if ok else 1
    print("genuine", y if y < 10 ** 12 else "2^%d" % (y.bit_length() - 1), d["verdict"], d.get("reason", ""))
    w2 = list(words)
    d0, e0 = w2[0]
    w2[0] = (d0, (e0 + 1) % 96)
    d2 = decide(n % 96, w2, 10 ** 18, L)
    print("  mutated position:", d2["verdict"], d2.get("reason", ""))
print("genuine reported open:", len(cases) - bad, "of", len(cases))
