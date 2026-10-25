import sys, os, json, time, subprocess, importlib.util
from collections import Counter
from math import comb
cand, ref, s = sys.argv[1], sys.argv[2], int(sys.argv[3])
cand_bin = sys.argv[4] if len(sys.argv) > 4 else os.path.join(cand, 'lvl12')
ref_bin = os.path.join(ref, 'lvl12')
work = sys.argv[5] if len(sys.argv) > 5 else '/private/tmp/persist-branchsplit/kdiff'
os.makedirs(work, exist_ok=True)
sys.path.insert(0, cand)
os.chdir(cand)
spec = importlib.util.spec_from_file_location('bsproto', '/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/math/r1-branch-split/engine/branchsplit.py')
bsp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bsp)
from tier0v2 import multisets
from export_cfg import export
from lattice import Coset


def npat(M):
    p = 12
    for d, k in Counter(M).items():
        p *= comb(12 + k - 1, k)
    return p


def run(binp, cfgp, extra, tag):
    outs, procs = [], []
    for i in range(2):
        lo, hi = 12 * i // 2, 12 * (i + 1) // 2
        op = f"{work}/{tag}_{i}.txt"
        outs.append(op)
        procs.append(subprocess.Popen([binp, cfgp, str(lo), str(hi)] + extra, stdout=open(op, 'w'), stderr=subprocess.PIPE, text=True))
    ctr = Counter()
    for p in procs:
        _, err = p.communicate()
        assert p.returncode == 0, err
        t = err.split()
        for k, v in zip(t[0::2], t[1::2]):
            ctr[k] += int(v)
    lines = []
    for op in outs:
        lines += open(op).read().splitlines()
    return lines, ctr


tot = Counter()
bad = []
t0 = time.time()
for M in sorted((tuple(sorted(m)) for m in multisets(s)), key=npat):
    cfgp = f"{work}/cfg_{s}_{''.join(map(str, M))}.txt"
    cfg = export(M, cfgp)
    U2 = cfg['U2']
    q = len(M)
    rl, rc = run(ref_bin, cfgp, [], 'ref')
    cl, cc = run(cand_bin, cfgp, ['bs'], 'cand')
    ol, oc = run(cand_bin, cfgp, [], 'off')
    keep = []
    for ln in rl:
        f = ln.split()
        if f[0] == 'OPEN':
            a, nu = int(f[1]), int(f[2]); eps = tuple(int(x) for x in f[3:3 + q]); b, c = int(f[3 + q]), int(f[4 + q])
            if not bsp.keep(M, a, nu, eps, Coset((b, c), tuple(U2[0]), tuple(U2[1]))):
                continue
        keep.append(ln)
    bsd = cc.pop('bsdrop')
    ok = (keep == cl) and (ol == rl) and (oc == rc) and (cc['open'] + bsd == rc['open'])
    ok = ok and all(cc[k] == rc[k] for k in rc if k != 'open')
    nopen_ref = sum(1 for l in rl if l.startswith('OPEN'))
    tot['equations'] += 1; tot['ref_open'] += nopen_ref; tot['cand_open'] += cc['open']; tot['bsdrop'] += bsd
    tot['exact'] += rc['exact']; tot['py_dropped'] += nopen_ref - sum(1 for l in keep if l.startswith('OPEN'))
    if not ok:
        bad.append(M)
        print('MISMATCH', s, M, flush=True)
print(json.dumps(dict(vertex=s, **tot, mismatches=len(bad), secs=round(time.time() - t0, 1))), flush=True)
sys.exit(1 if bad else 0)
