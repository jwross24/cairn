import sys, os, json, random
sys.dont_write_bytecode = True
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from ucert.env import *
from ucert import cert_dual, cert_cvp, planted
from ucert.run import load_patterns

PATS = {p['id']: p for p in load_patterns(os.path.join(ROOT, 'inputs', 'patterns-u2.jsonl'))}
CASES = [('14336 222222478 0 330812181 - -', 0, 1, 2), ('28672 22222222278 0 330812181 - -', 0, 1, 2),
         ('14336 47888 0 7411887 - -', 0, 2, 3), ('14112 22233477 1 2722734 - -', 0, 2, 3), ('42336 2246779 2 777924 - -', 0, 2, 3),
         ('28672 2227888 0 78121827 - -', 0, 2, 3)]


def build():
    out = []
    rng = random.Random(5)
    for pid, ri, E, D in CASES:
        p = PATS[pid]
        rep = p['reps'][ri]
        na = cert_dual.expand_nodes(p, rep, E)
        nb = {node_digest(n): n for n in cert_cvp.expand_nodes(p, rep, E)}
        for node in na[:2]:
            nbn = nb[node_digest(node)]
            vars_, types = planted.high_vars(node, D)
            words = planted.random_words(vars_, types, rng, 4)
            mins = [planted.sub_nearest(node, D, w)[0] for w in [[]] + words]
            out.append((node, nbn, D, mins, disc_radius2(p['U'])))
    return out


def failures(cases, backend):
    bad = enum_failures() if backend == 'cvp' else 0
    for node, nbn, D, mins, rho2 in cases:
        nodes = {'dual': node, 'cvp': nbn}[backend]
        mod = {'dual': cert_dual, 'cvp': cert_cvp}[backend]
        for nn in mins:
            try:
                r = mod.certify_node(nodes, D, nn)
                bad += bool(r['certified'])
            except Exception:
                bad += 1
        if min(mins) > 0:
            m = min(mins)
            r = mod.certify_node(nodes, D, m)
            bad += bool(r['certified'])
    return bad


def enum_failures():
    import itertools
    rng = random.Random(9)
    bad = 0
    for trial in range(40):
        n = rng.choice([3, 4])
        while True:
            B = [[rng.randint(-6, 6) for _ in range(n)] for _ in range(n)]
            if cert_cvp._det_int(B) != 0:
                break
        B = cert_cvp.lll_integral(B)
        tgt = [rng.randint(-8, 8) for _ in range(n)]
        best = None
        bound = 9 if n == 3 else 6
        rngc = range(-bound, bound + 1)
        for c in itertools.product(rngc, repeat=n):
            d = sum((tgt[j] - sum(c[i] * B[i][j] for i in range(n))) ** 2 for j in range(n))
            if best is None or d < best:
                best = d
        d2, cb, nodes, complete = cert_cvp.cvp_enumerate(B, tgt, best + 50, shrink=True)
        bad += (d2 is None or int(d2) > best or (all(abs(x) <= bound for x in cb) and int(d2) != best))
    return bad


def apply(mut):
    saved = {}
    if mut == 'dual_interval_off_by_one':
        orig = cert_dual.check_mu

        def check_mu(mu, M, alpha, omega, beta, vars_, zb):
            ok, wid = orig(mu, M, alpha, omega, beta, vars_, zb)
            if ok:
                return True, wid
            r = [cert_dual.cent(mu * al, M) for al in alpha]
            lo = hi = 0
            for rr, (zl, zh) in zip(r, zb):
                lo += min(rr * zl, rr * zh)
                hi += max(rr * zl, rr * zh)
            from collections import defaultdict
            groups = defaultdict(list)
            for (d, e, t), om in zip(vars_, omega):
                groups[(e, t)].append(cert_dual.cent(mu * om, M))
            for g in groups.values():
                lo += min(0, min(g))
                hi += max(0, max(g))
            b = (mu * beta) % M
            return (-((b - lo) // M)) >= ((hi - b) // M), wid
        saved['check_mu'] = orig
        cert_dual.check_mu = check_mu
    elif mut == 'dual_zbox_shrunk':
        orig = cert_dual.z_box
        saved['z_box'] = orig
        cert_dual.z_box = lambda co, rho2: tuple((lo + (hi - lo) // 3, hi - (hi - lo) // 3) for lo, hi in orig(co, rho2))
    elif mut == 'dual_groups_ignored':
        orig = cert_dual.check_mu

        def check_mu(mu, M, alpha, omega, beta, vars_, zb):
            return orig(mu, M, alpha, [], beta, [], zb)
        saved['check_mu'] = orig
        cert_dual.check_mu = check_mu
    elif mut == 'cvp_first_candidate_only':
        orig = cert_cvp._outward

        def outward(ci):
            x0 = (2 * ci.numerator + ci.denominator) // (2 * ci.denominator)
            yield x0
            while True:
                yield 10 ** 400
        saved['_outward'] = orig
        cert_cvp._outward = outward
    elif mut == 'cvp_radius_quartered':
        orig = cert_cvp.solve_block
        saved['solve_block'] = orig
        cert_cvp.solve_block = lambda node, D, N2, **kw: orig(node, D, N2 // 4, **kw)
    elif mut == 'cvp_lattice_missing_modulus_row':
        orig = cert_cvp.kernel_basis_and_particular

        def kb(coeffs, M, r):
            basis, part = orig(coeffs, M, r)
            return (basis[:-1], part) if basis is not None else (basis, part)
        saved['kernel_basis_and_particular'] = orig
        cert_cvp.kernel_basis_and_particular = kb
    return saved


def restore(mut, saved):
    mod = cert_dual if mut.startswith('dual') else cert_cvp
    for k, v in saved.items():
        setattr(mod, k, v)


if __name__ == '__main__':
    cases = build()
    print('unmutated dual failures', failures(cases, 'dual'), 'cvp failures', failures(cases, 'cvp'), flush=True)
    for mut in ('dual_interval_off_by_one', 'dual_zbox_shrunk', 'dual_groups_ignored', 'cvp_first_candidate_only', 'cvp_radius_quartered', 'cvp_lattice_missing_modulus_row'):
        saved = apply(mut)
        be = 'dual' if mut.startswith('dual') else 'cvp'
        try:
            n = failures(cases, be)
        finally:
            restore(mut, saved)
        print(mut, 'false certifications or crashes caught by the suite:', n, 'CAUGHT' if n else 'NOT CAUGHT', flush=True)
