import subprocess, random, itertools, sys
from collections import Counter

R96 = (10 ** 96 - 1) // 9
EX = {2: (1, 0, 0), 3: (0, 1, 0), 4: (2, 0, 0), 6: (1, 1, 0), 7: (0, 0, 1), 8: (3, 0, 0), 9: (0, 2, 0)}
VERT = (2, 1, 0)


def all_patterns(vert, maxk=3):
    dig = [2, 3, 4, 6, 7, 8, 9]
    pats = Counter()
    pairs = [(d, e) for d in dig for e in range(96)]
    for k in range(1, maxk + 1):
        for comb in itertools.combinations_with_replacement(pairs, k):
            tot = [0, 0, 0]
            for d, e in comb:
                for i in range(3):
                    tot[i] += EX[d][i]
            if tuple(tot) == vert:
                V = sum((d - 1) * 10 ** e for d, e in comb)
                pats[V] += 1
    return pats


def main():
    pats = all_patterns(VERT)
    print("distinct V", len(pats), "patterns", sum(pats.values()))
    random.seed(5)
    keys = list(pats)
    bad = 0
    tested = 0
    for trial in range(40):
        V = random.choice(keys)
        nu0 = random.randrange(0, 96)
        y = V + (10 ** nu0 - 1) // 9
        inp = f"{y} 0\n"
        out = subprocess.run(["./anchor_dp", "2", "1", "0", "count"], input=inp, capture_output=True, text=True).stdout.split()
        got = {}
        for tok in out[2:]:
            if tok.startswith("T:"):
                continue
            nu, c = tok.split(":")
            got[int(nu)] = int(c)
        for nu in range(96):
            Vp = y - (10 ** nu - 1) // 9
            exp = pats.get(Vp, 0) if Vp >= 0 else 0
            tested += 1
            if got.get(nu, 0) != exp:
                bad += 1
                print("MISMATCH", y, nu, got.get(nu, 0), exp)
    print("cells", tested, "bad", bad)


main()
