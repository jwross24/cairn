import random, pickle, time
from common import *
from tree import Pat, solve_direct, solve_pruned

def pt_check(a, K, L, pt):
    m = 10 ** K
    return pow(2, a, m) * pow(3, pt[0], m) * pow(7, pt[1], m) % m == L % m

def main():
    random.seed(20261020)
    Lam = DC.kernel_lattice(); pats = load_patterns()
    res = dict(identity_ok=0, identity_bad=0, flip_rejected=0, flip_accepted=0, acc_agree=0, acc_disagree=0,
               prune_keeps=0, prune_drops=0, prune_closes_below=0, prune_open_above=0)
    sample = [p for p in pats if len(p['M']) <= 8][:6]
    for p in sample:
        co0 = anchor_coset(p, Lam)
        for rep in reps_of(p)[:2]:
            pat = Pat(rep[1], p['y'], p['a'], co0)
            for D in (1, 2, 3):
                K = LMAX * D
                leaves = solve_direct(pat, K)
                for L, co in leaves:
                    nn, pt = DC.nearest_norm(co)
                    if pt_check(p['a'], K, L, pt): res['identity_ok'] += 1
                    else: res['identity_bad'] += 1
                    digs = [i for i in range(K) if (L // 10 ** i) % 10 != 1]
                    q = random.choice(digs) if digs else 0
                    L2 = L + 10 ** q * (1 if (L // 10 ** q) % 10 < 9 else -1)
                    L2 = L2 if L2 % 5 else L2 + 2 * 10 ** (q + 1)
                    c2 = cut_coset(co0, p['a'], L2, K) if v2(L2) == p['a'] and L2 % 5 else None
                    if c2 is not None and c2.contains(*pt): res['flip_accepted'] += 1
                    else: res['flip_rejected'] += 1
    m5 = 5 ** 5
    for p in pats[:12]:
        co0 = anchor_coset(p, Lam); a = p['a']; w = a + 9; y = p['y']; mod = m5 * 2 ** w
        for _ in range(30):
            if random.random() < 0.5:
                L = random.randrange(10 ** 96 // 10, 10 ** 96)
                L -= (L - y) % mod
                L += mod * random.randrange(1, 5) if L < 10 ** 95 else 0
            else:
                L = random.randrange(10 ** 95, 10 ** 96)
            if v2(L) != a or L % 5 == 0: continue
            acc = (L - y) % mod == 0
            cut = cut_coset(co0, a, L, 96) is not None
            res['acc_agree' if acc == cut else 'acc_disagree'] += 1
    p = [x for x in pats if x['key'][1] == '227888'][0]
    co0 = anchor_coset(p, Lam)
    rep = reps_of(p)[0]
    pat = Pat(rep[1], p['y'], p['a'], co0)
    K = 192
    leaves = solve_direct(pat, K)
    best = min(leaves, key=lambda x: DC.digits_bound(x[1]))
    nn, pt = DC.nearest_norm(best[1])
    plant_digits = max(abs(pt[0]), abs(pt[1])) * math.log10(3)
    plant_log = math.log10(plant_digits)
    closed_hi, cuts, stages, pruned, fr = solve_pruned(pat, [96, 192], plant_log + 0.05)
    res['prune_keeps'] = int(not closed_hi and any(f[3].contains(*pt) for f in fr))
    closed_lo, cuts2, stages2, pruned2, fr2 = solve_pruned(pat, [96, 192], DC.digits_bound(best[1]) - 0.05)
    res['prune_closes_below'] = int(closed_lo)
    res['planted_log10_digits'] = plant_log
    res['leaf_bound'] = DC.digits_bound(best[1])
    print(res)
    json.dump(res, open(os.path.join(HERE, 'planted.json'), 'w'))

main()
