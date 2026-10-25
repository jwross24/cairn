import os, sys, json, subprocess, shutil, glob, re, time
from math import gcd
from concurrent.futures import ThreadPoolExecutor
from gv_lib import *
from gv_corpus import synth_cfgs, synthN_inputs, init_py

CLANG = LLVM + '/clang'
PROFDATA = LLVM + '/llvm-profdata'
LLVMCOV = LLVM + '/llvm-cov'
NPAT_CAP = 3_000_000


def build_cov(work, kernel):
    src = os.path.join(work, 'ref', kernel + '.c')
    out = os.path.join(work, 'cov', kernel + '_cov')
    stamp = out + '.md5'
    m = md5file(src)
    if not os.path.exists(out) or not os.path.exists(stamp) or open(stamp).read() != m:
        p = subprocess.run([CLANG, '-O0', '-g', '-fprofile-instr-generate', '-fcoverage-mapping', '-o', out, src], capture_output=True, text=True)
        if p.returncode:
            raise SystemExit('coverage build failed: ' + p.stderr)
        open(stamp, 'w').write(m)
    return out


def facts(work):
    """Per-level facts the dead-branch rules rest on, recomputed from the exporters (the configs are independent of the equation)."""
    init_py(work)
    from export_level import level_chain, LEVELS
    from tier0v2 import ten_adic_K
    from lattice import Coset
    ch = level_chain((2,), 96)
    f = {}
    for L in LEVELS:
        pd, obj, U = ch[L]
        f[f'K{L}'] = sorted({ten_adic_K(Coset((0, 0), U[0], U[1]), 60, a) for a in range(64)})
        f[f'np{L}'] = len(pd)
        if L == 12:
            f['nc12'] = len(obj.comps)
        else:
            lin = []
            for (i, m, g1, g2, Nl) in obj.linear:
                g = gcd(abs(g1), abs(g2))
                lin.append(dict(m=m, g1=g1, g2=g2, g=g, d=gcd(g, m)))
            f[f'lin{L}'] = lin
    return f


def rules(F):
    allK = lambda lo, hi: all(lo <= k <= hi for L in (24, 48, 96) for k in F[f'K{L}'])
    lin_ok = all(l['g1'] > 0 and l['g2'] > 0 and l['d'] == 1 and l['m'] > 1 for L in (24, 48, 96) for l in F[f'lin{L}'])
    k12 = F['K12'] == [3] and F['np12'] == 5 and F['nc12'] == 4
    R = []
    A = R.append
    A(('lvl12', r'if\(g==ng\)', 'T', 'STRUCTURAL', 'rec_group is entered with g < ng: the only recursive call that advances g sits behind `if(g+1<ng)`, and ng >= 1 for q >= 1', True))
    A(('lvl12', r'K>18|K<1', 'T', 'DEAD12', 'K == 3 for every a in 0..63 at level 12 (ten_adic_K recomputed from U2 for all a), so K > 18 and K < 1 never hold', k12))
    A(('lvl12', r'printf\(" %d",eps\[i\]\); printf\(" %lld %lld\\n",b,c\); cnt_open\+\+; return', 'any', 'DEAD12', 'body of the K < 1 branch (K == 3 at level 12)', k12))
    A(('lvlN', r'int K=KT\[a_cur\]; if\(K>18\)|if\(K<1\)', 'T', 'DEAD-LIFT', 'K is 4/5/5 at levels 24/48/96 for every a in 0..63, so K > 18 and K < 1 never hold', allK(4, 5)))
    A(('lvlN', r'ull l2=K>=3', 'any', 'DEAD-LIFT', 'K >= 4 at every lift level, so the K < 3 arm of the l2 ternary is dead; lam is recomputed from gcd on the next statement', allK(4, 5)))
    A(('lvlN', r'if\(g<0\)\{g=-g', 'T', 'DEAD-LIFT', 'the only linear component (level 96) has g1, g2 > 0, so egcd returns g > 0', lin_ok))
    A(('lvlN', r'if\(key%d\)', 'T', 'DEAD-LIFT', 'the only linear component has gcd(g1, g2, m) == 1, so d == 1 and key % d == 0', lin_ok))
    A(('lvlN', r'if\(mm>1\)', 'F', 'DEAD-LIFT', 'mm = m/d = m > 1 for the only linear component', lin_ok))
    A(('lvlN', r'ull gi=\(g/d\)%mm; if\(gi<0\)', 'T', 'DEAD-LIFT', 'g/d > 0 so gi >= 0', lin_ok))
    A(('lvlN', r'if\(!hget\(f,cur,&dummy\)\)', 'F', 'STRUCTURAL', 'gamma has prime order q and the table holds m <= q consecutive powers, so no key repeats', True))
    A(('lvlN', r'for\(ull i=0;i<m\+1;i\+\+\)|bsgs failed', 'any', 'DEFENSIVE', 'baby-step table always contains the target for h in the order-q subgroup; the exit(4) path needs a corrupt dlog input', True))
    A(('lvlN', r'dlog verify failed', 'any', 'DEFENSIVE', 'self-check of the Pohlig-Hellman result; fires only on a defect (the N5 mutant)', True))
    A(('lvlN', r'no inverse', 'any', 'DEFENSIVE', 'gcd(a, m) == 1 for every modulus used (primes and prime powers of a prime-order subgroup)', True))
    A(('lvlN', r'for\(int i=0;i<nY;i\+\+\)\{ int d=dg\[i\]; if\(d==0\)', 'T', 'RARE', 'reachable at K = 4/5 only for a survivor whose tail value has an internal zero and n_Y == nu (mod L), about 1e-5 x 0.27/24 per child; exercised through the same code with a replaced K row (genuine parent with n = K)', True))
    A(('lvlN', r'v<0|neg\)|if\(neg\)', 'any', 'STRUCTURAL', 'print128 receives t1, t2 reduced by mod128, so v >= 0', True))
    A(('lvlN', r'\*s<=\'9\'', 'F', 'DEFENSIVE', 'parent files are written by this harness / run_c.py with decimal tokens only', True))
    return R


