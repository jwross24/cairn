import os, sys, subprocess, hashlib, json
S = "/private/tmp/claude-501/-Users-jwross-Documents-cairn/ec9f8f52-ce29-4a5c-9caf-2ecbd434509f/scratchpad/h12"
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "runs")
os.makedirs(OUT, exist_ok=True)


def run(binary, eq, tag, level=24, env=None, parents=None, extra_args=()):
    d = os.path.join(S, eq)
    cfg = os.path.join(d, f"cfgL{level}.txt")
    par = parents or os.path.join(d, f"parents{level}.txt")
    outp = os.path.join(OUT, f"{eq}_L{level}.{tag}.out")
    errp = os.path.join(OUT, f"{eq}_L{level}.{tag}.err")
    e = dict(os.environ)
    e.update(env or {})
    with open(outp, "w") as fo, open(errp, "w") as fe:
        p = subprocess.Popen(["nice", "-n", "10", binary, cfg, par, *extra_args], stdout=fo, stderr=fe, env=e)
        _, status, ru = os.wait4(p.pid, 0)
    rc = os.waitstatus_to_exitcode(status)
    lines = sorted(l for l in open(outp) if l.strip())
    sha = hashlib.sha256("".join(lines).encode()).hexdigest()
    err = open(errp).read()
    return dict(eq=eq, tag=tag, rc=rc, cpu=ru.ru_utime + ru.ru_stime, n=len(lines), sha=sha, err=err.strip().splitlines()[-3:])


if __name__ == "__main__":
    binary, tag = sys.argv[1], sys.argv[2]
    for eq in sys.argv[3:]:
        print(json.dumps(run(binary, eq, tag)))
