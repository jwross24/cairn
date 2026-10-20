import sys, os, subprocess, statistics, json, time
binp = sys.argv[1]; reps = int(sys.argv[2]); label = sys.argv[3] if len(sys.argv) > 3 else ''
EQ = [(864,(2,2,3,3,4,6)),(432,(2,2,2,2,3,3,3)),(1161216,(4,7,8,8,8,9,9)),(1161216,(6,6,7,8,8,8,9))]
res = {}
for s, M in EQ:
    cfgp = f"/private/tmp/persist-opt-scratch/oracle_{s}_{''.join(map(str,M))}.txt"
    cpu = []; wall = []; loads = []
    for r in range(reps):
        outf = open('/private/tmp/persist-opt-scratch/bench_out.txt', 'w')
        t0 = time.time()
        pr = subprocess.Popen([binp, cfgp], stdout=outf, stderr=subprocess.PIPE, text=True)
        _, st, ru = os.wait4(pr.pid, 0)
        err = pr.stderr.read(); pr.returncode = 0
        w = time.time() - t0
        n = int(err.split()[1])
        cpu.append((ru.ru_utime + ru.ru_stime) / n * 1e9); wall.append(w / n * 1e9)
        loads.append(os.getloadavg()[0])
    res[f"{s}:{''.join(map(str,M))}"] = dict(n=n, cpu_med=round(statistics.median(cpu),1), cpu_min=round(min(cpu),1), cpu_max=round(max(cpu),1),
                                           wall_med=round(statistics.median(wall),1), load=round(statistics.median(loads),1))
    print(label, s, M, res[f"{s}:{''.join(map(str,M))}"], flush=True)
