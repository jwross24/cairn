import sys, json, time
sys.dont_write_bytecode = True
sys.path.insert(0, '/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/unanchored8')
from uncut import *

D1 = '/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/final13/d1/pattern_status.json'
SH = '/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/final13/shadow/s480w.tsv'
st = json.load(open(D1))
ver = {}
for l in open(SH):
    p = l.rstrip('\n').split('\t')
    ver[p[0]] = p[7]
CONTROLS = [(1161216, '22222222222799', 14, 11519532122112), (11239424, '222222222247778', 8, 952342272), (1161216, '22222222223679', 1, 44471322)]
items = load_items({1161216, 11239424})
case_lines = []
out = {}
for (s, Ms, a, y) in CONTROLS:
    M = tuple(int(ch) for ch in Ms)
    fk = f'{s} {Ms} {a} {y} - -'
    fa, fb, fc = factor237(y)
    assert fa == a
    cand = [r for r in items if r['s'] == s and r['M'] == M and r['a'] == a and r['adm'] and (r['b0'], r['c0']) == (fb, fc)]
    assert cand, fk
    co = cand[0]['co']
    lam_same = all((c['co'].u1, c['co'].u2) == (co.u1, co.u2) for c in cand)
    t0 = time.time()
    reps = all_representations(M, y)
    print(fk, 'recorded status', st[fk], 's480w', ver.get(fk), 'items matching anchor', len(cand), 'lattice same', lam_same, 'reps', len(reps), '%.1fs' % (time.time() - t0), flush=True)
    rec_in = []
    for c in cand:
        want = sorted(zip(sorted(M), c['eps']), key=lambda t: (t[1], t[0]))
        got = [sorted(((d, e) for d, e in r), key=lambda t: (t[1], t[0])) for nu, r in reps if nu == c['nu']]
        rec_in.append(want in got)
    print('  record (nu, eps) of each matching item is among the anchor representations:', rec_in)
    closed_all = True
    nclosed = 0
    for nu, r in reps:
        De = sorted(r, key=lambda t: (t[0], t[1]))
        cl, bound, cases, stats = deep_cut(co, a, (nu, De), 1, 5000000)
        assert cl is not None
        nclosed += bool(cl)
        closed_all &= bool(cl)
        eps_in_M_order = []
        pool = list(De)
        for d in sorted(M):
            j = next(i for i, (dd, ee) in enumerate(pool) if dd == d)
            eps_in_M_order.append(pool.pop(j)[1])
        case_lines.append(f'{s} {Ms} {a} {co.v0[0]},{co.v0[1]} {nu} {",".join(map(str, eps_in_M_order))}')
        out[case_lines[-1]] = bool(cl)
    verdict = 'cut1' if closed_all else 'survivor'
    print('  python coset-from-record verdict:', verdict, f'({nclosed}/{len(reps)} representations closed by the cut)', 'recorded:', st[fk], 'MATCH' if (verdict == 'cut1') == (st[fk] == 'cut1') else 'MISMATCH', flush=True)
with open('control_cases.txt', 'x') as f:
    f.write('\n'.join(case_lines) + '\n')
json.dump(out, open('control_py_verdicts.json', 'x'))
