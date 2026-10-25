import sys, os, json, glob, math, random
from collections import Counter, defaultdict
from math import comb
HERE = os.path.dirname(os.path.abspath(__file__))
T0 = os.path.normpath(os.path.join(HERE, '..', '..', '..', 'tier0')); sys.path.insert(0, T0); sys.dont_write_bytecode = True
from tier0v2 import multisets
import numpy as np

TIER_B = [71663616, 226492416, 1194891264, 169869312, 4182119424, 1792336896, 13884223438848,
          2113929216, 1811939328, 11329339392, 4444263936, 3699376128, 1783627776]
M = json.load(open(os.path.join(HERE, 'measured.json')))

def npat(Ms):
    p = 12
    for d, k in Counter(Ms).items(): p *= comb(12 + k - 1, k)
    return p

def load_rows(minpat):
    rows = []
    for f in glob.glob(os.path.join(HERE, '..', 'tierb-lift', 'logs', 'h12_*.jsonl')):
        for l in open(f):
            r = json.loads(l)
            if r['npat'] >= minpat and 'lift24' in r: rows.append(r)
    return rows

def fit_xy(xs, ys):
    n = len(xs); mx = sum(xs) / n; my = sum(ys) / n
    b = sum((a - mx) * (c - my) for a, c in zip(xs, ys)) / sum((a - mx) ** 2 for a in xs)
    return my - b * mx, b

def laws_from(rows):
    S = defaultdict(lambda: defaultdict(float))
    for r in rows:
        d = S[r['k']]; d['npat'] += r['npat']; d['s12'] += r['l12_n']; d['par'] += r['lift24']['parents']; d['ch24'] += r['lift24']['children']
        if 'lift48' in r: d['par48'] += r['lift48']['parents']; d['ch48'] += r['lift48']['children']
    ks = sorted(k for k in S if S[k]['ch24'] > 0 and S[k]['par'] > 0 and S[k]['s12'] > 0)
    L = {}
    L['s12'] = fit_xy(ks, [math.log(S[k]['s12'] / S[k]['npat']) for k in ks])
    L['par'] = fit_xy(ks, [math.log(S[k]['par'] / S[k]['npat']) for k in ks])
    L['C24'] = fit_xy(ks, [math.log(S[k]['ch24'] / S[k]['par']) for k in ks])
    k48 = [k for k in ks if S[k]['ch48'] > 0 and S[k]['par48'] > 0]
    L['par48'] = fit_xy(k48, [math.log(S[k]['par48'] / S[k]['npat']) for k in k48])
    L['C48'] = fit_xy(k48, [math.log(S[k]['ch48'] / S[k]['par48']) for k in k48])
    return L

def ev(l, k): return math.exp(l[0] + l[1] * k)

MS = {}
def vertex_multisets(s):
    if s not in MS:
        MS[s] = [(npat(tuple(sorted(m))), len(m)) for m in multisets(s)]
    return MS[s]

def totals(L):
    out = {}
    for s in TIER_B:
        t = Counter()
        for n, k in vertex_multisets(s):
            par = n * ev(L['par'], k); par48 = n * ev(L['par48'], k)
            t['N12'] += n; t['S12'] += n * ev(L['s12'], k); t['P24'] += par; t['CH24'] += par * ev(L['C24'], k)
            t['P48'] += par48; t['CH48'] += par48 * ev(L['C48'], k)
            t['sqrtC24'] += par * 2 * math.sqrt(ev(L['C24'], k)); t['sqrtC48'] += par48 * 2 * math.sqrt(ev(L['C48'], k))
        out[s] = t
    return out

