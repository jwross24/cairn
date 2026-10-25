#!/usr/bin/env python3
"""Rerun suspect equations through the current tier0 binaries via run_c.run and compare with the recorded rows.

uv run --no-project --with gmpy2 python -I rerun.py [--workers W] [--ncores C] [--only s:M ...] [--limit N]
                                                    [--bindir DIR] [--out DIR] [--tag NAME] [--report]
Never writes under tier0/.  Output: <out>/eq_<tag>_<s>_<M>.json, one per equation (resume = skip existing).
workers*ncores is capped at 2 lvl12 processes unless --max-procs raises it.
"""
import sys, os, json, time, argparse, threading, resource, types, subprocess
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
sys.dont_write_bytecode = True
P = '/Users/jwross/Documents/cairn/research/intake/persistence'
T0 = P + '/tier0'
HERE = P + '/tier0-opt/kt-audit-l12/rerun'
sys.path.insert(0, T0)
sys.path.append(T0 + '/.venv/lib/python3.14/site-packages')
os.chdir(T0)
_cur = os.getpriority(os.PRIO_PROCESS, 0)
if _cur < 15:
    os.setpriority(os.PRIO_PROCESS, 0, 15)

ap = argparse.ArgumentParser()
ap.add_argument('--suspects', default=HERE + '/suspects.tsv')
ap.add_argument('--out', default=HERE + '/out')
ap.add_argument('--tag', default='cur')
ap.add_argument('--workers', type=int, default=1)
ap.add_argument('--ncores', type=int, default=2)
ap.add_argument('--max-procs', type=int, default=2)
ap.add_argument('--only', nargs='*', default=[])
ap.add_argument('--limit', type=int, default=0)
ap.add_argument('--bindir', default=T0)
ap.add_argument('--report', action='store_true')
ap.add_argument('--compare', nargs=2, metavar=('TAG_A', 'TAG_B'))
args = ap.parse_args()
if args.workers * args.ncores > args.max_procs:
    sys.exit(f'workers*ncores={args.workers * args.ncores} exceeds --max-procs {args.max_procs}')
if os.path.realpath(args.out).startswith(os.path.realpath(T0) + os.sep):
    sys.exit('refusing to write under tier0')

from gmpy2 import mpz
from math import comb
from collections import Counter
import run_c
from tier0v2 import multisets

run_c.HERE = args.bindir
tl = threading.local()
class _Sub:
    run = staticmethod(subprocess.run)
    PIPE = subprocess.PIPE
    @staticmethod
    def Popen(cmd, *a, **k):
        if not hasattr(tl, 't_start'):
            tl.t_start = time.time()
        return subprocess.Popen(cmd, *a, **k)
run_c.subprocess = _Sub
_scan = run_c.pydesc.scan12
def _scan12(paths, q):
    tl.t_l12 = time.time()
    return _scan(paths, q)
run_c.pydesc.scan12 = _scan12

def dp(x):
    p = 1
    for ch in str(x): p *= int(ch)
    return p
rows = [l.split() for l in open(T0 + '/zf_below_1e4000.txt') if l.startswith('ZF')]
S = [int(mpz(2) ** int(a) * mpz(3) ** int(b) * mpz(7) ** int(c)) for _, d, a, b, c, p in rows]
kids = defaultdict(list)
for y in S:
    if y >= 10: kids[dp(y)].append(y)

recorded_rows = {}
for l in open(T0 + '/trees_mac.jsonl'):
    r = json.loads(l); recorded_rows[r['s']] = r
recorded_eq = {}
for l in open(T0 + '/trees_mac.jsonl.eqs.jsonl'):
    d = json.loads(l); recorded_eq[(d['s'], tuple(d['M']))] = d

suspects = []
with open(args.suspects) as f:
    hdr = f.readline().rstrip('\n').split('\t')
    for l in f:
        t = dict(zip(hdr, l.rstrip('\n').split('\t')))
        suspects.append((int(t['s']), tuple(int(c) for c in t['M']), int(t['A']), t['class']))
if args.only:
    want = {(int(a.split(':')[0]), tuple(int(c) for c in a.split(':')[1])) for a in args.only}
    suspects = [x for x in suspects if (x[0], x[1]) in want]
if args.limit:
    suspects = suspects[:args.limit]

def verdict(eqs, s):
    found = set(); nopen = 0; bounds = []
    for d in eqs:
        found |= set(d['sols']); nopen += d['open']; bounds += d['bounds']
    kn = set(kids[s])
    return dict(open=nopen, found=sorted(found), closed=(nopen == 0 and found == kn), complete_below=(found == kn),
                digit_bound=(min(bounds) if bounds else None))

def canon_eq(d):
    lv = [(L, n, sv, dict(c)) for (L, n, sv, c) in d['levels']]
    return dict(open=d['open'], sols=sorted(d['sols']), levels=lv, bounds=sorted(d['bounds']),
                c=dict((k, d['c_stats'].get(k)) for k in ('patterns', 'open', 'exact', 'tail-dead')))

def outpath(s, M):
    return f"{args.out}/eq_{args.tag}_{s}_{''.join(map(str, M))}.json"

