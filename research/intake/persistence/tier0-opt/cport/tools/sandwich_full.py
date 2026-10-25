import argparse, hashlib, json, math, os, re, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from stage_io import entries, full_key, snapshot
from final_stage import baker_table, fixed_table, TIER0, SOURCES, CPORT, md5

ap = argparse.ArgumentParser()
ap.add_argument('--out', required=True)
ap.add_argument('--d1', default=os.path.join(TIER0, 'DEEPCUT-run-final-d1.txt'))
ap.add_argument('--sources', nargs='*', default=[os.path.join(TIER0, s) for s in SOURCES])
ap.add_argument('--jobs', type=int, default=2)
ap.add_argument('--utable-file', default=None)
ap.add_argument('--maxdepth', type=int, default=7)
ap.add_argument('--maxcases', type=int, default=4000000000)
ap.add_argument('--timeout', type=float, default=3600)
ap.add_argument('--deadline-epoch', type=float, default=None)
ap.add_argument('--cport', default=os.path.join(CPORT, 'cport'))
ap.add_argument('--lattice', default=os.path.join(CPORT, 'data', 'lattice96.txt'))
args = ap.parse_args()
os.makedirs(args.out, exist_ok=True)

rx = re.compile(r'^s=(\S+)\s+M=(\S+)\s+a=(\d+)\s+y=(\d+)\s+reps=(\d+)\s+cases=(\d+)\s+(.*)$')
want = []
for l in open(args.d1):
    m = rx.match(l.strip())
    if m and m.group(7) != 'CLOSED':
        want.append(m.groups()[:4])
snaps = []
for src in args.sources:
    dst = os.path.join(args.out, os.path.basename(src))
    snapshot(src, dst)
    snaps.append(dst)
recs = {}
for p in snaps:
    for (s, M, a, nu, eps, y, sol) in entries(p):
        recs.setdefault((str(s), ''.join(map(str, M)), str(a), str(y)), {})[full_key(s, M, a, nu, eps, y)] = (s, M, a, y)
todo = []
for key in dict.fromkeys(map(tuple, want)):
    for fk, v in recs[key].items():
        todo.append((fk, v))
pairs = {(len(v[1]), v[2]) for _, v in todo}
utable = os.path.join(args.out, 'utable.txt')
U = fixed_table(args.utable_file, pairs, utable) if args.utable_file else baker_table(pairs, utable)
todo.sort(key=lambda t: (len(t[1][1]), t[0]))
sw = os.path.join(args.out, 'sw')
os.makedirs(sw, exist_ok=True)


def logd(n):
    return math.log10(n) if n < 10 ** 300 else (len(str(n)) - 1) + math.log10(int(str(n)[:15]) / 1e14)


def one(i_t):
    i, (fk, v) = i_t
    base = os.path.join(sw, str(i))
    open(base + '.cases', 'w').write(fk + '\n')
    open(base + '.only', 'w').write(' '.join(fk.split()[:4]) + '\n')
    cmd = [args.cport, 'sandwich', '--dfs', '--lattice', args.lattice, '--utable', utable, '--cases', base + '.cases', '--only', base + '.only',
           '--maxdepth', str(args.maxdepth), '--maxcases', str(args.maxcases), '--tsv', base + '.tsv']
    limit = args.timeout
    if args.deadline_epoch is not None:
        limit = min(limit, args.deadline_epoch - time.time())
        if limit < 1:
            return i, 'unrun', time.time()
    t0 = time.time()
    with open(base + '.txt', 'w') as fo, open(base + '.err', 'w') as fe:
        pr = subprocess.Popen(cmd, stdout=fo, stderr=fe, preexec_fn=lambda: os.nice(10))
        try:
            pr.wait(timeout=limit)
            return i, 'done', time.time() - t0
        except subprocess.TimeoutExpired:
            pr.kill()
            pr.wait()
            return i, 'timeout', time.time() - t0


t_start = time.time()
with ThreadPoolExecutor(max_workers=args.jobs) as ex:
    results = list(ex.map(one, list(enumerate(todo))))
wall = time.time() - t_start

rows = []
for (i, st, wt), (fk, v) in zip(results, todo):
    s, M, a, y = v
    k = len(M)
    G = U[(k, a)]
    logG = logd(int(G))
    reps = {}
    tsvp = os.path.join(sw, f'{i}.tsv')
    if os.path.exists(tsvp):
        for l in open(tsvp):
            p = l.rstrip('\n').split('\t')
            ri, D, res, cases, stats, nn = int(p[5]), int(p[6]), p[7], int(p[8]) if p[7] not in ('BUDGET',) else int(p[8]), p[9], p[10]
            reps.setdefault(ri, []).append((D, res, cases, stats, nn))
    verdicts = []
    worstD = 0
    worst_sub = 0
    minb = None
    done_all = True
    for ri, lst in sorted(reps.items()):
        D, res, cases, stats, nn = lst[-1]
        if res == 'CLOSED-cut':
            sub = 0
            b = None
        elif res in ('CLOSED-sandwich', 'open'):
            sub = int(stats.strip('[]').split(',')[-1])
            b = 0.5 * logd(int(nn)) - 0.5 * math.log10(2) + math.log10(math.log10(3))
        else:
            sub = None
            b = None
        verdicts.append(res)
        if res not in ('CLOSED-cut', 'CLOSED-sandwich'):
            done_all = False
        if D > worstD or (D == worstD and (sub or 0) > worst_sub):
            worstD = D
            worst_sub = sub or 0
        if b is not None and (minb is None or b < minb):
            minb = b
    if st != 'done' or not reps:
        verdict = f'UNFINISHED({st}, deepest completed depth {worstD}, wall {wt:.0f}s)'
    elif done_all:
        verdict = 'CLOSED'
    else:
        verdict = 'OPEN'
    rows.append(f"s={s:<7} M={''.join(map(str, M)):<12} a={a} y={y:<11} k={k} reps={len(reps)} log10G={logG:.2f} depth={worstD} subcosets={worst_sub} "
                f"min-bound={'-' if minb is None else f'{minb:.2f}'} margin={'-' if minb is None else f'{minb - logG:+.2f}'} wall={wt:.0f}s -> {verdict}")
man = [(s, md5(s)) for s in args.sources] + [(args.d1, md5(args.d1)), (args.cport, md5(args.cport))]
with open(os.path.join(args.out, 'SANDWICH-full.txt'), 'w') as f:
    f.write('command: ' + ' '.join(sys.argv) + '\n')
    for p, h in man:
        f.write(f'md5 {h}  {p}\n')
    f.write('\n'.join(rows) + '\n')
    n_closed = sum(r.endswith('-> CLOSED') for r in rows)
    f.write(f"\n{n_closed} of {len(rows)} patterns CLOSED by the full sub-coset enumeration; wall {wall:.0f}s\n")
print(open(os.path.join(args.out, 'SANDWICH-full.txt')).read())
