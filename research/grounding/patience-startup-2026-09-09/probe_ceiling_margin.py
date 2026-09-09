import json
import os
import pathlib
import statistics
import sys

from cairn import runner
from cairn.skills import instance_maker as im

PY = sys.executable


def spawn(bits, seed=7, reps=7):
    vals = []
    for _ in range(reps):
        r, w = os.pipe()
        pid = os.fork()
        if pid == 0:
            os.close(w)
            os.dup2(r, 0)
            os.close(r)
            devnull = os.open(os.devnull, os.O_WRONLY)
            os.dup2(devnull, 1)
            os.dup2(devnull, 2)
            os.execv(PY, [PY, "-m", "cairn.skills.instance_maker"])  # noqa: S606
        os.close(r)
        os.write(w, json.dumps({"bits": bits, "seed": seed}).encode())
        os.close(w)
        _, st, ru = os.wait4(pid, 0)
        assert st == 0, (bits, st)
        vals.append(ru.ru_utime + ru.ru_stime)
    return vals


tiers = json.loads(pathlib.Path("bundle/tiers.json").read_text())
mult = tiers["ceiling_multiplier"]
startup_ms = int(sys.argv[1]) if len(sys.argv) > 1 else tiers["subprocess_startup_ms"]
print("ceiling_multiplier", mult, "subprocess_startup_ms", startup_ms, "load1", os.getloadavg()[0])
print(f"{'bits':>5} {'declared':>9} {'ceiling':>9} {'min':>8} {'median':>8} {'max':>8} {'max/ceil':>9}")
for bits in (28, 30, 40):
    d = im.COST_PROFILE.evaluate(bits).expected_wall_s
    c = runner.ceiling_for(d, mult, startup_ms)
    v = spawn(bits)
    print(f"{bits:5d} {d:9.4f} {c:9.4f} {min(v):8.4f} {statistics.median(v):8.4f} {max(v):8.4f} {max(v) / c:9.2f}")
print("load1 end", os.getloadavg()[0])
