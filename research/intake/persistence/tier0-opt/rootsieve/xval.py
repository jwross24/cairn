import subprocess
digits = [2, 4, 6, 6, 6, 6, 7, 7, 7]
q = len(digits)
inp = []; meta = []
for line in open("base_A4.out"):
    f = line.split()
    if f[0] != "OPEN":
        continue
    a = int(f[1]); nu = int(f[2]); eps = [int(x) for x in f[3:3 + q]]
    inp.append("%d %d %s" % (nu, q, " ".join("%d:%d" % (d, e) for d, e in zip(digits, eps))))
    meta.append(a)
res = subprocess.run(["./rs_check", "cfg_tierc.txt", "-check", "0"], input="\n".join(inp) + "\n", capture_output=True, text=True).stdout.splitlines()
assert len(res) == len(inp)
ok = 0; keep_rank2 = 0; rank_counts = {0: 0, 1: 0, 2: 0}
for a, r in zip(meta, res):
    segs = r.split(" | ")
    rk = int(segs[0].split()[1]); rank_counts[rk] += 1
    for s in segs[1:]:
        g = s.split()
        if int(g[0]) == a and int(g[2]) == 1:
            ok += 1
            if rk == 2 and int(g[1]) == 1:
                keep_rank2 += 1
print("baseline OPEN lines", len(inp), "reproduced as open by the sampler's test", ok, "of which rank 2 and kept", keep_rank2, "rank counts", rank_counts)
