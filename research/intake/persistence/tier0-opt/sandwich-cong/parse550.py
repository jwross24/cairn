import os, re, glob, json, sys
B = "/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/"
HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
RR = B + "tierc-r2bill/runs/"


def parse_file(f):
    t = open(f).read()
    r = {}
    m = re.search(r"REPFILE y=(\d+) a=(\d+) b=(\d+) c=(\d+) k=(\d+) nu=(\d+)", t)
    if m:
        r.update(y=int(m.group(1)), a=int(m.group(2)), k=int(m.group(5)), nu=int(m.group(6)))
    m = re.search(r"rep0: wrap=(\d+) words=(\d+) \(notappl=(\d+) taubad=(\d+)\) T=(\d+) units=(\d+) space=(\S+) \|G\|=(\d+) shadow=(\d+) compat\(word,child\)=(\d+) notshadow_compat=(\d+) passchain=(\d+) windows=(\d+) alive=(\d+) wordsalive=(\d+) notshadow_alive=(\d+)", t)
    if m:
        keys = "wrap words notappl taubad T units space G shadow compat nscompat passchain windows alive wordsalive nsalive".split()
        for k, v in zip(keys, m.groups()):
            r[k] = float(v) if k == "space" else int(v)
    m = re.search(r"^VERDICT (.*?) log10 U''=([\d.]+) \[(\d+)s\]", t, re.M)
    if m:
        r["verdict"] = m.group(1)
        r["logU"] = m.group(2)
    m = re.search(r"min nn=(\d+)\.\.\. \((\d+) digits\)", t)
    if m:
        r["nn"] = m.group(1)
        r["nndig"] = int(m.group(2))
    r["budget"] = "BUDGET detail" in t
    return r


def recorded(i):
    pre = {"s": "1", "t": "3"}.get(i[0])
    c = []
    if i[0] == "w":
        c = [RR + "o1_%s_def.txt" % i]
    else:
        c = [RR + "raised%s_%s_def.txt" % (pre, i), RR + "def%s_%s_def.txt" % (pre, i)]
    for f in c:
        if os.path.exists(f):
            r = parse_file(f)
            r["file"] = os.path.basename(f)
            return r
    return None


if __name__ == "__main__":
    ids = []
    RB = B + "tierc-r2bill/data/"
    for f in ("ids_all.txt", "ids_b3.txt", "ids_o1.txt"):
        ids += [l.strip() for l in open(RB + f) if l.strip()]
    ids = sorted(set(ids))
    out = {}
    for i in ids:
        out[i] = recorded(i)
    json.dump(out, open(HERE + "recorded550.json", "w"))
    import collections
    print(len(out), sum(1 for v in out.values() if v is None), collections.Counter(v.get("verdict", "?").split()[0] if v else None for v in out.values()))
