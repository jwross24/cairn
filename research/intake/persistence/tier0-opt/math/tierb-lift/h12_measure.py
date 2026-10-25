import sys, os, json, time, hashlib, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
T0 = os.path.normpath(os.path.join(HERE, '..', '..', '..', 'tier0'))
sys.path.insert(0, T0)
sys.dont_write_bytecode = True
from collections import Counter
from math import comb
import run_c
from tier0v2 import multisets
from gmpy2 import mpz

CAP = {}

def digit_product(x):
    p = 1
    for ch in str(x):
        p *= int(ch)
    return p

def known_children(s):
    out = []
    for l in open(os.path.join(T0, 'zf_below_1e4000.txt')):
        if not l.startswith('ZF'):
            continue
        _, d, a, b, c, p = l.split()
        y = int(mpz(2) ** int(a) * mpz(3) ** int(b) * mpz(7) ** int(c))
        if y >= 10 and digit_product(y) == s:
            out.append(y)
    return sorted(out)

def npat(M):
    p = 12
    for d, k in Counter(M).items():
        p *= comb(12 + k - 1, k)
    return p

def key(t):
    a, nu, eps, co = t
    return f"{a} {nu} {' '.join(map(str, eps))} {co.v0[0]} {co.v0[1]} {co.u1[0]} {co.u1[1]} {co.u2[0]} {co.u2[1]}"

_orig_make = run_c.make_c_lift
def make_wrapped(M, workdir, ncores=1):
    inner = _orig_make(M, workdir, ncores)
    def lift(Lp, L, survivors, fg):
        t = time.time()
        surv, ch, st = inner(Lp, L, survivors, fg)
        CAP[f'lift{L}'] = dict(parents=len(survivors), children=ch, survivors=len(surv), secs=time.time() - t, keys=sorted(key(x) for x in surv), stats=st)
        return surv, ch, st
    return lift
run_c.make_c_lift = make_wrapped
_orig_solve = run_c.solve_equation
def solve_wrapped(*a, **kw):
    l12 = kw.get('l12')
    if l12 is not None:
        CAP['l12'] = sorted(key(x) for x in list(l12))
    return _orig_solve(*a, **kw)
run_c.solve_equation = solve_wrapped

def sethash(keys):
    h = hashlib.sha256()
    for k in keys:
        h.update(k.encode()); h.update(b'\n')
    return h.hexdigest()

def run_one(s, M, ncores, work, dumpdir):
    CAP.clear()
    kn = known_children(s)
    t0 = time.time()
    r = run_c.run(s, M, kn, ncores=ncores, workdir=work)
    secs = time.time() - t0
    rec = dict(s=s, M=list(M), k=len(M), npat=npat(M), secs=round(secs, 3), open=len(r['open']),
               sols=sorted(y for y in r['solutions'] if y >= 10), c_stats=r['c_stats'],
               levels=[(L, n, sv, cls) for (L, ps, n, sv, cls, el) in r['levels']])
    for name, v in CAP.items():
        if name == 'l12':
            rec['l12_n'] = len(v); rec['l12_sha'] = sethash(v)
            if dumpdir:
                open(os.path.join(dumpdir, f"{s}_{''.join(map(str, M))}.l12"), 'w').write('\n'.join(v) + '\n')
        else:
            keys = v.pop('keys')
            rec[name] = v; rec[name]['sha'] = sethash(keys)
            if dumpdir:
                open(os.path.join(dumpdir, f"{s}_{''.join(map(str, M))}.{name}"), 'w').write('\n'.join(keys) + '\n')
    return rec

if __name__ == '__main__':
    s = int(sys.argv[1]); out = sys.argv[2]; scratch = sys.argv[3]
    lo = float(sys.argv[4]); hi = float(sys.argv[5]); ncores = int(sys.argv[6]) if len(sys.argv) > 6 else 2
    dump = sys.argv[7] if len(sys.argv) > 7 else None
    if dump: os.makedirs(dump, exist_ok=True)
    os.makedirs(scratch, exist_ok=True)
    done = set()
    if os.path.exists(out):
        for l in open(out):
            try: done.add(tuple(json.loads(l)['M']))
            except Exception: pass
    for M in sorted((tuple(sorted(m)) for m in multisets(s)), key=npat):
        if not (lo <= npat(M) <= hi) or M in done:
            continue
        if subprocess.run([sys.executable, os.path.join(HERE, 'gate.py')]).returncode != 0:
            print('compute gate closed', flush=True); break
        wd = os.path.join(scratch, f"{s}_{''.join(map(str, M))}"); os.makedirs(wd, exist_ok=True)
        rec = run_one(s, M, ncores, wd, dump)
        open(out, 'a').write(json.dumps(rec) + '\n')
        print(s, M, f"{rec['npat']:.2e}", rec['secs'], flush=True)
