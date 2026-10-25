#!/usr/bin/env python3
import sys, os, subprocess, hashlib
here = os.path.dirname(os.path.abspath(__file__))
cfg, par = sys.argv[1], sys.argv[2]
p = subprocess.run([os.path.join(here, "lvlN_real"), cfg, par], capture_output=True)
sys.stdout.buffer.write(p.stdout); sys.stderr.buffer.write(p.stderr)
key = hashlib.sha256(open(cfg, "rb").read() + b"|" + open(par, "rb").read()).hexdigest()
lines = sorted(l for l in p.stdout.decode().splitlines() if l.strip())
with open(os.path.join(here, "lvlN_calls.log"), "a") as f:
    f.write(f"{key} {p.returncode} {len(lines)} {hashlib.sha256(chr(10).join(lines).encode()).hexdigest()}\n")
sys.exit(p.returncode)
