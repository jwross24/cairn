"""cmp_c.py <pkl>... : C batch vs Python classify/ten_adic_K/descend per survivor"""
import sys, os, pickle, time
sys.path.insert(0, '/private/tmp/persist-pydesc/prod'); sys.path.insert(1, os.environ.get('PYDESC_DIR', '/private/tmp/persist-pydesc/work'))
from collections import defaultdict
import tier0v2
from tier0v2 import classify, ten_adic_K
from descent import descend
from lattice import Coset
import pydesc

def ref(co, a, D, nu, eps, L, M, kcap, do_descent=True):
    kind, val = classify(co, a, D, nu, eps, L, M, kcap)
    sols = set()
    if kind.startswith('SOLUTION'): sols.add(val)
    if kind in ('OPEN', 'SOLUTION+OPEN'):
        K = ten_adic_K(co, kcap, a)
        if K >= 1 and do_descent:
            st, s2 = descend(a, D, eps, nu, co, L, M, K, kcap)
            sols |= s2
            kind = 'OPEN' if st == 'OPEN' else 'RESOLVED(descent)'
        else:
            kind = 'OPEN'
    return kind, sols

tot = bad = fb = 0; tref = tc = 0.0
for pk in sys.argv[1:]:
    rec = pickle.load(open(pk, 'rb'))
    groups = defaultdict(list)
    KC = int(os.environ.get('KCAP', '0'))
    for r in rec: groups[(r[6], r[7], KC or r[8])].append(r)
    for (D, L, kcap), rs in groups.items():
        surv = [(a, nu, eps, Coset(v0, u1, u2)) for (a, nu, eps, v0, u1, u2, _, _, _) in rs]
        def safe(co, a, D, nu, eps, L, kcap):
            try: return ref(co, a, D, nu, eps, L, D, kcap)
            except Exception as ex: return ('EXC', type(ex).__name__)
        import hashlib
        ck = f"/private/tmp/persist-pydesc/cap/refcache_{hashlib.md5(pk.encode() + repr((D, L, kcap, len(rs))).encode()).hexdigest()}.pkl"
        t = time.perf_counter()
        if os.path.exists(ck): res = pickle.load(open(ck, 'rb'))
        else:
            res = [safe(co, a, D, nu, eps, L, kcap) for (a, nu, eps, co) in surv]
            pickle.dump(res, open(ck, 'wb'))
        tref += time.perf_counter() - t
        t = time.perf_counter(); out = pydesc.classify_batch(surv, D, L, kcap, True); tc += time.perf_counter() - t
        for i, ((kind, sols), (code, csols)) in enumerate(zip(res, out)):
            tot += 1
            if code == pydesc.CODE_FALLBACK: fb += 1; continue
            if kind == 'EXC':
                bad += 1; print('C answered where Python raised', sols, surv[i][:3], code); continue
            if pydesc.KIND[code] != kind or set(csols) != sols:
                bad += 1
                if bad <= 5: print('MISMATCH', pk, surv[i][:3], kind, sols, code, csols)
print(f'{tot} survivors, {bad} mismatches, {fb} fallbacks; python {tref:.2f}s, C batch {tc:.2f}s, ratio {tref/max(tc,1e-9):.1f}x')
sys.exit(1 if bad else 0)