def classify(kernel, fn, line, side, R, in_all):
    for (k, rx, sd, cls, why, ok) in R:
        if k == kernel and ok and (sd == 'any' or sd == side) and re.search(rx, line):
            return cls, why
    if in_all:
        return 'OFFNOMINAL', 'reached only by the synthetic configs (K row != 3 at level 12, np = 7); not reachable from any exporter output'
    return None, None


def cov_inputs(work, man, genuine_inputs=(), genuine=()):
    real = [i for i in man if i['kernel'] == 'lvlN' or i.get('npat', 0) <= NPAT_CAP]
    real += list(genuine_inputs)
    l12 = [i for i in man if i['kernel'] == 'lvl12' and 0 < i.get('npat', 0) <= 300000]
    base = max(l12, key=lambda i: i['npat'])
    cfg = base['args'][0]
    for rg in ((0, 5), (5, 12)):
        real.append(dict(kernel='lvl12', args=[cfg, str(rg[0]), str(rg[1])]))
    junk = os.path.join(work, 'cfg', 'junk.txt')
    open(junk, 'w').write('x\n')
    blank = os.path.join(work, 'par', 'blank.txt')
    os.makedirs(os.path.dirname(blank), exist_ok=True)
    open(blank, 'w').write('\n')
    lN = next(i for i in man if i['kernel'] == 'lvlN')
    real += [dict(kernel='lvl12', args=[]), dict(kernel='lvl12', args=['/nonexistent/cfg']), dict(kernel='lvl12', args=[junk]),
             dict(kernel='lvlN', args=[]), dict(kernel='lvlN', args=[lN['args'][0]]), dict(kernel='lvlN', args=['/nonexistent/cfg', lN['args'][1]]),
             dict(kernel='lvlN', args=[lN['args'][0], '/nonexistent/parents']), dict(kernel='lvlN', args=[lN['args'][0], blank])]
    synth = [dict(kernel='lvl12', args=[p], synth=t) for t, p in synth_cfgs(work, cfg)] + synthN_inputs(work, genuine)
    return real, synth


