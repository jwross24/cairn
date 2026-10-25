#!/usr/bin/env python3
"""anchorfirst.py -- anchor-first census of the predicted level-96 open sets of the six Tier-C vertices.

Pipeline (see RESULT-anchorfirst.md):
  1. anchor candidates: S-units y = 2^a 3^b 7^c, a <= 60, y < 10^98   (609,796 numbers)
  2. (y, k) scan: U = y + k R96 must satisfy the digit-sum identity  D(U mod 10^96) + 10 q <= 95 + Wmax
     (q = U div 10^96), for every k in [-9, 224]  -> 1,109,618 pairs (exact necessary condition)
  3. exact phase 1 (C, anchor_dp.c): for each pair and each nu, is V = U - R_nu a sum of (d-1) 10^e over a digit
     multiset of product s?  Exponent DP; run on a uniform random sample of pairs (the full set is ~5 CPU-h/vertex)
  4. phase 2 (Python, anchorlib.representations): exact count of patterns per (y,k,nu,W) hit, explicit
     representations for a subsample, each verified by the integer identity
  5. Lemma C depth-1 verdict (sandwich_lite.depth1_reduced, exact) on the representation subsample
  6. (anchorfirst_sandwich.py, run afterwards or via --sandwich) the tier0 Baker-lattice sandwich (deepcut.deep_cut
     depth <= 6, <= 1e6 cases) + exact reduced depth-1 verdict on sampled patterns, the task's cheap-filter rejection
     rates and the classify_open.exact_identity benchmark
Usage: python3 anchorfirst.py [--sample 3000] [--seed 7] [--phase2 40] [--reps 12] [--sandwich]
"""
import sys, os, time, json, random, pickle, collections, math, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import anchorlib as L
import sandwich_lite as SL

