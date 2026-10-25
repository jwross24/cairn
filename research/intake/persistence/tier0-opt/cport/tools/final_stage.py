import argparse, hashlib, json, math, os, subprocess, sys, threading, time
from concurrent.futures import ThreadPoolExecutor
from collections import Counter, defaultdict

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
CPORT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from stage_io import entries, full_key, snapshot

TIER0 = os.path.normpath(os.path.join(CPORT, '..', '..', 'tier0'))
SOURCES = ['runall_final.jsonl', 'trees_c.jsonl', 'trees_mac.jsonl']
KMAX = 24


def md5(path):
    return hashlib.md5(open(path, 'rb').read()).hexdigest()


def load_records(snaps):
    seen = {}
    vertices = {}
    per_vertex_open = defaultdict(int)
    per_vertex_listed = defaultdict(int)
    for p in snaps:
        for line in open(p):
            r = json.loads(line)
            listed = 0
            for eq in r.get('eqs', []):
                if isinstance(eq, dict):
                    listed += len(eq.get('exceptional', []))
            listed += len(r.get('exceptional', []))
            vertices.setdefault(r['s'], []).append((os.path.basename(p), r.get('open', 0), listed, r.get('closed')))
        for (s, M, a, nu, eps, y, sol) in entries(p):
            fk = full_key(s, M, a, nu, eps, y)
            if fk not in seen:
                seen[fk] = (s, M, a, nu, eps, y)
    return seen, vertices


def baker_table(pairs, path):
    sys.path.insert(0, TIER0)
    from baker_chain import baker_upper_bound
    have = {}
    if os.path.exists(path):
        for l in open(path):
            k, a, u = l.split()
            have[(int(k), int(a))] = u
    with open(path, 'a') as f:
        for (k, a) in sorted(pairs):
            if (k, a) not in have:
                u = str(baker_upper_bound(k, a))
                f.write(f"{k} {a} {u}\n")
                have[(k, a)] = u
    return have


def fixed_table(src, pairs, path):
    have = {}
    for l in open(src):
        k, a, u = l.split()
        have[(int(k), int(a))] = u
    missing = sorted(p for p in pairs if p not in have)
    if missing:
        raise SystemExit(f'{src} lacks (k, a): {missing}')
    with open(path, 'w') as f:
        for (k, a) in sorted(pairs):
            f.write(f"{k} {a} {have[(k, a)]}\n")
    return have


def run_shards(cmd_prefix, shards, outdir, tag, nice):
    procs = []
    for i, lines in enumerate(shards):
        cases = os.path.join(outdir, f'{tag}_cases_{i}.txt')
        open(cases, 'w').write(''.join(l + '\n' for l in lines))
        tsv = os.path.join(outdir, f'{tag}_{i}.tsv')
        out = open(os.path.join(outdir, f'{tag}_{i}.txt'), 'w')
        err = open(os.path.join(outdir, f'{tag}_{i}.err'), 'w')
        cmd = cmd_prefix(cases, tsv, i)
        procs.append((subprocess.Popen(cmd, stdout=out, stderr=err, preexec_fn=lambda: os.nice(nice)), out, err, i))
    rc = []
    for p, out, err, i in procs:
        p.wait()
        out.close()
        err.close()
        rc.append(p.returncode)
    if any(rc):
        for i, r in enumerate(rc):
            if r:
                sys.stderr.write(open(os.path.join(outdir, f'{tag}_{i}.err')).read()[-2000:])
        raise SystemExit(f'{tag}: a shard exited nonzero: {rc}')


