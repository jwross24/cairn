import sys, os, json, time, traceback
from collections import Counter, defaultdict
from math import comb
from tier0v2 import multisets
from run_c import run
import branchsplit

HERE = os.path.dirname(os.path.abspath(__file__))
s = int(sys.argv[1])
outp = sys.argv[2]
work = sys.argv[3]
cap = float(sys.argv[4]) if len(sys.argv) > 4 else 1e30
ncores = int(sys.argv[5]) if len(sys.argv) > 5 else 2


def dp(x):
    p = 1
    for ch in str(x):
        p *= int(ch)
    return p


def npat(M):
    p = 12
    for d, k in Counter(M).items():
        p *= comb(12 + k - 1, k)
    return p


def known_children(s):
    from gmpy2 import mpz
    out = []
    for l in open(os.path.join(HERE, 'zf_below_1e4000.txt')):
        if not l.startswith('ZF'):
            continue
        _, d, a, b, c, p = l.split()
        y = int(mpz(2) ** int(a) * mpz(3) ** int(b) * mpz(7) ** int(c))
        if y >= 10 and dp(y) == s:
            out.append(y)
    return sorted(out)


kn = known_children(s)
eqs = sorted((tuple(sorted(M)) for M in multisets(s)), key=npat)
done = set()
if os.path.exists(outp):
    for l in open(outp):
        try:
            done.add(tuple(json.loads(l)['M']))
        except Exception:
            pass
os.makedirs(work, exist_ok=True)
with open(outp, 'a') as fo:
    for M in eqs:
        if npat(M) > cap or M in done:
            continue
        t0 = time.time()
        wd = os.path.join(work, f"{s}_{''.join(map(str, M))}")
        os.makedirs(wd, exist_ok=True)
        try:
            r = run(s, M, kn, ncores=ncores, workdir=wd)
            if branchsplit.AUDIT:
                with open(os.environ['BRANCHSPLIT_AUDIT'], 'a') as fa:
                    for (tag, a, nu, eps, v0, u1, u2) in branchsplit.REMOVED:
                        fa.write(json.dumps(dict(s=s, M=M, tag=tag, a=a, nu=nu, eps=eps, v0=v0, u1=u1, u2=u2)) + '\n')
            d = dict(s=s, M=M, npat=npat(M), mode=branchsplit.MODE, mutant=branchsplit.MUTANT, open=len(r['open']),
                     sols=sorted(y for y in r['solutions'] if y >= 10), known=kn,
                     levels=[(L, n, sv, cls) for (L, ps, n, sv, cls, el) in r['levels']],
                     bs=r['bs'], c_stats=r['c_stats'], open_patterns=r['open_patterns'], bounds=r['bounds'],
                     exceptional=r['exceptional'], times=r['times'], secs=round(time.time() - t0, 3))
        except AssertionError as e:
            d = dict(s=s, M=M, npat=npat(M), mode=branchsplit.MODE, mutant=branchsplit.MUTANT, refused=str(e)[:300], secs=round(time.time() - t0, 1))
        fo.write(json.dumps(d) + '\n')
        fo.flush()
        print(f"s={s} M={M} npat={npat(M):.2e} {'REFUSED ' + d['refused'] if 'refused' in d else 'open=' + str(d['open']) + ' sols=' + str(d['sols'])} {d['secs']}s", flush=True)
