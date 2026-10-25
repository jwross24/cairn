import sys
d = sys.argv[1]
r = sorted(open(f"{d}.ref.out").read().splitlines())
for m in ("mutw", "mut6"):
    x = sorted(open(f"{d}.{m}.out").read().splitlines())
    sr, sx = set(r), set(x)
    print(m, "ref_lines", len(r), "mut_lines", len(x), "missing", len(sr - sx), "extra", len(sx - sr))
    for l in sorted(sr - sx)[:1]: print("  first missing:", l)
    for l in sorted(sx - sr)[:1]: print("  first extra:", l)
