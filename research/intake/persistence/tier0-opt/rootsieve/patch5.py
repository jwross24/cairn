t = open("chain.py").read()
i = t.index("    u = [p for p in pats if p[0] == \"U\"]")
j = t.index("main()\n", i)
new = '''    u = [p for p in pats if p[0] == "U"]
    print("uniform survivor subsample", len(u))
    for rk in (2,):
        sub = [p for p in u if p[1] == rk]
        n_all = len(sub)
        n_ch = 0; n_tail = 0; n_both = 0; capc = 0
        for tag, r_, nu, digs, lines in sub:
            ls = [l for l in lines if l[0] <= amax]
            ch = False; tl = False; both = False
            for a, keep, op in sorted(ls):
                f, cp = chain_feasible(a, digs)
                capc += cp
                ch |= f; tl |= bool(op); both |= (f and bool(op))
            n_ch += ch; n_tail += tl; n_both += both
        print("rank", rk, "survivors", n_all, "chain-any", n_ch, "tail-any", n_tail, "both", n_both, "capped lines", capc)

'''
t = t[:i] + new + t[j:]
open("chain.py", "w").write(t)
