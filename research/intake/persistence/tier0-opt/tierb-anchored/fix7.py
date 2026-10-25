p = "ref_check.py"
s = open(p).read()
i = s.index("def exact_verdict")
j = s.index("def identity_ok")
new = '''def exact_verdict(y, De):
    a, b, c = fct(y)
    co0 = Coset((b, c), Lam96.u1, Lam96.u2)
    bycls = collections.defaultdict(set)
    for d, e in De:
        bycls[e].add(d - 1)
    classes = sorted(bycls)
    lists = [sorted(bycls[e]) for e in classes]

    def rec(i, L):
        e = classes[i] if i < len(classes) else 96
        if e <= a:
            if L % (1 << e) != 0:
                return False
        elif v2(L) != a:
            return False
        if e >= 1 and L % 5 == 0:
            return False
        if i == len(classes):
            return cut_coset(co0, a, L, 96) is not None
        if rec(i + 1, L):
            return True
        for m in lists[i]:
            if rec(i + 1, L + m * 10**e):
                return True
        return False

    return rec(0, R96), False

'''
open(p, "w").write(s[:i] + new + s[j:])
