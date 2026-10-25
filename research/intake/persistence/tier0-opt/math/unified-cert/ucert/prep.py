import sys, os, json, re
from collections import Counter
from .env import *


def entries(path):
    for line in open(path):
        r = json.loads(line)
        if 'eqs' not in r:
            continue
        for eq in r['eqs']:
            if isinstance(eq, dict):
                M, ex = eq['M'], eq.get('exceptional', [])
                for e in ex:
                    if len(e) == 3:
                        a, y, sol = e
                        yield r['s'], tuple(M), a, None, None, y, sol
                    else:
                        yield r['s'], tuple(M), e[1], e[2], e[3], e[4][0], e[4][1]
        for e in r.get('exceptional', []):
            M, a, nu, eps, (y, sol) = e
            yield r['s'], tuple(M), a, nu, eps, y, sol


def full_key(s, M, a, nu, eps, y):
    nus = '-' if nu is None else str(nu)
    epss = '-' if eps is None else (','.join(map(str, eps)) or ',')
    return f"{s} {''.join(map(str, M))} {a} {y} {nus} {epss}"


def build_patterns(snapshot_dir, d1_path, utable_path, lam):
    rx = re.compile(r'^s=(\S+)\s+M=(\S+)\s+a=(\d+)\s+y=(\d+)\s+reps=(\d+)\s+cases=(\d+)\s+(.*)$')
    want = []
    for l in open(d1_path):
        m = rx.match(l.strip())
        if m and m.group(7) != 'CLOSED':
            want.append(m.groups()[:4])
    recs = {}
    for fn in ('runall_final.jsonl', 'trees_c.jsonl', 'trees_mac.jsonl'):
        for (s, M, a, nu, eps, y, sol) in entries(os.path.join(snapshot_dir, fn)):
            recs.setdefault((str(s), ''.join(map(str, M)), str(a), str(y)), {})[full_key(s, M, a, nu, eps, y)] = (s, M, a, nu, eps, y)
    U = load_utable(utable_path)
    todo = []
    for key in dict.fromkeys(map(tuple, want)):
        for fk, v in recs[key].items():
            todo.append((fk, v))
    todo.sort(key=lambda t: (len(t[1][1]), t[0]))
    out = []
    for fk, (s, M, a, nu, eps, y) in todo:
        a = int(a)
        f = factor237(y)
        assert f is not None and f[0] == a
        reps = DC.all_representations(M, y)
        if nu is not None:
            reps = [r for r in reps if r[0] == nu and Counter(e for _, e in r[1]) == Counter(e % LMAX for e in eps)]
        out.append({
            'format': 'ucert-pattern-v1', 'id': fk, 's': s, 'M': ''.join(map(str, M)), 'a': a, 'y': y,
            'b': f[1], 'c': f[2], 'k': len(M), 'U': U[(len(M), a)],
            'reps': [{'nu': r[0], 'De': [list(x) for x in r[1]]} for r in reps],
            'lam': lam})
    return out


if __name__ == '__main__':
    snap, d1, ut, outp = sys.argv[1:5]
    lam = coset_to_json(DC.kernel_lattice()) if len(sys.argv) < 6 else json.load(open(sys.argv[5]))
    pats = build_patterns(snap, d1, ut, lam)
    with open(outp, 'w') as f:
        for p in pats:
            f.write(json.dumps(p, sort_keys=True) + '\n')
    print(len(pats), 'patterns', sum(len(p['reps']) for p in pats), 'representations')
