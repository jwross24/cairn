import sys
from math import log10

P = "/Users/jwross/Documents/cairn/research/intake/persistence/tier0/zf_below_1e4000.txt"
OUT = sys.argv[1] if len(sys.argv) > 1 else "corpus_out.txt"
rows = [list(map(int, l.split()[1:])) for l in open(P)]
ys = []
for r in rows:
    a, b, c = r[1], r[2], r[3]
    y = 2 ** a * 3 ** b * 7 ** c
    ys.append((y, a, b, c))
lines = []
lines.append("corpus rows: %d, max digits %d" % (len(ys), max(len(str(y)) for y, *_ in ys)))


def spearman(xs, ys_):
    def rank(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        rk = [0.0] * len(v)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2 + 1
            for t in range(i, j + 1):
                rk[order[t]] = avg
            i = j + 1
        return rk
    rx, ry = rank(xs), rank(ys_)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    num = sum((p - mx) * (q - my) for p, q in zip(rx, ry))
    dx = sum((p - mx) ** 2 for p in rx) ** 0.5
    dy = sum((q - my) ** 2 for q in ry) ** 0.5
    return num / (dx * dy)


kdist = {}
children = []
for y, a, b, c in ys:
    s = str(y)
    n = len(s)
    pos = [i + 1 for i, ch in enumerate(s) if ch != "1"]
    k = len(pos)
    kdist[k] = kdist.get(k, 0) + 1
    if k >= 1:
        E = [n - p for p in pos]
        lhs = 9 * y + 1
        rhs = 10 ** n + sum(9 * (int(s[p - 1]) - 1) * 10 ** e for p, e in zip(pos, E))
        assert lhs == rhs
        children.append((y, a, b, c, n, pos))
lines.append("identity 9y+1 = 10^n + sum c_i 10^E_i verified on %d rows" % len(children))
lines.append("k distribution (number of non-1 digits): " + ", ".join("%d:%d" % (k, kdist[k]) for k in sorted(kdist) if k <= 12) + " ... max k %d" % max(kdist))

best = {}
for y, a, b, c, n, pos in children:
    k = len(pos)
    for j in range(1, k):
        sj = pos[j - 1]
        gj = pos[j] - pos[j - 1]
        r = (sj + gj) / sj
        bucket = 1 if sj == 1 else 2 if sj == 2 else 3 if sj <= 4 else 5 if sj <= 8 else 9 if sj <= 16 else 17 if sj <= 32 else 33 if sj <= 64 else 65
        cur = best.get(bucket)
        if cur is None or r > cur[0]:
            best[bucket] = (r, sj, gj, n, k)
lines.append("max s_(j+1)/s_j over children and interior j>=1, by s_j bucket (lower end of bucket; ratio, s_j, g_j, n, k):")
for bk in sorted(best):
    lines.append("  s_j>=%d: %s" % (bk, best[bk]))

pairs_prev, pairs_next, pairs_s = [], [], []
for y, a, b, c, n, pos in children:
    k = len(pos)
    if k >= 3:
        gaps = [pos[i + 1] - pos[i] for i in range(k - 1)]
        for j in range(1, len(gaps)):
            pairs_prev.append(gaps[j - 1])
            pairs_next.append(gaps[j])
lines.append("consecutive interior gap pairs (children with k>=3): %d, Spearman(g_(j-1), g_j) = %.3f" % (len(pairs_prev), spearman(pairs_prev, pairs_next)))
sv, gv = [], []
for y, a, b, c, n, pos in children:
    k = len(pos)
    for j in range(1, k):
        sv.append(pos[j - 1])
        gv.append(pos[j] - pos[j - 1])
lines.append("Spearman(s_j, g_j) over all interior (child, j): %d pairs, %.3f" % (len(sv), spearman(sv, gv)))

lines.append("first exceptional index j*(theta) = least j with s_(j+1) >= theta (s_(k+1) := n); nesting N_(j*-1) exceptional would need s_j* >= theta:")
for theta in (10, 20, 40):
    viol = 0
    tot = 0
    jumps = []
    for y, a, b, c, n, pos in children:
        if n < theta:
            continue
        sseq = [0] + pos + [n]
        jstar = next(j for j in range(len(sseq) - 1) if sseq[j + 1] >= theta)
        tot += 1
        if sseq[jstar] < theta:
            viol += 1
        if jstar >= 1:
            jumps.append((sseq[jstar + 1] / sseq[jstar], sseq[jstar], sseq[jstar + 1], n))
    jumps.sort(reverse=True)
    med = sorted(j[0] for j in jumps)[len(jumps) // 2] if jumps else None
    lines.append("  theta=%d: children with n>=theta %d, nesting violated at j* in %d (= all); jump ratio s_(j*+1)/s_j*: max %s, median %.2f" % (theta, tot, viol, jumps[0] if jumps else None, med))

lines.append("longest run of 1s between non-1 digits (or at the ends) over children:")
mx = (0, None)
for y, a, b, c, n, pos in children:
    seq = [0] + pos + [n + 1]
    for i in range(len(seq) - 1):
        run = seq[i + 1] - seq[i] - 1
        if run > mx[0]:
            mx = (run, (n, len(pos), seq[i]))
lines.append("  %s" % (mx,))
open(OUT, "w").write("\n".join(lines) + "\n")
