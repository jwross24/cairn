p = "ref_check.py"
s = open(p).read()
i = s.index("    def rec(i, L):")
j = s.index("    return rec(0, R96), False")
new = '''    def rec(i, L):
        e = classes[i] if i < len(classes) else 96
        if e <= a:
            if L % (1 << e) != 0:
                return False
        else:
            if v2(L) != a:
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

'''
s = s[:i] + new + s[j:]
s = s.replace("    nodes = [0]\n", "")
open(p, "w").write(s)
