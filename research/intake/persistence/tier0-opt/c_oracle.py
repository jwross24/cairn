import sys, json, subprocess, hashlib
from export_cfg import export
from tier0v2 import multisets
from eq_golden import EQS
binp, out = sys.argv[1], sys.argv[2]
eqs = []
for s in (4,14,27,72,98,189,294):
    for M in sorted(tuple(sorted(M)) for M in multisets(s)): eqs.append((s, M))
eqs += EQS
with open(out, 'w') as f:
    for s, M in eqs:
        cfgp = f"/private/tmp/persist-opt-scratch/oracle_{s}_{''.join(map(str,M))}.txt"
        export(M, cfgp)
        p = subprocess.run([binp, cfgp], capture_output=True, text=True); assert p.returncode == 0, p.stderr
        lines = sorted(p.stdout.splitlines())
        f.write(json.dumps(dict(s=s, M=M, nlines=len(lines), sha=hashlib.sha256('\n'.join(lines).encode()).hexdigest(), err=p.stderr.strip()), sort_keys=True) + '\n')
