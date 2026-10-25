import math
import re
import sys
from collections import Counter

SRC = '/Users/jwross/Documents/cairn/research/intake/persistence/tier0/SANDWICH-run.txt'
LOG_G0 = {0: 12.987, 1: 14.925}


def depth_rule(logU):
    return math.ceil((logU - 72) / 48) + 1


def model_logS(theta, c_step, log_s0, k):
    s = 10.0 ** log_s0 if log_s0 < 300 else None
    from mpmath import mp, mpf, log10
    mp.dps = 40
    s = mpf(10) ** log_s0
    C = mpf(10) ** c_step
    for _ in range(k):
        s = s + C * s ** mpf(theta)
    return float(log10(s))


def main():
    rows = []
    for line in open(SRC):
        m = re.search(r'a=(\d+)\s+y=(\d+)\s+k=(\d+)\s+log10 U=([\d.]+)\s+reps=(\d+)\s+-> CLOSED (\[.*\])', line)
        if not m:
            continue
        a, k, logU = int(m.group(1)), int(m.group(3)), float(m.group(4))
        depths = [int(t) for t in re.findall(r"\('CLOSED-sandwich', (\d+),", m.group(6))]
        cuts = len(re.findall(r"CLOSED-cut", m.group(6)))
        rows.append((a, k, logU, max(depths) if depths else 1, cuts))
    print('parsed %d recorded patterns from SANDWICH-run.txt' % len(rows))
    bad = 0
    for a, k, logU, D, cuts in rows:
        if D > 1 and depth_rule(logU) != D:
            bad += 1
            print('  depth rule mismatch', a, k, logU, D, depth_rule(logU))
    print('depth rule D = ceil((log10 U - 72)/48) + 1 reproduces the recorded sandwich depth: mismatches %d of %d' % (bad, sum(1 for r in rows if r[3] > 1)))
    neg = depth_rule(logU=60.0)
    print('planted negative: the rule applied to log10 U = 60 gives D=%d (a pattern with U below 10^72 needs no sandwich beyond depth 1): %s' % (neg, neg == 1 or neg < 2))
    print()
    print('theta-model depth for the recorded patterns (S_{j+1} = S_j + C S_j^theta, C calibrated so theta = 1 reproduces the recorded log10 U):')
    hist = {}
    for theta in (1.0, 0.9, 0.75, 0.5):
        cnt = Counter()
        for a, k, logU, D, cuts in rows:
            g0 = LOG_G0[0 if a == 0 else 1]
            c_step = (logU - g0) / k
            if theta == 1.0:
                ls = logU
            else:
                ls = model_logS(theta, c_step, g0, k)
            cnt[max(1, depth_rule(ls))] += 1
        hist[theta] = cnt
        print('  theta=%.2f  depth histogram %s' % (theta, dict(sorted(cnt.items()))))
    rec = Counter(max(1, r[3]) for r in rows)
    print('  recorded depths  %s' % dict(sorted(rec.items())))
    ks = sorted(set(r[1] for r in rows))
    print('k range of recorded patterns: %d..%d (Tier C is k = 31..44)' % (ks[0], ks[-1]))
    print()
    print('per-gap multiplier implied by the recorded log10 U (a>=1 rows, (log10 U - 14.925)/k):')
    for a, k, logU, D, cuts in rows[:0]:
        pass
    mult = sorted(set((k, round((logU - LOG_G0[1]) / k, 2)) for a, k, logU, D, c in rows if a >= 1))
    print('  ', mult)


if __name__ == '__main__':
    main()
