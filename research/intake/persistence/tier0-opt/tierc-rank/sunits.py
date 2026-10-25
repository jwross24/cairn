import sys, json

R96 = (10 ** 96 - 1) // 9
LIM = 10 ** 98


def sunits(amax=60, lim=LIM):
    out = []
    for a in range(amax + 1):
        pa = 2 ** a
        if pa >= lim:
            break
        b = 0
        pb = pa
        while pb < lim:
            c = 0
            pc = pb
            while pc < lim:
                out.append((pc, a, b, c))
                pc *= 7
                c += 1
            pb *= 3
            b += 1
    return out


def digit_sum(x):
    return sum(map(int, str(x)))


def passes(y, k, wmax=126):
    u = y + k * R96
    q, low = divmod(u, 10 ** 96)
    return digit_sum(low) + 10 * q <= 95 + wmax


def main():
    su = sunits()
    rk = {0: 0, 1: 0, 2: 0}
    for y, a, b, c in su:
        rk[(b > 0) + (c > 0)] += 1
    print("sunits", len(su), "rank", rk)
    cnt = {0: 0, 1: 0, 2: 0}
    pairs = []
    for y, a, b, c in su:
        r = (b > 0) + (c > 0)
        for k in range(-9, 225):
            u = y + k * R96
            if u < 0:
                continue
            if passes(y, k):
                cnt[r] += 1
                pairs.append((y, a, b, c, k))
    print("filtered pairs", sum(cnt.values()), cnt, "raw", len(su) * 234)
    with open("pairs_filtered.jsonl", "w") as f:
        for p in pairs:
            f.write(json.dumps(p) + "\n")


main()
