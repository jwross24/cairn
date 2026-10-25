#!/usr/bin/env python3
"""
d5b_depth1.py — depth-1 (Lemma C, reduced exact verdict) survival over a large sample of anchored census patterns.
Usage: VERTS=<verts.json> python3 d5b_depth1.py <vertex index> <hits file> <n_hits> <cap per hit> [seed]
Per pattern: words = copy choices of the low classes e < a+9 (one digit value or none per class) passing the K = 96
window (cut_small, exact by verify_reduction).  Reports survivors / patterns, by k and by wrap.
"""
import sys, os, json, time, itertools, random, collections
sys.path.insert(0, '/home/claude/tier0'); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import anchorlib as AL
from sandwich_lite import cut_small
from lattice import Coset
from descent import v2
import deepcut as DC, classify_open as C

if __name__ == "__main__":
    vi, hits, nh, cap = int(sys.argv[1]), sys.argv[2], int(sys.argv[3]), int(sys.argv[4]); seed = int(sys.argv[5]) if len(sys.argv) > 5 else 1
    verts = [json.loads(l) for l in open(os.environ.get('VERTS', '/home/claude/scouts/tierC.txt'))]; v = verts[vi]; A, B, Cc = v['a'], v['b'], v['c']
    rows = [tuple(map(int, l.split())) for l in open(hits)]
    random.seed(seed); picks = random.choices(rows, weights=[r[4] for r in rows], k=nh)
    t0 = time.time(); cvl = AL.count_vectors(A, B, Cc); Lam96 = DC.kernel_lattice(); base = (10 ** 96 - 1) // 9
    npat = nsurv = 0; byk = collections.Counter(); byk_s = collections.Counter(); byw = collections.Counter(); byw_s = collections.Counter(); surv_list = []
    for hi, (y, k, nu, Wm, cnt) in enumerate(picks):
        fct = C.factor237(y); a = fct[0]; co0 = Coset((fct[1], fct[2]), Lam96.u1, Lam96.u2)
        U = y + k * base
        n, reps = AL.representations(U, nu, A, B, Cc, Wm, cvl, cap=cap)
        mod = 5 ** 6 * 2 ** (a + 10)
        for (M, De) in reps:
            De = list(De); bycls = collections.defaultdict(list)
            for d, e in De: bycls[e].append(d)
            low = sorted(e for e in bycls if e < a + 9)
            choice_lists = [[0] + sorted(set(d - 1 for d in bycls[e])) for e in low]
            surv = 0
            for ch in itertools.product(*choice_lists):
                L = base + sum(m * 10 ** e for e, m in zip(low, ch) if m)
                Lr = L % mod
                if v2(Lr) != a: continue
                if cut_small(co0, a, Lr) is not None: surv += 1
            npat += 1; byk[len(De)] += 1; byw[k] += 1
            if surv: nsurv += 1; byk_s[len(De)] += 1; byw_s[k] += 1; surv_list.append((y, k, nu, Wm, len(De), surv))
        if (hi + 1) % 50 == 0: print(f"  {hi+1} hits, {npat} patterns, {nsurv} with surviving words [{time.time()-t0:.0f}s]", flush=True)
    print(f"RESULT vertex {v['s']}: {npat} patterns from {nh} hits (cap {cap}), {nsurv} survive depth 1 ({nsurv/max(1,npat):.4f}); by k: {sorted((k, byk_s[k], byk[k]) for k in byk)}; by wrap: {sorted((w, byw_s[w], byw[w]) for w in byw)} [{time.time()-t0:.0f}s]")
    for s in surv_list[:40]: print("  SURV", s)
