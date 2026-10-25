"""Ground truth for the level-192 child correspondence: for synthetic representations, enumerate EVERY child (S, sn) with exact
integers, keep those whose pattern value is congruent to the shadow value V modulo 193 and 769 (the children that pass both
prime cuts when the word lattice has trivial image there and the shadow passes), and compare with the C DP's solution set.
usage: planted_dp.py BINARY [--mutant noNu|wrongmod] [--reps N] [--k K] [--seed S]"""
import sys, random, subprocess

def R(n): return (10 ** n - 1) // 9

def truth(nu, De):
    """children (S, sn) whose pattern value, built from the actual digit positions (e, or e + 96 for S) and the length
    nu + 96 sn, is congruent to the shadow value modulo 193 and modulo 769 -- no use of the algebraic difference formula."""
    k = len(De)
    sols = set()
    per = []
    for p in (193, 769):
        inv9 = pow(9, -1, p)
        Rn = lambda n, p=p, inv9=inv9: (pow(10, n, p) - 1) * inv9 % p
        base = [(d - 1) * pow(10, e, p) % p for d, e in De]
        moved = [(d - 1) * pow(10, e + 96, p) % p for d, e in De]
        sums = [0] * (1 << k)
        for m in range(1, 1 << k):
            b = (m & -m).bit_length() - 1
            sums[m] = sums[m & (m - 1)] + moved[b] - base[b]
        V = (Rn(nu) + sum(base)) % p
        per.append((p, Rn, sums, V))
    for sn in (0, 1):
        for m in range(1 << k):
            ok = True
            for p, Rn, sums, V in per:
                if (Rn(nu + 96 * sn) + sum_base(per, p) + sums[m] - V) % p != 0:
                    ok = False; break
            if ok: sols.add((m, sn))
    return sols

def sum_base(per, p):
    return _BASE[p]

_BASE = {}

def main():
    binary = sys.argv[1]
    mut = sys.argv[sys.argv.index('--mutant') + 1] if '--mutant' in sys.argv else None
    nreps = int(sys.argv[sys.argv.index('--reps') + 1]) if '--reps' in sys.argv else 6
    k = int(sys.argv[sys.argv.index('--k') + 1]) if '--k' in sys.argv else 16
    seed = int(sys.argv[sys.argv.index('--seed') + 1]) if '--seed' in sys.argv else 1
    rng = random.Random(seed)
    reps = [(rng.randrange(96), [(rng.randrange(2, 10), rng.randrange(96)) for _ in range(k)]) for _ in range(nreps)]
    lines = ''.join(f"{nu} {k} " + ' '.join(f"{d} {e}" for d, e in De) + '\n' for nu, De in reps)
    cmd = [binary, 'dptest'] + (['--mutant', mut] if mut else [])
    out = subprocess.run(cmd, input=lines, capture_output=True, text=True, check=True).stdout.strip().split('\n')
    bad = 0; tot_truth = 0; tot_sn1 = 0
    for (nu, De), o in zip(reps, out):
        for p in (193, 769): _BASE[p] = sum((d - 1) * pow(10, e, p) for d, e in De) % p
        t = truth(nu, De)
        parts = o.split()[1:]
        got = {(int(p.split(':')[0]), int(p.split(':')[1])) for p in parts}
        tot_truth += len(t); tot_sn1 += sum(1 for _, sn in t if sn)
        if got != t:
            bad += 1
            print(f"MISMATCH nu={nu}: truth {len(t)} (sn=1: {sum(1 for _, sn in t if sn)}), DP {len(got)}; missing {len(t - got)}, spurious {len(got - t)}")
    print(f"mutant={mut}: {nreps} synthetic reps (k={k}), truth solutions {tot_truth} ({tot_sn1} with the nu-shift), representations where DP != truth: {bad}")
    sys.exit(1 if bad else 0)
main()
