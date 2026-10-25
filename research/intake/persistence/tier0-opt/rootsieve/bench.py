import subprocess, resource, sys, re

def run(binary, cfg, outp, errp):
    r0 = resource.getrusage(resource.RUSAGE_CHILDREN)
    with open(outp, "w") as fo, open(errp, "w") as fe:
        subprocess.run(["nice", "-n", "10", "./" + binary, cfg], stdout=fo, stderr=fe, check=True)
    r1 = resource.getrusage(resource.RUSAGE_CHILDREN)
    return r1.ru_utime - r0.ru_utime

def rank2(nu, digits, eps):
    s3 = (nu + sum(d - 1 for d in digits)) % 3
    r7 = [0]
    for i in range(5):
        r7.append((r7[-1] * 10 + 1) % 7)
    y7 = (r7[nu % 6] + sum((d - 1) * pow(10, e % 6, 7) for d, e in zip(digits, eps))) % 7
    return s3 == 0 and y7 == 0

def lines(path, digits, filt):
    out = []
    q = len(digits)
    for line in open(path):
        f = line.split()
        if f[0] not in ("OPEN", "EXACT"):
            continue
        nu = int(f[2]); eps = [int(x) for x in f[3:3 + q]]
        if filt and not rank2(nu, digits, eps):
            continue
        out.append(tuple(f))
    return sorted(out)

for T, digits in (("A1", [2, 3, 7, 7, 7, 8, 8]), ("A2", [3, 4, 4, 7, 7, 7, 8]), ("A3", [4, 6, 6, 6, 6, 9, 9, 9]), ("A4", [2, 4, 6, 6, 6, 6, 7, 7, 7])):
    cfg = "cfg_%s.txt" % T
    tb = []; tr = []
    for rep in range(3):
        tb.append(run("lvl12_base", cfg, "base_%s.out" % T, "base_%s.err" % T))
        tr.append(run("lvl12_r2", cfg, "r2_%s.out" % T, "r2_%s.err" % T))
    sb = open("base_%s.err" % T).read().strip().splitlines()[-1]
    sr = open("r2_%s.err" % T).read().strip().splitlines()[-1]
    base = lines("base_%s.out" % T, digits, True)
    r2 = lines("r2_%s.out" % T, digits, False)
    npb = int(re.search(r"patterns (\d+)", sb).group(1)); npr = int(re.search(r"patterns (\d+)", sr).group(1))
    print(T, digits)
    print("  baseline:", sb)
    print("  stream  :", sr)
    print("  patterns visited: baseline %d stream %d ratio %.2f" % (npb, npr, npb / npr))
    print("  user CPU seconds, best of 3: baseline %.3f stream %.3f ratio %.2f (all: %s | %s)" % (min(tb), min(tr), min(tb) / min(tr), ["%.2f" % x for x in tb], ["%.2f" % x for x in tr]))
    print("  OPEN/EXACT lines: baseline restricted to rank 2 = %d, stream = %d, identical = %s" % (len(base), len(r2), base == r2))
