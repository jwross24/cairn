import os, sys, hashlib, json, subprocess, time, shutil, re, glob, threading

HERE = os.path.dirname(os.path.abspath(__file__))
PERSIST = os.path.abspath(os.path.join(HERE, '..', '..'))
TIER0 = os.path.join(PERSIST, 'tier0')
REF_DIR = os.path.join(PERSIST, 'tier0-opt', 'reference')
PINS = {'lvl12.c': '35528aabe055f6f92b696cfae66c930b', 'lvlN.c': '3493e68c1fdc5756d4a01f0e6ed46c74'}
LLVM = '/opt/homebrew/opt/llvm/bin'
DEFAULT_WORK = '/private/tmp/persist-gatev2/work'
CC = ['cc', '-O3', '-march=native']
ENV_C = dict(os.environ, LC_ALL='C')


def md5file(p):
    return hashlib.md5(open(p, 'rb').read()).hexdigest()


def sha256file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for ch in iter(lambda: f.read(1 << 20), b''):
            h.update(ch)
    return h.hexdigest()


def sha256s(*parts):
    h = hashlib.sha256()
    for p in parts:
        h.update(p if isinstance(p, bytes) else str(p).encode())
        h.update(b'\0')
    return h.hexdigest()


def count_lines(p):
    n = 0
    with open(p, 'rb') as f:
        for ch in iter(lambda: f.read(1 << 20), b''):
            n += ch.count(b'\n')
    return n


def parse_counters(err):
    parts = err.split()
    out = {}
    for k, v in zip(parts[0::2], parts[1::2]):
        try:
            out[k] = int(v)
        except ValueError:
            out[k] = v
    return out


def build(src, out, cc=None, extra=()):
    cmd = (cc or CC) + list(extra) + ['-o', out, src]
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def setup_work(work):
    for d in ('src', 'ref', 'cache', 'cfg', 'tmp', 'pipes', 'cov', 'mut'):
        os.makedirs(os.path.join(work, d), exist_ok=True)
    for f in glob.glob(os.path.join(TIER0, '*.py')):
        dst = os.path.join(work, 'src', os.path.basename(f))
        if not os.path.exists(dst) or md5file(dst) != md5file(f):
            shutil.copy2(f, dst)
    z = os.path.join(TIER0, 'zf_below_1e4000.txt')
    zd = os.path.join(work, 'src', 'zf_below_1e4000.txt')
    if not os.path.exists(zd):
        shutil.copy2(z, zd)
    for name, pin in PINS.items():
        src = os.path.join(REF_DIR, name)
        got = md5file(src)
        if got != pin:
            raise SystemExit(f"frozen reference {src} md5 {got} != pinned {pin}")
        dst = os.path.join(work, 'ref', name)
        shutil.copy2(src, dst)
        binp = os.path.join(work, 'ref', name[:-2])
        stamp = binp + '.md5'
        if not os.path.exists(binp) or not os.path.exists(stamp) or open(stamp).read() != got:
            rc, log = build(dst, binp)
            if rc:
                raise SystemExit(f"reference build failed:\n{log}")
            open(stamp, 'w').write(got)
    return dict(lvl12=os.path.join(work, 'ref', 'lvl12'), lvlN=os.path.join(work, 'ref', 'lvlN'),
                lvl12_md5=PINS['lvl12.c'], lvlN_md5=PINS['lvlN.c'])


def make_pipe(work, name, lvl12, lvlN):
    d = os.path.join(work, 'pipes', name)
    os.makedirs(d, exist_ok=True)
    for f in glob.glob(os.path.join(work, 'src', '*')):
        if os.path.isdir(f):
            continue
        dst = os.path.join(d, os.path.basename(f))
        if not os.path.exists(dst):
            os.symlink(f, dst) if f.endswith('.txt') else shutil.copy2(f, dst)
    for nm, tgt in (('lvl12', lvl12), ('lvlN', lvlN)):
        dst = os.path.join(d, nm)
        if os.path.lexists(dst):
            os.remove(dst)
        os.symlink(os.path.abspath(tgt), dst)
    return d


