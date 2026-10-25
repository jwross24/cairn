import json
census = {0: 2.999e8, 1: 3.121e8, 2: 3.133e8, 3: 4.270e8, 4: 2.877e8, 5: 4.070e8, 6: 2.888e8, 7: 1.334e9, 8: 1.560e9, 9: 1.374e9, 10: 1.978e9, 11: 1.892e9, 12: 6.649e9}
meta = json.load(open("/dev/stdin")) if False else None
rows = []
exact = {0: ("exact", 195464, 299922194, 4638.85), 4: ("exact", 160868, 287670253, None), 8: ("exact", 1317160, 1560031123, None)}
f4 = json.load(open("full_v4.json")); f8 = json.load(open("full_v8.json"))
exact[4] = ("exact", f4["survivors"], f4["N"], f4["bill_cpu_s"]); exact[8] = ("exact", f8["survivors"], f8["N"], f8["bill_cpu_s"])
tot = [0, 0, 0]; surv = [0, 0, 0]
print("| v | s | patterns | basis | survivors (95%) | CPU-s total (95%) | core-days |")
for v in range(13):
    if v in exact:
        b, s, N, c = exact[v]
        lo = hi = None
        if v == 0: ci = (c, c)
        else:
            d = f4 if v == 4 else f8; ci = tuple(d["bill_ci"])
        print(f"| {v} | | {N:.3e} | exact count, all cport on {'all' if v==0 else 'thinned sample'} | {s} | {c:.0f} [{ci[0]:.0f}, {ci[1]:.0f}] | {c/86400:.2f} |")
        tot[0] += c; tot[1] += ci[0]; tot[2] += ci[1]; surv[0] += s; surv[1] += s; surv[2] += s
    else:
        d = json.load(open(f"est_v{v}.json"))
        print(f"| {v} | {d['s']} | {d['N']:.3e} | sampled (2000 triples) | {d['survivors_est']:.3g} [{d['survivors_ci'][0]:.3g}, {d['survivors_ci'][1]:.3g}] | {d['bill_cpu_s']:.0f} [{d['bill_ci'][0]:.0f}, {d['bill_ci'][1]:.0f}] | {d['bill_cpu_s']/86400:.2f} |")
        tot[0] += d["bill_cpu_s"]; tot[1] += d["bill_ci"][0]; tot[2] += d["bill_ci"][1]
        surv[0] += d["survivors_est"]; surv[1] += d["survivors_ci"][0]; surv[2] += d["survivors_ci"][1]
print("survivors", surv, "cpu-s", tot, "core-days", [t / 86400 for t in tot])
