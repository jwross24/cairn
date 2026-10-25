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
    nodes = [0]

    def rec(i, L):
        nodes[0] += 1
        e = classes[i] if i < len(classes) else None
        low = min(a + 1, e) if e is not None else a + 1
        if L % (1 << low) != 0 and low <= a:
            if (L % (1 << low)) != 0:
                return False
        if e is None or e >= a + 1:
            if v2(L) != a or L % 5 == 0:
                return False
            if i == len(classes) or True:
                pass
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
s = s[:i] + new + s[j:]
open(p, "w").write(s)
