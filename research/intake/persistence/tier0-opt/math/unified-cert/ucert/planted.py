import sys, os, json, time, random, argparse, itertools
from collections import Counter
from .env import *
from . import cert_dual, cert_cvp
from .run import load_patterns


DUAL_CAP = 60


def high_vars(node, D):
    E = node['s'] // LMAX
    types = Counter(tuple(x) for x in node['remaining'])
    return [(d, e, t) for (d, e), cnt in sorted(types.items()) for t in range(E, D)], types


def word_target(node, D, word):
    Tbase = int(node['Y']) + 10 ** node['s'] * R(LMAX * D - node['s'])
    L = Tbase
    for (d, e, t) in word:
        L += (d - 1) * 10 ** (e + LMAX * t)
    return L


def sub_nearest(node, D, word):
    co = coset_from_json(node['coset'])
    K = LMAX * D
    L = word_target(node, D, word)
    c2 = cut_coset(co, node['a'], L, K)
    if c2 is None:
        return None
    nn, pt = DC.nearest_norm(c2)
    return nn, pt, L


def exact_unit_ok(a, pt, L, K):
    return cert_dual.lattice_point_value(pt[0], pt[1], a, K) == L % 10 ** K


def random_words(vars_, types, rng, n):
    seen = set()
    out = []
    tries = 0
    if not vars_:
        return out
    while len(out) < n and tries < 200:
        tries += 1
        k = rng.randint(1, max(1, min(len(vars_), sum(types.values()))))
        w = rng.sample(vars_, k)
        if not cert_dual.valid_x([1 if v in w else 0 for v in vars_], vars_, types):
            continue
        key = tuple(sorted(w))
        if key in seen:
            continue
        seen.add(key)
        out.append(list(key))
    return out


def z_of(co, pt):
    u1, u2, v0 = co.u1, co.u2, co.v0
    det = u1[0] * u2[1] - u2[0] * u1[1]
    db, dc = pt[0] - v0[0], pt[1] - v0[1]
    z1n = db * u2[1] - dc * u2[0]
    z2n = -db * u1[1] + dc * u1[0]
    assert z1n % det == 0 and z2n % det == 0
    return z1n // det, z2n // det


def linear_holds(node, node_b, D, word, pt):
    z1, z2 = z_of(coset_from_json(node['coset']), pt)
    sysd = cert_dual.system_from_node(node, D)
    x = [1 if v in word else 0 for v in sysd['vars']]
    lhs = (sysd['alpha'][0] * z1 + sysd['alpha'][1] * z2 + sum(o * xi for o, xi in zip(sysd['omega'], x))) % sysd['M']
    ok_a = lhs == sysd['beta'] % sysd['M']
    prob = cert_cvp.block_problem(node_b, D, 1)
    z1b, z2b = z_of(coset_from_json(node_b['coset']), pt)
    De = [tuple(r) for r in node_b['remaining']]
    used = set()
    xb = [0] * prob['f']
    for (d, e, tt) in word:
        for idx, (j, p, w) in enumerate(prob['vars']):
            if De[j] == (d, e) and p == e + LMAX * tt and j not in used:
                xb[idx] = 1
                used.add(j)
                break
    lhsb = (prob['coeffs'][0] * z1b + prob['coeffs'][1] * z2b + sum(c * xi for c, xi in zip(prob['coeffs'][2:], xb))) % prob['M']
    ok_b = lhsb == prob['beta'] % prob['M']
    return ok_a, ok_b


def refusal(node, node_b, D, rho2):
    ra = cert_dual.certify_node(node, D, rho2, node_cap=DUAL_CAP)
    rb = cert_cvp.certify_node(node_b, D, rho2)
    okpt = None
    if rb.get('refused_point') is not None:
        b, c = rb['refused_point']
        okpt = b * b + c * c <= rho2
    return ra['certified'], rb['certified'], okpt, rb


