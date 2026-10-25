import json, os, sys, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import runbin
import eval as ev

HERE = runbin.HERE
BIN = os.environ.get("MUTBIN") or os.path.join(HERE, "src", "lane2_mut")
MUTS = {
    "M1": {"JOIN_MUTANT": "3"},
    "M2": {"JOIN_MUTANT": "2"},
    "CMUT": {"LANE2_CMUT": "1"},
    "CMUT2": {"LANE2_CMUT": "2"},
    "AMUT": {"LANE2_AMUT": "4"},
}


def main():
    name, mut = sys.argv[1], sys.argv[2]
    only = sys.argv[3].split(",") if len(sys.argv) > 3 and sys.argv[3] else None
    _, base_env = ev.CONFIGS[name]
    env = dict(base_env); env.update(MUTS[mut])
    outf = os.path.join(HERE, "logs", f"mut_{name}_{mut}.jsonl")
    done = set()
    if os.path.exists(outf) and not only:
        done = {json.loads(l)["eq"] for l in open(outf)}
    eqs = sorted(ev.GATE, key=lambda e: ev.GATE[e]["children"][0])
    if only:
        eqs = [e for e in eqs if e in only]
    for eq in eqs:
        if eq in done or eq not in ev.REF:
            continue
        ref = ev.REF[eq]
        res = runbin.run(BIN, eq, f"mu_{name}_{mut}", env=env)
        sh = ev.sets(eq, f"mu_{name}_{mut}")
        count = sum(ref["sig"].get(k, 0) for k in ("tail-dead", "open", "exact"))
        caught = sh[0] != ref["sha"] or res["rc"] != ref["rc"]
        rec = dict(eq=eq, name=name, mut=mut, count=count, outputs=ref["n"], caught=bool(caught), cpu=res["cpu"])
        if not caught and ref["n"] > 0 and mut in ("M2", "M1"):
            rec["forced"] = {}
            for fs in range(5):
                e2 = dict(env); e2["JOIN_FORCE_SET"] = str(fs)
                r2 = runbin.run(BIN, eq, f"mu_{name}_{mut}_f{fs}", env=e2)
                s2 = ev.sets(eq, f"mu_{name}_{mut}_f{fs}")
                rec["forced"][fs] = bool(s2[0] != ref["sha"] or r2["rc"] != ref["rc"])
        with open(outf, "a") as f:
            f.write(json.dumps(rec) + "\n")
    print("done", name, mut)


if __name__ == "__main__":
    main()
