for fn in ("chain.py", "chain_sound.py"):
    t = open(fn).read()
    t = t.replace("        w = pow(5, p)\n", "        pw = pow(5, p)\n").replace("(u + c * w) // 2", "(u + c * pw) // 2")
    open(fn, "w").write(t)
