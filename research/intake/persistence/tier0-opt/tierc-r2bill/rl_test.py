import resource, subprocess, sys
def lim():
    resource.setrlimit(resource.RLIMIT_AS, (2 << 30, 2 << 30))
r = subprocess.run([sys.executable, "-I", "-c", "x = bytearray(3 << 30); print(len(x))"], preexec_fn=lim, capture_output=True, text=True)
print(r.returncode, r.stdout[-100:], r.stderr[-200:])
