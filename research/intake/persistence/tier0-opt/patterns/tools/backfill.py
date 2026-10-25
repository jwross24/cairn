import sys, os, json, time, argparse
from collections import Counter, defaultdict
ap = argparse.ArgumentParser()
ap.add_argument('src')
ap.add_argument('eqs')
ap.add_argument('zf')
ap.add_argument('out')
ap.add_argument('--vertex', type=int, action='append')
ap.add_argument('--ncores', type=int, default=3)
ap.add_argument('--max-npat', type=float, default=1e30)
ap.add_argument('--dry', action='store_true')
a = ap.parse_args()
src = os.path.abspath(a.src)
os.chdir(src); sys.path.insert(0, src)
from gmpy2 import mpz
from run_c import run

def dp(x):
    p = 1
    for ch in str(x): p *= int(ch)
    return p

kids = defaultdict(list)
for l in open(a.zf):
    if l.startswith('ZF'):
        _, d, e2, e3, e7, p = l.split()
        y = int(mpz(2) ** int(e2) * mpz(3) ** int(e3) * mpz(7) ** int(e7))
        if y >= 10: kids[dp(y)].append(y)

def record(M, r):
    return dict(level=int(r['levels'][-1][0]), M=[int(d) for d in M], items=[dict(a=int(x), nu=int(nu), eps=[int(e) for e in eps], v0=[int(t) for t in co.v0], u1=[int(t) for t in co.u1], u2=[int(t) for t in co.u2]) for (x, nu, eps, co) in r['open']])

done = set()
if os.path.exists(a.out):
    for l in open(a.out):
        try:
            d = json.loads(l); done.add((d['s'], tuple(d['M'])))
        except Exception: pass
todo = []
for l in open(a.eqs):
    try: d = json.loads(l)
    except Exception: continue
    if d.get('open_patterns') is not None or not d['open']: continue
    if a.vertex and d['s'] not in a.vertex: continue
    if d['npat'] > a.max_npat or (d['s'], tuple(d['M'])) in done: continue
    todo.append(d)
print(f"{len(todo)} equations with open patterns and no field; {sum(d['open'] for d in todo)} open patterns; {sum(d['npat'] for d in todo):.3e} level-12 patterns", file=sys.stderr, flush=True)
if a.dry: sys.exit(0)
out = open(a.out, 'a')
for d in todo:
    t0 = time.time()
    M = tuple(d['M'])
    r = run(d['s'], M, kids[d['s']], ncores=a.ncores)
    op = r['open_patterns'] if 'open_patterns' in r else record(M, r)
    same = (len(r['open']) == d['open'] and json.loads(json.dumps(r['bounds'])) == d['bounds'] and json.loads(json.dumps(r['exceptional'])) == d['exceptional'])
    out.write(json.dumps(dict(s=d['s'], M=list(M), consistent=same, open_patterns=op if same else None, secs=round(time.time() - t0, 1))) + '\n'); out.flush()
    print(f"s={d['s']} M={M} npat={d['npat']:.2e} open={d['open']} consistent={same} {time.time() - t0:.1f}s", file=sys.stderr, flush=True)
