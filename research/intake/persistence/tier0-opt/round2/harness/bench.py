import sys, os, subprocess, statistics, time
# usage: bench.py reps cfg nu_lo nu_hi bin1 bin2 ...   (interleaved A B A B ...)
reps = int(sys.argv[1]); cfg = sys.argv[2]; lo, hi = sys.argv[3], sys.argv[4]; bins = sys.argv[5:]
cpu = {b: [] for b in bins}; loads = {b: [] for b in bins}; n = {}
for r in range(reps):
    for b in bins:
        pr = subprocess.Popen(['nice', '-n', '10', b, cfg, lo, hi], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        load = os.getloadavg()[0]
        _, st, ru = os.wait4(pr.pid, 0)
        err = pr.stderr.read()
        n[b] = int(err.split()[1])
        cpu[b].append((ru.ru_utime + ru.ru_stime) / n[b] * 1e9); loads[b].append(load)
for b in bins:
    c = cpu[b]
    print(f"{os.path.basename(b):14s} n={n[b]:.3e} ns/pat med={statistics.median(c):6.2f} q25={sorted(c)[len(c)//4]:6.2f} min={min(c):6.2f} max={max(c):6.2f} load1m(med)={statistics.median(loads[b]):.1f}", flush=True)
if len(bins) > 1:
    base = cpu[bins[0]]
    for b in bins[1:]:
        ratios = [x / y for x, y in zip(base, cpu[b])]
        print(f"ratio {os.path.basename(bins[0])}/{os.path.basename(b)}: med={statistics.median(ratios):.3f} min={min(ratios):.3f} max={max(ratios):.3f}  of-minima={min(base)/min(cpu[b]):.3f}")
