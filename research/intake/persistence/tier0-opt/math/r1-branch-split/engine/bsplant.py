import sys, os, json, time
from collections import Counter
from math import comb
sys.path.insert(0, '/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/gatev2')
from run_c import run
import branchsplit

def npat(M):
    p = 12
    for d, k in Counter(M).items():
        p *= comb(12 + k - 1, k)
    return p

cap = float(sys.argv[1]); work = sys.argv[2]; outp = sys.argv[3]
rows = []
for a in range(0, 130):
    for b in range(0, 80):
        for c in range(0, 50):
            y = 2 ** a * 3 ** b * 7 ** c
            if y < 10 or y >= 10 ** 40:
                continue
            s = str(y)
            if '0' in s:
                continue
            M = tuple(sorted(int(ch) for ch in s if ch != '1'))
            if npat(M) > cap:
                continue
            rows.append((npat(M), y, a, b, c, M, len(s)))
rows.sort()
os.makedirs(work, exist_ok=True)
res = Counter()
with open(outp, 'a') as fo:
    for np_, y, a, b, c, M, n in rows:
        sp = 1
        for d in M:
            sp *= d
        wd = os.path.join(work, f"p{y}")
        os.makedirs(wd, exist_ok=True)
        t0 = time.time()
        cls = (b > 0, c > 0)
        try:
            r = run(sp, M, [y], ncores=2, workdir=wd)
            found = y in r['solutions']
            out = dict(y=y, n=n, a=a, b=b, c=c, cls=cls, s=sp, M=M, npat=np_, found=found, open=len(r['open']), mode=branchsplit.MODE, mutant=branchsplit.MUTANT)
        except AssertionError as e:
            out = dict(y=y, n=n, a=a, b=b, c=c, cls=cls, s=sp, M=M, npat=np_, found=False, lost=str(e)[:200], mode=branchsplit.MODE, mutant=branchsplit.MUTANT)
        res[(cls, 'lost' in out)] += 1
        fo.write(json.dumps(out) + '\n'); fo.flush()
print(dict(res))
