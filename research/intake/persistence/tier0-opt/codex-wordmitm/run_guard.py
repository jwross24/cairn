import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time

here = Path(__file__).resolve().parent
root = here.parent
mode = sys.argv[1]
common = ["shadow480", "--lattice", str(root / "tierc-r2shadow/data/lattice96.txt"), "--levelprimes", str(root / "tierc-r2shadow/data/levelprimes480.txt"), "--utable", str(root / "tierc-r2bill/data/utable_u2_k34.txt"), "--verbose"]
if mode == "full":
    jobs = [("full_" + jid, [str(here / "a_full"), *common, "--rep-file", str(root / f"tierc-r2bill/data/rep_{jid}.rep"), "--mitm-space-cap", "1e30", "--mitm-right-cap", "1e14", "--points", str(here / f"full_{jid}.points.jsonl")], 3500) for jid in ("t347", "t348")]
elif mode == "controls":
    jobs = [(f"control_{binary}", [str(here / binary), *common, "--rep-file", str(root / "tierc-r2bill/data/rep_t000.rep"), *(["--word-mitm"] if binary == "b_original" else [])], 60) for binary in ("a_original", "b_original")]
elif mode == "btargets":
    jobs = [("b_" + jid, [str(here / "b_original"), *common, "--rep-file", str(root / f"tierc-r2bill/data/rep_{jid}.rep"), "--mitm-space-cap", "1e30", "--mitm-right-cap", "1e14", "--word-mitm", "--points", str(here / f"b_{jid}.points.jsonl")], 600) for jid in ("t347", "t348")]
else:
    raise ValueError(mode)
for label, args, cpu_limit in jobs:
    cmd = ["nice", "-n", "10", *args]
    with (here / f"{label}.out").open("x") as out:
        def limits():
            resource.setrlimit(resource.RLIMIT_CPU, (cpu_limit, cpu_limit + 1))
        proc = subprocess.Popen(cmd, stdout=out, stderr=subprocess.STDOUT, preexec_fn=limits)
    peak = 0
    reason = None
    started = time.monotonic()
    while True:
        pid, status, ru = os.wait4(proc.pid, os.WNOHANG)
        if pid:
            result = dict(label=label, command=cmd, exit=os.waitstatus_to_exitcode(status), cpu=ru.ru_utime + ru.ru_stime, maxrss_bytes=ru.ru_maxrss, wall=time.monotonic() - started, stopped=reason)
            with (here / f"{label}.resources.json").open("x") as f:
                json.dump(result, f, indent=2)
            print(json.dumps(result), flush=True)
            break
        time.sleep(0.25)
