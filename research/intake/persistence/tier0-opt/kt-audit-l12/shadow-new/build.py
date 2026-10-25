import sys, json, glob, os, collections

P = "/Users/jwross/Documents/cairn/research/intake/persistence"
SH = P + "/tier0-opt/cport-shadow"
RERUN = P + "/tier0-opt/kt-audit-l12/rerun/out"
TIER0 = P + "/tier0"
HERE = P + "/tier0-opt/kt-audit-l12/shadow-new"


def mstr(M):
    return "".join(str(int(d)) for d in M)


def tier0_entries(path):
    for line in open(path):
        r = json.loads(line)
        if "eqs" not in r:
            continue
        for eq in r["eqs"]:
            if isinstance(eq, dict):
                for e in eq.get("exceptional", []):
                    if len(e) == 3:
                        yield str(r["s"]), mstr(eq["M"]), e[0], e[1]
                    else:
                        yield str(r["s"]), mstr(eq["M"]), e[1], e[4][0]
        for e in r.get("exceptional", []):
            M, a, nu, eps, (y, sol) = e
            yield str(r["s"]), mstr(M), a, y


def keyline(k):
    s, M, a, y = k
    return f"{s} {M} {a} {y} - -"


def write_cases(prefix, keys):
    with open(prefix + "_cases.txt", "x") as f:
        for k in keys:
            f.write(keyline(k) + "\n")
    with open(prefix + "_only.txt", "x") as f:
        for k in keys:
            f.write(" ".join(str(x) for x in k) + "\n")


def load_verdicts_1335():
    out = {}
    rows = open(SH + "/VERDICTS_1335.tsv").read().split("\n")[1:]
    for l in rows:
        if not l:
            continue
        c = l.split("\t")
        s, M, a, y = c[0].split()[:4]
        out[(s, M, int(a), int(y))] = (c[6], c[7])
    return out


def control(vertices, prefix):
    ref = load_verdicts_1335()
    cases1335 = set(open(SH + "/data/cases_1335.txt").read().split("\n"))
    raw = collections.Counter()
    for fn in ("trees_mac.jsonl", "trees_c.jsonl", "runall_final.jsonl"):
        for s, M, a, y in tier0_entries(TIER0 + "/" + fn):
            if isinstance(y, str) or s not in vertices:
                continue
            raw[(s, M, a, y)] += 1
    keys = sorted(raw)
    inref = [k for k in keys if k in ref]
    line_match = sum(1 for k in keys if keyline(k) in cases1335)
    print("raw", sum(raw.values()), "distinct", len(keys), "in_VERDICTS_1335", len(inref), "line_in_cases_1335", line_match)
    per = collections.defaultdict(lambda: [0, 0, 0])
    for k, n in raw.items():
        per[k[0]][0] += n
        per[k[0]][1] += 1
        per[k[0]][2] += k in ref
    for s in sorted(per):
        print("vertex", s, "raw", per[s][0], "distinct", per[s][1], "in_ref", per[s][2])
    write_cases(prefix, keys)
    with open(prefix + "_ref.tsv", "x") as f:
        for k in inref:
            f.write(" ".join(str(x) for x in k) + "\t" + "\t".join(ref[k]) + "\n")


def new(prefix, done_files):
    done = set()
    for fn in done_files:
        for l in open(fn):
            c = l.rstrip("\n").split("\t")
            if c and c[0] and not c[0].startswith("pattern"):
                p = c[0].split()
                done.add((p[0], p[1], int(p[2]), int(p[3])))
    raw = collections.Counter()
    per = {}
    skipped_eq = []
    for fn in sorted(glob.glob(RERUN + "/eq_ex_*.json")):
        d = json.load(open(fn))
        n = collections.Counter((e[0], e[1], bool(e[2])) for e in d["exceptional_new"])
        r = collections.Counter((e[0], e[1], bool(e[2])) for e in d["exceptional_recorded"])
        diff = n - r
        s, M = str(d["s"]), mstr(d["M"])
        for (a, y, ok), c in diff.items():
            raw[(s, M, a, y, ok)] += c
        pv = per.setdefault(s, [0, set()])
        pv[0] += sum(diff.values())
    keys = []
    flagged = []
    strs = []
    for (s, M, a, y, ok), c in raw.items():
        if ok:
            flagged.append((s, M, a, y))
            continue
        if isinstance(y, str):
            strs.append((s, M, a, y))
            continue
        per[s][1].add((s, M, a, y))
        if (s, M, a, y) not in done:
            keys.append((s, M, a, y))
    keys.sort()
    print("raw_new_only", sum(raw.values()), "distinct", sum(len(v[1]) for v in per.values()), "to_run", len(keys), "flagged_solution", len(flagged), "string_y", len(strs))
    for s in sorted(per):
        print("vertex", s, "raw", per[s][0], "distinct", len(per[s][1]))
    if keys:
        write_cases(prefix, keys)
    json.dump({s: [v[0], len(v[1])] for s, v in per.items()}, open(prefix + "_counts.json", "x"))


if __name__ == "__main__":
    if sys.argv[1] == "control":
        control(set(sys.argv[3].split(",")), sys.argv[2])
    else:
        new(sys.argv[2], sys.argv[3:])
