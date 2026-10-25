import os, sys, json, random, time, subprocess, hashlib, shutil
from gv_lib import *
import gv_corpus as C

SPLIT = [(0, 5), (5, 12)]


def ref_exec(work, refbin, args, ranges=(None,), keep_limit=3_000_000):
    files = [a for a in args if os.path.isfile(a)]
    key = sha256s(md5file(refbin), *[sha256file(f) for f in files], json.dumps(list(ranges)))
    base = os.path.join(work, 'cache', key)
    if os.path.exists(base + '.json'):
        d = json.load(open(base + '.json'))
        d['raw'], d['sorted'] = base + '.raw', base + '.sorted'
        return d
    r = run_kernel(refbin, args, os.path.join(work, 'cache'), key, ranges, timeout=14400)
    meta = {k: v for k, v in r.items() if k not in ('raw', 'sorted')}
    meta['kept'] = r['n'] <= keep_limit
    if not meta['kept']:
        drop_files(r)
    json.dump(meta, open(base + '.json.tmp', 'w'))
    os.replace(base + '.json.tmp', base + '.json')
    r.update(meta)
    return r


def write_parents(work, surv):
    body = ''.join(f"{a} {nu} " + ' '.join(map(str, eps)) + f" {co.v0[0]} {co.v0[1]}\n" for (a, nu, eps, co) in surv)
    p = os.path.join(work, 'par', hashlib.sha256(body.encode()).hexdigest()[:24] + '.txt')
    os.makedirs(os.path.dirname(p), exist_ok=True)
    if not os.path.exists(p):
        open(p + f'.{os.getpid()}', 'w').write(body)
        os.replace(p + f'.{os.getpid()}', p)
    return p


def est_children(M, eps):
    from collections import Counter, defaultdict
    g = defaultdict(list)
    for d, e in zip(M, eps):
        g[d].append(e)
    est = 2
    for d, es in g.items():
        for r, m in Counter(es).items():
            est *= (m + 1)
    return est


