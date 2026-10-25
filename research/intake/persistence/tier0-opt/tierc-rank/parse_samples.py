import sys, json

src, out = sys.argv[1], sys.argv[2]
rows = []
head = None
with open(src) as f, open(out, "w") as g:
    for ln in f:
        ln = ln.strip()
        if ln.startswith("["):
            words = json.loads(ln)
            if head is None:
                continue
            y, k, nu, tot = head
            g.write(json.dumps({"y": y, "k": k, "nu": nu, "total": tot, "words": words}) + "\n")
        elif ln == "NOV":
            head = None
        else:
            t = ln.split()
            head = (int(t[0]), int(t[1]), int(t[2]), int(t[4]))
