import sys, os, json, copy, random, traceback
sys.dont_write_bytecode = True
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from ucert.env import *
from ucert import cert_dual, cert_cvp, planted
from ucert.run import load_patterns, load_oracle

PATS = {p['id']: p for p in load_patterns(os.path.join(ROOT, 'inputs', 'patterns-u2.jsonl'))}
ORC = load_oracle(os.path.join(ROOT, 'oracle-u2', 'cport-sandwich-u2.tsv'))
P1 = PATS['14336 222222478 0 330812181 - -']
P2 = PATS['28672 78888 2 1411788 - -']


def nodes_both(p, ri, E):
    a = cert_dual.expand_nodes(p, p['reps'][ri], E)
    b = cert_cvp.expand_nodes(p, p['reps'][ri], E)
    return a, b


def test_node_sets_agree():
    for p, ri, E in ((P1, 0, 1), (P1, 1, 1), (P2, 0, 2)):
        a, b = nodes_both(p, ri, E)
        assert len(a) == len(b) > 0
        assert sorted(node_digest(n) for n in a) == sorted(node_digest(n) for n in b)


def test_open_then_closed_matches_oracle():
    a, b = nodes_both(P1, 0, 1)
    rho2 = disc_radius2(P1['U'])
    for D, want_closed in ((1, False), (2, True)):
        oc = ORC[P1['id']][0][D]
        assert (oc[0] == 'CLOSED-sandwich') == want_closed
        ca = all(cert_dual.certify_node(n, D, rho2)['certified'] for n in a)
        cb = all(cert_cvp.certify_node(n, D, rho2)['certified'] for n in b)
        assert ca == want_closed and cb == want_closed
        ma = min(cert_dual.min_node(n, D)['nn'] for n in a)
        mb = min(cert_cvp.min_node(n, D)['nn'] for n in b)
        assert ma == mb == oc[2]


def test_planted_refused_and_threshold():
    a, b = nodes_both(P1, 0, 1)
    D = 2
    node, nb = a[0], b[0]
    vars_, types = planted.high_vars(node, D)
    rng = random.Random(3)
    words = planted.random_words(vars_, types, rng, 4)
    assert words
    for w in words:
        nn, pt, L = planted.sub_nearest(node, D, w)
        assert planted.exact_unit_ok(node['a'], pt, L, LMAX * D)
        la, lb = planted.linear_holds(node, nb, D, w, pt)
        assert la and lb
        ca, cb, okpt, rb = planted.refusal(node, nb, D, nn)
        assert not ca and not cb and okpt is True
    m = cert_cvp.min_node(nb, D)['nn']
    assert not cert_cvp.certify_node(nb, D, m)['certified']
    assert not cert_dual.certify_node(node, D, m)['certified']
    assert cert_cvp.certify_node(nb, D, m - 1)['certified']


def test_verifiers_refuse_tampering():
    a, b = nodes_both(P1, 0, 1)
    D = 2
    rho2 = disc_radius2(P1['U'])
    node, nb = a[0], b[0]
    rec = cert_dual.certify_node(node, D, rho2)
    assert rec['certified'] and cert_dual.verify_record(node, rec, rho2)
    bad = copy.deepcopy(rec)
    t = bad['tree']
    while 'mu' not in t:
        t = t['children'][0]['tree']
    t['mu'] += 1
    assert not cert_dual.verify_record(node, bad, rho2)
    bigger = int(min(cert_dual.min_node(node, D)['nn'], 10 ** 400))
    assert not cert_dual.verify_record(node, rec, bigger)
    recb = cert_cvp.certify_node(nb, D, rho2)
    assert recb['certified'] and cert_cvp.verify_record(nb, recb, rho2)
    bad = copy.deepcopy(recb)
    bad['pack']['EB'][0][0] += 2
    assert not cert_cvp.verify_record(nb, bad, rho2)
    bad = copy.deepcopy(recb)
    bad['pack']['basis'][0][0] += 1
    assert not cert_cvp.verify_record(nb, bad, rho2)
    assert not cert_cvp.verify_record(nb, recb, bigger)


def test_nearest_routines_agree():
    a, b = nodes_both(P2, 0, 2)
    for n in a:
        co = coset_from_json(n['coset'])
        assert DC.nearest_norm(co)[0] == cert_cvp.nearest2d(co)


if __name__ == '__main__':
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith('test_') and callable(fn):
            try:
                fn()
                print('PASS', name, flush=True)
            except Exception:
                fails += 1
                print('FAIL', name, flush=True)
                traceback.print_exc()
    print('failures', fails)
    sys.exit(1 if fails else 0)
