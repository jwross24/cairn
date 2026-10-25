import sys, os, subprocess, resource, hashlib, json, glob, time
HERE = os.path.dirname(os.path.abspath(__file__))
T0 = os.path.normpath(os.path.join(HERE, '..', '..', '..', 'tier0'))
SCR = '/private/tmp/claude-501/-Users-jwross-Documents-cairn/ec9f8f52-ce29-4a5c-9caf-2ecbd434509f/scratchpad'
H = os.path.join(SCR, 'h12')
OUT = os.path.join(SCR, 'li'); os.makedirs(OUT, exist_ok=True)
KEYS = ('tail-dead', 'open', 'exact')

def run(binary, cfg, par, outp, env=None, timeout=float(os.environ.get('LDIFF_TIMEOUT', '300'))):
    e = dict(os.environ); e.update(env or {})
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    t0 = time.time()
    with open(outp, 'w') as fo:
        try:
            pr = subprocess.run(['nice', '-n', '10', binary, cfg, par], stdout=fo, stderr=subprocess.PIPE, text=True, env=e, timeout=timeout)
        except subprocess.TimeoutExpired:
            return None, None, {}, time.time() - t0
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    cpu = (after.ru_utime - before.ru_utime) + (after.ru_stime - before.ru_stime)
    stats = {}
    parts = pr.stderr.split()
    for k, v in zip(parts[0::2], parts[1::2]):
        try: stats[k] = int(v)
        except ValueError: pass
    return pr.returncode, cpu, stats, time.time() - t0

def canon(path):
    lines = sorted(l for l in open(path) if l.strip())
    return len(lines), hashlib.sha256(''.join(lines).encode()).hexdigest()

def chrange():
    v = os.environ.get('LDIFF_CH')
    if not v: return None
    lo, hi = (float(x) for x in v.split(':'))
    ok = set()
    for f in glob.glob(os.path.join(HERE, '..', 'tierb-lift', 'logs', 'h12_*.jsonl')):
        for l in open(f):
            r = json.loads(l)
            x = r.get('lift' + LEVEL_FOR_CH)
            if x and lo <= x['children'] <= hi: ok.add(f"{r['s']}_{''.join(map(str, r['M']))}")
    return ok

LEVEL_FOR_CH = '24'

def dirs_for(level):
    global LEVEL_FOR_CH
    LEVEL_FOR_CH = str(level)
    sel = chrange()
    ds = []
    for d in sorted(glob.glob(os.path.join(H, '*'))):
        p = os.path.join(d, f'parents{level}.txt')
        if os.path.exists(p) and os.path.getsize(p) > 0 and (sel is None or os.path.basename(d) in sel):
            ds.append((os.path.getsize(p), d))
    ds.sort()
    return [d for _, d in ds]

def sig(stats):
    return tuple(stats.get(k) for k in KEYS)

if __name__ == '__main__':
    level, logname, maxn = sys.argv[1], sys.argv[2], int(sys.argv[3])
    variants = json.loads(sys.argv[4])
    binj = os.path.join(HERE, 'lvlJ3')
    logp = os.path.join(HERE, 'logs', logname)
    done = set()
    if os.path.exists(logp):
        for l in open(logp):
            r = json.loads(l); done.add((r['dir'], r['variant']))
    refcache = {}
    n = 0
    order = dirs_for(level)
    if os.environ.get('LDIFF_DESC') == '1': order = order[::-1]
    for d in order:
        if n >= maxn: break
        name = os.path.basename(d); cfg = os.path.join(d, f'cfgL{level}.txt'); par = os.path.join(d, f'parents{level}.txt')
        if all((name, v['name']) in done for v in variants): continue
        n += 1
        ro = os.path.join(OUT, f'ref_{level}_{logname}.out')
        rc, cpu_ref, sref, wall = run(os.path.join(T0, 'lvlN'), cfg, par, ro)
        if rc is None:
            with open(logp, 'a') as f: f.write(json.dumps(dict(dir=name, variant='ref', timeout=True)) + '\n')
            continue
        nref, href = canon(ro); cnt = sum(sref.get(k, 0) for k in KEYS)
        for v in variants:
            if (name, v['name']) in done: continue
            if v.get('min_count', 0) > cnt: continue
            jo = os.path.join(OUT, f'j_{level}_{logname}.out')
            rc2, cpu_j, sj, wall2 = run(os.path.join(HERE, v.get('bin', 'lvlJ3')), cfg, par, jo, v.get('env'))
            n2, h2 = canon(jo)
            row = dict(dir=name, level=level, variant=v['name'], rc=[rc, rc2], lines=[nref, n2], sha_equal=(href == h2), stats_equal=(sig(sref) == sig(sj)),
                       caught=(href != h2) or (sig(sref) != sig(sj)), ref_counts=dict(zip(KEYS, sig(sref))), count=cnt, parents=sref.get('parents'), children=sref.get('children'),
                       cpu_ref=round(cpu_ref, 3), cpu_j=round(cpu_j, 3), wall_j=round(wall2, 3), wall_ref=round(wall, 3), speedup=round(cpu_ref / cpu_j, 2) if cpu_j and cpu_j > 0 else None,
                       ns_per_child_ref=round(cpu_ref * 1e9 / max(sref.get('children', 1), 1), 1), ref_sha=href[:16],
                       extra={k: sj[k] for k in ('gpu_us', 'cpu_cand_us', 'prep_us', 'total_us', 'gcand', 'retry', 'p0', 'p1', 'probes', 'cands', 'built', 'pairadds', 'fp_par_big', 'fp_dead_big', 'fp_dead_all', 'fp_ch_small', 'fp_ch_all', 'fp_rank0') if k in sj})
            with open(logp, 'a') as f: f.write(json.dumps(row) + '\n')
