p = "run_surv.py"
s = open(p).read()
s = s.replace("    reason = None\n    while True:\n        r = os.wait4(p.pid, os.WNOHANG)\n        if r[0] != 0:\n            ru = r[2]\n            return {\"rc\": os.waitstatus_to_exitcode(r[1]), \"cpu\": ru.ru_utime + ru.ru_stime, \"maxrss_mb\": ru.ru_maxrss / 1e6, \"killed\": reason}\n",
"    reason = None\n    last_ps = time.monotonic()\n    while True:\n        r = os.wait4(p.pid, os.WNOHANG)\n        if r[0] != 0:\n            ru = r[2]\n            return {\"rc\": os.waitstatus_to_exitcode(r[1]), \"cpu\": ru.ru_utime + ru.ru_stime, \"maxrss_mb\": ru.ru_maxrss / 1e6, \"killed\": reason}\n        if time.monotonic() - last_ps < 0.25:\n            wait_evt.wait(0.003)\n            continue\n        last_ps = time.monotonic()\n")
s = s.replace("import json, os, re, signal, subprocess, sys, threading", "import json, os, re, signal, subprocess, sys, threading, time")
s = s.replace("        wait_evt.wait(0.25)\n", "")
open(p, "w").write(s)
