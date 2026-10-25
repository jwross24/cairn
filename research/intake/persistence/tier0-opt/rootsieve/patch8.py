t = open("reach.py").read()
i = t.index("def reach_zero")
j = t.index("def main")
new = '''def cycle_vals(e, mod):
    v0 = pow(10, e, mod)
    step = pow(10, 12, mod)
    vals = [v0]
    v = (v0 * step) % mod
    while v != v0:
        vals.append(v)
        v = (v * step) % mod
    return vals

def reach_zero(M, nu, digs):
    n_opts = set(((v - 1) // 9) % M for v in cycle_vals(nu, 9 * M))
    cur = np.zeros(M, dtype=bool)
    for r in n_opts:
        cur[r] = True
    for d, e in digs:
        vs = set(v % M for v in cycle_vals(e, M))
        nxt = np.zeros(M, dtype=bool)
        for v in vs:
            nxt |= np.roll(cur, ((d - 1) * v) % M)
        cur = nxt
    return bool(cur[0]), int(cur.sum())

'''
t = t[:i] + new + t[j:]
open("reach.py", "w").write(t)
