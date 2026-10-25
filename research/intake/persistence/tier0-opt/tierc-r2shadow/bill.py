import random, sys

t = [float(x) for x in sys.argv[1:]]
n = len(t)
rng = random.Random(7)
means = sorted(sum(rng.choice(t) for _ in range(n)) / n for _ in range(100000))
lo, hi = means[2500], means[97500]
m = sum(t) / n
S = (1.4e6, 7.2e6, 1.5e7)
print("cpu seconds", t)
print("mean %.1f s bootstrap95 [%.1f, %.1f]" % (m, lo, hi))
print("max %.1f median %.1f" % (max(t), sorted(t)[n // 2]))
for lab, s, tt in (("low", S[0], lo), ("central", S[1], m), ("high", S[2], hi)):
    print(lab, "core-days %.3g" % (s * tt / 86400))
print("wall-free sanity: Method A central 1.47e7 core-days")
