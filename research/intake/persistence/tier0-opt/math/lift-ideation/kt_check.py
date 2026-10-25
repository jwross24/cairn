import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ldiff
rows = []
for name in ('9437184_22222222222222222266', '9437184_222222222222222222229', '9437184_2222222222222222289'):
    d = os.path.join(ldiff.H, name)
    for L in ('24', '48'):
        cfg = os.path.join(d, f'cfgL{L}.txt'); par = os.path.join(d, f'parents{L}.txt')
        if not os.path.exists(par) or os.path.getsize(par) == 0: continue
        res = {}
        for tag, binary, env in (('prod', os.path.join(ldiff.T0, 'lvlN'), None), ('fixed', os.path.join(ldiff.HERE, 'lvlNf'), None), ('join_fixed', os.path.join(ldiff.HERE, 'lvlJ3'), None)):
            o = os.path.join(ldiff.OUT, 'kt.out')
            rc, c, s, w = ldiff.run(binary, cfg, par, o, env)
            n, h = ldiff.canon(o); res[tag] = (rc, n, h[:12], ldiff.sig(s), (round(c, 1) if c else None))
        a = int(open(cfg).readline().split()[2])
        print(name, 'L', L, 'A', a, res, flush=True)