def deal(items, n, weight):
    shards = [[] for _ in range(n)]
    load = [0] * n
    for it in sorted(items, key=weight, reverse=True):
        i = load.index(min(load))
        shards[i].append(it)
        load[i] += weight(it)
    return shards


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--sources', nargs='*', default=[os.path.join(TIER0, s) for s in SOURCES])
    ap.add_argument('--jobs', type=int, default=2)
    ap.add_argument('--maxdepth', type=int, default=5)
    ap.add_argument('--maxcases', type=int, default=2000000)
    ap.add_argument('--nice', type=int, default=10)
    ap.add_argument('--cport', default=os.path.join(CPORT, 'cport'))
    ap.add_argument('--lattice', default=os.path.join(CPORT, 'data', 'lattice96.txt'))
    ap.add_argument('--vertices', default=None)
    ap.add_argument('--utable-file', default=None)
    ap.add_argument('--reuse', default=None)
    ap.add_argument('--d1-maxcases', type=int, default=5000000)
    ap.add_argument('--pattern-timeout', type=float, default=1200)
    ap.add_argument('--deadline-epoch', type=float, default=None)
    args = ap.parse_args()
    t_start = time.time()
    out = args.out
    os.makedirs(out, exist_ok=True)
    snapdir = os.path.join(out, 'snap')
    os.makedirs(snapdir, exist_ok=True)
    snaps = []
    manifest = []
    for src in args.sources:
        dst = os.path.join(snapdir, os.path.basename(src))
        n = snapshot(src, dst)
        snaps.append(dst)
        manifest.append(dict(source=src, bytes=n, md5=md5(dst)))
    json.dump(manifest, open(os.path.join(out, 'manifest.json'), 'w'), indent=1)

    seen, vertices = load_records(snaps)
    only_v = None if args.vertices is None else set(args.vertices.split(','))
    recs = {fk: v for fk, v in seen.items() if only_v is None or str(v[0]) in only_v}
    unsupported = {fk for fk, v in recs.items() if len(v[1]) > KMAX or (v[4] is not None and len(v[4]) > KMAX)}
    todo = [fk for fk in recs if fk not in unsupported]
    jobs = max(1, args.jobs)
    prev = json.load(open(os.path.join(args.reuse, 'pattern_status.json'))) if args.reuse else {}
    done = {fk: st for fk, st in prev.items() if st in ('cut1', 'sandwich') and fk in recs}
    todo = [fk for fk in todo if fk not in done]

    shards = deal(todo, jobs, lambda fk: 2 ** len(recs[fk][1]))
    t0 = time.time()
    run_shards(lambda cases, tsv, i: [args.cport, 'deepcut', '--lattice', args.lattice, '--cases', cases, '--depth', '1',
                                       '--maxcases', str(args.d1_maxcases), '--tsv', tsv], shards, out, 'deepcut', args.nice)
    t_deepcut = time.time() - t0

    status = dict(done)
    for i in range(len(shards)):
        rows = defaultdict(list)
        for l in open(os.path.join(out, f'deepcut_{i}.tsv')):
            p = l.rstrip('\n').split('\t')
            rows[p[0]].append(int(p[6]))
        for fk in shards[i]:
            r = rows.get(fk)
            if not r:
                raise SystemExit(f'no deepcut rows for {fk}')
            status[fk] = 'budget' if -1 in r else ('cut1' if all(x == 1 for x in r) else 'survivor')
    survivors = [fk for fk in todo if status[fk] == 'survivor']

    pairs = {(len(recs[fk][1]), recs[fk][2]) for fk in survivors}
    utable = os.path.join(out, 'utable.txt')
    if args.utable_file:
        fixed_table(args.utable_file, pairs, utable)
    else:
        baker_table(pairs, utable)

    swdir = os.path.join(out, 'sw')
    os.makedirs(swdir, exist_ok=True)
    order = sorted(survivors, key=lambda fk: (len(recs[fk][1]), fk))
    deadline = args.deadline_epoch
    lock = threading.Lock()
    t0 = time.time()

    def one(n_fk):
        n, fk = n_fk
        if deadline is not None and time.time() > deadline:
            return fk, 'unrun'
        base = os.path.join(swdir, str(n))
        open(base + '.cases', 'w').write(fk + '\n')
        open(base + '.only', 'w').write(' '.join(fk.split()[:4]) + '\n')
        cmd = [args.cport, 'sandwich', '--dfs', '--lattice', args.lattice, '--utable', utable, '--cases', base + '.cases', '--only', base + '.only',
               '--maxdepth', str(args.maxdepth), '--maxcases', str(args.maxcases), '--tsv', base + '.tsv']
        limit = args.pattern_timeout
        if deadline is not None:
            limit = min(limit, max(1, deadline - time.time()))
        with open(base + '.txt', 'w') as fo, open(base + '.err', 'w') as fe:
            pr = subprocess.Popen(cmd, stdout=fo, stderr=fe, preexec_fn=lambda: os.nice(args.nice))
            try:
                rc = pr.wait(timeout=limit)
            except subprocess.TimeoutExpired:
                pr.kill()
                pr.wait()
                return fk, 'timeout'
        if rc:
            return fk, 'error'
        last = {}
        for l in open(base + '.tsv'):
            p = l.rstrip('\n').split('\t')
            ri, D, res = int(p[5]), int(p[6]), p[7]
            if ri not in last or D > last[ri][0]:
                last[ri] = (D, res)
        rs = [r for _, r in last.values()]
        if not rs:
            return fk, 'error'
        if any(r == 'BUDGET' for r in rs):
            return fk, 'budget'
        if all(r in ('CLOSED-cut', 'CLOSED-sandwich') for r in rs):
            return fk, 'sandwich'
        return fk, 'open'

    with ThreadPoolExecutor(max_workers=jobs) as ex:
        for fk, st in ex.map(one, list(enumerate(order))):
            status[fk] = st
    t_sandwich = time.time() - t0
    with open(os.path.join(out, 'sandwich_all.txt'), 'w') as fo:
        for n in range(len(order)):
            f = os.path.join(swdir, f'{n}.txt')
            if os.path.exists(f):
                fo.write(''.join(l for l in open(f) if l.startswith('s=')))
    for fk in unsupported:
        status[fk] = 'unsupported'

    by_v = defaultdict(Counter)
    for fk, v in recs.items():
        by_v[v[0]][status[fk]] += 1
    bad_invariant = {s for s, rows in vertices.items() if any(o != l for _, o, l, _ in rows)}
    lines = []
    closed_vertices = 0
    open_left = 0
    for s in sorted(vertices, key=lambda x: (len(str(x)), x)):
        if only_v is not None and str(s) not in only_v:
            continue
        c = by_v.get(s, Counter())
        n = sum(c.values())
        left = sum(v for k2, v in c.items() if k2 not in ('cut1', 'sandwich'))
        ok = left == 0 and s not in bad_invariant
        closed_vertices += ok
        open_left += left
        lines.append(f"s={s:<12} open-patterns={n:<6} CLOSED-cut={c['cut1']:<6} CLOSED-sandwich={c['sandwich']:<5} "
                     f"open={c['open']} BUDGET={c['budget']} UNSUPPORTED={c['unsupported']} UNFINISHED={c['timeout'] + c['unrun'] + c['error']}"
                     f"{' RECORD-MISMATCH' if s in bad_invariant else ''} -> {'CLOSED' if ok else 'OPEN'}")
    tot = Counter(status.values())
    wall = time.time() - t_start
    summary = (f"{len(lines)} vertices: {closed_vertices} fully CLOSED, {len(lines) - closed_vertices} not; "
               f"{len(recs)} open patterns: {tot['cut1']} closed by Lemma C depth 1, {tot['sandwich']} closed by the sandwich, "
               f"{open_left} left (open {tot['open']}, budget {tot['budget']}, unsupported {tot['unsupported']}, timeout {tot['timeout']}, unrun {tot['unrun']}, error {tot['error']}); "
               f"survivors of depth 1: {len(survivors)}; wall {wall:.1f}s (deepcut {t_deepcut:.1f}s, sandwich {t_sandwich:.1f}s) on {jobs} processes")
    with open(os.path.join(out, 'FINAL-STAGE-run.txt'), 'w') as f:
        for l in lines:
            f.write(l + '\n')
        f.write('\n' + summary + '\n')
    json.dump({fk: status[fk] for fk in recs}, open(os.path.join(out, 'pattern_status.json'), 'w'))
    print('\n'.join(lines))
    print('\n' + summary)


if __name__ == '__main__':
    main()
