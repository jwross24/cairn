import os, subprocess, sys, time
B = "/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/"
BIN = B + "tierc-r2shadow/cport_r2c"
SH = B + "tierc-r2shadow/data/"
RB = B + "tierc-r2bill/data/"
HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
ids = []
for f in ("ids_all.txt", "ids_b3.txt", "ids_o1.txt"):
    ids += [l.strip() for l in open(RB + f) if l.strip()]
ids = sorted(set(ids))
print(len(ids), flush=True)
t0 = time.time()
for i in ids:
    rep = RB + "rep_%s.rep" % i
    if not os.path.exists(rep):
        print("missing", i); continue
    wf = HERE + "runs/words_%s.jsonl" % i
    of = HERE + "runs/wd_%s.txt" % i
    if os.path.exists(of):
        continue
    cmd = ["nice", "-n", "10", BIN, "shadow480", "--rep-file", rep, "--lattice", SH + "lattice96.txt",
           "--levelprimes", SH + "levelprimes480.txt", "--utable", RB + "utable_u2_k34.txt",
           "--mitm-space-cap", "1", "--dump-words", wf]
    with open(of, "x") as fo:
        subprocess.run(cmd, stdout=fo, stderr=subprocess.STDOUT, timeout=900)
print("done", time.time() - t0)
