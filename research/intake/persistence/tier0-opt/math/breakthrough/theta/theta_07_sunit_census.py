import sys
import time
from math import log10, log

NMAX = int(sys.argv[1]) if len(sys.argv) > 1 else 120


def longest_run(s, ch='1'):
    best = cur = 0
    for c in s:
        if c == ch:
            cur += 1
            if cur > best:
                best = cur
        else:
            cur = 0
    return best


def main():
    limit = 10 ** NMAX
    mink = {}
    maxrun = {}
    count = {}
    t0 = time.time()
    p2 = 1
    a = 0
    while p2 < limit:
        p3 = p2
        while p3 < limit:
            p7 = p3
            while p7 < limit:
                s = str(p7)
                n = len(s)
                k = n - s.count('1')
                if n not in mink or k < mink[n][0]:
                    mink[n] = (k, p7)
                r = longest_run(s)
                if r > maxrun.get(n, (0, 0))[0]:
                    maxrun[n] = (r, p7)
                count[n] = count.get(n, 0) + 1
                p7 *= 7
            p3 *= 3
        p2 *= 2
        a += 1
    print('S-units 2^a 3^b 7^c below 10^%d: %d numbers, %.0fs' % (NMAX, sum(count.values()), time.time() - t0))
    print('  n   #S-units  min #non-1 digits (k)  k/n   longest run of 1s   log10(#S-units with n digits)')
    for n in sorted(mink):
        if n <= 14 or n % 10 == 0:
            print('%4d  %8d  %5d  %.3f   %3d    %.2f' % (n, count[n], mink[n][0], mink[n][0] / n, maxrun[n][0], log10(count[n])))
    kmax_by_n = {}
    for kk in (0, 1, 2, 3, 4, 5, 6, 8, 10, 12):
        ns = [n for n in mink if mink[n][0] <= kk]
        kmax_by_n[kk] = max(ns) if ns else None
    print('largest n with an S-unit having at most k non-1 digits:', kmax_by_n)
    return mink


if __name__ == '__main__':
    main()
