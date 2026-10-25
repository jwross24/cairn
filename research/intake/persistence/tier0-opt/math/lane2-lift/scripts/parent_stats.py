import sys, os, collections
S = "/private/tmp/claude-501/-Users-jwross-Documents-cairn/ec9f8f52-ce29-4a5c-9caf-2ecbd434509f/scratchpad/h12"
for eq in sys.argv[1:]:
    n = 0
    pat = collections.Counter(); pat_nu = collections.Counter(); abc = collections.Counter(); asz = collections.Counter(); sorted_pat = collections.Counter()
    for l in open(f"{S}/{eq}/parents24.txt"):
        t = l.split()
        a, nu = int(t[0]), int(t[1])
        q = len(t) - 4
        eps = tuple(map(int, t[2:2 + q]))
        b, c = int(t[2 + q]), int(t[3 + q])
        n += 1
        pat[(nu, eps)] += 1
        asz[a] += 1
    print(eq, "parents", n, "distinct (nu,eps)", len(pat), "max mult", max(pat.values()), "distinct a", len(asz))
