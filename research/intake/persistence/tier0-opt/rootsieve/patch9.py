t = open("reach.py").read()
t = t.replace("\nmain()\n", '''
def negative(pats_sel, M, lim):
    tested = 0; zero_ok = 0
    for d3, d7, nu, digs in pats_sel:
        if d3:
            continue
        ok, sz = reach_zero(M, nu, digs)
        tested += 1; zero_ok += ok
        if tested >= lim:
            break
    return tested, zero_ok

main_sel = None
main()
''')
t = t.replace('        print("modulus", name, "patterns', '        MAINSEL[0] = sel\n        print("modulus", name, "patterns')
t = t.replace("def main():", "MAINSEL = [None]\ndef main():")
t = t.replace("main_sel = None\nmain()\n", 'main()\nprint("negative control (3 does not divide x), modulus 27: tested %d, zero reachable %d" % negative(MAINSEL[0], 27, 400))\nprint("negative control (7 does not divide x), modulus 49: tested %d, zero reachable %d" % negative([(a, True, c, d) for (a, b, c, d) in MAINSEL[0] if not b], 49, 400)) if False else None\n')
open("reach.py", "w").write(t)
