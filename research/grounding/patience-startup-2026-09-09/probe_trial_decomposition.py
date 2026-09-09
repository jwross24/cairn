import json
import os
import statistics
import subprocess
import sys

REPS = 5
DOC = json.dumps({"bits": 28, "seed": 7})


def spawn_cpu(argv, stdin_text=""):
    r, w = os.pipe()
    pid = os.fork()
    if pid == 0:
        os.close(w)
        os.dup2(r, 0)
        os.close(r)
        os.execv(argv[0], argv)  # noqa: S606
    os.close(r)
    os.write(w, stdin_text.encode())
    os.close(w)
    _, status, ru = os.wait4(pid, 0)
    return status, ru.ru_utime + ru.ru_stime


def series(label, argv, stdin_text=""):
    vals = []
    for _ in range(REPS):
        status, cpu = spawn_cpu(argv, stdin_text)
        assert status == 0, (label, status)
        vals.append(cpu)
    print(f"{label:34s} min={min(vals):.4f} median={statistics.median(vals):.4f} max={max(vals):.4f}")
    return min(vals)


PY = sys.executable
print("load1", os.getloadavg()[0])

floor = series("import instance_maker", [PY, "-c", "import cairn.skills.instance_maker"])
total = series("real child, bits=28 seed=7", [PY, "-m", "cairn.skills.instance_maker"], DOC)

PHASES = r"""
import json, sys, time
t = {}
t0 = time.process_time()
from cairn.skills import instance_maker as im
from cairn.skills import toy_curve
from cairn import ec, keys
t["import"] = time.process_time() - t0
m = time.process_time
bits, seed = im.parse_inputs(json.dumps({"bits": 28, "seed": 7}))
a0 = m(); im.validate(bits, seed); t["validate"] = m() - a0
a0 = m(); curve = toy_curve.run(bits, seed); t["toy_curve.run"] = m() - a0
p, a, b, n, P = curve.p, curve.a, curve.b, curve.n, tuple(curve.P)
a0 = m(); x = im.draw_x(seed, n); Q = ec.mul(p, a, P, x); t["draw_x+ec.mul"] = m() - a0
inst = {"p": p, "a": a, "b": b, "n": n, "P": list(P), "Q": list(Q)}
out = im.InstanceOutput(bits, seed, p, a, b, n, P, Q, x, curve.tries, keys.instance_hash(inst), im._cross_check("untested"), im.STATUS_OK)
a0 = m(); im.check_postcondition(out); t["check_postcondition"] = m() - a0
a0 = m(); im.second_opinion(p, a, b, n, P, Q, seed); t["second_opinion(bsgs)"] = m() - a0
a0 = m(); out.to_json(); t["to_json"] = m() - a0
t["_process_total"] = time.process_time()
print(json.dumps(t))
"""
runs = []
for _ in range(REPS):
    out = subprocess.run([PY, "-c", PHASES], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr[-2000:]
    runs.append(json.loads(out.stdout))
print()
keys_ = [k for k in runs[0] if k != "_process_total"]
for k in keys_:
    v = [r[k] for r in runs]
    print(f"  {k:24s} min={min(v):.4f} median={statistics.median(v):.4f}")
print(
    f"  {'_process_total':24s} min={min(r['_process_total'] for r in runs):.4f} median={statistics.median([r['_process_total'] for r in runs]):.4f}"
)
print()
print(f"import floor (wait4 min)      {floor:.4f}")
print(f"real child total (wait4 min)  {total:.4f}")
print(f"gap above import floor        {total - floor:.4f}")
print("load1 end", os.getloadavg()[0])