def run_real(pattern, ri, D, ntr, rng, log):
    a = pattern['a']
    rep = pattern['reps'][ri]
    E = exact_E(D, a)
    if E >= D:
        return Counter()
    nodes_a = cert_dual.expand_nodes(pattern, rep, E)
    nodes_b = {node_digest(n): n for n in cert_cvp.expand_nodes(pattern, rep, E)}
    res = Counter()
    for node in nodes_a:
        nb = nodes_b[node_digest(node)]
        vars_, types = high_vars(node, D)
        words = random_words(vars_, types, rng, ntr)
        mins = []
        for w in [[]] + words:
            sn = sub_nearest(node, D, w)
            if sn is None:
                continue
            nn, pt, L = sn
            assert exact_unit_ok(a, pt, L, LMAX * D)
            mins.append(nn)
            la, lb = linear_holds(node, nb, D, w, pt)
            res['linear_audit'] += 1
            res['linear_audit_dual_ok'] += la
            res['linear_audit_cvp_ok'] += lb
            ca, cb, okpt, rb = refusal(node, nb, D, nn)
            ok = (not ca) and (not cb) and okpt is True
            res['planted'] += 1
            res['planted_refused_dual'] += (not ca)
            res['planted_refused_cvp'] += (not cb)
            res['planted_cvp_point_in_ball'] += (okpt is True)
            log({'kind': 'planted-subcoset', 'pattern': pattern['id'], 'rep': ri, 'D': D, 'E': E, 'word': [list(v) for v in w],
                 'rho2': str(nn), 'dual_certified': ca, 'cvp_certified': cb, 'cvp_point_ok': okpt, 'ok': ok})
        if mins:
            m_a = cert_dual.min_node(node, D)['nn']
            m_b = cert_cvp.min_node(nb, D)['nn']
            res['min_agree'] += (m_a == m_b)
            res['min_rows'] += 1
            for rho2, expect_refuse in ((m_a, True), (m_a - 1, False)):
                ca = cert_dual.certify_node(node, D, rho2, node_cap=DUAL_CAP)['certified']
                cb = cert_cvp.certify_node(nb, D, rho2)['certified']
                res['edge_total'] += 1
                if expect_refuse:
                    res['edge_at_min_refused_dual'] += (not ca)
                    res['edge_at_min_refused_cvp'] += (not cb)
                    res['edge_at_min_total'] += 1
                else:
                    res['edge_below_min_certified_dual'] += ca
                    res['edge_below_min_certified_cvp'] += cb
                    res['edge_below_min_total'] += 1
                log({'kind': 'edge', 'pattern': pattern['id'], 'rep': ri, 'D': D, 'rho2': str(rho2), 'at_min': expect_refuse,
                     'dual_certified': ca, 'cvp_certified': cb, 'min_dual': str(m_a), 'min_cvp': str(m_b)})
    return res


def genuine(a, b, c, D, lam, log):
    E = exact_E(D, a)
    if E >= D:
        return None
    y = 2 ** a * 3 ** b * 7 ** c
    ds = [int(ch) for ch in str(y)[::-1]]
    K = LMAX * D
    s = LMAX * E
    assert len(ds) > K + 2
    co0 = Coset((b, c), lam.u1, lam.u2)
    if y % 10 ** s % 5 == 0:
        return None
    co = cut_coset(co0, a, y % 10 ** s, s)
    assert co is not None and co.contains(b, c)
    rem = [[ds[i], i % LMAX] for i in range(s, K) if ds[i] != 1]
    node = {'format': 'ucert-node-v1', 'a': a, 's': s, 'Y': str(y % 10 ** s), 'coset': coset_to_json(co), 'remaining': sorted(rem)}
    rho2 = b * b + c * c
    ca, cb, okpt, rb = refusal(node, node, D, rho2)
    ok = (not ca) and (not cb) and okpt is True
    row = {'kind': 'genuine-S-unit', 'a': a, 'b': b, 'c': c, 'D': D, 'E': E, 'remaining': len(rem), 'rho2': str(rho2),
           'dual_certified': ca, 'cvp_certified': cb, 'cvp_point_ok': okpt, 'ok': ok}
    log(row)
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--seed', type=int, default=11)
    ap.add_argument('--ntr', type=int, default=6)
    ap.add_argument('--real', nargs='*', default=[])
    ap.add_argument('--genuine', type=int, default=0)
    args = ap.parse_args()
    rng = random.Random(args.seed)
    pats = {p['id']: p for p in load_patterns(os.path.join(ROOT, 'inputs', 'patterns-u2.jsonl'))}
    tot = Counter()
    with open(args.out, 'a') as fo:
        def log(r):
            fo.write(json.dumps(r, sort_keys=True) + '\n')
            fo.flush()
        for spec in args.real:
            pid, ri, D = spec.rsplit(':', 2)
            r = run_real(pats[pid], int(ri), int(D), args.ntr, rng, log)
            print(spec, dict(r), flush=True)
            tot.update(r)
        lam = coset_from_json(json.load(open(os.path.join(ROOT, 'inputs', 'lam96.json'))))
        gres = Counter()
        for _ in range(args.genuine):
            D = rng.choice([2, 3, 3])
            a = rng.choice([0, 0, 0, 1, 2, 3, 5, 9] if D > 2 else [0])
            if D == 2:
                a = 0
            b = rng.randrange(900, 1500)
            c = rng.randrange(500, 900)
            row = genuine(a, b, c, D, lam, log)
            if row is None:
                continue
            gres['genuine'] += 1
            gres['genuine_refused_dual'] += (not row['dual_certified'])
            gres['genuine_refused_cvp'] += (not row['cvp_certified'])
            gres['genuine_cvp_point_ok'] += (row['cvp_point_ok'] is True)
            print('genuine', row, flush=True)
        tot.update(gres)
        print('TOTAL', dict(tot))
        log({'kind': 'total', 'counts': dict(tot)})


if __name__ == '__main__':
    main()