def run_kernel(binp, args, tmp, tag, ranges=(None,), timeout=1500):
    """Run binp once per range; return rc, per-run stderr, raw (concatenated) and canonically sorted stdout."""
    os.makedirs(tmp, exist_ok=True)
    raws, errs, rcs = [], [], []
    t0 = time.time()
    for i, rg in enumerate(ranges):
        rawp = os.path.join(tmp, f'{tag}.{i}.raw')
        argv = [binp] + list(args) + ([str(rg[0]), str(rg[1])] if rg else [])
        with open(rawp, 'wb') as fo:
            try:
                p = subprocess.run(argv, stdout=fo, stderr=subprocess.PIPE, timeout=timeout)
                errs.append(p.stderr.decode(errors='replace').strip())
                rcs.append(p.returncode)
            except subprocess.TimeoutExpired:
                errs.append(f'timeout after {timeout}s')
                rcs.append(-999)
        raws.append(rawp)
    rawp = os.path.join(tmp, f'{tag}.raw')
    with open(rawp, 'wb') as fo:
        for r in raws:
            with open(r, 'rb') as fi:
                shutil.copyfileobj(fi, fo)
            os.remove(r)
    sortp = os.path.join(tmp, f'{tag}.sorted')
    subprocess.run(['sort', '-T', tmp, '-S', '256M', '-o', sortp, rawp], env=ENV_C, check=True)
    ctr = {}
    for e in errs:
        for k, v in parse_counters(e).items():
            ctr[k] = ctr[k] + v if isinstance(v, int) and isinstance(ctr.get(k), int) else v
    return dict(rc=max(rcs), rcs=rcs, errs=errs, counters=ctr, raw=rawp, sorted=sortp,
                sha=sha256file(sortp), n=count_lines(sortp), secs=time.time() - t0)


def drop_files(res, keep_sorted=False):
    for k in ('raw', 'sorted'):
        if k == 'sorted' and keep_sorted:
            continue
        p = res.get(k)
        if p and os.path.exists(p):
            os.remove(p)


def diff_runs(ref, cand, label, logdir, nshow=6):
    """Findings between reference and candidate runs of one invocation; every difference is written verbatim."""
    out = []
    if ref['rc'] != cand['rc']:
        out.append(dict(kind='rc', label=label, text=f"exit codes ref={ref['rcs']} cand={cand['rcs']}; cand stderr: {cand['errs']}"))
        return out
    if len(ref['errs']) == len(cand['errs']):
        if ref['errs'] != cand['errs']:
            out.append(dict(kind='counters', label=label, text="stderr counters differ\n  ref : " + ' | '.join(ref['errs']) + "\n  cand: " + ' | '.join(cand['errs'])))
    if ref['counters'] != cand['counters'] and not any(f['kind'] == 'counters' for f in out):
        out.append(dict(kind='counters', label=label, text=f"summed counters differ\n  ref : {ref['counters']}\n  cand: {cand['counters']}"))
    if ref['sha'] != cand['sha']:
        os.makedirs(logdir, exist_ok=True)
        dp = os.path.join(logdir, f'diff_{label}.txt')
        with open(dp, 'w') as f:
            p = subprocess.run(['comm', '-3', ref['sorted'], cand['sorted']], env=ENV_C, stdout=f)
        lines = open(dp, errors='replace').read().split('\n')
        shown = []
        for ln in lines:
            if not ln:
                continue
            shown.append(('ref  only: ' + ln.strip()) if not ln.startswith('\t') else ('cand only: ' + ln.strip()))
            if len(shown) >= nshow:
                break
        out.append(dict(kind='stdout', label=label,
                        text=f"sorted stdout differs: ref sha {ref['sha'][:16]} n={ref['n']}, cand sha {cand['sha'][:16]} n={cand['n']}; full diff {dp}\n  " + '\n  '.join(shown)))
    return out