def one(item):
    s, M, A, cls = item
    p = outpath(s, M)
    if os.path.exists(p):
        return 'skip', s, M
    tl.__dict__.pop('t_start', None); tl.__dict__.pop('t_l12', None)
    t0 = time.time(); c0 = resource.getrusage(resource.RUSAGE_CHILDREN)
    r = run_c.run(s, M, kids[s], ncores=args.ncores)
    wall = time.time() - t0; c1 = resource.getrusage(resource.RUSAGE_CHILDREN)
    sols = sorted(y for y in r['solutions'] if y >= 10)
    new = dict(s=s, M=list(M), npat=r['c_stats'].get('patterns'), open=len(r['open']), sols=sols, bounds=r['bounds'],
               exceptional=r['exceptional'], c_stats=r['c_stats'],
               levels=[(L, n, sv, cls_) for (L, ps, n, sv, cls_, el) in r['levels']])
    rec = recorded_eq.get((s, M))
    a, b = canon_eq(new), (canon_eq(rec) if rec else None)
    diffs = [] if b is None else [k for k in ('open', 'sols', 'bounds') if a[k] != b[k]]
    info_diffs = [] if b is None else [k for k in ('levels', 'c') if a[k] != b[k]]
    row = recorded_rows.get(s)
    vd = None
    if row is not None:
        base = [e for e in row['eqs']]
        recorded_v = verdict(base, s)
        swapped = [new if tuple(e['M']) == M else e for e in base]
        new_v = verdict(swapped, s)
        vd = dict(recorded_row=dict(open=row['open'], closed=row['closed'], complete_below=row['complete_below'],
                                    digit_bound=row['digit_bound'], found=row['found']),
                  recorded_recomputed=recorded_v, new=new_v, row_consistent=(recorded_v['open'] == row['open'] and recorded_v['closed'] == row['closed']
                                                                              and recorded_v['digit_bound'] == row['digit_bound'] and recorded_v['found'] == row['found']),
                  verdict_changed=(new_v != recorded_v))
    t_start = getattr(tl, 't_start', t0); t_l12 = getattr(tl, 't_l12', None)
    res = dict(s=s, M=list(M), A=A, cls=cls, tag=args.tag, bindir=args.bindir, rec_found=rec is not None,
               eq_diff_keys=diffs, info_diff_keys=info_diffs, differs=bool(diffs), vertex=vd,
               new=canon_eq(new), recorded=b, patterns=r['c_stats'].get('patterns'),
               exceptional_new=[list(e) for e in r['exceptional']],
               exceptional_recorded=([list(e) for e in rec.get('exceptional', [])] if rec else None),
               wall_s=round(wall, 2), l12_wall_s=(round(t_l12 - t_start, 2) if t_l12 else None),
               children_cpu_s=round((c1.ru_utime + c1.ru_stime) - (c0.ru_utime + c0.ru_stime), 2) if args.workers == 1 else None,
               ncores=args.ncores, workers=args.workers, finished_epoch=int(time.time()), bsdrop=r['bsdrop'])
    tmp = p + '.tmp'
    with open(tmp, 'w') as f: json.dump(res, f)
    os.rename(tmp, p)
    return ('DIFF' if diffs else 'same'), s, M

if args.compare:
    ta, tb = args.compare
    for s, M, A, cls in suspects:
        pa, pb = (f"{args.out}/eq_{t}_{s}_{''.join(map(str, M))}.json" for t in (ta, tb))
        if os.path.exists(pa) and os.path.exists(pb):
            a, b = json.load(open(pa))['new'], json.load(open(pb))['new']
            print(s, ''.join(map(str, M)), 'A', A, ta, 'vs', tb, 'level12 survivors', a['levels'][0][2], b['levels'][0][2],
                  'DIFF' if a != b else 'same', [k for k in a if a[k] != b[k]])
    sys.exit(0)

if args.report:
    n = 0
    for s, M, A, cls in suspects:
        p = outpath(s, M)
        if os.path.exists(p):
            d = json.load(open(p)); n += 1
            ek = [k for k in ('open', 'sols', 'bounds') if d['recorded'] is not None and d['new'][k] != d['recorded'][k]]
            print(s, ''.join(map(str, M)), 'A', A, 'DIFF' if ek else 'same', ek,
                  'verdict_changed' if (d['vertex'] or {}).get('verdict_changed') else '', 'wall', d['wall_s'], 'l12', d['l12_wall_s'], 'pat/s(l12)',
                  (round(d['patterns'] / d['l12_wall_s'] / 1e6, 1) if d['l12_wall_s'] else None), 'M')
    sys.exit(0)

os.makedirs(args.out, exist_ok=True)
todo = [x for x in suspects if not os.path.exists(outpath(x[0], x[1]))]
print(f'{len(suspects)} selected, {len(todo)} to run, workers={args.workers} ncores={args.ncores}', flush=True)
with ThreadPoolExecutor(args.workers) as ex:
    for st, s, M in ex.map(one, todo):
        print(st, s, ''.join(map(str, M)), flush=True)
