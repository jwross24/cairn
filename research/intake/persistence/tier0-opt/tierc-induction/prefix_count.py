from math import lgamma, log, log10

def lC(n, r):
    return (lgamma(n + 1) - lgamma(r + 1) - lgamma(n - r + 1)) / log(10)

out = []
for k, theta in ((31, 1126), (44, 1608)):
    v = lC(theta, k) + k * log10(8)
    out.append("k=%d: prefixes with s<=%d digits and k blocks, 8 digit values: 10^%.1f (positions 10^%.1f)" % (k, theta, v, lC(theta, k)))
open("prefix_count_out.txt", "w").write("\n".join(out) + "\n")
