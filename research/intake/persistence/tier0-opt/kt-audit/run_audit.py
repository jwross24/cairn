import sys, os, json, subprocess, time, hashlib, tempfile
sys.dont_write_bytecode = True
T0 = '/Users/jwross/Documents/cairn/research/intake/persistence/tier0'
sys.path.insert(0, T0)
from collections import Counter
from export_cfg import export
from export_level import export as export_level
import pydesc
from tier0v2 import solve_equation, canon, factor237
from lattice import Coset
PROD = '/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/kt-audit/lvlN_prod_pinned'
FIX = '/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/math/lift-ideation/lvlNf'
LVL12 = T0 + '/lvl12'
SCR = '/private/tmp/claude-501/-Users-jwross-Documents-cairn/ec9f8f52-ce29-4a5c-9caf-2ecbd434509f/scratchpad/ktaudit'
os.makedirs(SCR, exist_ok=True)

CACHE = {}
def keys_of(text, q):
    ks = set()
    for l in text.splitlines():
        f = l.split()
        if f and f[0] in ('OPEN', 'EXACT'): ks.add(tuple(f[:4 + q]))
    return ks

def make_lift(M, workdir, mode, rec):
    M = tuple(sorted(M)); q = len(M)
    def lift(L_prev, L, survivors, fg):
        cfgp = f"{workdir}/cfgL{L}.txt"; info = export_level(M, L, cfgp)
        Uo = info['U_old']; Un = info['U_new']
        par = f"{workdir}/parents{L}_{mode}.txt"
        with open(par, 'w') as f:
            for (a, nu, eps, co) in survivors: f.write(f"{a} {nu} " + ' '.join(map(str, eps)) + f" {co.v0[0]} {co.v0[1]}\n")
        binp = PROD if mode == 'prod' else FIX
        if mode == 'fixed' and L == 24 and 'o2_24' in CACHE:
            out = CACHE['o2_24']
        else:
            out = subprocess.run(['nice', '-n', '10', binp, cfgp, par], capture_output=True, text=True)
        assert out.returncode == 0, out.stderr
        r = dict(level=L, parents=len(survivors), stats=out.stderr.strip(), out_sha=hashlib.sha256(''.join(sorted(out.stdout.splitlines(True))).encode()).hexdigest()[:16])
        if mode == 'prod':
            o2 = subprocess.run(['nice', '-n', '10', FIX, cfgp, par], capture_output=True, text=True)
            assert o2.returncode == 0, o2.stderr
            if L == 24: CACHE['o2_24'] = o2
            kp = keys_of(out.stdout, q); kf = keys_of(o2.stdout, q)
            r.update(fixed_stats=o2.stderr.strip(), prod_keys=len(kp), fixed_keys=len(kf), fixed_not_in_prod=len(kf - kp), prod_not_in_fixed=len(kp - kf),
                     fixed_not_in_prod_sample=sorted(kf - kp)[:5], same_output=(sorted(out.stdout.splitlines()) == sorted(o2.stdout.splitlines())))
        rec.append(r)
        print(json.dumps(r), flush=True)
        parts = out.stderr.split(); stats = {k: int(v) for k, v in zip(parts[0::2], parts[1::2]) if v.lstrip('-').isdigit()}
        surv = []; seen = set()
        for line in out.stdout.splitlines():
            f = line.split()
            if f[0] not in ('OPEN', 'EXACT'): continue
            pidx, a, nu = int(f[1]), int(f[2]), int(f[3]); eps = tuple(int(x) for x in f[4:4 + q]); t1, t2 = int(f[4 + q]), int(f[5 + q])
            pa = survivors[pidx]; b = pa[3].v0[0] + t1 * Uo[0][0] + t2 * Uo[1][0]; c = pa[3].v0[1] + t1 * Uo[0][1] + t2 * Uo[1][1]
            nu2, eps2 = canon(M, nu, eps); key = (a, nu2, eps2)
            if key in seen: continue
            seen.add(key); surv.append((a, nu2, eps2, Coset((b, c), tuple(Un[0]), tuple(Un[1]))))
        return surv, stats.get('children', 0), stats
    return lift

def main(s, M, ncores):
    M = tuple(sorted(M)); tag = f"{s}_{''.join(map(str, M))}"
    workdir = f"{SCR}/{tag}"; os.makedirs(workdir, exist_ok=True)
    cfgp = f"{workdir}/cfg_{tag}.txt"; cfg = export(M, cfgp)
    L = cfg['L']; U2 = cfg['U2']; q = len(M)
    outs = []; procs = []
    t0 = time.time()
    for i in range(ncores):
        lo = L * i // ncores; hi = L * (i + 1) // ncores
        outp = f"{workdir}/l12_{tag}_{i}.txt"; outs.append(outp)
        procs.append(subprocess.Popen(['nice', '-n', '10', LVL12, cfgp, str(lo), str(hi), 'bs'], stdout=open(outp, 'w'), stderr=subprocess.PIPE, text=True))
    stats = Counter()
    for p in procs:
        _, err = p.communicate(); assert p.returncode == 0, err
        parts = err.split()
        for k, v in zip(parts[0::2], parts[1::2]):
            try: stats[k] += int(v)
            except ValueError: pass
    stats.pop('bsdrop', None)
    print('lvl12 done', dict(stats), round(time.time() - t0), flush=True)
    res = dict(s=s, M=list(M), A=cfg['A'], l12=dict(stats))
    for mode in ('prod', 'fixed'):
        rec = []
        scan = pydesc.scan12(outs, q) if pydesc.ENABLED else None
        surv = pydesc.RawSurv(outs, M, U2, scan[0]); exact = []
        for line in scan[1]:
            f = line.split()
            a, nu = int(f[1]), int(f[2]); eps = tuple(int(x) for x in f[3:3 + q]); b, c = int(f[3 + q]), int(f[4 + q]); Y = int(f[5 + q])
            exact.append((a, nu, eps, b, c, Y))
        sols = set()
        for a, nu, eps, b, c, Y in exact:
            fct = factor237(Y)
            if fct and fct[0] == a and Coset((b, c), tuple(U2[0]), tuple(U2[1])).contains(fct[1], fct[2]): sols.add(Y)
        r = solve_equation(s, M, [], verbose=False, l12=surv, l12_n_in=stats['patterns'], presolved=sols, lift_fn=make_lift(M, workdir, mode, rec))
        res[mode] = dict(levels=[(int(Lv), n, sv) for (Lv, ps, n, sv, cls, el) in r['levels']], open=len(r['open']), solutions=sorted(r['solutions']), per_level=rec)
        print(mode, 'levels', res[mode]['levels'], 'open', res[mode]['open'], flush=True)
    json.dump(res, open(f'results/{tag}.json', 'w'), default=str)

if __name__ == '__main__':
    main(int(sys.argv[1]), [int(x) for x in sys.argv[2].split(',')], int(sys.argv[3]))
