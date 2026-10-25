import json, os, sys, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import runbin

HERE = runbin.HERE
GATE = os.path.join(HERE, "..", "..", "join24swap", "gate.jsonl")
rows = {}
for l in open(GATE):
    r = json.loads(l)
    if r["phase"] == "diff" and r["level"] == "24":
        rows[r["eq"]] = r


def parse_err(err_lines):
    sig = None
    for l in err_lines:
        if l.startswith("parents "):
            t = l.split()
            sig = {t[i]: int(t[i + 1]) for i in range(0, len(t), 2) if t[i + 1].lstrip("-").isdigit()}
    return sig


def main():
    binary, tag, outf = sys.argv[1], sys.argv[2], sys.argv[3]
    order = os.environ.get("ORDER", "asc")
    only = [e for e in os.environ.get("ONLY", "").split(",") if e]
    env = {}
    for kv in os.environ.get("VARENV", "").split(","):
        if "=" in kv:
            k, v = kv.split("=", 1)
            env[k] = v
    eqs = sorted(rows, key=lambda e: rows[e]["children"][0], reverse=(order == "desc"))
    if only:
        eqs = [e for e in eqs if e in only]
    done = set()
    path = os.path.join(HERE, "logs", outf)
    if os.path.exists(path):
        done = {json.loads(l)["eq"] for l in open(path)}
    for eq in eqs:
        if eq in done:
            continue
        res = runbin.run(binary if os.path.isabs(binary) else os.path.join(HERE, binary), eq, tag, env=env)
        errp = os.path.join(runbin.OUT, f"{eq}_L24.{tag}.err")
        sig = parse_err(open(errp).read().splitlines())
        outp = os.path.join(runbin.OUT, f"{eq}_L24.{tag}.out")
        lines = sorted(l for l in open(outp) if l.strip())
        open_sha = hashlib.sha256("".join(l for l in lines if l.startswith("OPEN")).encode()).hexdigest()
        exact_sha = hashlib.sha256("".join(l for l in lines if l.startswith("EXACT")).encode()).hexdigest()
        rec = dict(eq=eq, tag=tag, rc=res["rc"], cpu=res["cpu"], n=res["n"], sha=res["sha"], open_sha=open_sha, exact_sha=exact_sha, sig=sig)
        with open(path, "a") as f:
            f.write(json.dumps(rec) + "\n")
    print("done", tag)


if __name__ == "__main__":
    main()
