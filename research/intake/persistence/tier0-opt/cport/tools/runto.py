import os, subprocess, sys, time

out, err = sys.argv[1], sys.argv[2]
cmd = sys.argv[3:]
t0 = time.time()
with open(out, 'w') as fo, open(err, 'w') as fe:
    p = subprocess.Popen(cmd, stdout=fo, stderr=fe, preexec_fn=lambda: os.nice(10))
    rc = p.wait()
print(f"exit {rc} wall {time.time() - t0:.1f}s")
sys.exit(rc)
