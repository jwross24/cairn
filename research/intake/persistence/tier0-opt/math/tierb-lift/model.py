import sys, os, json, glob, math
from collections import Counter, defaultdict
from math import comb
HERE = os.path.dirname(os.path.abspath(__file__))
T0 = os.path.normpath(os.path.join(HERE, '..', '..', '..', 'tier0'))
sys.path.insert(0, T0)
sys.dont_write_bytecode = True
from tier0v2 import multisets, two_adic_bound

TIER_B = [71663616, 226492416, 1194891264, 169869312, 4182119424, 1792336896, 13884223438848,
          2113929216, 1811939328, 11329339392, 4444263936, 3699376128, 1783627776]

SETS24 = [(2, 1 / 36), (34, 1 / 4), (68, 1 / 144), (111100, 1.111e-3), (111100, 1.543e-5)]
SETS48 = [(2, 1 / 8), (122549, 2.083e-2), (245098, 2.604e-3)]

def env(name, default):
    return float(os.environ.get(name, default))

def npat(M):
    p = 12
    for d, k in Counter(M).items():
        p *= comb(12 + k - 1, k)
    return p

def fit(xs, ys):
    n = len(xs); mx = sum(xs) / n; my = sum(ys) / n
    b = sum((a - mx) * (c - my) for a, c in zip(xs, ys)) / sum((a - mx) ** 2 for a in xs)
    return my - b * mx, b

def load_h12(minpat):
    S = defaultdict(lambda: defaultdict(float))
    for f in glob.glob(os.path.join(HERE, 'logs', 'h12_*.jsonl')):
        for l in open(f):
            r = json.loads(l)
            if r['npat'] < minpat or 'lift24' not in r:
                continue
            d = S[r['k']]
            d['n'] += 1; d['npat'] += r['npat']; d['s12'] += r['l12_n']
            d['par'] += r['lift24']['parents']; d['ch24'] += r['lift24']['children']; d['s24'] += r['lift24']['survivors']
            if 'lift48' in r:
                d['par48'] += r['lift48']['parents']; d['ch48'] += r['lift48']['children']
    return S

def laws(minpat):
    S = load_h12(minpat)
    ks = sorted(k for k in S if S[k]['ch24'] > 0)
    L = {}
    L['par'] = fit(ks, [math.log(S[k]['par'] / S[k]['npat']) for k in ks])
    L['C24'] = fit(ks, [math.log(S[k]['ch24'] / S[k]['par']) for k in ks])
    k48 = [k for k in ks if S[k]['ch48'] > 0 and S[k]['par48'] > 0]
    L['par48'] = fit(k48, [math.log(S[k]['par48'] / S[k]['npat']) for k in k48])
    L['C48'] = fit(k48, [math.log(S[k]['ch48'] / S[k]['par48']) for k in k48])
    L['ks'] = ks; L['k48'] = k48
    return L, S

def ev(law, k):
    return math.exp(law[0] + law[1] * k)

def join_cost(C, sets, wp, wb, wc):
    best = 1e300
    for K, acc in sets:
        nA = max(1.0, math.sqrt(C / 2 / K))
        nB = C / 2 / nA
        best = min(best, wp * 2 * nA * K + wb * (nA + nB) + wc * C * acc)
    return best

def dual12_steps(M):
    A = int(os.environ.get('A_ASSUME', 40)); W = sum(d - 1 for d in M)
    Mm = W * 1e11 / 5291005291.0
    st = 0.0
    for nu in range(12):
        nb = 9900 if (nu + W) % 3 == 0 else 1
        st += (A + 1) * nb * (900 + 6) * Mm / 63
    return st

if __name__ == '__main__':
    t_pat12 = env('T_PAT12', 5.0e-9)
    t_child24 = env('T_CHILD24', 30e-9)
    t_child48 = env('T_CHILD48', 1.0e-6)
    wp, wb, wc24, wc48 = env('W_PROBE', 15e-9), env('W_BUILD', 15e-9), env('W_CAND24', 100e-9), env('W_CAND48', 2e-6)
    t_step = env('T_DUAL12_STEP', 30e-9)
    L, S = laws(env('MINPAT', 1e8))
    for name in ('par', 'C24', 'par48', 'C48'):
        print(name, 'a=%.3f b=%.4f x%.3f per digit' % (L[name][0], L[name][1], math.exp(L[name][1])))
    print('fit k24', L['ks'], 'fit k48', L['k48'])
    tot = defaultdict(float)
    print('vertex k_max N12 | core-days ref: lvl12 lift24 lift48 | mixed: dual12 join24 join48 | C24 C48 at k_max')
    for s in TIER_B:
        N12 = 0; kmax = 0; d = defaultdict(float)
        for M in multisets(s):
            M = tuple(sorted(M)); n = npat(M); k = len(M); kmax = max(kmax, k); N12 += n
            par = n * ev(L['par'], k); C24 = ev(L['C24'], k)
            par48 = n * ev(L['par48'], k); C48 = ev(L['C48'], k)
            d['r12'] += n * t_pat12
            d['r24'] += par * C24 * t_child24
            d['r48'] += par48 * C48 * t_child48
            d['d12'] += dual12_steps(M) * t_step + 1e-7 * par
            d['j24'] += par * join_cost(C24, SETS24, wp, wb, wc24)
            d['j48'] += par48 * C48 * t_child48 / env('J48_GAIN', 3)
        D = 86400.0
        print(f"{s:>15d} {kmax:3d} {N12:.2e} | {d['r12']/D:9.3g} {d['r24']/D:9.3g} {d['r48']/D:9.3g} | {d['d12']/D:9.3g} {d['j24']/D:9.3g} {d['j48']/D:9.3g} | {ev(L['C24'], kmax):.3g} {ev(L['C48'], kmax):.3g}")
        for key in d: tot[key] += d[key]
    D = 86400.0
    ref = (tot['r12'] + tot['r24'] + tot['r48']) / D; mix = (tot['d12'] + tot['j24'] + tot['j48']) / D
    print('TOTAL core-days: reference %.3g (lvl12 %.3g, lift24 %.3g, lift48 %.3g); mixed %.3g (dual12 %.3g, join24 %.3g, join48 %.3g)' % (
        ref, tot['r12'] / D, tot['r24'] / D, tot['r48'] / D, mix, tot['d12'] / D, tot['j24'] / D, tot['j48'] / D))
    print('Mac-days at 2 cores: reference %.3g mixed %.3g' % (ref / 2, mix / 2))
