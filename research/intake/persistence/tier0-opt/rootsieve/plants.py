import sys
D = int(sys.argv[1])
ALLOWED = set("12346789")
out_in = open("plants_in.txt", "w")
out_meta = open("plants_meta.txt", "w")
count = 0
by_rank = {}
LIM = 10 ** D
for g in range(0, 400):
    x7 = 7 ** g
    if x7 >= LIM:
        break
    for b in range(0, 1000):
        x37 = x7 * 3 ** b
        if x37 >= LIM:
            break
        x = x37
        for a in range(0, 161):
            if x >= LIM:
                break
            if x >= 1000:
                if (x % 10 ** 12) and "0" not in str(x % 10 ** 12):
                    s = str(x)
                    if "0" not in s and "5" not in s:
                        n = len(s)
                        pat = []
                        for i, ch in enumerate(reversed(s)):
                            if ch != "1":
                                pat.append("%s:%d" % (ch, i % 12))
                        out_in.write("%d %d %s\n" % (n % 12, len(pat), " ".join(pat)))
                        out_meta.write("%d %d %d %d %d\n" % (a, b, g, n, len(pat)))
                        count += 1
                        rk = (b > 0) + (g > 0)
                        by_rank[rk] = by_rank.get(rk, 0) + 1
            x *= 2
print("plants", count, "by number of odd primes dividing", by_rank)
