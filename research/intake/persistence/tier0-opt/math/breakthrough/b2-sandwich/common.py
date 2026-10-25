import os, sys, re, math, itertools, json
from collections import Counter, defaultdict
sys.dont_write_bytecode = True
T0 = '/Users/jwross/Documents/cairn/research/intake/persistence/tier0'
sys.path.insert(0, T0)
os.chdir(T0)
HERE = os.path.dirname(os.path.abspath(__file__))
from lattice import Coset
from descent import cut_coset, v2
import deepcut as DC
import classify_open as C
from baker_chain import baker_upper_bound
LMAX = 96

def survivor_keys():
    keys = []
    for line in open(os.path.join(T0, 'SANDWICH-run.txt')):
        m = re.match(r's=(\d+)\s+M=(\d+)\s+a=(\d+)\s+y=(\d+)', line)
        if m: keys.append(m.groups())
    return keys

def load_patterns(keys=None):
    keys = keys or survivor_keys()
    want = set(keys)
    out = []; seen = set()
    for f in ('runall_final.jsonl', 'trees_c.jsonl', 'trees_mac.jsonl'):
        for (s, M, a, nu, eps, y, sol) in C.entries(os.path.join(T0, f)):
            key = (str(s), ''.join(map(str, M)), str(a), str(y))
            fullkey = key + (nu, None if eps is None else tuple(eps))
            if key not in want or fullkey in seen: continue
            seen.add(fullkey)
            out.append(dict(s=s, M=M, a=a, nu=nu, eps=eps, y=y, key=key))
    return out

def reps_of(p):
    reps = DC.all_representations(p['M'], p['y'])
    if p['nu'] is not None:
        reps = [r for r in reps if r[0] == p['nu'] and Counter(e for _, e in r[1]) == Counter(e % LMAX for e in p['eps'])]
    return reps

def anchor_coset(p, Lam):
    fct = C.factor237(p['y'])
    return Coset((fct[1], fct[2]), Lam.u1, Lam.u2)

def coset_key(co):
    n = co.nearest if hasattr(co, 'nearest') else None
    nn, pt = DC.nearest_norm(co)
    return pt

def deep_cut_inst(co0, a, rep, depth, maxcases=10**9, maxcuts=10**9):
    nu, De = rep
    survivors = [(co0, ())]
    stats = []; cases = 0; levels = []; cuts = 0
    for D in range(1, depth + 1):
        K = LMAX * D; RK = (10 ** K - 1) // 9
        new = []
        for co, assigned in survivors:
            fixed = dict(assigned)
            free = [j for j in range(len(De)) if j not in fixed]
            for choice in itertools.product((0, 1), repeat=len(free)):
                taken = Counter(De[j][1] for j, c in zip(free, choice) if c)
                if any(cnt > 1 for cnt in taken.values()): continue
                L = RK
                for j, t in fixed.items(): L += (De[j][0] - 1) * 10 ** (De[j][1] + LMAX * t)
                for j, c in zip(free, choice):
                    if c: L += (De[j][0] - 1) * 10 ** (De[j][1] + LMAX * (D - 1))
                cases += 1
                if v2(L) != a or L % 5 == 0: continue
                cuts += 1
                if cuts > maxcuts: return 'BUDGET', None, cases, stats, levels
                co2 = cut_coset(co, a, L, K)
                if co2 is None: continue
                new.append((co2, assigned + tuple((j, D - 1) for j, c in zip(free, choice) if c)))
        survivors = new
        stats.append(len(new))
        levels.append(list(new))
        if not survivors: return True, None, cases, stats, levels
    bound = min(DC.digits_bound(co) for co, _ in survivors)
    return False, bound, cases, stats, levels
