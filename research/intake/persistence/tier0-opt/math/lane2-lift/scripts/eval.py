import json, os, sys, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import runbin

HERE = runbin.HERE
J24 = os.path.join(HERE, "..", "..", "join24swap", "lvlN")
CONFIGS = {
    "J24": (J24, {}),
    "L0": ("src/lane2", {"LANE2_E0": "0"}),
    "E0": ("src/lane2", {"LANE2_E0": "3"}),
    "A": ("src/lane2", {"LANE2_E0": "0", "LANE2_A": "3"}),
    "A_E0": ("src/lane2", {"LANE2_E0": "3", "LANE2_A": "3"}),
    "C": ("src/lane2", {"LANE2_E0": "0", "LANE2_C": "1"}),
    "C_E0": ("src/lane2", {"LANE2_E0": "3", "LANE2_C": "1"}),
    "E": ("src/lane2", {"LANE2_E0": "0", "LANE2_E": "1"}),
    "E_E0": ("src/lane2", {"LANE2_E0": "3", "LANE2_E": "1"}),
    "COMBO": ("src/lane2", {"LANE2_E0": "3", "LANE2_A": "3", "LANE2_C": "1"}),
    "BEST": ("src/lane2", {"LANE2_E0": "3", "LANE2_A": "3", "LANE2_C": "1", "LANE2_WCAND": "40"}),
    "BEST_E": ("src/lane2", {"LANE2_E0": "3", "LANE2_A": "3", "LANE2_C": "1", "LANE2_WCAND": "40", "LANE2_E": "1"}),
    "B0": ("src/lane2_mut", {"LANE2_E0": "0", "JOIN_FORCE_SET": "0"}),
    "B1": ("src/lane2_mut", {"LANE2_E0": "0", "JOIN_FORCE_SET": "1"}),
    "B2": ("src/lane2_mut", {"LANE2_E0": "0", "JOIN_FORCE_SET": "2"}),
    "B3": ("src/lane2_mut", {"LANE2_E0": "0", "JOIN_FORCE_SET": "3"}),
    "B4": ("src/lane2_mut", {"LANE2_E0": "0", "JOIN_FORCE_SET": "4"}),
    "DH": ("src/lane2_new", {"LANE2_E0": "3", "LANE2_A": "3", "LANE2_WCAND": "40", "LANE2_DH_T": "600"}),
    "DH0": ("src/lane2_new", {"LANE2_E0": "3", "LANE2_A": "3", "LANE2_WCAND": "40"}),
    "LA": ("src/lane2_new", {"LANE2_E0": "3", "LANE2_E": "2"}),
    "LA_A": ("src/lane2_new", {"LANE2_E0": "3", "LANE2_E": "2", "LANE2_A": "3"}),
    "COMBO_E": ("src/lane2", {"LANE2_E0": "3", "LANE2_A": "3", "LANE2_C": "1", "LANE2_E": "1"}),
}
refp = os.path.join(HERE, "logs", "ref228.jsonl")
REF = {json.loads(l)["eq"]: json.loads(l) for l in open(refp)}
GATE = {}
for l in open(os.path.join(HERE, "..", "..", "join24swap", "gate.jsonl")):
    r = json.loads(l)
    if r["phase"] == "diff" and r["level"] == "24":
        GATE[r["eq"]] = r


def sets(eq, tag):
    outp = os.path.join(runbin.OUT, f"{eq}_L24.{tag}.out")
    lines = sorted(l for l in open(outp) if l.strip())
    h = lambda ls: hashlib.sha256("".join(ls).encode()).hexdigest()
    return h(lines), h([l for l in lines if l.startswith("OPEN")]), h([l for l in lines if l.startswith("EXACT")])


def main():
    name = sys.argv[1]
    only = sys.argv[2].split(",") if len(sys.argv) > 2 and sys.argv[2] else None
    reps = int(os.environ.get("REPS", "1"))
    binary, env = CONFIGS[name]
    binary = binary if os.path.isabs(binary) else os.path.join(HERE, binary)
    outf = os.path.join(HERE, "logs", f"eval_{name}.jsonl")
    done = set()
    if os.path.exists(outf) and not only:
        done = {json.loads(l)["eq"] for l in open(outf)}
    eqs = sorted(GATE, key=lambda e: GATE[e]["children"][0])
    if only:
        eqs = [e for e in eqs if e in only]
        outf = os.path.join(HERE, "logs", f"evalsub_{name}.jsonl")
    for eq in eqs:
        if eq in done:
            continue
        if eq not in REF:
            continue
        cpus = []
        for r_ in range(reps):
            res = runbin.run(binary, eq, "ev_" + name, env=env)
            cpus.append(res["cpu"])
        sh = sets(eq, "ev_" + name)
        ref = REF[eq]
        same = (sh[0] == ref["sha"]) and res["rc"] == ref["rc"]
        err = open(os.path.join(runbin.OUT, f"{eq}_L24.ev_{name}.err")).read().splitlines()
        summ = [l for l in err if l.startswith("parents ")][-1].split()
        sig = {summ[i]: int(summ[i + 1]) for i in range(0, len(summ), 2)}
        sig_ok = all(sig.get(k) == ref["sig"].get(k) for k in ("children", "open", "exact"))
        td_ok = sig.get("tail-dead") == ref["sig"].get("tail-dead")
        rec = dict(eq=eq, name=name, A=GATE[eq]["A"], children=GATE[eq]["children"][0], cpu=min(cpus), cpus=cpus, rc=res["rc"], identical=bool(same and sig_ok), tail_dead_equal=bool(td_ok), n=res["n"], count=sum(ref["sig"].get(k, 0) for k in ("tail-dead", "open", "exact")), sha=sh[0])
        with open(outf, "a") as f:
            f.write(json.dumps(rec) + "\n")
    print("done", name)


if __name__ == "__main__":
    main()
