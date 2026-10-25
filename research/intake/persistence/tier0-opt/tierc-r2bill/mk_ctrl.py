src = "../tierc-r2shadow/data/r2.rep"
lines = [l for l in open(src) if l.strip()]
for i, l in enumerate(lines, 1):
    with open("data/rep_C%d.rep" % i, "x") as f:
        f.write(l)
with open("data/ctrl_ids.txt", "x") as f:
    for i in range(1, len(lines) + 1):
        f.write("C%d\n" % i)
with open("data/utable_inflated_400_k34.txt", "x") as g:
    for l in open("data/utable_u2_k34.txt"):
        t = l.split()
        g.write("%s %s %s\n" % (t[0], t[1], 10 ** 400))
print(len(lines))
