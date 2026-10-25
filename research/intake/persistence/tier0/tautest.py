#!/usr/bin/env python3
"""
tautest.py — test of the τ lemma (HSHADOW.md §7) on Cairn's 1,335 final-stage patterns.

For every pattern key in Cairn's runs/shadow1335.tsv, every representation (ν, De) of the anchor (the same
enumeration and ν/ε filter as shadowcert.py), its wrap w := (V − y)/R_96 with V = R_ν + Σ (d_j − 1)10^{e_j},
its depth-1 words (Lemma C at K = 96), and per word the DP target
    τ_W = (2^a 3^{w′_b} 7^{w′_c} − V) · (10^96 − 1)^{-1}  (mod 148417)
from the word's coset base point w′.  The lemma predicts τ_W ≡ −w/9 (mod 148417) for every word, hence
τ_W = 0 exactly for the words of wrap-0 representations.  Output per pattern: [(wrap, #words, #τ-mismatches)…];
summary: words by wrap, mismatches, and the count of τ ≠ 0 words (Cairn's port: 16 words in 4 patterns).

Usage: python3 tautest.py <shadow1335.tsv> <trees.jsonl> [--part i/n]
"""
import sys, time
from collections import Counter
from lattice import Coset
import deepcut as DC, classify_open as C, wordlift as W

PT = 193 * 769
NEG9 = (-pow(9, -1, PT)) % PT        # −1/9 ≡ 65963

if __name__ == "__main__":
    tsv, jf = sys.argv[1], sys.argv[2]
    part = (0, 1)
    if '--part' in sys.argv:
        i, n = sys.argv[sys.argv.index('--part') + 1].split('/'); part = (int(i), int(n))
    keys = []
    for l in open(tsv):
        p = l.split('\t')[0].split()
        if len(p) >= 4: keys.append(tuple(p[:4]))
    want = set(keys); seen = set(); t0 = time.time()
    done = set()
    if '--resume' in sys.argv:
        for l in open(sys.argv[sys.argv.index('--resume') + 1]):
            p = l.split()
            if len(p) > 4 and p[4].startswith('k='): done.add(tuple(p[:4]))
        print(f"resume: {len(done)} patterns already done", flush=True)
    Lam96 = DC.kernel_lattice(); winv = pow((10 ** 96 - 1) % PT, -1, PT)
    by_wrap = Counter(); mism = 0; nonzero = 0; nz_patterns = []; n_pat = 0; reps_by_wrap = Counter(); reps_words_by_wrap = Counter()
    idx = -1
    for (s, M, a, nu, eps, y, sol) in C.entries(jf):
        key = (str(s), ''.join(map(str, M)), str(a), str(y))
        if key not in want or key in seen: continue
        seen.add(key); idx += 1
        if idx % part[1] != part[0] or key in done: continue
        n_pat += 1; k = len(M)
        fct = C.factor237(y); co0 = Coset((fct[1], fct[2]), Lam96.u1, Lam96.u2)
        reps = DC.all_representations(M, y)
        if nu is not None:
            reps = [r for r in reps if r[0] == nu and Counter(e for _, e in r[1]) == Counter(e % 96 for e in eps)]
        log = []; pat_nz = 0
        for (nu0, De) in reps:
            V = W.R(nu0) + sum((d - 1) * 10 ** e for d, e in De)
            assert (V - y) % W.R(96) == 0
            w = (V - y) // W.R(96); reps_by_wrap[w] += 1
            words = W.depth1_words(co0, a, (nu0, De))
            if words: reps_words_by_wrap[w] += 1
            bad = 0
            for co, state in words:
                x = pow(2, a, PT) * pow(3, co.v0[0], PT) * pow(7, co.v0[1], PT) % PT
                tau = (x - V) * winv % PT
                if tau != (NEG9 * w) % PT: bad += 1
                if tau: pat_nz += 1
                by_wrap[w] += 1
            mism += bad; log.append((w, len(words), bad))
        nonzero += pat_nz
        if pat_nz: nz_patterns.append(key)
        print(f"{' '.join(key)} k={k} reps={len(reps)} {log}{' TAU!=0' if pat_nz else ''} [{time.time()-t0:.0f}s]", flush=True)
    print(f"\nSUMMARY part {part[0]}/{part[1]}: patterns {n_pat}; representations by wrap {dict(sorted(reps_by_wrap.items()))}; "
          f"representations with words by wrap {dict(sorted(reps_words_by_wrap.items()))}; words by wrap {dict(sorted(by_wrap.items()))}; "
          f"τ mismatches {mism}; τ≠0 words {nonzero} in {len(nz_patterns)} patterns {nz_patterns} [{time.time()-t0:.0f}s]")
