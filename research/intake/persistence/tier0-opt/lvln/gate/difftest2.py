#!/usr/bin/env python3
"""difftest.py with the pure-Python (NOCLIFT) side cached: it does not depend on lvlN.
Usage (cwd = scratch tier0 copy): difftest2.py <vertex> <known,...> <cache_dir>
Same key function and same IDENTICAL/DIFFERENT verdict as tier0/difftest.py."""
import sys, json, os, subprocess
sys.path.insert(0, os.getcwd())
from difftest import runv, key

s, kn, cache = sys.argv[1], sys.argv[2], sys.argv[3]
cp = f"{cache}/py_{s}.json"
C = runv(s, kn, {'DESCENT_MAX': '1e18'})
if C is None: sys.exit(1)
if os.path.exists(cp):
    kp = set(json.load(open(cp)))
else:
    P = runv(s, kn, {'NOCLIFT': '1', 'DESCENT_MAX': '1e18'})
    if P is None: sys.exit(1)
    kpr = {key(e) for e in P if 'M' in e}
    json.dump(sorted(json.dumps(k) for k in kpr), open(cp, 'w'))
    kp = {json.dumps(k) for k in kpr}
kc = {json.dumps(key(e)) for e in C if 'M' in e}
if kc == kp: print(f"vertex {s}: IDENTICAL ({len(kc)} equations)")
else:
    print(f"vertex {s}: DIFFERENT")
    for k in sorted(kc ^ kp): print("  ", "C " if k in kc else "Py", k)
    sys.exit(2)
