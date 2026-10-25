import re, sys

def norm(p):
    out = []
    for ln in open(p):
        ln = re.sub(r"\[\d+s\]", "[T]", ln.rstrip("\n"))
        out.append(ln)
    return out

a = norm(sys.argv[1])
b = norm(sys.argv[2])
ra = [l for l in a if l.startswith("rep0:") or l.startswith("min nn") or l.startswith("VERDICT")]
rb = [l for l in b if l.startswith("rep0:") or l.startswith("min nn") or l.startswith("VERDICT")]
rb = [l.replace("rep0: wrap=0 ", "rep0: ") for l in rb]
print("lines", len(ra), len(rb), "equal", ra == rb)
sys.exit(0 if ra == rb and len(ra) == 3 else 1)
