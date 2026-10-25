import sys, os, json, time
from collections import Counter
from math import comb
src, cap, work, outp = sys.argv[1], float(sys.argv[2]), sys.argv[3], sys.argv[4]
os.chdir(src); sys.path.insert(0, src)
from run_c import run


def npat(M):
    p = 12
    for d, k in Counter(M).items():
        p *= comb(12 + k - 1, k)
    return p


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
with open(outp, 'w') as fo:
    for np_, y, a, b, c, M, n in rows:
        sp = 1
        for d in M:
            sp *= d
        wd = os.path.join(work, f"p{y}")
        os.makedirs(wd, exist_ok=True)
        cls = (b > 0, c > 0)
        try:
            r = run(sp, M, [y], ncores=2, workdir=wd)
            out = dict(y=y, n=n, a=a, b=b, c=c, cls=cls, s=sp, M=M, npat=np_, found=y in r['solutions'], open=len(r['open']), bsdrop=r['bsdrop'])
        except AssertionError as e:
            out = dict(y=y, n=n, a=a, b=b, c=c, cls=cls, s=sp, M=M, npat=np_, found=False, lost=str(e)[:200])
        res[(cls, out['found'])] += 1
        fo.write(json.dumps(out) + '\n'); fo.flush()
print(json.dumps(dict(plants=len(rows), found=sum(v for (c, f), v in res.items() if f), lost=sum(v for (c, f), v in res.items() if not f))))
