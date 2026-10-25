import json, os, resource, subprocess, sys

C = "/private/tmp/claude-501/-Users-jwross-Documents-cairn/ec9f8f52-ce29-4a5c-9caf-2ecbd434509f/scratchpad/h12"
P = "/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt"
BINS = {"join24": f"{P}/join24swap/lvlN", "blind": f"{P}/codex-blind-lane2/lvl24_blind"}
OUT = sys.argv[1]


def cpu(binary, cfg, par):
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    with open(os.devnull, "w") as dn:
        rc = subprocess.run(["nice", "-n", "10", binary, cfg, par], stdout=dn, stderr=dn).returncode
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    return rc, (after.ru_utime - before.ru_utime) + (after.ru_stime - before.ru_stime), after.ru_maxrss


eqs = [d for d in sorted(os.listdir(C)) if os.path.exists(f"{C}/{d}/cfgL24.txt") and os.path.getsize(f"{C}/{d}/parents24.txt") > 0]
assert len(eqs) == 228
with open(OUT, "w") as f:
    for i, d in enumerate(eqs):
        cfg, par = f"{C}/{d}/cfgL24.txt", f"{C}/{d}/parents24.txt"
        order = ["join24", "blind"] if i % 2 == 0 else ["blind", "join24"]
        row = {"eq": d}
        for name in order:
            rc, t, _ = cpu(BINS[name], cfg, par)
            row[name] = {"rc": rc, "cpu": round(t, 4)}
        f.write(json.dumps(row) + "\n")
        f.flush()