def sample_parents(M, surv, max_parents=300, max_children=300_000):
    if not surv:
        return []
    step = max(1, len(surv) // max_parents)
    out, tot = [], 0
    for s in surv[::step]:
        e = est_children(M, s[2])
        if out and tot + e > max_children:
            continue
        out.append(s)
        tot += e
        if len(out) >= max_parents:
            break
    return out


def wild_parents(M, A, Lold, rng, count=40, max_children=150_000, nu_bias=None):
    from lattice import Coset
    out, tot = [], 0
    for _ in range(count * 3):
        eps = tuple(rng.randrange(Lold) for _ in M)
        e = est_children(M, eps)
        if out and tot + e > max_children:
            continue
        mag = rng.choice([10, 10 ** 6, 10 ** 15, 10 ** 30])
        b, c = rng.randint(-mag, mag), rng.randint(-mag, mag)
        out.append((rng.randint(0, A), (nu_bias if nu_bias is not None and rng.random() < 0.6 else rng.randrange(Lold)), eps, Coset((b, c), (1, 0), (0, 1))))
        tot += e
        if len(out) >= count:
            break
    return out


def parse_survivors12(sortedp, M, U2):
    from lattice import Coset
    from tier0v2 import canon
    q = len(M)
    out = []
    for line in open(sortedp):
        f = line.split()
        if not f or f[0] != 'OPEN':
            continue
        a, nu = int(f[1]), int(f[2])
        eps = tuple(int(x) for x in f[3:3 + q])
        b, c = int(f[3 + q]), int(f[4 + q])
        nu2, eps2 = canon(M, nu, eps)
        out.append((a, nu2, eps2, Coset((b, c), tuple(U2[0]), tuple(U2[1]))))
    return out


def recon_lift(rawp, parents, info, M):
    from lattice import Coset
    from tier0v2 import canon
    q = len(M)
    Uo, Un = info['U_old'], info['U_new']
    surv, seen = [], set()
    for line in open(rawp):
        f = line.split()
        if not f or f[0] not in ('OPEN', 'EXACT'):
            continue
        pidx, a, nu = int(f[1]), int(f[2]), int(f[3])
        eps = tuple(int(x) for x in f[4:4 + q])
        t1, t2 = int(f[4 + q]), int(f[5 + q])
        pa = parents[pidx]
        b = pa[3].v0[0] + t1 * Uo[0][0] + t2 * Uo[1][0]
        c = pa[3].v0[1] + t1 * Uo[0][1] + t2 * Uo[1][1]
        nu2, eps2 = canon(M, nu, eps)
        key = (a, nu2, eps2)
        if key in seen:
            continue
        seen.add(key)
        surv.append((a, nu2, eps2, Coset((b, c), tuple(Un[0]), tuple(Un[1]))))
    return surv


def recon_digest(surv):
    rows = sorted(repr((a, nu, eps, tuple(co.v0), tuple(co.u1), tuple(co.u2))) for (a, nu, eps, co) in surv)
    return hashlib.sha256('\n'.join(rows).encode()).hexdigest()


def eq_task(job):
    work, eq = job['work'], job['eq']
    C.init_py(work)
    M = tuple(eq['M'])
    q = len(M)
    ref12, refN = job['ref12'], job['refN']
    cand12, candN = job.get('cand12'), job.get('candN')
    logdir = job['logdir']
    tmp = os.path.join(work, 'tmp', f"w{os.getpid()}")
    os.makedirs(tmp, exist_ok=True)
    res = dict(id=eq['id'], findings=[], inputs=[], stats=dict(M=list(M), npat=eq['npat'], tag=eq['tag']), secs={})
    t0 = time.time()
    cfgp, info = C.export12(work, M)
    st = res['stats']
    st.update(A=info['A'], K12=sorted(set(info['K'])), np12=info['np'], nc12=info['nc'], levels={})
    split = eq['npat'] >= 20000 and (hash(eq['id']) % 4 == 0 or job.get('split_all'))
    rg = SPLIT if split else (None,)
    r_full = ref_exec(work, ref12, [cfgp])
    res['inputs'].append(dict(kernel='lvl12', args=[cfgp], ranges=[None], npat=eq['npat']))
    if cand12:
        c = run_kernel(cand12, [cfgp], tmp, f"{eq['id']}_c12", rg)
        ref_cmp = r_full if split else ref_exec(work, ref12, [cfgp], rg)
        res['findings'] += diff_runs(ref_cmp, c, f"{eq['id']}_L12", logdir)
        drop_files(c)
        res['secs']['cand12'] = round(c['secs'], 2)
        st['split12'] = bool(split)
    res['secs']['ref12'] = round(r_full['secs'], 2)
    st['levels'][12] = dict(open=r_full['counters'].get('open', 0), exact=r_full['counters'].get('exact', 0), patterns=r_full['counters'].get('patterns', 0))
    if job.get('lvl12_only') or not r_full.get('kept', True):
        return res
    surv = parse_survivors12(r_full['sorted'], M, info['U2'])
    rng = random.Random(int(eq['id'][1:]) * 7919 + 1)
    prevL = 12
    for L in (24, 48, 96):
        cfgN, infoN = C.exportN(work, M, L)
        st['levels'][L] = dict(K=sorted(set(infoN['K'])), np=len(infoN['primes']), parents=0, wild=0, children=0, open=0, exact=0)
        sub = sample_parents(M, surv, job.get('max_parents', 1500), job.get('max_children', 1_200_000))
        wild = wild_parents(M, info['A'], prevL, rng, nu_bias=infoN['K'][0]) if job.get('wild', True) else []
        next_surv = []
        for kind, plist in (('chain', sub), ('wild', wild)):
            if not plist:
                continue
            parp = write_parents(work, plist)
            res['inputs'].append(dict(kernel='lvlN', args=[cfgN, parp], ranges=[None]))
            r = ref_exec(work, refN, [cfgN, parp])
            if r['rc']:
                res['findings'].append(dict(kind='refrc', label=f"{eq['id']}_{kind}{L}", text=f"REFERENCE exit {r['rcs']}: {r['errs']}"))
                continue
            sl = st['levels'][L]
            sl['parents' if kind == 'chain' else 'wild'] += len(plist)
            sl['children'] += r['counters'].get('children', 0)
            sl['open'] += r['counters'].get('open', 0)
            sl['exact'] += r['counters'].get('exact', 0)
            recon_ref = recon_lift(r['raw'], plist, infoN, M) if r.get('kept', True) else None
            if kind == 'chain':
                next_surv = recon_ref or []
            if candN:
                c = run_kernel(candN, [cfgN, parp], tmp, f"{eq['id']}_{kind}{L}")
                res['findings'] += diff_runs(r, c, f"{eq['id']}_{kind}{L}", logdir)
                if recon_ref is not None and c['rc'] == 0:
                    rc_ = recon_lift(c['raw'], plist, infoN, M)
                    if recon_digest(rc_) != recon_digest(recon_ref):
                        res['findings'].append(dict(kind='pyrecon', label=f"{eq['id']}_{kind}{L}",
                                                    text=f"difftest-style reconstruction differs: ref {len(recon_ref)} survivors ({recon_digest(recon_ref)[:12]}), cand {len(rc_)} ({recon_digest(rc_)[:12]})"))
                drop_files(c)
        surv = next_surv
        prevL = L
        if not surv:
            break
    res['secs']['total'] = round(time.time() - t0, 2)
    return res


def big_task(job):
    work = job['work']
    C.init_py(work)
    M = tuple(job['M'])
    cfgp, info = C.export12(work, M)
    tmp = os.path.join(work, 'tmp', f"w{os.getpid()}")
    nsplit = 3 if job['npat'] > 3e7 else 1
    rg = [(12 * i // nsplit, 12 * (i + 1) // nsplit) for i in range(nsplit)] if nsplit > 1 else (None,)
    ref = ref_exec(work, job['ref12'], [cfgp], rg, keep_limit=6_000_000)
    res = dict(id=f"v{job['s']}_{C.mkey(M)}", findings=[], npat=job['npat'], secs_ref=round(ref['secs'], 1), n=ref['n'])
    if job.get('cand12'):
        c = run_kernel(job['cand12'], [cfgp], tmp, res['id'] + '_c', rg)
        if not ref.get('kept', True) and ref['sha'] == c['sha'] and ref['counters'] == c['counters']:
            pass
        elif ref.get('kept', True):
            res['findings'] += diff_runs(ref, c, res['id'], job['logdir'])
        else:
            if ref['rc'] != c['rc'] or ref['counters'] != c['counters'] or ref['sha'] != c['sha']:
                res['findings'].append(dict(kind='stdout' if ref['sha'] != c['sha'] else 'counters', label=res['id'],
                                            text=f"ref {ref['sha'][:16]} n={ref['n']} {ref['counters']} / cand {c['sha'][:16]} n={c['n']} {c['counters']}"))
        res['secs_cand'] = round(c['secs'], 1)
        res['sha'] = c['sha']
        drop_files(c)
    return res


def plant_task(job):
    pr = job['plant']
    cmd = [sys.executable, os.path.join(HERE, 'gv_plant.py'), job['pipe'], str(pr['y']), str(pr['s']), json.dumps(pr['M'])]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=job.get('timeout', 1500),
                           env=dict(os.environ, TMPDIR=os.path.join(job['work'], 'tmp')))
    except subprocess.TimeoutExpired:
        return dict(plant=pr, found=False, lost='timeout')
    for ln in p.stdout.splitlines():
        if ln.startswith('PLANT '):
            d = json.loads(ln[6:])
            d['plant'] = pr
            return d
    return dict(plant=pr, found=False, lost=f'no result (rc {p.returncode}): {p.stderr[-300:]}')


def vertex_task(job):
    key = sha256s(job['pipe_id'], job['s'])
    cp = os.path.join(job['work'], 'cache', f"vertex_{job['s']}_{key[:16]}.json")
    if job.get('cache') and os.path.exists(cp):
        return json.load(open(cp))
    p = subprocess.run([sys.executable, os.path.join(HERE, 'gv_vertex.py'), job['pipe'], str(job['s'])], capture_output=True, text=True,
                       env=dict(os.environ, TMPDIR=os.path.join(job['work'], 'tmp')))
    for ln in p.stdout.splitlines():
        if ln.startswith('VERTEX '):
            d = json.loads(ln[7:])
            d['s'] = job['s']
            if job.get('cache'):
                json.dump(d, open(cp, 'w'))
            return d
    return dict(s=job['s'], rc=p.returncode, rows=[], err=p.stderr[-400:])


def synth_task(job):
    work = job['work']
    tag = job['tag']
    tmp = os.path.join(work, 'tmp', f"w{os.getpid()}")
    refbin, candbin = (job['ref12'], job['cand12']) if job['kernel'] == 'lvl12' else (job['refN'], job['candN'])
    ref = ref_exec(work, refbin, job['args'])
    c = run_kernel(candbin, job['args'], tmp, f"synth_{tag}")
    if c['rc'] < 0:
        verdict, text = 'CRASH', f"killed by signal {-c['rc']}"
    elif c['rc'] != 0:
        verdict, text = 'REFUSES', f"exit {c['rc']}: {c['errs'][0][:160]}"
    else:
        d = diff_runs(ref, c, f"synth_{tag}", job['logdir'])
        verdict, text = ('EQUIVALENT', 'identical sorted stdout and counters') if not d else ('DIVERGED', '; '.join(x['text'].split('\n')[0] for x in d))
    drop_files(c)
    return dict(tag=tag, kernel=job['kernel'], verdict=verdict, text=text, ref_open=ref['counters'].get('open'))


def genuine_parent(y, M, Lold):
    s = str(y)
    pos = sorted((int(ch), i) for i, ch in enumerate(reversed(s)) if ch != '1')
    eps = [i % Lold for _, i in pos]
    a = b = c = 0
    t = y
    while t % 2 == 0:
        t //= 2
        a += 1
    while t % 3 == 0:
        t //= 3
        b += 1
    while t % 7 == 0:
        t //= 7
        c += 1
    assert t == 1
    return f"{a} {len(s) % Lold} " + ' '.join(map(str, eps)) + f" {b} {c}\n", (len(s) % Lold, eps)


def genuine_task(job):
    work, g = job['work'], job['g']
    C.init_py(work)
    from tier0v2 import canon
    M = tuple(sorted(g['M']))
    y = g['y']
    tmp = os.path.join(work, 'tmp', f"w{os.getpid()}")
    res = dict(id=f"g{y}", findings=[], inputs=[])
    pos = sorted((int(ch), i) for i, ch in enumerate(reversed(str(y))) if ch != '1')
    for L in (24, 48, 96):
        Lold = L // 2
        cfgN, infoN = C.exportN(work, M, L)
        body, _ = genuine_parent(y, M, Lold)
        parp = os.path.join(work, 'par', f"g{y}_{L}.txt")
        os.makedirs(os.path.dirname(parp), exist_ok=True)
        open(parp, 'w').write(body)
        res['inputs'].append(dict(kernel='lvlN', args=[cfgN, parp], ranges=[None]))
        r = ref_exec(work, job['refN'], [cfgN, parp])
        want = canon(M, len(str(y)) % L, tuple(i % L for _, i in pos))
        for tag in ('ref', 'cand'):
            if tag == 'cand':
                if not job.get('candN'):
                    continue
                run = run_kernel(job['candN'], [cfgN, parp], tmp, f"g{y}_{L}")
                res['findings'] += diff_runs(r, run, f"g{y}_L{L}_chain", job['logdir'])
            else:
                run = r
            if run['rc']:
                continue
            found = False
            q = len(M)
            for line in open(run['sorted']):
                f = line.split()
                if f and f[0] in ('OPEN', 'EXACT') and canon(M, int(f[3]), tuple(int(x) for x in f[4:4 + q])) == want:
                    found = True
                    break
            if not found and y >= 10:
                res['findings'].append(dict(kind='genuine-lost' if tag == 'cand' else 'refrc', label=f"g{y}_L{L}_chain",
                                            text=f"{tag}: the true child of genuine parent y={y} (M={list(M)}) is absent from level-{L} output"))
            if tag == 'cand':
                drop_files(run)
    return res
