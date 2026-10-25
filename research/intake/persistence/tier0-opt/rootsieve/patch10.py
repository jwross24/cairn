for fn in ("chain.py", "chain_sound.py"):
    t = open(fn).read()
    if fn == "chain.py":
        old_head = "def chain_feasible(a, digs):\n    pool = {}"
    else:
        old_head = "def chain_feasible(a, digs):\n    pool = {}"
    assert old_head in t
    t = t.replace("def chain_feasible(a, digs):\n    pool = {}", "def chain_feasible(a, digs):\n    q = len(digs)\n    exact = a < q\n    w = a if exact else q\n    pool = {}")
    t = t.replace("        if p == a:\n            for c in cands:\n                if (c - u) % 2 == 1:\n                    return True\n            return False",
                  "        if p == w:\n            if not exact:\n                return True\n            for c in cands:\n                if (c - u) % 2 == 1:\n                    return True\n            return False")
    open(fn, "w").write(t)