def arg(name, default):
    return type(default)(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default

SAMPLE = arg('--sample', 3000); SEED = arg('--seed', 7); NPH2 = arg('--phase2', 40); NREPS = arg('--reps', 12)
SC = HERE
T0 = time.time()
log = open(os.path.join(HERE, 'anchorfirst-run.log'), 'a')
def say(*a):
    s = ' '.join(str(x) for x in a); print(s, flush=True); log.write(s + '\n'); log.flush()

# ------------------------------------------------------------------ 1. S-units
LIM = 10 ** 98
ys = []
p2 = 1
for a in range(0, 61):
    p23 = p2
    for b in range(0, 400):
        if p23 >= LIM: break
        y = p23
        for c in range(0, 200):
            if y >= LIM: break
            ys.append((y, a, b, c)); y *= 7
        p23 *= 3
    p2 *= 2
say(f"S-units y=2^a3^b7^c < 1e98, a<=60: {len(ys)}  [{time.time()-T0:.0f}s]")

# ------------------------------------------------------------------ 2. (y,k) scan
verts = [json.loads(l) for l in open('/home/claude/scouts/tierB13.txt')]
WMAX = max(sum(d - 1 for d in M) for v in verts for M in v['multisets'])
THR = 95 + WMAX
R96, T96 = L.R96, L.T96
DS = [sum(map(int, str(i))) for i in range(1000)]
def dsum(x): return sum(map(int, str(x)))
cache = os.path.join(HERE, 'pairs.txt')
if os.path.exists(cache):
    pairs = [tuple(map(int, l.split())) for l in open(cache)]
    say(f"(y,k) pairs loaded from cache: {len(pairs)}")
else:
    pairs = []
    for (y, a, b, c) in ys:
        if 1000 <= y < 10 ** 94:
            for r in range(9):
                X = y + r * R96; DX = dsum(X); t = X % 1000; Dt = DS[t]
                for m in range(0, 25):
                    if 10 * m > THR: break
                    D = DX - Dt + DS[t - m] if t >= m else dsum(X - m)
                    if D + 10 * m <= THR: pairs.append((y, 9 * m + r, D + 10 * m))
        else:
            for k in range(-9 if y >= R96 else 0, 225):
                U = y + k * R96
                if U < 0: continue
                q, low = divmod(U, T96); D = dsum(low)
                if D + 10 * q <= THR: pairs.append((y, k, D + 10 * q))
    with open(cache, 'w') as f:
        for y, k, Dq in pairs: f.write(f"{y} {k} {Dq}\n")
    say(f"(y,k) pairs passing the digit-sum filter (k in [-9,224]): {len(pairs)}  [{time.time()-T0:.0f}s]")
NPAIRS = len(pairs)
byk = collections.Counter(k for y, k, _ in pairs)
say("  by wrap count k (top 12):", sorted(byk.items(), key=lambda t: -t[1])[:12])
say("  k>=2 with k mod 9 >= 2 (r>=2):", sum(n for k, n in byk.items() if k % 9 >= 2 and k >= 2), " negative k:", sum(n for k, n in byk.items() if k < 0))

# ------------------------------------------------------------------ 3. phase 1 on a uniform sample
random.seed(SEED)
sample = random.sample(pairs, SAMPLE) if SAMPLE < NPAIRS else list(pairs)
pf = os.path.join(SC, f'pairs_sample{SAMPLE}_{SEED}.txt')
with open(pf, 'w') as f:
    for y, k, _ in sample: f.write(f"{y} {k}\n")
binary = os.path.join(HERE, 'anchor_dp')
if not os.path.exists(binary):
    subprocess.run(['gcc', '-O2', '-o', binary, os.path.join(HERE, 'anchor_dp.c')], check=True)
yinfo = {y: (a, b, c) for (y, a, b, c) in ys}
results = {}
for vi, v in enumerate(verts):
    A, B, C = v['a'], v['b'], v['c']; Ms = v['multisets']
    Wset = set(sum(d - 1 for d in M) for M in Ms); kmax = max(len(M) for M in Ms)
    tab = os.path.join(SC, f'table_v{vi}.txt'); cvl = L.write_table(tab, A, B, C, Wset, kmax)
    # completeness of the multiset list
    F = set(L.all_factorizations(A, B, C)); G = set(tuple(sorted(M)) for M in Ms)
    assert F == G, "tierC multiset list is not the full factorization list"
    hitfile = os.path.join(SC, f'hits_v{vi}_sample{SAMPLE}_{SEED}.txt')
    t1 = time.time()
    if os.path.exists(hitfile) and os.path.getsize(hitfile) > 0:
        hits = [tuple(map(int, l.split())) for l in open(hitfile)]; err = 'cached'
    else:
        hits, err = L.run_dp(tab, pf, binary)
        with open(hitfile, 'w') as f:
            for h in hits: f.write(' '.join(map(str, h)) + '\n')
    dt = time.time() - t1
    pairs_hit = sorted(set((y, k) for y, k, nu, W, n in hits))
    say(f"\n== vertex {v['s']} = 2^{A}3^{B}7^{C}: {len(Ms)} multisets, k in [{min(len(M) for M in Ms)},{kmax}], W in [{min(Wset)},{max(Wset)}]")
    say(f"   phase 1 on {len(sample)} sampled pairs: {err}; {len(pairs_hit)} anchored (y,k) pairs, {len(hits)} (y,k,nu,W) hits  [{dt:.0f}s]")
    frac = len(pairs_hit) / len(sample)
    se = math.sqrt(frac * (1 - frac) / len(sample))
    est_pairs = frac * NPAIRS; est_hits = len(hits) / len(sample) * NPAIRS
    say(f"   anchored-pair fraction {frac:.4f} +- {se:.4f}  -> predicted anchored (y,k) pairs ~ {est_pairs:.0f} (+- {se*NPAIRS:.0f}), (y,k,nu,W) hits ~ {est_hits:.0f}")
    ka = collections.Counter(k for y, k in pairs_hit); aa = collections.Counter(yinfo[y][0] for y, k in pairs_hit)
    na = collections.Counter(len(str(y)) for y, k in pairs_hit); nua = collections.Counter(nu for y, k, nu, W, n in hits)
    Wa = collections.Counter(W for y, k, nu, W, n in hits)
    say(f"   wrap k of anchored pairs: {sorted(ka.items())}")
    n9 = sum(n for k, n in ka.items() if 0 <= k <= 9); n0 = ka.get(0, 0)
    say(f"   anchored pairs with k<=9 (the spec's range): {n9} ({n9/len(sample)*NPAIRS:.0f} predicted); with k=0: {n0}; sampled pairs with k<=9: {sum(1 for y,k,_ in sample if 0<=k<=9)}")
    say(f"   2-adic a of anchors: {sorted(aa.items())}")
    say(f"   digits of y: {sorted(na.items())}")
    say(f"   nu of hits (top 10): {sorted(nua.items(), key=lambda t:-t[1])[:10]};  W of hits: {sorted(Wa.items())}")
    # ------------------------------------------------------------- 4. pattern counts (exact, from the C DP) + explicit reps
    counts = sorted(n for y, k, nu, W, n in hits)
    tot = sum(counts); gm = math.exp(sum(math.log(c) for c in counts) / len(counts))
    say(f"   patterns per (y,k,nu,W) hit (exact counts, all {len(counts)} hits): min {counts[0]}, median {counts[len(counts)//2]}, "
        f"geo-mean {gm:.1f}, mean {tot/len(counts):.1f}, max {counts[-1]}; total over the sample {tot}")
    est_pat = tot / len(sample) * NPAIRS
    big = sorted(hits, key=lambda h: -h[4])[:3]
    say(f"   -> predicted anchored patterns at level 96 ~ {est_pat:.3e}  (heavy-tailed: the 3 largest hits {[(h[0],h[1],h[2],h[4]) for h in big]} carry {sum(h[4] for h in big)/tot:.0%} of the sample total)")
    perpair = collections.Counter()
    for y, k, nu, W, n in hits: perpair[(y, k)] += n
    pp = sorted(perpair.values())
    say(f"   patterns per anchored (y,k) pair: median {pp[len(pp)//2]}, mean {sum(pp)/len(pp):.0f}, max {pp[-1]}")
    random.seed(SEED + vi)
    small = [h for h in hits if h[4] <= 500]
    sub = random.sample(small, min(NPH2, len(small)))
    t2 = time.time(); reps_pool = []
    for (y, k, nu, W, n) in sub:
        if time.time() - t2 > 45: break
        U = y + k * R96
        n2, reps = L.representations(U, nu, A, B, C, W, cvl, cap=3)
        if n2 < 0: continue
        assert n2 == n and all(L.check_representation(U, nu, r) for r in reps), (y, k, nu, W, n, n2)
        reps_pool.append((y, k, nu, W, n, reps))
    say(f"   phase 2 (Python) on {len(reps_pool)} hits with <= 3000 patterns: counts agree with the C DP, every explicit representation verified by the integer identity  [{time.time()-t2:.0f}s]")
    distinctM = set(r[0] for *_, reps in reps_pool for r in reps)
    say(f"   distinct multisets M among the {sum(len(r[-1]) for r in reps_pool)} explicit representations: {len(distinctM)} (of {len(Ms)})")
    # ------------------------------------------------------------- 5. Lemma C depth 1 on representations
    assert SL.verify_reduction(0)[0]
    Lm = SL.lam(); ver = collections.Counter(); t3 = time.time(); lines = []
    random.seed(SEED + 100 + vi)
    pool = [(y, k, nu, W, r) for (y, k, nu, W, n, reps) in reps_pool for r in reps]
    for (y, k, nu, W, (M, placed)) in random.sample(pool, min(NREPS, len(pool))):
        a, b, c = yinfo[y]
        assert SL.verify_reduction(a)[0]
        from lattice import Coset
        co0 = Coset((b, c), Lm.u1, Lm.u2)
        rep = (nu, list(placed))
        kdig = len(M); logU = math.log10(SL.baker_upper_bound(kdig, a))
        r1 = SL.depth1_reduced(co0, a, rep, maxchoices=20000)
        ncls = len(set(e for d, e in placed)); nlow = len(set(e for d, e in placed if e < a + 9))
        full = ''
        if ncls <= 11:
            r2 = SL.depth1_full(co0, a, rep, 4000); full = f" full-deep_cut={r2[0]}"
            assert r2[0] == 'BUDGET' or r2[0] == r1[0]
        ver[r1[0]] += 1
        lines.append(f"      y={y} (a={a}) k={k} nu={nu} M={''.join(map(str,M))} (k={kdig}, classes={ncls}, low={nlow}) log10 G(k,a)={logU:.0f}: depth-1 {r1}{full}")
    say(f"   Lemma C depth 1 on {sum(ver.values())} representations: {dict(ver)}  [{time.time()-t3:.0f}s]")
    for l in lines: say(l)
    results[v['s']] = dict(A=A, B=B, C=C, nM=len(Ms), kmin=min(len(M) for M in Ms), kmax=kmax, sample=len(sample), pairs_hit=len(pairs_hit),
                           hits=len(hits), frac=frac, se=se, est_pairs=est_pairs, est_hits=est_hits, counts=counts, est_pat=est_pat, tot=tot, gm=gm, ver=dict(ver), ka=dict(ka), aa=dict(aa), na=dict(na), Wa=dict(Wa), dt=dt, lines=lines)
pickle.dump(results, open(os.path.join(SC, f'results_sample{SAMPLE}_{SEED}.pkl'), 'wb'))
say(f"\ntotal wall time {time.time()-T0:.0f}s")
if '--sandwich' in sys.argv:
    subprocess.run([sys.executable, os.path.join(HERE, 'anchorfirst_sandwich.py'), '--sample', str(SAMPLE), '--seed', str(SEED), '--nreps', '6', '--tcap', '12'], check=False)
