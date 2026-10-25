p = "bill2.py"
s = open(p).read()
s = s.replace('''    lab[r["id"]] = r["label"]
            cens[r["id"]] = bool(r["killed"])''', '''    lab[r["id"]] = "BUDGET" if r["label"] == "ERROR" else r["label"]
            cens[r["id"]] = bool(r["killed"]) or r["label"] == "ERROR"''')
s = s.replace('''def boot(extra_w0=None):''', '''def boot(extra_w0=None, sub=None):''')
s = s.replace('''        pool = c0 + (extra_w0 or [])''', '''        pool = (c0 if sub is None else sub) + (extra_w0 or [])''')
s = s.replace('''old = []''', '''ce0 = [cens[i] for i in ids]
sub = [7200.0 if f else x for x, f in zip(c0, ce0)]
print("censored (BUDGET) survivors", sum(ce0), [(i, meta[i]["k"], round(cost[i], 1)) for i, f in zip(ids, ce0) if f])
loS, mdS, hiS = boot(None, sub)
secS = N_W0 * (sum(sub) / n0) + secw
print("BUDGET cases at 7200 s: central %.3g core-years, bootstrap [%.3g, %.3g]" % (secS / YR, loS / YR, hiS / YR))
old = []''')
open(p, "w").write(s)