def run_set(work, bins, inputs, profdir, jobs):
    if os.path.isdir(profdir):
        shutil.rmtree(profdir)
    os.makedirs(profdir)
    env = dict(os.environ, LLVM_PROFILE_FILE=os.path.join(profdir, '%p.profraw'))

    def go(i):
        subprocess.run([bins[i['kernel']]] + i['args'], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    with ThreadPoolExecutor(jobs) as ex:
        list(ex.map(go, inputs))


def merge(profdirs, out):
    files = [f for d in profdirs for f in glob.glob(os.path.join(d, '*.profraw'))]
    subprocess.run([PROFDATA, 'merge', '-sparse', '-o', out] + files, check=True)


def export(binp, prof):
    p = subprocess.run([LLVMCOV, 'export', binp, f'-instr-profile={prof}', '-format=text'], capture_output=True, text=True, check=True)
    return json.loads(p.stdout)['data'][0]


def unreached(d, srcpath):
    src = open(srcpath).read().split('\n')
    out = {}
    for f in d['functions']:
        fn = f['name'].split(':')[-1]
        for br in f['branches']:
            l1, c1, l2, c2, t, fa = br[:6]
            for side, cnt in (('T', t), ('F', fa)):
                if cnt == 0:
                    out[(fn, l1, c1, side)] = src[l1 - 1].strip()
    return out


def coverage_stage(ctx, fh=None):
    work = ctx['work']
    man = ctx.get('manifest')
    name = 'branch coverage (reference)'
    if not man:
        return dict(name=name, status='FAIL', detail='no manifest: run a candidate gate first', findings=[])
    cov = os.path.join(work, 'cov')
    jobs = ctx.get('jobs', 3)
    bins = {k: build_cov(work, k) for k in ('lvl12', 'lvlN')}
    real, synth = cov_inputs(work, man, ctx.get('genuine_inputs', ()), ctx.get('genuine', []))
    run_set(work, bins, real, os.path.join(cov, 'prof_real'), jobs)
    run_set(work, bins, synth, os.path.join(cov, 'prof_synth'), jobs)
    merge([os.path.join(cov, 'prof_real')], os.path.join(cov, 'real.profdata'))
    merge([os.path.join(cov, 'prof_real'), os.path.join(cov, 'prof_synth')], os.path.join(cov, 'all.profdata'))
    F = facts(work)
    R = rules(F)
    lines = [f"coverage inputs: {len(real)} runs (corpus, genuine parents, wild parents, range splits, CLI error cases) + {len(synth)} synthetic off-nominal configs", f"facts: {json.dumps(F)}"]
    findings, summ, cnts = [], {}, {}
    for k in ('lvl12', 'lvlN'):
        src = os.path.join(work, 'ref', k + '.c')
        dr, da = export(bins[k], os.path.join(cov, 'real.profdata')), export(bins[k], os.path.join(cov, 'all.profdata'))
        t = dr['totals']
        summ[k] = f"{k}: lines {t['lines']['percent']:.1f}% ({t['lines']['covered']}/{t['lines']['count']}), branches {t['branches']['percent']:.1f}% ({t['branches']['covered']}/{t['branches']['count']}), regions {t['regions']['percent']:.1f}%"
        rep = subprocess.run([LLVMCOV, 'report', bins[k], f"-instr-profile={os.path.join(cov, 'real.profdata')}", '-show-functions', src], capture_output=True, text=True).stdout
        lines += ['', f'== {k}: per-function coverage (corpus without synthetic configs) ==', rep]
        ur, ua = unreached(dr, src), unreached(da, src)
        lines.append(f'== {k}: unreached branch sides ({len(ur)}) ==')
        for key in sorted(ur, key=lambda x: (x[1], x[2], x[3])):
            fn, ln, col, side = key
            cls, why = classify(k, fn, ur[key], side, R, key not in ua)
            if cls == 'RARE' and key in ua:
                cls, why = None, None
            cnts[cls or 'NEEDS-CASE'] = cnts.get(cls or 'NEEDS-CASE', 0) + 1
            lines.append(f"  {k}.c:{ln}:{col} {fn} [{side}-side never taken] {cls or 'NEEDS-CASE'}: {why or 'no rule and not reached by any input'}\n      {ur[key][:150]}")
            if cls is None:
                findings.append(dict(kind='coverage', label=f'{k}.c:{ln}:{col}', text=f"{fn} {side}-side unreached and unclassified: {ur[key][:120]}"))
    open(os.path.join(ctx['logdir'], 'coverage.txt'), 'w').write('\n'.join(lines) + '\n')
    detail = '; '.join(summ.values()) + f"; unreached sides {dict(sorted(cnts.items()))} (see coverage.txt)"
    return dict(name=name, status='FAIL' if findings else 'PASS', detail=detail, findings=findings)
