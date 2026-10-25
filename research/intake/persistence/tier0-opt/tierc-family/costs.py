import sys
sys.dont_write_bytecode = True
sys.path.insert(0, '/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/tierc-family')
import random, time, json, math
from famlib import *
from famtest import *
from validate import load_cases
from refcheck import key_of


def timeit(f, n=1):
    t = time.perf_counter()
    for _ in range(n):
        out = f()
    return (time.perf_counter() - t) / n, out


if __name__ == '__main__':
    rng = random.Random(77)
    lam = build_lambdas()
    cases = load_cases()
    bykey = {}
    for c in cases:
        bykey.setdefault(len(c[1]), []).append(c)
    sample = []
    for k, lst in sorted(bykey.items()):
        sample += rng.sample(lst, min(len(lst), 12))
    rows = []
    unit96 = []
    unit_hi = []
    for (s, M, a, y) in sample:
        t_reps, reps = timeit(lambda: reps_wrap0(M, y))
        n_words = n_pre = n_valid = 0
        t_fam = 0.0
        t_fam_c = 0.0
        valid_words = []
        for nu, De in reps:
            g = groups_of(De)
            tt, (res, ns, mu) = timeit(lambda: family_counts(a, y, De, COND, compress=False))
            t_fam += tt
            tt2, _ = timeit(lambda: family_counts(a, y, De, COND, compress=True))
            t_fam_c += tt2
            sums = subset_sums(g)
            n_words += len(sums)
            base = R(96) - y
            m96 = modulus(a, 96)
            for sm in sums:
                w = R(96) + sm
                if w % (1 << a) == 0 and ((w >> a) & 1) and w % 5:
                    n_pre += 1
                if (base + sm) % m96 == 0:
                    n_valid += 1
                    if len(valid_words) < 3:
                        valid_words.append(sm)
            if len(unit96) < 60:
                for sm in sums[:2]:
                    w = R(96) + sm
                    if w % (1 << a) == 0 and ((w >> a) & 1) and w % 5:
                        dt, _ = timeit(lambda: ref_alive(a, y, w, 96, lam))
                        unit96.append(dt)
        for sm in valid_words:
            dt, _ = timeit(lambda: [ref_alive(a, y, R(L) + sm, L, lam) for L in (192, 384, 480)])
            unit_hi.append(dt)
        rows.append(dict(k=len(M), a=a, reps=len(reps), words=n_words, pre=n_pre, valid=n_valid, t_reps=t_reps, t_fam=t_fam, t_fam_c=t_fam_c))
    c96 = sum(unit96) / len(unit96)
    chi = sum(unit_hi) / len(unit_hi)
    print('unit costs: ref window+lattice at level 96 per prefiltered word', c96, 's (n=%d); levels 192+384+480 per valid word' % len(unit96), chi, 's (n=%d)' % len(unit_hi))
    ratios = []
    ratios_with_reps = []
    for r in rows:
        ref = r['pre'] * c96 + r['valid'] * chi
        r['ref_est'] = ref
        ratios.append(ref / r['t_fam'] if r['t_fam'] > 0 else float('nan'))
        ratios_with_reps.append((r['t_reps'] + ref) / (r['t_reps'] + r['t_fam']))
    json.dump(dict(rows=rows, c96=c96, chi=chi), open(OUT + 'costs.json', 'w'))

    def gmean(x):
        x = [v for v in x if v == v and v > 0]
        return math.exp(sum(math.log(v) for v in x) / len(x))

    def boot(x, n=2000):
        g = []
        for _ in range(n):
            b = [x[rng.randrange(len(x))] for _ in x]
            g.append(gmean(b))
        g.sort()
        return g[int(0.025 * n)], g[int(0.975 * n)]

    print('patterns', len(rows))
    print('geometric mean ratio (rep DP excluded)', gmean(ratios), 'CI', boot(ratios))
    print('geometric mean ratio (rep DP included)', gmean(ratios_with_reps), 'CI', boot(ratios_with_reps))
    tot_ref = sum(r['ref_est'] for r in rows)
    tot_fam = sum(r['t_fam'] for r in rows)
    tot_reps = sum(r['t_reps'] for r in rows)
    print('totals: ref est', tot_ref, 's; family', tot_fam, 's; rep DP', tot_reps, 's; ratio of totals', tot_ref / tot_fam, 'with DP', (tot_ref + tot_reps) / (tot_fam + tot_reps))
    for lo, hi in ((5, 8), (9, 11), (12, 14), (15, 18)):
        sub = [r for r in rows if lo <= r['k'] <= hi]
        if sub:
            print('k', lo, hi, 'n', len(sub), 'gmean ratio', gmean([r['ref_est'] / r['t_fam'] for r in sub if r['t_fam'] > 0]), 'median words', sorted(r['words'] for r in sub)[len(sub) // 2], 'median t_reps', sorted(r['t_reps'] for r in sub)[len(sub) // 2])
