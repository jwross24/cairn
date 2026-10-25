import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cc_lib import *
b96, _ = load_lam96()


def prim(level):
    out = []
    for line in open(SH + "levelprimes480.txt"):
        if line[0] == "#" or not line.strip():
            continue
        t = line.split()
        if t[0] == "B":
            L, p, l3, l7 = int(t[1]), int(t[2]), int(t[5]), int(t[6])
        else:
            L, p, l3, l7 = int(t[0]), int(t[1]), int(t[4]), int(t[5])
        if L == level:
            out.append((p, l3, l7))
    return out


def lam(levels):
    b = b96
    for L in levels:
        for p, l3, l7 in prim(L):
            b = kernel_cond(b, l3, l7, p - 1)
    return b


for name, lv in (("96", []), ("96+192", [192]), ("96+192+384", [192, 384]), ("96+480", [480]), ("96+192+384+480", [192, 384, 480])):
    b = lam(lv)
    W = Window(b)
    print("%-16s index digits %3d  c2=%2d |A2|=%d  t5=%d |A5|=%d" % (name, len(str(det(b))), W.c2, len(W.A2), W.t5, len(W.A5)))
