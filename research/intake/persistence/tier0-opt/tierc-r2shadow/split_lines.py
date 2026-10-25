import sys

stem = sys.argv[1]
for i, ln in enumerate(open(stem + ".cases"), 1):
    with open("%s_c%d.txt" % (stem, i), "w") as f:
        f.write(ln)
    with open("%s_o%d.txt" % (stem, i), "w") as f:
        f.write(" ".join(ln.split()[:4]) + "\n")
    with open("%s_r%d.rep" % (stem, i), "w") as f:
        f.write(open(stem + ".rep").read().splitlines()[i - 1] + "\n")
