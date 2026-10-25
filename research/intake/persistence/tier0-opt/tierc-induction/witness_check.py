import sys
import time
from bisect import bisect_left
from math import log

P = "/Users/jwross/Documents/cairn/research/intake/persistence/tier0/zf_below_1e4000.txt"
OUT = sys.argv[1] if len(sys.argv) > 1 else "witness_out.txt"
KD = 40
NMAX = 141
lines = []
t0 = time.time()

keys = []
limit = 10 ** NMAX
p2 = 1
while p2 < limit:
    p3 = p2
    while p3 < limit:
        p7 = p3
        while p7 < limit:
            keys.append(int(str(p7)[:KD].ljust(KD, "0")))
            p7 *= 7
        p3 *= 3
    p2 *= 2
keys.sort()
lines.append("S-units below 10^%d: %d keys (leading %d digits, zero padded), build+sort %.0fs" % (NMAX, len(keys), KD, time.time() - t0))


def key_of(m):
    return int(str(m)[:KD].ljust(KD, "0"))


def count_sharing(keyset, m_key, L):
    L = min(L, KD)
    scale = 10 ** (KD - L)
    lo = (m_key // scale) * scale
    hi = lo + scale
    return bisect_left(keyset, hi) - bisect_left(keyset, lo)


def unique_witness(keyset, m_key, L):
    return count_sharing(keyset, m_key, L) == 1


def nest_ok(s, g, lam):
    return g <= (lam - 1) * s


rows = [list(map(int, l.split()[1:])) for l in open(P)]
children = []
for r in rows:
    y = 2 ** r[1] * 3 ** r[2] * 7 ** r[3]
    st = str(y)
    pos = [i + 1 for i, ch in enumerate(st) if ch != "1"]
    if pos:
        children.append((y, len(st), pos))

stat = {}
capped = 0
for y, n, pos in children:
    mk = key_of(9 * y)
    assert count_sharing(keys, mk, KD) >= 1
    seq = pos + [n + 1]
    for j in range(len(pos)):
        L = seq[j] - 1
        if L < 1:
            continue
        if L > KD:
            capped += 1
        Lc = min(L, KD)
        d = stat.setdefault(Lc, [0, 0])
        d[0] += 1
        if count_sharing(keys, mk, Lc) > 1:
            d[1] += 1
lines.append("zero-free corpus children: prefix j followed by its run of 1s (M = 9y agrees with N_j then zeros for L = p_(j+1) - 1 digits); any other S-unit below 10^%d sharing the leading L digits?" % NMAX)
lines.append("  L = digits of agreement (capped at %d; %d cases above the cap); (child,j) pairs; pairs with another S-unit sharing them" % (KD, capped))
for Lc in sorted(stat):
    lines.append("  L=%2d  pairs=%6d  shared=%6d" % (Lc, stat[Lc][0], stat[Lc][1]))
firstzero = min((Lc for Lc in stat if all(stat[x][1] == 0 for x in stat if x >= Lc)), default=None)
lines.append("smallest L from which no pair has a competitor: %s" % firstzero)

tot_pairs = 0
rfree = 0
logr = []
for y, n, pos in children:
    st = str(y)
    for j in range(1, len(pos)):
        E = n - pos[j - 1]
        s_j = pos[j - 1]
        if s_j < 6:
            continue
        N = 9 * (y // 10 ** E) + 1
        R = N
        for p in (2, 7):
            while R % p == 0:
                R //= p
        assert R % 3 != 0
        tot_pairs += 1
        if R == 1:
            rfree += 1
        logr.append(log(R) / log(N))
logr.sort()
lines.append("Codex T1 cofactor on real prefixes (s_j >= 6): N_j = 9*floor(y/10^E_j)+1 = 2^r 7^t R; pairs %d; R = 1 (N_j an S-unit): %d; median log R / log N_j = %.3f; 5th percentile %.3f" % (tot_pairs, rfree, logr[len(logr) // 2], logr[len(logr) // 20]))

lines.append("PLANTED NEGATIVES")
y0, n0, pos0 = children[len(children) // 2]
for y, n, pos in children:
    if n >= 60 and len(pos) >= 10:
        y0, n0, pos0 = y, n, pos
        break
mk = key_of(9 * y0)
res = unique_witness(keys, mk, 6)
lines.append("N1 step (b) 'witness unique' on child n=%d at L=6 (competitors known to exist): %s" % (n0, "FLAGGED (competitor found)" if not res else "CERTIFIED (WRONG)"))
res2 = unique_witness(keys, mk, 24)
lines.append("N1 control, same child at L=24: %s" % ("certified unique" if res2 else "flagged"))
twin = mk + 1 if mk % 10 != 9 else mk - 1
keys_plant = sorted(keys + [twin])
res3 = unique_witness(keys_plant, mk, 39)
lines.append("N2 planted twin sharing 39 digits inserted: %s" % ("FLAGGED" if not res3 else "CERTIFIED (WRONG)"))
res4 = unique_witness(keys, mk, 39)
lines.append("N2 same query without the twin: %s" % ("certified unique" if res4 else "flagged"))
rec = (143, 126, 75, 81, 5, 8)
m_rec = 2 ** rec[1] * 3 ** rec[2] * 7 ** rec[3]
st = str(m_rec)
lines.append("N3 record unit 2^126 3^75 7^81: digits %d, digits 1..%d = %s, then %s zeros: %s" % (len(st), rec[4] + 3, st[: rec[4] + 3], len(st[rec[4]:]) - len(st[rec[4]:].lstrip("0")), "run verified" if set(st[rec[4]: rec[4] + rec[5]]) == {"0"} else "RUN NOT FOUND"))
lines.append("N3 step (a) nest_ok(s=5, g=8, lambda=2) [claims scale ratio (s+g)/s <= 2]: %s" % ("holds (WRONG)" if nest_ok(5, 8, 2) else "FLAGGED (ratio 2.6)"))
lines.append("N3 same step at lambda=3: %s" % ("holds" if nest_ok(5, 8, 3) else "flagged"))


def mutant(keyset, m_key, L):
    return True


lines.append("mutant (always-unique tester) on the N1 query: %s -> the N1 check above would be CERTIFIED, so the planted negative distinguishes the real tester from the mutant" % mutant(keys, mk, 6))
open(OUT, "w").write("\n".join(lines) + "\n")
