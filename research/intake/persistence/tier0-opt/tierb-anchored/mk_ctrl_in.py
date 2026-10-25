out = open("work/ctrl5_in.txt", "w")
for l in open("data/ctrl5.rep"):
    t = l.split()
    y, nu, n = t[:3]
    out.write(" ".join([y, "0", nu, "0", n] + t[3:]) + "\n")