def gpu_cost(T, scale, eff, cfg):
    tot = Counter()
    for s, t in T.items():
        r = {}
        r['h12'] = t['N12'] / (M['lvl12_patterns_per_s_m5'] * scale * eff) / 3600
        r['h24'] = t['CH24'] / (M['pf24_children_per_s_m5'] * scale * eff) / 3600
        r['h48'] = t['CH48'] / (M['pf48_children_per_s_m5'] * scale * eff) / 3600
        r['host_core_s'] = t['CH24'] * M['cand_frac24'] * M['cand_ns24'] * 1e-9 + t['CH48'] * M['cand_frac48'] * M['cand_ns48'] * 1e-9 + t['S12'] * cfg['stream_ns'] * 1e-9 + (t['P24'] + t['P48']) * M['prep_a_s'] + (t['sqrtC24'] + t['sqrtC48']) * M['prep_b_s']
        r['host_core_s_nostream'] = r['host_core_s'] - t['S12'] * cfg['stream_ns'] * 1e-9
        r['pcie_bytes'] = t['P24'] * 64 + 8 * t['sqrtC24'] + t['P48'] * 64 + 8 * t['sqrtC48'] + 16 * (t['CH24'] * M['cand_frac24'] + t['CH48'] * M['cand_frac48'])
        for k, v in r.items(): tot[k] += v
        tot['S12'] += t['S12']; tot['N12'] += t['N12']; tot['P24'] += t['P24']; tot['CH24'] += t['CH24']; tot['CH48'] += t['CH48']; tot['P48'] += t['P48']
        tot['per_vertex_%d' % s] = r['h12'] + r['h24'] + r['h48']
    return tot

if __name__ == '__main__':
    rows = load_rows(float(os.environ.get('MINPAT', 1e8)))
    L0 = laws_from(rows)
    print('rows', len(rows), {k: 'x%.3f/digit' % math.exp(v[1]) for k, v in L0.items()})
    T0v = totals(L0)
    GR = dict(imad_m5=M['imad_per_s_m5'], h100=16.7e12)
    scale = GR['h100'] / GR['imad_m5']
    cfg = dict(stream_ns=float(os.environ.get('STREAM_NS', 3000)))
    print('H100/M5 IMAD scale %.1f' % scale)
    for eff in (1.0, 0.6, 0.4):
        c = gpu_cost(T0v, scale, eff, cfg)
        gh = c['h12'] + c['h24'] + c['h48']
        print('eff %.1f: GPU-h level12 %.0f lift24 %.0f lift48 %.0f total %.0f | host core-days %.0f | PCIe %.2e B -> %.2f GPU-h at 25 GB/s' % (eff, c['h12'], c['h24'], c['h48'], gh, c['host_core_s'] / 86400, c['pcie_bytes'], c['pcie_bytes'] / 25e9 / 3600))
    random.seed(1)
    res = []
    for b in range(int(os.environ.get('NBOOT', 200))):
        rs = [random.choice(rows) for _ in rows]
        try: Lb = laws_from(rs)
        except Exception: continue
        Tb = totals(Lb); c = gpu_cost(Tb, scale, 0.6, cfg)
        res.append((c['h12'], c['h24'], c['h48'], c['host_core_s'] / 86400))
    a = np.array(res)
    for i, nm in enumerate(('level12', 'lift24', 'lift48', 'host core-days')):
        print('bootstrap (law refit, eff 0.6) %-14s p5 %.3g p50 %.3g p95 %.3g' % (nm, *np.percentile(a[:, i], [5, 50, 95])))
    tot = a[:, :3].sum(axis=1); print('bootstrap total GPU-h p5 %.3g p50 %.3g p95 %.3g' % tuple(np.percentile(tot, [5, 50, 95])))
    c = gpu_cost(T0v, scale, 0.6, cfg)
    print('per-vertex GPU-h at eff 0.6 (law point estimate):')
    for s in TIER_B: print('  %15d %.1f' % (s, c['per_vertex_%d' % s]))
    json.dump(dict(laws={k: list(v) for k, v in L0.items()}, totals={str(s): dict(T0v[s]) for s in TIER_B}), open(os.path.join(HERE, 'logs', 'model_cuda_totals.json'), 'w'))
