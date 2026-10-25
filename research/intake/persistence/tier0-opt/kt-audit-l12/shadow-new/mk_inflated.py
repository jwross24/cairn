src = "/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/cport-shadow/data/utable_u2.txt"
dst = "/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/kt-audit-l12/shadow-new/inputs/utable_inflated_400.txt"
with open(dst, "x") as f:
    for l in open(src):
        t = l.split()
        if len(t) == 3 and not l.startswith("#"):
            f.write(f"{t[0]} {t[1]} {10 ** 400}\n")
        else:
            f.write(l)
