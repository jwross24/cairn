from itertools import permutations
P = "/Users/jwross/Documents/cairn/research/intake/persistence/tier0/zf_below_1e4000.txt"
rows = [list(map(int, l.split()[1:])) for l in open(P)]
for perm in permutations(range(5), 3):
    ok = True
    for r in rows[::37]:
        y = 2**r[perm[0]] * 3**r[perm[1]] * 7**r[perm[2]]
        if "0" in str(y):
            ok = False
            break
    if ok:
        print("perm", perm)
