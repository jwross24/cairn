t = open("chain.py").read()
t = t.replace("CAP_NODES = 200000", "CAP_NODES = 30000")
t = t.replace("""        for a, keep, op in sel:
            lines_total += 1
            r, cp = chain_feasible(a, digs)
            by_a0[a % 12] += 1
            if r:
                lines_pass += 1; by_a0_pass[a % 12] += 1; any_pass = True
            if cp:
                any_cap = True""", """        for a, keep, op in sorted(sel):
            lines_total += 1
            r, cp = chain_feasible(a, digs)
            by_a0[a % 12] += 1
            if cp:
                any_cap = True
            if r:
                lines_pass += 1; by_a0_pass[a % 12] += 1; any_pass = True
                break""")
t = t.replace("""            for a, keep, op in ls:
                f, cp = chain_feasible(a, digs)
                capc += cp
                ch |= f; tl |= bool(op); both |= (f and bool(op))""", """            for a, keep, op in sorted(ls):
                tl |= bool(op)
                if ch and (tl or not op):
                    continue
                f, cp = chain_feasible(a, digs)
                capc += cp
                ch |= f; both |= (f and bool(op))""")
open("chain.py", "w").write(t)
