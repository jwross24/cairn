import re, json, random, sys

def tm(errp):
    t = open(errp).read()
    m = re.search(r"([\d.]+) real\s+([\d.]+) user\s+([\d.]+) sys", t)
    r = re.search(r"(\d+)\s+maximum resident", t)
    return float(m.group(1)), float(m.group(2)) + float(m.group(3)), int(r.group(1)) / 1e6

def verdict(txtp):
    t = open(txtp).read()
    v = re.search(r"^VERDICT (.*)$", t, re.M).group(1)
    sp = re.search(r"space=([\d.e+]+)", t)
    wd = re.search(r"words=(\d+)", t)
    return v, sp.group(1) if sp else "-", wd.group(1) if wd else "-"

def label(v):
    if v.startswith("CLOSED-cut"):
        return "closed by the cut"
    if v.startswith("CLOSED-sandwich"):
        b = re.search(r"10\^302|10\^\(10\^([\d.]+)", v)
        return "closed by the sandwich (U'')"
    if v.startswith("BUDGET"):
        return "budget"
    if v.startswith("NOTAPPL"):
        return "NOTAPPL"
    return "open"

rows = []
spec = json.load(open(sys.argv[1]))
for name, txt, err in spec:
    v, sp, wd = verdict(txt)
    w, c, rss = tm(err)
    b = re.search(r"bound 10\^\(10\^([\d.]+) log10 U''=([\d.]+)", v)
    print("%s | %s | bound 10^%s digits vs U'' 10^%s | words %s | space %s | wall %.2f s | cpu %.2f s | rss %.0f MB" % (name, label(v), b.group(1) if b else "-", b.group(2) if b else "-", wd, sp, w, c, rss))
