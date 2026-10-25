import sys
meta = [l.split() for l in open(sys.argv[1])]
res = [l.rstrip("\n") for l in open(sys.argv[2])]
assert len(meta) == len(res), (len(meta), len(res))
tot = 0; kept = 0; lost = []; deadc = 0; nolinec = 0
by_rank = {}
for m, r in zip(meta, res):
    a = int(m[0]); tot += 1
    segs = r.split(" | ")
    rk = int(segs[0].split()[1])
    if "dead" in segs[0]:
        deadc += 1; lost.append((m, r[:80])); continue
    found = None
    for s in segs[1:]:
        f = s.split()
        if int(f[0]) == a:
            found = (int(f[1]), int(f[2]))
    if found is None:
        nolinec += 1; lost.append((m, "no line for a")); continue
    ok = found[0] == 1 and found[1] == 1
    st = by_rank.setdefault(rk, [0, 0])
    st[0] += 1
    if ok:
        kept += 1; st[1] += 1
    else:
        lost.append((m, "keep=%d open=%d rank=%d" % (found[0], found[1], rk)))
print("items", tot, "kept(keep=1 and open=1 at the recorded a)", kept, "lost", len(lost), "dead", deadc, "no a-line", nolinec)
print("by rank (items, kept):", by_rank)
for x in lost[:8]:
    print("LOST", x)
